"""HTTP-обёртка LLM-очереди: отправка job'а, поллинг статуса/позиции, отмена."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user
from app.models import LLMJob, User
from app.schemas import LLMJobOut, LLMJobSubmit
from app.services.llm_queue import queue_position, submit_job

router = APIRouter(prefix="/api/llm/jobs", tags=["llm-jobs"])


def _get_own(db: Session, user: User, job_id: int) -> LLMJob:
    job = db.get(LLMJob, job_id)
    if job is None or job.user_id != user.id:
        raise HTTPException(404, "Задача не найдена")
    return job


def _out(db: Session, job: LLMJob) -> LLMJobOut:
    return LLMJobOut(
        id=job.id,
        kind=job.kind,
        status=job.status,
        position=(queue_position(db, job) if job.status in ("pending", "running") else 0),
        result=job.result,
        error=job.error,
    )


@router.post("", response_model=LLMJobOut, status_code=202)
def create_job(
    payload: LLMJobSubmit,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    try:
        job = submit_job(
            db,
            user.id,
            payload.kind,
            messages=payload.messages,
            temperature=payload.temperature,
            max_tokens=payload.max_tokens,
            meta=payload.meta,
        )
    except ValueError as e:
        raise HTTPException(422, str(e)) from e
    return _out(db, job)


@router.get("/{job_id}", response_model=LLMJobOut)
def get_job(job_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return _out(db, _get_own(db, user, job_id))


@router.get("", response_model=list[LLMJobOut])
def get_jobs(ids: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Пакетный статус (для «нового комплекта» — десятки job'ов)."""
    try:
        id_list = [int(x) for x in ids.split(",") if x.strip()]
    except ValueError:
        raise HTTPException(422, "ids: список чисел через запятую")
    if not id_list or len(id_list) > 200:
        raise HTTPException(422, "ids: от 1 до 200")
    rows = db.scalars(select(LLMJob).where(LLMJob.id.in_(id_list), LLMJob.user_id == user.id)).all()
    by_id = {r.id: r for r in rows}
    return [_out(db, by_id[i]) for i in id_list if i in by_id]


@router.delete("/{job_id}")
def cancel_job(job_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    job = _get_own(db, user, job_id)
    if job.status != "pending":
        raise HTTPException(409, f"Отменить можно только ожидающую задачу (статус: {job.status})")
    job.status = "cancelled"
    db.commit()
    return {"ok": True}
