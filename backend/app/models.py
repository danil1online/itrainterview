"""SQLAlchemy-модели доменной БД: пользователи, задачи, сабмиты, чаты, вайб-кодинг, LLM-очередь."""

from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


def utcnow() -> datetime:
    """Возвращает текущее время в UTC (default для временных колонок)."""
    return datetime.now(timezone.utc)


class User(Base):
    """Пользователь системы: студент или администратор."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    username: Mapped[str] = mapped_column(String(64), unique=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(16), default="student")  # student | admin
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    submissions: Mapped[list["Submission"]] = relationship(back_populates="user")


class Task(Base):
    """Задача из банка: легенда, паттерн, уровень, тесты и эталонное решение."""

    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(255))
    legend: Mapped[str] = mapped_column(Text)
    pattern: Mapped[str] = mapped_column(String(64), index=True)
    level: Mapped[str] = mapped_column(String(16), index=True)  # junior | middle | senior
    hints: Mapped[list] = mapped_column(JSON, default=list)
    tests: Mapped[list] = mapped_column(JSON, default=list)  # [{name, stdin, expected_stdout, sample}]
    reference_solution: Mapped[str] = mapped_column(Text, default="")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class TaskVariant(Base):
    """Сгенерированная ИИ легенда задачи для конкретного студента."""

    __tablename__ = "task_variants"
    __table_args__ = (UniqueConstraint("user_id", "task_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id"), index=True)
    title: Mapped[str] = mapped_column(String(255))
    legend: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Submission(Base):
    """Попытка студента решить задачу: код, статус и результаты тестов."""

    __tablename__ = "submissions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id"), index=True)
    language: Mapped[str] = mapped_column(String(16))
    code: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), default="pending")
    # pending|accepted|wrong_answer|runtime_error|compile_error|timeout|internal_error
    passed_count: Mapped[int] = mapped_column(Integer, default=0)
    total_count: Mapped[int] = mapped_column(Integer, default=0)
    results: Mapped[list] = mapped_column(JSON, default=list)
    time_ms: Mapped[int] = mapped_column(Integer, default=0)
    ai_feedback: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)

    user: Mapped["User"] = relationship(back_populates="submissions")
    task: Mapped["Task"] = relationship()


class RunLog(Base):
    """Последний запуск кода студента (run или submit) — контекст для ИИ-помощника."""

    __tablename__ = "run_logs"
    __table_args__ = (UniqueConstraint("user_id", "task_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id"), index=True)
    language: Mapped[str] = mapped_column(String(16))
    status: Mapped[str] = mapped_column(String(32), default="pending")
    passed_count: Mapped[int] = mapped_column(Integer, default=0)
    total_count: Mapped[int] = mapped_column(Integer, default=0)
    results: Mapped[list] = mapped_column(JSON, default=list)  # [{name, passed, status, got_stdout, stderr}]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ChatMessage(Base):
    """Сообщение диалога студента с ИИ-помощником по задаче."""

    __tablename__ = "chat_messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id"), index=True)
    role: Mapped[str] = mapped_column(String(16))  # user | assistant
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Resume(Base):
    """Резюме студента (JSON) — одно на пользователя."""

    __tablename__ = "resumes"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True, index=True)
    data: Mapped[dict] = mapped_column(JSON, default=dict)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )


class RecruiterMessage(Base):
    """Сообщение диалога студента со скрининг-рекрутером."""

    __tablename__ = "recruiter_messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    role: Mapped[str] = mapped_column(String(16))  # user | assistant
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)


class RecruiterProgress(Base):
    """Обязательные технические вопросы собеседования и статус их задавания."""

    __tablename__ = "recruiter_progress"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True, index=True)
    task_question: Mapped[str | None] = mapped_column(Text, nullable=True)  # вопрос по решённой задаче
    tech_question: Mapped[str | None] = mapped_column(Text, nullable=True)  # вопрос по технологии из резюме
    meta: Mapped[dict] = mapped_column(JSON, default=dict)  # для детекции: {"task": {...}, "tech": {...}}
    task_asked: Mapped[bool] = mapped_column(Boolean, default=False)
    tech_asked: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class VibeTask(Base):
    """Задача тренажёра «Вайб-кодинг» (bugfix|tests|refactor|contract)."""

    __tablename__ = "vibe_tasks"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(96), unique=True, index=True)
    task_type: Mapped[str] = mapped_column(String(16))  # bugfix | tests | refactor | contract
    title: Mapped[str] = mapped_column(String(255))
    description_md: Mapped[str] = mapped_column(Text, default="")
    initial_code: Mapped[str] = mapped_column(Text, default="")
    # скрытые assert-кейсы: [{"name": str, "code": str}] — дописываются после кода студента;
    # для типа tests — это тесты студента (driver оборачивает их в try/except AssertionError)
    hidden_tests: Mapped[list] = mapped_column(JSON, default=list)
    reference_solution: Mapped[str] = mapped_column(Text, default="")
    # для типа tests: [{"name": str, "code": str}] — мутанты эталона, должны ловиться тестами
    mutants: Mapped[list] = mapped_column(JSON, default=list)
    min_mutants_caught: Mapped[int] = mapped_column(Integer, default=1)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class VibeSession(Base):
    """Сессия студента в задаче вайб-кодинга: код, чат, прогоны и счёт."""

    __tablename__ = "vibe_sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("vibe_tasks.id"), index=True)
    status: Mapped[str] = mapped_column(String(16), default="in_progress")  # in_progress | passed
    messages: Mapped[list] = mapped_column(JSON, default=list)  # [{role, content, ts}]
    code: Mapped[str] = mapped_column(Text, default="")
    prompts_count: Mapped[int] = mapped_column(Integer, default=0)
    run_count: Mapped[int] = mapped_column(Integer, default=0)
    last_run: Mapped[dict] = mapped_column(JSON, default=dict)  # результаты последнего прогона
    score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    __table_args__ = (UniqueConstraint("user_id", "task_id", name="uq_vibe_session_user_task"),)


class LLMJob(Base):
    """Очередная задача к LLM. Живёт в БД — переживает рестарт бэкенда."""

    __tablename__ = "llm_jobs"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    kind: Mapped[str] = mapped_column(String(32), index=True)  # assistant_chat|recruiter_chat|...
    status: Mapped[str] = mapped_column(String(16), default="pending", index=True)  # pending|running|done|error|cancelled
    payload: Mapped[dict] = mapped_column(JSON, default=dict)  # {messages, temperature, max_tokens, meta}
    result: Mapped[str | None] = mapped_column(Text, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class SystemSetting(Base):
    """Системная настройка в формате ключ-значение (LLM, песочница и т.п.)."""

    __tablename__ = "system_settings"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[str] = mapped_column(Text, default="")


EDITABLE_SETTINGS = [
    "llm_base_url",
    "llm_model",
    "llm_api_key",
    "sandbox_timeout_sec",
    "sandbox_memory_mb",
    "allow_self_registration",
    "llm_max_concurrent",
    "sandbox_max_concurrent",
]


def get_setting(db, key: str, default: str = "") -> str:
    """Возвращает настройку из БД; если её нет или она пуста — default."""
    row = db.get(SystemSetting, key)
    return row.value if row is not None and row.value != "" else default


def set_setting(db, key: str, value: str) -> None:
    """Создаёт или обновляет системную настройку в БД."""
    row = db.get(SystemSetting, key)
    if row is None:
        db.add(SystemSetting(key=key, value=value))
    else:
        row.value = value
