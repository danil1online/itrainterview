"""Резюме студента: хранение, навыки, экспорт в DOCX."""

import io
from urllib.parse import quote

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user
from app.models import RecruiterMessage, RecruiterProgress, Resume, User
from app.schemas import ResumeData
from app.services.resume_docx import build_resume_docx
from app.services.skills import TECH_STACK, aggregate_skills, resume_completion, solved_info, solved_tasks

router = APIRouter(prefix="/api/resume", tags=["resume"])


@router.get("/tech-stack")
def tech_stack(user: User = Depends(get_current_user)):
    """Единый список стека технологий для чекбоксов формы."""
    return TECH_STACK


@router.get("")
def get_resume(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Данные резюме, готовность, навыки (с учётом решённых задач) и список решённых; пустые по умолчанию."""
    row = db.scalar(select(Resume).where(Resume.user_id == user.id))
    data = ResumeData.model_validate(row.data) if row else ResumeData()
    patterns, langs = solved_info(db, user)
    skills = aggregate_skills(data, patterns, langs)
    from app.services.skills import PATTERN_RU

    solved = solved_tasks(db, user)
    return {
        "data": data.model_dump(),
        "completion": resume_completion(data),
        "skills": skills,
        "solved": {
            "count": len(solved),
            "tasks": [
                {"title": t["title"], "pattern_ru": PATTERN_RU.get(t["pattern"], t["pattern"]), "level": t["level"]}
                for t in solved
            ],
        },
        "updated_at": row.updated_at.isoformat() if row else None,
    }


@router.put("")
def put_resume(
    payload: ResumeData,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Сохраняет резюме; при изменении данных сбрасывает историю общения с рекрутером (recruiter_reset=true)."""
    row = db.scalar(select(Resume).where(Resume.user_id == user.id))
    dumped = payload.model_dump()
    recruiter_reset = False
    if row is None:
        db.add(Resume(user_id=user.id, data=dumped))
    else:
        if row.data != dumped:
            # резюме изменилось — контекст скрининга устарел, сбрасываем историю и прогресс вопросов
            db.execute(delete(RecruiterMessage).where(RecruiterMessage.user_id == user.id))
            db.execute(delete(RecruiterProgress).where(RecruiterProgress.user_id == user.id))
            recruiter_reset = True
        row.data = dumped
    db.commit()
    return {"ok": True, "recruiter_reset": recruiter_reset}


@router.get("/export.docx")
def export_docx(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """DOCX-версия резюме со скиллами; имя файла — ФИО или 'resume'."""
    row = db.scalar(select(Resume).where(Resume.user_id == user.id))
    data = ResumeData.model_validate(row.data) if row else ResumeData()
    patterns, langs = solved_info(db, user)
    skills = aggregate_skills(data, patterns, langs)
    content = build_resume_docx(data, skills)
    name = " ".join(x for x in (data.last_name, data.first_name) if x.strip()) or "resume"
    return StreamingResponse(
        io.BytesIO(content),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{quote(name)}.docx"'},
    )
