"""Обработчики job'ов LLM-очереди. Каждый хендлер делает свою работу АТОМАРНО
с завершением job'а (сторона эффекты — сохранение в истории/таблицы — здесь,
а не на стороне поллинга)."""

import json

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models import ChatMessage, Task, TaskVariant, Submission, VibeSession
from app.services.assistant import generate_variant
from app.services.grading import generate_submission_feedback
from app.services.llm import LLMError, chat_completion
from app.services.llm_queue import JOB_TIMEOUT_SEC, register_handler


async def _plain_chat(job, db: Session) -> str:
    """chat_completion с параметрами из job.payload и таймаутом JOB_TIMEOUT_SEC."""
    p = job.payload or {}
    return await chat_completion(
        p["messages"],
        db=db,
        temperature=p.get("temperature", 0.4),
        max_tokens=p.get("max_tokens", 1200),
        timeout_sec=JOB_TIMEOUT_SEC,
    )


def _upsert_variant(db: Session, user_id: int, task: Task, variant: dict) -> None:
    """Создаёт или обновляет вариант задачи пользователя; коммитит."""
    row = db.scalar(
        select(TaskVariant).where(TaskVariant.user_id == user_id, TaskVariant.task_id == task.id)
    )
    if row is None:
        db.add(TaskVariant(user_id=user_id, task_id=task.id, title=variant["title"], legend=variant["legend"]))
    else:
        row.title = variant["title"]
        row.legend = variant["legend"]
    db.commit()


@register_handler("assistant_chat")
async def h_assistant_chat(job, db: Session) -> str:
    """Ответ наставника + сохранение в историю чата задачи."""
    reply = await _plain_chat(job, db)
    meta = (job.payload or {}).get("meta", {})
    task = db.scalar(select(Task).where(Task.slug == meta.get("task_slug", ""))) if meta.get("task_slug") else None
    if task is not None:
        db.add(ChatMessage(user_id=job.user_id, task_id=task.id, role="assistant", content=reply))
        db.commit()
    return reply


@register_handler("recruiter_chat")
async def h_recruiter_chat(job, db: Session) -> str:
    """Чат с рекрутером: ответ + сохранение в историю RecruiterMessage."""
    from app.models import RecruiterMessage

    reply = await _plain_chat(job, db)
    db.add(RecruiterMessage(user_id=job.user_id, role="assistant", content=reply))
    db.commit()
    return reply


@register_handler("recommendation")
async def h_recommendation(job, db: Session) -> str:
    """Рекомендация: новый ответ заменяет старую recommendation в истории."""
    from app.models import RecruiterMessage

    reply = await _plain_chat(job, db)
    db.execute(
        delete(RecruiterMessage).where(
            RecruiterMessage.user_id == job.user_id, RecruiterMessage.role == "recommendation"
        )
    )
    db.add(RecruiterMessage(user_id=job.user_id, role="recommendation", content=reply))
    db.commit()
    return reply


def _is_admin(db: Session, user_id: int | None) -> bool:
    """Владелец job'а — администратор (нужно для привилегированных операций)."""
    if user_id is None:
        return False
    from app.models import User

    u = db.get(User, user_id)
    return u is not None and u.role == "admin"


@register_handler("vibe_chat")
async def h_vibe_chat(job, db: Session) -> str:
    """Чат вайб-кодинга: ответ дописывается к сообщениям сессии, prompts_count увеличивается."""
    reply = await _plain_chat(job, db)
    meta = (job.payload or {}).get("meta", {})
    session = db.get(VibeSession, int(meta["session_id"])) if meta.get("session_id") else None
    if session is not None:
        if session.user_id != job.user_id and not _is_admin(db, job.user_id):
            raise LLMError("Сессия принадлежит другому пользователю")
        messages = list(session.messages or [])
        messages.append({"role": "assistant", "content": reply})
        session.messages = messages
        db.commit()
    return reply


@register_handler("retitle")
async def h_retitle(job, db: Session) -> str:
    """Новая легенда. meta: {task_id, theme, target: 'variant'|'task'}."""
    meta = (job.payload or {}).get("meta", {})
    task = db.get(Task, int(meta["task_id"]))
    if task is None:
        raise LLMError("Задача не найдена")
    if meta.get("target") == "task" and not _is_admin(db, job.user_id):
        raise LLMError("Обновлять легенду задачи для всех может только администратор")
    variant = await generate_variant(task, db=db, theme=meta.get("theme"))
    if meta.get("target") == "task":
        task.title = variant["title"]
        task.legend = variant["legend"]
        db.commit()
    elif job.user_id is not None:
        _upsert_variant(db, job.user_id, task, variant)
    return json.dumps(variant, ensure_ascii=False)


@register_handler("generate_set")
async def h_generate_set(job, db: Session) -> str:
    """Легенда одной задачи персонального комплекта. meta: {task_slug, theme}."""
    meta = (job.payload or {}).get("meta", {})
    task = db.scalar(select(Task).where(Task.slug == meta.get("task_slug", "")))
    if task is None:
        raise LLMError("Задача не найдена")
    variant = await generate_variant(task, db=db, theme=meta.get("theme"))
    if job.user_id is not None:
        _upsert_variant(db, job.user_id, task, variant)
    return json.dumps(variant, ensure_ascii=False)


@register_handler("submission_feedback")
async def h_submission_feedback(job, db: Session) -> str:
    """Разбор проваленного сабмита. meta: {submission_id}."""
    meta = (job.payload or {}).get("meta", {})
    sub = db.get(Submission, int(meta["submission_id"]))
    if sub is None:
        raise LLMError("Сабмит не найден")
    if sub.user_id != job.user_id and not _is_admin(db, job.user_id):
        raise LLMError("Сабмит принадлежит другому пользователю")
    task = db.get(Task, sub.task_id)
    if task is None:
        raise LLMError("Задача не найдена")
    await generate_submission_feedback(db, sub, task)
    return sub.ai_feedback or ""
