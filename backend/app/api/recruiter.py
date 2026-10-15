"""Скрининг (общение) с рекрутером: LLM-чат + рекомендации по итогам."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user
from app.models import RecruiterMessage, Resume, User
from app.schemas import RecruiterChatRequest, ResumeData
from app.services.llm_queue import submit_job
from app.services.skills import aggregate_skills, resume_completion, resume_to_text, solved_info

router = APIRouter(prefix="/api/recruiter", tags=["recruiter"])

SYSTEM_PROMPT = """Ты — рекрутер в IT-компании. Проводишь скрининг-собеседование (15–20 минут) со студентом-кандидатом без коммерческого опыта, но с учебными проектами, лабораторными и курсовыми работами.

Резюме кандидата:
{resume_text}

Правила проведения:
1. Начни с короткого представления (имя + отдел кадров) и объясни формат беседы.
2. Задавай уточняющие вопросы по реальному опыту кандидата из резюме: проекты, лабораторные работы, практика, курсы, хакатоны. Цель — убедиться, что кандидат действительно помнит, с чем работал, и может об этом рассказать. 1–2 вопроса в одном сообщении.
3. Когда основные пункты опыта покрыты, перейди к зарплатным ожиданиям и базовым требованиям (график, локация, удалёнка).
4. Не задавай алгоритмические задачи, не давай код, не обещай трудоустройство.
5. Будь доброжелательным, разговорным и кратким — не более 3–4 фраз в сообщении.

Отвечай на русском языке."""

RECOMMEND_SYSTEM = (
    "Ты — опытный tech-рекрутер. По итогам скрининг-собеседования дай кандидату конкретные рекомендации:\n"
    "1) Навыки разработки, которые стоит усилить (с привязкой к его реальному опыту и целевой должности).\n"
    "2) Коммуникационные навыки: что улучшить в самопрезентации и ответах.\n"
    "3) Что подчеркнуть в резюме и на собеседовании.\n"
    "Будь конкретным, опирайся только на факты из резюме и диалога. Отвечай на русском языке."
)


def _load_resume(db: Session, user: User) -> tuple[ResumeData, dict]:
    """Данные резюме пользователя (пустые по умолчанию) и степень его готовности к скринингу."""
    row = db.scalar(select(Resume).where(Resume.user_id == user.id))
    data = ResumeData.model_validate(row.data) if row else ResumeData()
    return data, resume_completion(data)


def _latest_recommendation(db: Session, user: User) -> RecruiterMessage | None:
    """Последнее сообщение с ролью recommendation, если оно есть."""
    return db.scalar(
        select(RecruiterMessage)
        .where(RecruiterMessage.user_id == user.id, RecruiterMessage.role == "recommendation")
        .order_by(RecruiterMessage.id.desc())
        .limit(1)
    )


def _is_fresh(db: Session, user: User, rec: RecruiterMessage) -> bool:
    """Свежая = после неё не было ни одного сообщения чата (id монотонен)."""
    newer = db.scalar(
        select(RecruiterMessage.id)
        .where(
            RecruiterMessage.user_id == user.id,
            RecruiterMessage.role != "recommendation",
            RecruiterMessage.id > rec.id,
        )
        .limit(1)
    )
    return newer is None


@router.post("/chat")
async def chat(
    payload: RecruiterChatRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Шаг диалога со скрининг-рекрутером: user-сообщение сохраняется сразу, ответ придёт job'ом 'recruiter_chat'. 409 — резюме не готово."""
    data, comp = _load_resume(db, user)
    if not comp["ready"]:
        raise HTTPException(409, detail={"issues": comp["missing"]})
    patterns, langs = solved_info(db, user)
    skills = aggregate_skills(data, patterns, langs)
    system = SYSTEM_PROMPT.format(resume_text=resume_to_text(data, skills))
    history = [{"role": m.role, "content": m.content} for m in payload.messages[-10:]]
    last = payload.messages[-1]
    if last.role == "user":
        db.add(RecruiterMessage(user_id=user.id, role="user", content=last.content))
        db.commit()
    job = submit_job(
        db, user.id, "recruiter_chat",
        messages=[{"role": "system", "content": system}] + history,
        temperature=0.6, max_tokens=500,
    )
    return {"job_id": job.id}


@router.get("/history")
def history(
    limit: int = 40,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Диалог с рекрутером в хронологическом порядке (без сообщений recommendation; limit 1..100)."""
    rows = db.scalars(
        select(RecruiterMessage)
        .where(RecruiterMessage.user_id == user.id, RecruiterMessage.role != "recommendation")
        .order_by(RecruiterMessage.created_at.desc(), RecruiterMessage.id.desc())
        .limit(max(1, min(limit, 100)))
    ).all()
    rows = list(reversed(rows))
    return [
        {"id": r.id, "role": r.role, "content": r.content, "created_at": r.created_at.isoformat()}
        for r in rows
    ]


@router.get("/recommendation")
def get_recommendation(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Последние рекомендации; fresh=False, если после них шёл новый диалог. 404 — рекомендаций ещё нет."""
    rec = _latest_recommendation(db, user)
    if rec is None:
        raise HTTPException(404, "Рекомендаций пока нет")
    return {
        "reply": rec.content,
        "fresh": _is_fresh(db, user, rec),
        "created_at": rec.created_at.isoformat(),
    }


@router.post("/reset")
def reset(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Полный сброс истории общения с рекрутёром (включая рекомендации)."""
    db.execute(delete(RecruiterMessage).where(RecruiterMessage.user_id == user.id))
    db.commit()
    return {"ok": True}


@router.post("/recommendations")
async def recommendations(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Генерация рекомендаций по резюме и транскрипту последних 20 сообщений через очередь. 409 — резюме не готово или текущие ещё актуальны."""
    data, comp = _load_resume(db, user)
    if not comp["ready"]:
        raise HTTPException(409, detail={"issues": comp["missing"]})

    existing = _latest_recommendation(db, user)
    if existing is not None and _is_fresh(db, user, existing):
        raise HTTPException(
            409, "Рекомендации актуальны — перегенерация появится после нового диалога"
        )

    rows = db.scalars(
        select(RecruiterMessage)
        .where(RecruiterMessage.user_id == user.id, RecruiterMessage.role != "recommendation")
        .order_by(RecruiterMessage.created_at.desc(), RecruiterMessage.id.desc())
        .limit(20)
    ).all()
    rows = list(reversed(rows))
    transcript = "\n".join(f"{'Кандидат' if r.role == 'user' else 'Рекрутер'}: {r.content}" for r in rows) or "(диалог пуст)"
    patterns, langs = solved_info(db, user)
    skills = aggregate_skills(data, patterns, langs)
    user_content = (
        "Резюме:\n" + resume_to_text(data, skills) + "\n\nТранскрипт собеседования:\n" + transcript
    )
    job = submit_job(
        db, user.id, "recommendation",
        messages=[
            {"role": "system", "content": RECOMMEND_SYSTEM},
            {"role": "user", "content": user_content},
        ],
        temperature=0.5, max_tokens=2800,
    )
    return {"job_id": job.id}
