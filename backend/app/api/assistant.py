"""ИИ-помощник по задаче /api/assistant: чат через LLM-очередь и история диалога."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api._common import get_task_or_404
from app.db import get_db
from app.deps import get_current_user
from app.models import ChatMessage, RunLog, User
from app.schemas import ChatHistoryItem, ChatRequest
from app.services.assistant import build_chat_messages
from app.services.llm_queue import submit_job

router = APIRouter(prefix="/api/assistant", tags=["assistant"])


def _last_run_summary(db: Session, user: User, task_id: int) -> str | None:
    """Результат последнего запуска (run или submit) со stderr — для контекста ИИ."""
    log = db.scalar(
        select(RunLog)
        .where(RunLog.user_id == user.id, RunLog.task_id == task_id)
        .order_by(RunLog.created_at.desc())
        .limit(1)
    )
    if log is None:
        return None
    lines = [
        f"Последний запуск: язык={log.language}, статус={log.status}, "
        f"пройдено {log.passed_count} из {log.total_count}."
    ]
    for r in (log.results or []):
        if r.get("passed"):
            continue
        stderr = (r.get("stderr") or "").strip()
        got = (r.get("got_stdout") or "").strip()
        detail = f"Тест {r.get('name')} ({r.get('status')}):"
        if stderr:
            detail += f"\n  stderr:\n{stderr[:800]}"
        elif got:
            detail += f"\n  фактический вывод (неверный):\n{got[:400]}"
        lines.append(detail)
    return "\n".join(lines)


@router.post("/chat")
async def chat(
    payload: ChatRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Сохраняет последнее сообщение студента в историю и ставит job 'assistant_chat'; ответ придёт асинхронно по job_id. 404 — нет задачи."""
    task = get_task_or_404(db, payload.task_slug)
    history = [{"role": m.role, "content": m.content} for m in payload.messages]
    messages = build_chat_messages(
        task,
        history,
        payload.code,
        payload.language,
        payload.mode,
        _last_run_summary(db, user, task.id),
    )
    last_user = payload.messages[-1]
    if last_user.role == "user":
        db.add(ChatMessage(user_id=user.id, task_id=task.id, role="user", content=last_user.content))
    db.commit()
    job = submit_job(
        db, user.id, "assistant_chat", messages=messages, temperature=0.5, max_tokens=900,
        meta={"task_slug": task.slug},
    )
    return {"job_id": job.id}


@router.get("/history", response_model=list[ChatHistoryItem])
def history(
    task_slug: str,
    limit: int = 40,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """История диалога по задаче в хронологическом порядке (limit 1..100); 404 — нет задачи."""
    task = get_task_or_404(db, task_slug, active_only=False)
    rows = db.scalars(
        select(ChatMessage)
        .where(ChatMessage.user_id == user.id, ChatMessage.task_id == task.id)
        .order_by(ChatMessage.created_at.desc())
        .limit(max(1, min(limit, 100)))
    ).all()
    return list(reversed(rows))
