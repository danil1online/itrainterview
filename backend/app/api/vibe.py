"""Вайб-кодинг: тренажёр работы с ИИ-напарником (чат + редактор + скрытые тесты)."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user
from app.models import User, VibeSession, VibeTask
from app.schemas import (
    VibeChatRequest,
    VibeCodeRequest,
    VibeRunResponse,
    VibeSessionOut,
    VibeTaskListItem,
)
from app.services.llm_queue import submit_job
from app.services.vibe_runner import evaluate, run_assert_cases, run_mutation

router = APIRouter(prefix="/api/vibe", tags=["vibe"])

ASSISTANT_SYSTEM = """Ты — ИИ-напарник по программированию в браузерном тренажёре. Студент решает небольшую задачу (одну-две функции) и общается с тобой.

Правила:
- Отвечай только на то, о чём спросили. Если прислали код и текст ошибки — разбери причину и предложи точечное исправление.
- Код давай в блоках ```python. При исправлении показывай только изменённую функцию или фрагмент, а не весь файл.
- Не выдумывай API: используй только то, что есть в присланном фрагменте, или стандартную библиотеку. Если контекста не хватает — попроси прислать нужный фрагмент кода.
- Помни: у тебя нет доступа к редактору студента. Работает только тот код, который он сам вставил в сообщение.
- Пиши кратко: 2–6 предложений плюс код."""

HISTORY_LIMIT = 10
MSG_TRUNCATE = 1500


def _budgeted(messages: list[dict]) -> list[dict]:
    """История для LLM: последние 10 сообщений, role сводится к user/assistant, контент обрезан до 1500 символов."""
    out = []
    for m in messages[-HISTORY_LIMIT:]:
        role = m.get("role") if m.get("role") in ("user", "assistant") else "user"
        out.append({"role": role, "content": (m.get("content") or "")[:MSG_TRUNCATE]})
    return out


def _session_out(s: VibeSession, t: VibeTask) -> VibeSessionOut:
    """VibeSession + VibeTask -> VibeSessionOut; NULL-поля как пустые списки/словари."""
    return VibeSessionOut(
        id=s.id, task_id=t.id, slug=t.slug, task_type=t.task_type, title=t.title,
        description_md=t.description_md, initial_code=t.initial_code, status=s.status,
        messages=s.messages or [], code=s.code, prompts_count=s.prompts_count,
        run_count=s.run_count, last_run=s.last_run or {}, score=s.score,
    )


def _get_session(db: Session, user: User, session_id: int) -> tuple[VibeSession, VibeTask]:
    """Сессия и её задача; 404 если сессия чужая/не найдена или задача удалена."""
    s = db.get(VibeSession, session_id)
    if s is None or s.user_id != user.id:
        raise HTTPException(404, "Сессия не найдена")
    t = db.get(VibeTask, s.task_id)
    if t is None:
        raise HTTPException(404, "Задача не найдена")
    return s, t


@router.get("/tasks", response_model=list[VibeTaskListItem])
def list_tasks(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Включённые вайб-задачи со статусом и баллом сессии пользователя, если она уже есть."""
    tasks = db.scalars(select(VibeTask).where(VibeTask.enabled).order_by(VibeTask.id)).all()
    sessions = {
        s.task_id: s
        for s in db.scalars(select(VibeSession).where(VibeSession.user_id == user.id)).all()
    }
    return [
        VibeTaskListItem(
            id=t.id, slug=t.slug, task_type=t.task_type, title=t.title,
            status=(sessions[t.id].status if t.id in sessions else None),
            score=(sessions[t.id].score if t.id in sessions else None),
        )
        for t in tasks
    ]


@router.post("/tasks/{task_id}/session", response_model=VibeSessionOut)
def start_session(task_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Создаёт сессию с initial_code (или возвращает существующую); 404 — задача нет или отключена."""
    t = db.get(VibeTask, task_id)
    if t is None or not t.enabled:
        raise HTTPException(404, "Задача не найдена")
    s = db.scalar(
        select(VibeSession).where(VibeSession.user_id == user.id, VibeSession.task_id == task_id)
    )
    if s is None:
        s = VibeSession(user_id=user.id, task_id=task_id, code=t.initial_code)
        db.add(s)
        db.commit()
        db.refresh(s)
    return _session_out(s, t)


@router.get("/sessions/{session_id}", response_model=VibeSessionOut)
def get_session(session_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Текущее состояние сессии: код, история, последний прогон, балл; 404 — чужая или нет."""
    s, t = _get_session(db, user, session_id)
    return _session_out(s, t)


@router.put("/sessions/{session_id}/code")
def save_code(
    session_id: int,
    payload: VibeCodeRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Сохраняет код студента в сессии (commit); 404 — чужая или нет."""
    s, _t = _get_session(db, user, session_id)
    s.code = payload.code
    db.commit()
    return {"ok": True}


@router.post("/sessions/{session_id}/chat")
async def chat(
    session_id: int,
    payload: VibeChatRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Сообщение ИИ-напарнику: user-сообщение сразу в историю, ответ придёт job'ом 'vibe_chat'. 409 — задача решена, 422 — пустое сообщение."""
    s, _t = _get_session(db, user, session_id)
    if s.status == "passed":
        raise HTTPException(409, "Задача уже решена — диалог закрыт")
    content = payload.content.strip()
    if not content:
        raise HTTPException(422, "Пустое сообщение")

    history = list(s.messages or [])
    history.append({"role": "user", "content": content})
    s.messages = history
    s.prompts_count = (s.prompts_count or 0) + 1
    db.commit()

    job = submit_job(
        db, user.id, "vibe_chat",
        messages=[{"role": "system", "content": ASSISTANT_SYSTEM}] + _budgeted(history),
        temperature=0.6, max_tokens=900,
        meta={"session_id": s.id},
    )
    return {"job_id": job.id, "prompts_count": s.prompts_count}


@router.post("/sessions/{session_id}/run", response_model=VibeRunResponse)
def run(
    session_id: int,
    payload: VibeCodeRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Прогон кода: мутанты для типа tests, скрытые тесты иначе; обновляет last_run/балл, при успехе status='passed'. 502 — песочница недоступна."""
    from dataclasses import asdict

    from app.services.sandbox import SandboxError

    s, t = _get_session(db, user, session_id)
    code = payload.code if payload.code else s.code
    prompts = [m.get("content", "") for m in (s.messages or []) if m.get("role") == "user"]

    mutation = None
    try:
        if t.task_type == "tests":
            mutation = run_mutation(code, t.initial_code, t.mutants or [])
            status = "ok" if mutation["orig_ok"] else "broken"
            results = [dict(r) for r in mutation["orig_results"]]
            ev = evaluate(
                t.task_type, code, t.initial_code, t.reference_solution, prompts,
                status, [], mutation, t.min_mutants_caught,
            )
        else:
            status, case_results = run_assert_cases(code, t.hidden_tests or [])
            results = [asdict(r) for r in case_results]
            ev = evaluate(
                t.task_type, code, t.initial_code, t.reference_solution, prompts,
                status, case_results, None, t.min_mutants_caught,
            )
    except SandboxError as e:
        raise HTTPException(502, f"Песочница недоступна: {e}") from e

    s.code = code
    s.run_count = (s.run_count or 0) + 1
    s.last_run = {
        "status": status, "results": results, "mutation": mutation,
        "breakdown": ev["breakdown"], "passed": ev["passed"], "score": ev["score"],
    }
    if ev["passed"]:
        s.status = "passed"
    if s.score is None or ev["score"] > s.score:
        s.score = ev["score"]
    db.commit()

    return VibeRunResponse(
        status=status, results=results, mutation=mutation,
        passed=ev["passed"], score=ev["score"], breakdown=ev["breakdown"],
    )
