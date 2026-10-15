"""Pydantic-схемы запросов и ответов API (auth, задачи, резюме, вайб-кодинг, LLM-очередь)."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

# ---------- Auth ----------


class UserCreate(BaseModel):
    email: EmailStr
    username: str = Field(min_length=2, max_length=64)
    password: str = Field(min_length=6, max_length=128)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    email: str
    username: str
    role: str
    is_active: bool
    created_at: datetime


class LoginRequest(BaseModel):
    login: str  # email или username
    password: str


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


# ---------- Tasks ----------


class TaskListItem(BaseModel):
    slug: str
    title: str
    pattern: str
    level: str
    solved: bool = False


class TestOut(BaseModel):
    name: str
    stdin: str
    expected_stdout: str
    sample: bool = False


class TaskOut(BaseModel):
    """Карточка задачи для студента: только sample-тесты, без эталона."""

    slug: str
    title: str
    legend: str
    pattern: str
    level: str
    hints: list[str] = []
    tests: list[TestOut] = []  # только sample-тесты
    solved: bool | None = None


class TaskAdminOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    slug: str
    title: str
    legend: str
    pattern: str
    level: str
    hints: list[str] = []
    tests: list[TestOut] = []
    reference_solution: str = ""
    is_active: bool


class TaskUpsert(BaseModel):
    slug: str = Field(min_length=3, max_length=128, pattern=r"^[a-z0-9\-]+$")
    title: str = Field(min_length=3, max_length=255)
    legend: str = Field(min_length=10)
    pattern: str = Field(min_length=2, max_length=64)
    level: str = Field(pattern=r"^(junior|middle|senior)$")
    hints: list[str] = []
    tests: list[TestOut] = Field(min_length=1)
    reference_solution: str = ""
    is_active: bool = True


class RetitleRequest(BaseModel):
    """Перегенерация легенды задачи; save — закрепить вариант за студентом."""

    save: bool = False  # студент: сохранить вариант за собой
    theme: str | None = Field(default=None, max_length=200)  # единый стиль легенд для комплекта


class GenerateSetRequest(BaseModel):
    """Комплект задач для генерации легенд; пустые slugs — весь банк."""

    slugs: list[str] = []  # пусто — все задачи банка
    theme: str | None = Field(default=None, max_length=200)


class ExportCommunityRequest(BaseModel):
    author: str = Field(min_length=1, max_length=64, description="Имя автора вклада")


# ---------- Резюме ----------

class ResumeProjectItem(BaseModel):
    """1.1.1 Курсовые и дипломные проекты."""
    model_config = ConfigDict(extra="allow")
    name: str = ""
    problem: str = ""  # решённая задача
    tech_stack: list[str] = []


class ResumeLabItem(BaseModel):
    """1.1.2 Лабораторные и практические работы."""
    model_config = ConfigDict(extra="allow")
    subject: str = ""  # предмет
    work_name: str = ""  # название работы
    goal: str = ""  # цель работы
    tech_stack: list[str] = []


class ResumeInternshipItem(BaseModel):
    """1.2 Практика и стажировки."""
    model_config = ConfigDict(extra="allow")
    city: str = ""
    organization: str = ""
    period: str = ""  # сроки (свободный текст)
    goal: str = ""


class ResumeCourseItem(BaseModel):
    """1.4 Курсы дополнительного обучения."""
    model_config = ConfigDict(extra="allow")
    month_year: str = ""
    name: str = ""
    tech_stack: list[str] = []


class ResumeHackathonItem(BaseModel):
    """1.5.1 Хакатоны и олимпиады."""
    model_config = ConfigDict(extra="allow")
    name: str = ""
    organizer: str = ""
    location: str = ""
    month_year: str = ""
    role: str = ""  # frontend | backend | QA
    tech_stack: list[str] = []


class ResumeLabMembership(BaseModel):
    """1.5.2/1.5.3 Научно-исследовательская лаборатория и проекты."""
    model_config = ConfigDict(extra="allow")
    university: str = ""
    department: str = ""
    department_url: str = ""
    supervisor: str = ""  # ФИО руководителя
    own_project: str = ""  # личный проект
    other_projects: list[str] = []  # проекты других студентов (каждый — отдельным элементом)


class ResumeData(BaseModel):
    """Тело резюме. extra='allow' — новые поля формы не ломают сохранение."""
    model_config = ConfigDict(extra="allow")

    # 1.0 Основная информация
    last_name: str = ""
    first_name: str = ""
    middle_name: str = ""
    gender: str = ""  # male | female
    city: str = ""
    phone: str = ""
    birth_day: str = ""
    birth_month: str = ""
    birth_year: str = ""
    citizenship: str = ""
    work_permit: str = ""

    # Образование (для раздела DOCX)
    university: str = ""
    faculty: str = ""
    department: str = ""  # кафедра — заполняется студентом
    major: str = ""  # специальность / направление
    graduation_year: str = ""  # год окончания или «окончание ожидается в N»

    # Ссылки
    github: str = ""
    gitverse: str = ""
    gitflic: str = ""

    # Разделы
    projects: list[ResumeProjectItem] = []
    labs: list[ResumeLabItem] = []
    internships: list[ResumeInternshipItem] = []
    courses: list[ResumeCourseItem] = []
    hackathons: list[ResumeHackathonItem] = []
    lab_membership: ResumeLabMembership | None = None


class ResumeOut(BaseModel):
    data: ResumeData
    completion: dict  # {"ready": bool, "missing": [str]}
    updated_at: str | None = None


class RecruiterChatMessage(BaseModel):
    role: str = Field(pattern=r"^(user|assistant)$")
    content: str = Field(min_length=1, max_length=20000)


class RecruiterChatRequest(BaseModel):
    messages: list[RecruiterChatMessage] = Field(min_length=1)


class RecruiterChatResponse(BaseModel):
    reply: str


# ---------- Runs / submissions ----------

class RunRequest(BaseModel):
    language: str = Field(pattern=r"^(python|java|cpp|javascript)$")
    code: str = Field(min_length=1, max_length=60000)


class TestResult(BaseModel):
    name: str
    passed: bool
    expected_stdout: str = ""
    got_stdout: str = ""
    stderr: str = ""
    status: str = "ok"  # ok|wrong_answer|runtime_error|timeout|compile_error|internal_error
    time_ms: int = 0


class RunResponse(BaseModel):
    status: str
    passed_count: int
    total_count: int
    time_ms: int
    results: list[TestResult]


class SubmissionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    task_id: int
    task_slug: str | None = None
    language: str
    code: str
    status: str
    passed_count: int
    total_count: int
    results: list[TestResult] = []
    time_ms: int
    ai_feedback: str | None = None
    feedback_job_id: int | None = None  # разбор ещё генерируется в LLM-очереди
    created_at: datetime


class SubmitRequest(RunRequest):
    want_feedback: bool = True


# ---------- Assistant ----------


class ChatMessageIn(BaseModel):
    role: str = Field(pattern=r"^(user|assistant)$")
    content: str = Field(min_length=1, max_length=8000)


class ChatRequest(BaseModel):
    task_slug: str
    messages: list[ChatMessageIn] = Field(min_length=1, max_length=40)
    code: str | None = None
    language: str | None = None
    mode: str = "hint"  # hint | explain


class ChatResponse(BaseModel):
    reply: str


# ---------- Admin ----------


class AdminUserUpdate(BaseModel):
    is_active: bool | None = None
    role: str | None = Field(default=None, pattern=r"^(student|admin)$")


class SettingsUpdate(BaseModel):
    values: dict[str, str]


class PasswordResetRequest(BaseModel):
    """Новый пароль в теле запроса (не в URL — не попадает в логи/историю)."""

    new_password: str = Field(min_length=6)


class ChatHistoryItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    role: str
    content: str
    created_at: datetime


# ---------- Вайб-кодинг ----------


class VibeTaskListItem(BaseModel):
    id: int
    slug: str
    task_type: str
    title: str
    status: str | None = None  # сессия студента: in_progress | passed | None
    score: int | None = None


class VibeSessionOut(BaseModel):
    id: int
    task_id: int
    slug: str
    task_type: str
    title: str
    description_md: str
    initial_code: str
    status: str
    messages: list[dict]
    code: str
    prompts_count: int
    run_count: int
    last_run: dict
    score: int | None


class VibeChatRequest(BaseModel):
    content: str = Field(min_length=1, max_length=8000)


class VibeChatResponse(BaseModel):
    reply: str
    prompts_count: int


class VibeCodeRequest(BaseModel):
    code: str = Field(default="", max_length=60000)


class VibeRunResponse(BaseModel):
    """Результат прогона вайб-сессии: тесты, пойманные мутанты и разбивка счёта."""

    status: str
    results: list[dict]
    mutation: dict | None = None
    passed: bool
    score: int
    breakdown: dict


class VibeTaskAdminIn(BaseModel):
    slug: str = Field(min_length=3, max_length=96, pattern=r"^[a-z0-9-]+$")
    task_type: str = Field(pattern=r"^(bugfix|tests|refactor|contract)$")
    title: str = Field(min_length=3, max_length=255)
    description_md: str = ""
    initial_code: str = ""
    hidden_tests: list[dict] = []
    reference_solution: str = ""
    mutants: list[dict] = []
    min_mutants_caught: int = Field(default=0, ge=0, le=20)
    enabled: bool = True


class VibeTaskAdminOut(VibeTaskAdminIn):
    id: int


# ---------- LLM-очередь ----------


class LLMJobSubmit(BaseModel):
    """Отправка задачи в LLM-очередь; kind определяет обработчик job'а."""

    kind: str = Field(pattern=r"^(assistant_chat|recruiter_chat|recommendation|vibe_chat|retitle|generate_set|submission_feedback)$")
    messages: list[dict] = []
    temperature: float = 0.4
    max_tokens: int = Field(default=1200, ge=1, le=8192)
    meta: dict = {}


class LLMJobOut(BaseModel):
    """Статус job'а в очереди; position — место в очереди для pending."""

    id: int
    kind: str
    status: str
    position: int = 0
    result: str | None = None
    error: str | None = None
