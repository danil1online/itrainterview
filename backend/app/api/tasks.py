from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api._common import effective_legend, get_task_or_404, solved_task_ids
from app.db import get_db
from app.deps import get_current_user
from app.models import Task, User
from app.schemas import GenerateSetRequest, RetitleRequest, TaskListItem, TaskOut, TestOut
from app.services.llm_queue import submit_job

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


@router.get("", response_model=list[TaskListItem])
def list_tasks(
    pattern: str | None = None,
    level: str | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    stmt = select(Task).where(Task.is_active.is_(True))
    if pattern:
        stmt = stmt.where(Task.pattern == pattern)
    if level:
        stmt = stmt.where(Task.level == level)
    tasks = db.scalars(stmt.order_by(Task.level, Task.slug)).all()
    solved = solved_task_ids(db, user)
    return [
        TaskListItem(
            slug=t.slug, title=t.title, pattern=t.pattern, level=t.level,
            solved=t.id in solved,
        )
        for t in tasks
    ]


@router.get("/{slug}", response_model=TaskOut)
def get_task(
    slug: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    task = get_task_or_404(db, slug)
    title, legend = effective_legend(db, user, task)
    sample_tests = [TestOut(**t) for t in task.tests if t.get("sample")]
    return TaskOut(
        slug=task.slug,
        title=title,
        legend=legend,
        pattern=task.pattern,
        level=task.level,
        hints=task.hints or [],
        tests=sample_tests,
        solved=(task.id in solved_task_ids(db, user)),
    )


@router.post("/{slug}/retitle")
async def retitle_task(
    slug: str,
    payload: RetitleRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    task = get_task_or_404(db, slug)
    job = submit_job(
        db, user.id, "retitle",
        meta={"task_id": task.id, "theme": payload.theme, "target": "variant" if payload.save else None},
    )
    return {"job_id": job.id}


@router.post("/generate-set")
async def generate_set(
    payload: GenerateSetRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Персональный комплект: по одному job'у на задачу — очередь остаётся справедливой."""
    slugs = payload.slugs or [t.slug for t in db.scalars(select(Task).order_by(Task.id)).all()]
    if not slugs:
        raise HTTPException(422, "Нет задач для генерации")
    existing = {t.slug for t in db.scalars(select(Task).where(Task.slug.in_(slugs))).all()}
    unknown = [s for s in slugs if s not in existing]
    if unknown:
        raise HTTPException(422, f"Неизвестные задачи: {', '.join(unknown[:5])}")
    job_ids = []
    for slug in slugs:
        job = submit_job(db, user.id, "generate_set", meta={"task_slug": slug, "theme": payload.theme})
        job_ids.append(job.id)
    return {"job_ids": job_ids}
