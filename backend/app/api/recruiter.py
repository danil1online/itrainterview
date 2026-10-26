"""Скрининг (общение) с рекрутером: LLM-чат + рекомендации по итогам.

Доступ — после заполнения резюме и решения хотя бы одной задачи. В ходе диалога
рекрутер обязан задать два технических вопроса («почему выбрали X, а не Y»):
по решённой задаче и по технологии из резюме; ответы на них учитываются в рекомендациях.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user
from app.models import RecruiterMessage, RecruiterProgress, Resume, User
from app.schemas import RecruiterChatRequest, ResumeData
from app.services.llm_queue import submit_job
from app.services.recruiter_questions import detect_asked, get_or_create_progress
from app.services.skills import aggregate_skills, resume_completion, resume_to_text, solved_info, solved_tasks

router = APIRouter(prefix="/api/recruiter", tags=["recruiter"])

SYSTEM_PROMPT = """Ты — рекрутер в IT-компании. Проводишь скрининг-собеседование (15–20 минут) со студентом-кандидатом без коммерческого опыта, но с учебными проектами, лабораторными и курсовыми работами.

Резюме кандидата:
{resume_text}

Задачи, решённые кандидатом на платформе:
{solved_context}

Правила проведения:
1. Начни с короткого представления: придумай себе имя и назови отдел кадров (не пиши плейсхолдеры вида «[имя]»), объясни формат беседы.
2. Задавай уточняющие вопросы по реальному опыту кандидата из резюме: проекты, лабораторные работы, практика, курсы, хакатоны. Цель — убедиться, что кандидат действительно помнит, с чем работал, и может об этом рассказать. 1–2 вопроса в одном сообщении.
3. Когда основные пункты опыта покрыты, перейди к зарплатным ожиданиям и базовым требованиям (график, локация, удалёнка).
4. Не задавай новые алгоритмические задачи, не давай код, не обещай трудоустройство.
5. Будь доброжелательным, разговорным и кратким — не более 3–4 фраз в сообщении.

Отвечай на русском языке.

