"""Вспомогательные функции API-слоя: поиск задачи по slug, решённые задачи, легенда с ИИ-вариантом."""

from fastapi import HTTPException
from sqlalchemy import distinct, select
from sqlalchemy.orm import Session

from app.models import Submission, Task, TaskVariant, User


def get_task_or_404(db: Session, slug: str, active_only: bool = True) -> Task:
    """Задача по slug; 404 если её нет или она неактивна (active_only=True)."""
    task = db.scalar(select(Task).where(Task.slug == slug))
    if task is None or (active_only and not task.is_active):
        raise HTTPException(404, "Задача не найдена")
    return task


def solved_task_ids(db: Session, user: User) -> set[int]:
    """Множество id задач, по которым у пользователя есть хотя бы один accepted-сабмит."""
    rows = db.scalars(
        select(distinct(Submission.task_id)).where(
            Submission.user_id == user.id, Submission.status == "accepted"
        )
    )
    return set(rows)


def effective_legend(db: Session, user: User, task: Task) -> tuple[str, str]:
    """Легенда задачи с учётом сохранённого ИИ-варианта студента."""
    variant = db.scalar(
        select(TaskVariant).where(
            TaskVariant.user_id == user.id, TaskVariant.task_id == task.id
        )
    )
    if variant:
        return variant.title, variant.legend
    return task.title, task.legend
