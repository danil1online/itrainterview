"""FIFO-очередь задач к LLM на базе БД.

Причины: компактная модель инферит однопоточно, при 25+ студентах параллельные
запросы просто копаются в задержке (и падают по таймауту nginx/HTTP). Здесь:
- job живёт в таблице llm_jobs — переживает рестарт бэкенда;
- воркеры забирают задачи строго по FIFO (created_at, id), FOR UPDATE SKIP LOCKED;
- на сбой модели — ретраи с backoff, «ответ обязательно дойдёт»;
- фронтенд поллит статус/позицию, не держя долгоживущие HTTP-соединения.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Awaitable, Callable

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models import LLMJob, get_setting
from app.services.llm import LLMError

logger = logging.getLogger("llm_queue")

JOB_KINDS = {
    "assistant_chat",
    "recruiter_chat",
    "recommendation",
    "vibe_chat",
    "retitle",
    "generate_set",
    "submission_feedback",
}

MAX_ATTEMPTS = 3
RETRY_BACKOFFS = (5, 15, 45)
JOB_TIMEOUT_SEC = 900.0

# kind -> async (job, db) -> str (текст результата)
JobHandler = Callable[[LLMJob, Session], Awaitable[str]]
HANDLERS: dict[str, JobHandler] = {}


def register_handler(kind: str):
    def deco(fn: JobHandler) -> JobHandler:
        HANDLERS[kind] = fn
        return fn

    return deco


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _max_concurrent(db: Session | None = None) -> int:
    raw = get_setting(db, "llm_max_concurrent", "") if db is not None else ""
    try:
        return max(1, min(32, int(raw)))
    except (TypeError, ValueError):
        return 1


def submit_job(
    db: Session,
    user_id: int | None,
    kind: str,
    *,
    messages: list[dict] | None = None,
    temperature: float = 0.4,
    max_tokens: int = 1200,
    meta: dict | None = None,
) -> LLMJob:
    if kind not in JOB_KINDS:
        raise ValueError(f"Неизвестный kind job'а: {kind}")
    job = LLMJob(
        user_id=user_id,
        kind=kind,
        status="pending",
        payload={
            "messages": messages or [],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "meta": meta or {},
        },
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def queue_position(db: Session, job: LLMJob) -> int:
    """Сколько задач стоит перед данной (0 — следующий по очереди)."""
    if job.status == "running":
        return 0
    return (
        db.scalar(
            select(func.count())
            .select_from(LLMJob)
            .where(
                LLMJob.status == "pending",
                (LLMJob.created_at < job.created_at)
                | ((LLMJob.created_at == job.created_at) & (LLMJob.id < job.id)),
            )
        )
        or 0
    )


async def process_next_job() -> bool:
    """Забрать старейшую pending-задачу и выполнить её (с ретраями). True, если была задача."""
    db = SessionLocal()
    try:
        job = db.scalar(
            select(LLMJob)
            .where(LLMJob.status == "pending")
            .order_by(LLMJob.created_at, LLMJob.id)
            .limit(1)
            .with_for_update(skip_locked=True)
        )
        if job is None:
            return False
        job.status = "running"
        job.started_at = utcnow()
        db.commit()

        handler = HANDLERS.get(job.kind)
        attempts = 0
        while True:
            attempts += 1
            job.attempts = attempts
            db.commit()
            try:
                if handler is None:
                    raise LLMError(f"Нет обработчика для kind={job.kind}")
                result = await handler(job, db)
                job.result = result
                job.status = "done"
                job.finished_at = utcnow()
                db.commit()
                return True
            except LLMError as e:
                if attempts >= MAX_ATTEMPTS:
                    job.status = "error"
                    job.error = str(e)
                    job.finished_at = utcnow()
                    db.commit()
                    logger.warning("llm_job %s (%s) failed after %d attempts: %s", job.id, job.kind, attempts, e)
                    return True
                await asyncio.sleep(RETRY_BACKOFFS[attempts - 1])
    finally:
        db.close()


_workers: list[asyncio.Task] = []


async def _worker_loop() -> None:
    while True:
        try:
            await process_next_job()
        except Exception:
            logger.exception("llm_queue worker error")
        await asyncio.sleep(0.5)


def start_workers() -> None:
    global _workers
    if _workers:
        return
    db = SessionLocal()
    try:
        # crash recovery: после рестарта бэкенда «running»-задачи никто не доведёт — возвращаем в очередь
        stuck = db.scalars(select(LLMJob).where(LLMJob.status == "running")).all()
        for job in stuck:
            job.status = "pending"
            job.started_at = None
        if stuck:
            db.commit()
            logger.info("llm_queue: возвращено в очередь после рестарта: %d", len(stuck))
        n = _max_concurrent(db)
    finally:
        db.close()
    for i in range(n):
        _workers.append(asyncio.create_task(_worker_loop(), name=f"llm-worker-{i}"))
    logger.info("llm_queue: запущено воркеров: %d", n)


def stop_workers() -> None:
    global _workers
    for w in _workers:
        w.cancel()
    _workers = []