{required_questions}"""

RECOMMEND_SYSTEM = (
    "Ты — опытный tech-рекрутер. По итогам скрининг-собеседования дай кандидату конкретные рекомендации:\n"
    "1) Навыки разработки, которые стоит усилить (с привязкой к его реальному опыту и целевой должности).\n"
    "2) Коммуникационные навыки: что улучшить в самопрезентации и ответах.\n"
    "3) Что подчеркнуть в резюме и на собеседовании.\n"
    "4) Оцени глубину ответов кандидата на обязательные технические вопросы (аргументация выбора "
    "алгоритма/технологии, осознанность отказа от альтернатив) и отрази эту оценку в рекомендациях.\n"
    "Будь конкретным, опирайся только на факты из резюме и диалога. Отвечай на русском языке."
)


def _solved_context(solved: list[dict]) -> str:
    """Список решённых задач для системного промпта (или «(нет)»)."""
    if not solved:
        return "(нет)"
    from app.services.skills import PATTERN_RU

    return ", ".join(f"«{t['title']}» ({PATTERN_RU.get(t['pattern'], t['pattern'])}, {t['level']})" for t in solved)


def _required_block(progress: RecruiterProgress | None) -> str:
    """Блок обязательных вопросов для системного промпта (только ещё не заданные).

    Стоит в КОНЦЕ промпта — модель лучше следует последней инструкции.
    Формулировка жёсткая: похожие по смыслу вопросы не засчитываются,
    иначе модель «закрывает» обязательный вопрос аналогичным (проверено на GigaChat).
    """
    pending = []
    if progress is not None:
        if progress.task_question and not progress.task_asked:
            pending.append(progress.task_question)
        if progress.tech_question and not progress.tech_asked:
            pending.append(progress.tech_question)
    if not pending:
        return "Обязательные технические вопросы уже заданы — продолжай собеседование."
    lines = "\n".join(f"{i}) {q}" for i, q in enumerate(pending, 1))
    return (
        "Обязательные технические вопросы — задай их обязательно в ходе беседы, по одному за сообщение, "
        "сохраняя форму «почему выбрали X, а не Y». Задай именно эти вопросы (можно с минимальными "
        "поправками), не заменяя их похожими: вопрос о другой задаче или другой технологии "
        "не засчитывается и его нужно будет задать дополнительно.\n" + lines
    )


def _pending_questions(progress: RecruiterProgress | None) -> list[str]:
    """Ещё не заданные обязательные вопросы (пусто — все заданы или прогресса нет)."""
    if progress is None:
        return []
    pending = []
    if progress.task_question and not progress.task_asked:
        pending.append(progress.task_question)
    if progress.tech_question and not progress.tech_asked:
        pending.append(progress.tech_question)
    return pending


def _qa_section(progress: RecruiterProgress, rows: list[RecruiterMessage]) -> str:
    """Обязательные вопросы + ответы кандидата (первое user-сообщение после вопроса)."""
    pairs = []
    for kind in ("task", "tech"):
        meta = (progress.meta or {}).get(kind)
        q_text = progress.task_question if kind == "task" else progress.tech_question
        if not meta or not q_text:
            continue
        answer = None
        for i, r in enumerate(rows):
            if r.role == "assistant" and detect_asked(meta, r.content):
                for nxt in rows[i + 1:]:
                    if nxt.role == "user":
                        answer = nxt.content
                        break
                break
        pairs.append(f"Вопрос: {q_text}\nОтвет: {answer or '(ответа не было)'}")
    return "\n\n".join(pairs) or "(вопросы ещё не задавались)"


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
    """Шаг диалога со скрининг-рекрутером: user-сообщение сохраняется сразу, ответ придёт job'ом 'recruiter_chat'.

    409 — резюме не готово или не решена ни одна задача.
    """
    data, comp = _load_resume(db, user)
    if not comp["ready"]:
        raise HTTPException(409, detail={"issues": comp["missing"]})
    solved = solved_tasks(db, user)
    if not solved:
        raise HTTPException(409, detail={"issues": ["Решите хотя бы одну задачу из банка"]})
    patterns, langs = solved_info(db, user)
    skills = aggregate_skills(data, patterns, langs)
    progress = get_or_create_progress(db, user, solved, data)
    system = SYSTEM_PROMPT.format(
        resume_text=resume_to_text(data, skills),
        solved_context=_solved_context(solved),
        required_questions=_required_block(progress),
    )
    history = [{"role": m.role, "content": m.content} for m in payload.messages[-10:]]
    messages = [{"role": "system", "content": system}] + history
    # Целенаправленное напоминание: постоянный блок в системном промпте модель может «забыть»
    # (проверено на GigaChat — подменяет обязательный вопрос похожим). Если обязательный вопрос
    # ещё не задан, а рекрутёр уже отвечал хотя бы раз, дублируем его отдельным system-сообщением
    # в конце запроса — последняя инструкция выполняется надёжнее.
    pending = _pending_questions(progress)
    if pending and any(m["role"] == "assistant" for m in history):
        messages.append(
            {
                "role": "system",
                "content": (
                    "Напоминание: обязательный технический вопрос ещё не был задан. Включи его в свой "
                    f"ответ сейчас, дословно или с минимальными поправками (похожий вопрос о другой "
                    f"задаче/технологии не засчитывается): {pending[0]}"
                ),
            }
        )
    last = payload.messages[-1]
    if last.role == "user":
        db.add(RecruiterMessage(user_id=user.id, role="user", content=last.content))
        db.commit()
    job = submit_job(
        db, user.id, "recruiter_chat",
        messages=messages,
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


@router.get("/status")
def status(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Готовность к собеседованию и статус обязательных технических вопросов."""
    data, comp = _load_resume(db, user)
    solved = solved_tasks(db, user)
    progress = db.scalar(select(RecruiterProgress).where(RecruiterProgress.user_id == user.id))
    questions = []
    if progress is not None:
        if progress.task_question:
            questions.append({"kind": "task", "text": progress.task_question, "asked": progress.task_asked})
        if progress.tech_question:
            questions.append({"kind": "tech", "text": progress.tech_question, "asked": progress.tech_asked})
    return {
        "interview_ready": bool(comp["ready"] and solved),
        "missing_resume": comp["missing"],
        "solved_count": len(solved),
        "questions": questions,
    }


@router.post("/reset")
def reset(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Полный сброс истории общения с рекрутёром (включая рекомендации и прогресс вопросов)."""
    db.execute(delete(RecruiterMessage).where(RecruiterMessage.user_id == user.id))
    db.execute(delete(RecruiterProgress).where(RecruiterProgress.user_id == user.id))
    db.commit()
    return {"ok": True}


@router.post("/recommendations")
async def recommendations(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Генерация рекомендаций по резюме и транскрипту последних 20 сообщений через очередь.

    409 — резюме не готово, нет решённых задач, обязательные вопросы ещё не заданы или текущие ещё актуальны.
    """
    data, comp = _load_resume(db, user)
    if not comp["ready"]:
        raise HTTPException(409, detail={"issues": comp["missing"]})
    solved = solved_tasks(db, user)
    if not solved:
        raise HTTPException(409, detail={"issues": ["Решите хотя бы одну задачу из банка"]})

    progress = db.scalar(select(RecruiterProgress).where(RecruiterProgress.user_id == user.id))
    pending = _pending_questions(progress)
    if progress is None or pending:
        raise HTTPException(409, "Сначала задайте обязательные технические вопросы в диалоге")

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
        "Резюме:\n" + resume_to_text(data, skills)
        + "\n\nТранскрипт собеседования:\n" + transcript
        + "\n\nОбязательные технические вопросы и ответы кандидата на них:\n" + _qa_section(progress, rows)
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
