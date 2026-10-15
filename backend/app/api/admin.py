"""Админ-панель /api/admin, доступ только role=admin.

Пользователи, CRUD задач, результаты/статистика/CSV, системные настройки, управление вайб-задачами."""

import csv
import io
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import hash_password
from app.db import get_db
from app.deps import require_admin
from app.models import (
    EDITABLE_SETTINGS,
    Submission,
    Task,
    User,
    VibeSession,
    VibeTask,
    get_setting,
    set_setting,
)
from app.schemas import (
    AdminUserUpdate,
    PasswordResetRequest,
    VibeTaskAdminIn,
    VibeTaskAdminOut,
    ExportCommunityRequest,
    SettingsUpdate,
    TaskAdminOut,
    TaskUpsert,
)
from app.services.contribute import ContributeError, export_task
from app.services.llm_queue import submit_job

router = APIRouter(prefix="/api/admin", tags=["admin"])


# ---------- Пользователи ----------


@router.get("/users")
def list_users(
    q: str | None = None,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Список пользователей с числом сабмитов и решённых задач; q — поиск по username/email."""
    return _list_users_impl(db, q)


def _list_users_impl(db: Session, q: str | None):
    """Сборка строк списка: LEFT JOIN со счётчиками всех и accepted-сабмитов на пользователя."""
    sub_counts = (
        select(Submission.user_id.label("uid"), func.count().label("cnt"))
        .group_by(Submission.user_id)
        .subquery()
    )
    solved_counts = (
        select(
            Submission.user_id.label("uid"),
            func.count(func.distinct(Submission.task_id)).label("cnt"),
        )
        .where(Submission.status == "accepted")
        .group_by(Submission.user_id)
        .subquery()
    )
    stmt = (
        select(
            User,
            func.coalesce(sub_counts.c.cnt, 0),
            func.coalesce(solved_counts.c.cnt, 0),
        )
        .outerjoin(sub_counts, sub_counts.c.uid == User.id)
        .outerjoin(solved_counts, solved_counts.c.uid == User.id)
    )
    if q:
        like = f"%{q}%"
        stmt = stmt.where(or_(User.username.ilike(like), User.email.ilike(like)))
    rows = db.execute(stmt.order_by(User.created_at.desc())).all()
    return [
        {
            "id": u.id,
            "email": u.email,
            "username": u.username,
            "role": u.role,
            "is_active": u.is_active,
            "created_at": u.created_at,
            "submissions": int(total),
            "solved_tasks": int(solved),
        }
        for u, total, solved in rows
    ]


@router.patch("/users/{user_id}")
def update_user(
    user_id: int,
    payload: AdminUserUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Меняет роль/статус пользователя (commit); 404 — не найден, 400 — попытка заблокировать себя или сменить себе роль."""
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(404, "Пользователь не найден")
    if user.id == admin.id and payload.is_active is False:
        raise HTTPException(400, "Нельзя заблокировать самого себя")
    if user.id == admin.id and payload.role is not None:
        raise HTTPException(400, "Нельзя сменить роль самому себе")
    if payload.is_active is not None:
        user.is_active = payload.is_active
    if payload.role is not None:
        user.role = payload.role
    db.commit()
    return {"ok": True}


@router.post("/users/{user_id}/reset_password")
def reset_password(
    user_id: int,
    payload: PasswordResetRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Устанавливает новый пароль (мин. 6 символов); 400 — короткий, 404 — нет пользователя."""
    new_password = payload.new_password
    if len(new_password) < 6:
        raise HTTPException(400, "Пароль слишком короткий")
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(404, "Пользователь не найден")
    user.hashed_password = hash_password(new_password)
    db.commit()
    return {"ok": True}


# ---------- Задачи ----------


@router.get("/tasks", response_model=list[TaskAdminOut])
def admin_tasks(
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Все задачи банка (включая неактивные), отсортированы по паттерну и уровню."""
    return db.scalars(select(Task).order_by(Task.pattern, Task.level)).all()


@router.post("/tasks", response_model=TaskAdminOut, status_code=201)
def create_task(
    payload: TaskUpsert,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Создаёт задачу; 409 — slug уже занят."""
    existing = db.scalar(select(Task).where(Task.slug == payload.slug))
    if existing:
        raise HTTPException(409, "Slug уже используется")
    task = Task(**payload.model_dump())
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


@router.put("/tasks/{task_id}", response_model=TaskAdminOut)
def update_task(
    task_id: int,
    payload: TaskUpsert,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Полное обновление задачи по id; 404 — нет задачи, 409 — slug занят другой задачей."""
    task = db.get(Task, task_id)
    if task is None:
        raise HTTPException(404, "Задача не найдена")
    clash = db.scalar(select(Task).where(Task.slug == payload.slug, Task.id != task_id))
    if clash:
        raise HTTPException(409, "Slug уже используется другой задачей")
    for k, v in payload.model_dump().items():
        setattr(task, k, v)
    db.commit()
    db.refresh(task)
    return task


@router.delete("/tasks/{task_id}")
def deactivate_task(
    task_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Мягкое удаление задачи (is_active=False), сабмиты и варианты сохраняются; 404 — нет задачи."""
    task = db.get(Task, task_id)
    if task is None:
        raise HTTPException(404, "Задача не найдена")
    task.is_active = False
    db.commit()
    return {"ok": True}


@router.post("/tasks/{task_id}/retitle")
async def admin_retitle(
    task_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Переписывает заголовок/легенду задачи через LLM-очередь (target='task', меняет для всех); асинхронно, возвращает job_id."""
    task = db.get(Task, task_id)
    if task is None:
        raise HTTPException(404, "Задача не найдена")
    job = submit_job(db, admin.id, "retitle", meta={"task_id": task_id, "target": "task"})
    return {"job_id": job.id}


@router.post("/tasks/{task_id}/export-community")
def export_community(
    task_id: int,
    payload: ExportCommunityRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Экспорт задачи как community-файла (валидация эталона в песочнице)."""
    task = db.get(Task, task_id)
    if task is None:
        raise HTTPException(404, "Задача не найдена")
    try:
        return export_task(task, payload.author)
    except ContributeError as e:
        raise HTTPException(422, detail={"issues": e.issues}) from e


# ---------- Результаты и статистика ----------


def _results_query(db: Session, user_id: int | None, task_id: int | None, status: str | None):
    """Базовый SELECT сабмитов с джойнами на User/Task и опциональными фильтрами; сортировка по новизне."""
    stmt = (
        select(Submission, User.username, Task.slug, Task.level, Task.pattern)
        .join(User, User.id == Submission.user_id)
        .join(Task, Task.id == Submission.task_id)
    )
    if user_id:
        stmt = stmt.where(Submission.user_id == user_id)
    if task_id:
        stmt = stmt.where(Submission.task_id == task_id)
    if status:
        stmt = stmt.where(Submission.status == status)
    return stmt.order_by(Submission.created_at.desc())


@router.get("/results")
def list_results(
    user_id: int | None = None,
    task_id: int | None = None,
    status: str | None = None,
    limit: int = 100,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Сабмиты по фильтрам user/task/status; limit ограничен 1..500."""
    rows = db.execute(_results_query(db, user_id, task_id, status).limit(max(1, min(limit, 500)))).all()
    return [
        {
            "id": s.id,
            "user_id": s.user_id,
            "username": username,
            "task_slug": slug,
            "level": level,
            "pattern": pattern,
            "language": s.language,
            "status": s.status,
            "passed_count": s.passed_count,
            "total_count": s.total_count,
            "time_ms": s.time_ms,
            "created_at": s.created_at,
        }
        for s, username, slug, level, pattern in rows
    ]


@router.get("/results/{submission_id}")
def result_detail(
    submission_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Детали сабмита: результаты тестов, код, ИИ-фидбек; 404 — не найден."""
    sub = db.get(Submission, submission_id)
    if sub is None:
        raise HTTPException(404, "Отправка не найдена")
    task = db.get(Task, sub.task_id)
    user = db.get(User, sub.user_id)
    return {
        "id": sub.id,
        "username": user.username,
        "task": task.title if task else None,
        "language": sub.language,
        "status": sub.status,
        "passed_count": sub.passed_count,
        "total_count": sub.total_count,
        "results": sub.results,
        "ai_feedback": sub.ai_feedback,
        "code": sub.code,
        "created_at": sub.created_at,
    }


@router.get("/stats")
def stats(
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Сводка: пользователи/задачи/сабмиты, решённые пары по паттернам и уровням, топ-10, динамика за 14 дней."""
    total_users = db.scalar(select(func.count()).select_from(User))
    total_tasks = db.scalar(select(func.count()).select_from(Task).where(Task.is_active.is_(True)))
    total_subs = db.scalar(select(func.count()).select_from(Submission))
    accepted = db.scalar(
        select(func.count()).select_from(Submission).where(Submission.status == "accepted")
    )

    solved_pairs = (
        select(
            Submission.user_id.label("uid"),
            Submission.task_id.label("tid"),
        )
        .where(Submission.status == "accepted")
        .distinct()
        .subquery()
    )

    by_pattern = db.execute(
        select(Task.pattern, func.count())
        .select_from(solved_pairs)
        .join(Task, Task.id == solved_pairs.c.tid)
        .group_by(Task.pattern)
    ).all()

    by_level = db.execute(
        select(Task.level, func.count())
        .select_from(solved_pairs)
        .join(Task, Task.id == solved_pairs.c.tid)
        .group_by(Task.level)
    ).all()

    top = db.execute(
        select(User.username, func.count().label("solved"))
        .select_from(solved_pairs)
        .join(User, User.id == solved_pairs.c.uid)
        .group_by(User.id, User.username)
        .order_by(func.count().desc())
        .limit(10)
    ).all()

    since = datetime.now(timezone.utc) - timedelta(days=14)
    day_col = func.date(Submission.created_at)
    per_day = db.execute(
        select(day_col, func.count())
        .where(Submission.created_at >= since)
        .group_by(day_col)
        .order_by(day_col)
    ).all()

    return {
        "total_users": total_users,
        "total_tasks": total_tasks,
        "total_submissions": total_subs,
        "accepted_submissions": accepted,
        "solved_pairs": db.scalar(select(func.count()).select_from(solved_pairs)),
        "by_pattern": [{"pattern": p, "solved": c} for p, c in by_pattern],
        "by_level": [{"level": l, "solved": c} for l, c in by_level],
        "top_solvers": [{"username": u, "solved": c} for u, c in top],
        "per_day": [{"date": str(d), "count": int(c)} for d, c in per_day],
    }


@router.get("/export/submissions.csv")
def export_csv(
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Все сабмиты в CSV (разделитель ";"), отдача как attachment без фильтрации."""
    rows = db.execute(_results_query(db, None, None, None)).all()
    buf = io.StringIO()
    writer = csv.writer(buf, delimiter=";")
    writer.writerow(
        ["id", "user", "task_slug", "level", "pattern", "language", "status",
         "passed", "total", "time_ms", "created_at"]
    )
    for s, username, slug, level, pattern in rows:
        writer.writerow(
            [s.id, username, slug, level, pattern, s.language, s.status,
             s.passed_count, s.total_count, s.time_ms, s.created_at.isoformat()]
        )
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="submissions.csv"'},
    )


# ---------- Настройки системы ----------

_SETTING_DEFAULTS = {
    "llm_base_url": lambda: settings.llm_base_url,
    "llm_model": lambda: settings.llm_model,
    "llm_api_key": lambda: settings.llm_api_key,
    "sandbox_timeout_sec": lambda: str(settings.sandbox_timeout_sec),
    "sandbox_memory_mb": lambda: str(settings.sandbox_memory_mb),
    "allow_self_registration": lambda: "true",
    "llm_max_concurrent": lambda: "1",
    "sandbox_max_concurrent": lambda: "",
}


@router.get("/settings")
def get_settings_admin(
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Текущие значения системных настроек с дефолтами из env-конфига."""
    return {key: get_setting(db, key, default()) for key, default in _SETTING_DEFAULTS.items()}


@router.put("/settings")
def put_settings(
    payload: SettingsUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Обновляет настройки; 400 — неизвестный ключ, неверный тип или выход за диапазон (таймаут/память/конкурентность)."""
    for key, value in payload.values.items():
        if key not in EDITABLE_SETTINGS:
            raise HTTPException(400, f"Настройка '{key}' не поддерживается")
        if key in ("sandbox_timeout_sec", "sandbox_memory_mb"):
            try:
                num = int(value)
            except ValueError:
                raise HTTPException(400, f"'{key}' должно быть числом")
            if key == "sandbox_timeout_sec" and not (1 <= num <= 60):
                raise HTTPException(400, "Таймаут песочницы: 1..60 секунд")
            if key == "sandbox_memory_mb" and not (64 <= num <= 2048):
                raise HTTPException(400, "Память песочницы: 64..2048 МБ")
        if key in ("llm_max_concurrent", "sandbox_max_concurrent"):
            try:
                num = int(value)
            except ValueError:
                raise HTTPException(400, f"'{key}' должно быть числом")
            if not (1 <= num <= 32):
                raise HTTPException(400, f"'{key}': 1..32")
        if key == "allow_self_registration" and str(value).lower() not in ("true", "false"):
            raise HTTPException(400, "allow_self_registration: true или false")
        set_setting(db, key, str(value))
    db.commit()
    return {"ok": True}


# ---------- Вайб-кодинг: задачи ----------


def _vibe_validate(payload: VibeTaskAdminIn) -> None:
    """Проверки качества вайб-задачи + прогон эталона в песочнице."""
    from app.services.sandbox import SandboxError
    from app.services.vibe_runner import (
        MARKER,
        MAX_NESTING,
        max_nesting,
        run_assert_cases,
    )

    issues: list[str] = []
    if payload.task_type == "tests":
        if MARKER not in payload.initial_code:
            issues.append("Для типа tests в initial_code нужен маркер: " + MARKER)
        if not payload.mutants:
            issues.append("Для типа tests нужны мутанты (mutants)")
        if payload.min_mutants_caught > len(payload.mutants):
            issues.append("min_mutants_caught больше числа мутантов")
    else:
        if not payload.hidden_tests:
            issues.append("Нужен хотя бы один скрытый тест (hidden_tests)")
        if not payload.reference_solution.strip():
            issues.append("Нужно эталонное решение (reference_solution)")
        for i, case in enumerate(payload.hidden_tests):
            if not (case.get("code") or "").strip():
                issues.append(f"hidden_tests[{i}]: пустое поле code")
    if payload.task_type == "refactor":
        init_n = max_nesting(payload.initial_code)
        ref_n = max_nesting(payload.reference_solution)
        if init_n is None:
            issues.append("initial_code: синтаксическая ошибка")
        elif init_n <= MAX_NESTING:
            issues.append(f"initial_code уже достаточно плоский (вложенность {init_n}) — задача тривиальна")
        if ref_n is not None and ref_n > MAX_NESTING:
            issues.append(f"эталон нарушает лимит вложенности ({ref_n} > {MAX_NESTING})")
    if issues:
        raise HTTPException(422, {"issues": issues})

    if payload.task_type != "tests":
        try:
            status, results = run_assert_cases(payload.reference_solution, payload.hidden_tests)
        except SandboxError as e:
            raise HTTPException(502, f"Песочница недоступна: {e}") from e
        bad = [r.name for r in results if not r.passed]
        if status != "ok" or bad:
            raise HTTPException(422, {"issues": ["Эталон не проходит скрытые тесты: " + ", ".join(bad[:5])]})


def _vibe_out(t: VibeTask) -> VibeTaskAdminOut:
    """VibeTask -> VibeTaskAdminOut; NULL-списки отдаются пустыми."""
    return VibeTaskAdminOut(
        id=t.id, slug=t.slug, task_type=t.task_type, title=t.title,
        description_md=t.description_md, initial_code=t.initial_code,
        hidden_tests=t.hidden_tests or [], reference_solution=t.reference_solution,
        mutants=t.mutants or [], min_mutants_caught=t.min_mutants_caught, enabled=t.enabled,
    )


@router.get("/vibe-tasks", response_model=list[VibeTaskAdminOut])
def admin_vibe_tasks(db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    """Все вайб-задачи, включая отключённые."""
    tasks = db.scalars(select(VibeTask).order_by(VibeTask.id)).all()
    return [_vibe_out(t) for t in tasks]


@router.post("/vibe-tasks", response_model=VibeTaskAdminOut, status_code=201)
def admin_vibe_create(
    payload: VibeTaskAdminIn,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Создаёт вайб-задачу после валидации эталона; 409 — slug занят, 422/502 — из _vibe_validate."""
    if db.scalar(select(VibeTask).where(VibeTask.slug == payload.slug)):
        raise HTTPException(409, "slug уже занят")
    _vibe_validate(payload)
    t = VibeTask(**payload.model_dump())
    db.add(t)
    db.commit()
    db.refresh(t)
    return _vibe_out(t)


@router.patch("/vibe-tasks/{task_id}", response_model=VibeTaskAdminOut)
def admin_vibe_update(
    task_id: int,
    payload: VibeTaskAdminIn,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Полное обновление вайб-задачи с повторной валидацией; 404 — нет задачи, 409 — slug занят."""
    t = db.get(VibeTask, task_id)
    if t is None:
        raise HTTPException(404, "Задача не найдена")
    other = db.scalar(select(VibeTask).where(VibeTask.slug == payload.slug, VibeTask.id != task_id))
    if other:
        raise HTTPException(409, "slug уже занят")
    _vibe_validate(payload)
    for key, value in payload.model_dump().items():
        setattr(t, key, value)
    db.commit()
    db.refresh(t)
    return _vibe_out(t)


@router.delete("/vibe-tasks/{task_id}")
def admin_vibe_delete(
    task_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Удаляет вайб-задачу; 409, если по ней уже есть сессии (нужно отключить enabled=false)."""
    t = db.get(VibeTask, task_id)
    if t is None:
        raise HTTPException(404, "Задача не найдена")
    used = db.scalar(select(func.count()).select_from(VibeSession).where(VibeSession.task_id == task_id))
    if used:
        raise HTTPException(409, f"По задаче уже есть {used} сессий — вместо удаления отключите её (enabled=false)")
    db.delete(t)
    db.commit()
    return {"ok": True}
