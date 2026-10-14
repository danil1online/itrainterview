from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from app.api._common import get_task_or_404
from app.db import get_db
from app.deps import get_current_user
from app.models import RunLog, Submission, Task, User
from app.schemas import RunRequest, RunResponse, SubmissionOut, SubmitRequest
from app.services.grading import (
    create_submission,
    outcome_to_dict,
    run_tests,
)
from app.services.llm_queue import submit_job
from app.services.sandbox import SandboxError

router = APIRouter(prefix="/api", tags=["runs"])


def _sample_tests(task: Task) -> list[dict]:
    samples = [t for t in task.tests if t.get("sample")]
    return samples or task.tests[:1]


def _save_run_log(db: Session, user: User, task: Task, language: str, outcome_dict: dict) -> None:
    """Сохраняем (обновляем) последний запуск — контекст для ИИ-помощника."""
    results = [
        {
            "name": r.get("name"),
            "passed": r.get("passed"),
            "status": r.get("status"),
            "got_stdout": (r.get("got_stdout") or "")[:500],
            "stderr": (r.get("stderr") or "")[:800],
        }
        for r in outcome_dict.get("results", [])
    ]
    row = db.scalar(
        select(RunLog).where(RunLog.user_id == user.id, RunLog.task_id == task.id)
    )
    if row is None:
        db.add(
            RunLog(
                user_id=user.id,
                task_id=task.id,
                language=language,
                status=outcome_dict.get("status", "internal_error"),
                passed_count=outcome_dict.get("passed_count", 0),
                total_count=outcome_dict.get("total_count", 0),
                results=results,
            )
        )
    else:
        row.language = language
        row.status = outcome_dict.get("status", "internal_error")
        row.passed_count = outcome_dict.get("passed_count", 0)
        row.total_count = outcome_dict.get("total_count", 0)
        row.results = results
    db.commit()


@router.post("/tasks/{slug}/run", response_model=RunResponse)
async def run_code(
    slug: str,
    payload: RunRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    task = get_task_or_404(db, slug)
    try:
        outcome = await run_in_threadpool(
            run_tests, db, payload.language, payload.code, _sample_tests(task)
        )
    except SandboxError as e:
        raise HTTPException(503, str(e))
    out = outcome_to_dict(outcome)
    _save_run_log(db, user, task, payload.language, out)
    return RunResponse(**out)


@router.post("/tasks/{slug}/submit", response_model=SubmissionOut)
async def submit_code(
    slug: str,
    payload: SubmitRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    task = get_task_or_404(db, slug)
    try:
        outcome = await run_in_threadpool(
            run_tests, db, payload.language, payload.code, task.tests
        )
    except SandboxError as e:
        raise HTTPException(503, str(e))
    sub = create_submission(db, user, task, payload.language, payload.code, outcome)
    feedback_job_id = None
    if payload.want_feedback and outcome.status != "accepted":
        # разбор не блокирует ответ: сабмит уходит сразу, фидбек догонит job'ом
        job = submit_job(db, user.id, "submission_feedback", meta={"submission_id": sub.id})
        feedback_job_id = job.id
    db.refresh(sub)
    _save_run_log(db, user, task, payload.language, outcome_to_dict(outcome))
    out = SubmissionOut.model_validate(sub)
    out.task_slug = task.slug
    out.feedback_job_id = feedback_job_id
    return out


@router.get("/submissions", response_model=list[SubmissionOut])
def my_submissions(
    task_slug: str | None = None,
    limit: int = 50,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    stmt = select(Submission).where(Submission.user_id == user.id)
    if task_slug:
        task = get_task_or_404(db, task_slug, active_only=False)
        stmt = stmt.where(Submission.task_id == task.id)
    rows = db.scalars(
        stmt.order_by(Submission.created_at.desc()).limit(min(limit, 200))
    ).all()
    slugs = {t.id: t.slug for t in db.scalars(select(Task).where(Task.id.in_([r.task_id for r in rows]))).all()} if rows else {}
    out = []
    for r in rows:
        item = SubmissionOut.model_validate(r)
        item.task_slug = slugs.get(r.task_id)
        out.append(item)
    return out


@router.get("/submissions/{submission_id}", response_model=SubmissionOut)
def get_submission(
    submission_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    sub = db.get(Submission, submission_id)
    if sub is None or (sub.user_id != user.id and user.role != "admin"):
        raise HTTPException(404, "Отправка не найдена")
    task = db.get(Task, sub.task_id)
    out = SubmissionOut.model_validate(sub)
    out.task_slug = task.slug if task else None
    return out


@router.post("/submissions/{submission_id}/feedback")
async def regenerate_feedback(
    submission_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    sub = db.get(Submission, submission_id)
    if sub is None or (sub.user_id != user.id and user.role != "admin"):
        raise HTTPException(404, "Отправка не найдена")
    job = submit_job(db, user.id, "submission_feedback", meta={"submission_id": sub.id})
    return {"job_id": job.id}
