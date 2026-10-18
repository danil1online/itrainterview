"""Тесты резюме (хранение, навыки, DOCX) и скрининга с рекрутером."""

import io
import re
import zipfile


def _reg(client, name):
    r = client.post(
        "/api/auth/register",
        json={"email": f"{name}@example.com", "username": name, "password": "secret123"},
    )
    assert r.status_code == 201, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


RESUME_BODY = {
    "last_name": "Иванов", "first_name": "Иван", "middle_name": "Иванович",
    "gender": "male", "city": "Томск", "phone": "+7 900 000-00-00",
    "birth_day": "1", "birth_month": "1", "birth_year": "2005",
    "citizenship": "Российская Федерация", "work_permit": "не требуется",
    "university": "ТПУ", "faculty": "Кибернетика", "department": "Кафедра программирования",
    "major": "Прикладная информатика",
    "graduation_year": "2027",
    "github": "https://github.com/ivanov", "gitverse": "", "gitflic": "",
    "projects": [
        {"name": "Портал записи на секции", "problem": "Запись студентов на занятия", "tech_stack": ["Python", "Django", "PostgreSQL"]},
    ],
    "labs": [
        {"subject": "Программирование", "work_name": "ЛР5: Двусвязный список", "goal": "Освоить структуры данных", "tech_stack": ["C++"]},
    ],
    "internships": [],
    "courses": [{"month_year": "март 2026", "name": "Курс по Git и Docker", "tech_stack": ["Git", "Docker"]}],
    "hackathons": [],
    "lab_membership": None,
}


def _solve_task(client, name, slug="two-sum-ii"):
    """Отмечает задачу решённой (accepted submission напрямую в БД)."""
    from sqlalchemy import select

    from app.db import SessionLocal
    from app.models import Submission, Task, User

    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == f"{name}@example.com"))
        task = db.scalar(select(Task).where(Task.slug == slug))
        assert user is not None and task is not None
        db.add(
            Submission(user_id=user.id, task_id=task.id, language="python", code="x",
                       status="accepted", passed_count=1, total_count=1)
        )
        db.commit()


async def _recruiter_fake_chat(messages, db=None, temperature=0.4, max_tokens=1200, timeout_sec=None):
    """Фейковая LLM: в чате задаёт все ещё не заданные обязательные вопросы (дословно из промпта),
    для рекомендаций — фиксированный текст."""
    if messages[0]["content"].startswith("Ты — опытный tech-рекрутер"):
        return "Рекомендации: усильте Docker и Git; отвечайте на вопросы о выборе алгоритмов аргументированно."
    qs = re.findall(r"^\d+\) (.+)$", messages[0]["content"], re.M)
    return "Здравствуйте! Меня зовут Алексей, отдел кадров. " + " ".join(qs)


def test_resume_completion_empty(client):
    hdr = _reg(client, "res-empty")
    r = client.get("/api/resume", headers=hdr)
    assert r.status_code == 200
    body = r.json()
    assert body["completion"]["ready"] is False
    assert len(body["completion"]["missing"]) >= 5
    assert body["data"]["last_name"] == ""


def test_resume_put_get_and_skills(client):
    hdr = _reg(client, "res-full")
    assert client.put("/api/resume", json=RESUME_BODY, headers=hdr).status_code == 200
    r = client.get("/api/resume", headers=hdr)
    body = r.json()
    assert body["data"]["last_name"] == "Иванов"
    assert body["completion"]["ready"] is True
    # навыки: из галочек стеков
    assert "Python" in body["skills"]["hard_skills"]
    assert "PostgreSQL" in body["skills"]["hard_skills"]
    assert "Git" in body["skills"]["tools"] and "Docker" in body["skills"]["tools"]
    # рекомендация должности — детерминированная
    assert body["skills"]["position"]["position"] == "Python-разработчик"


def test_resume_docx_export(client):
    hdr = _reg(client, "res-docx")
    client.put("/api/resume", json=RESUME_BODY, headers=hdr)
    r = client.get("/api/resume/export.docx", headers=hdr)
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("application/vnd.openxmlformats")
    assert r.content[:2] == b"PK"  # docx — это zip
    zf = zipfile.ZipFile(io.BytesIO(r.content))
    names = zf.namelist()
    assert "word/document.xml" in names
    xml = zf.read("word/document.xml").decode("utf-8")
    # предзаполненные поля (фамилия, город, телефон, ВУЗ…) выделены красным
    assert 'w:val="FF0000"' in xml
    # кафедра (заполняемое студентом поле) попала в раздел «Образование»
    assert "Кафедра программирования" in xml


def test_recruiter_gated_without_resume(client):
    hdr = _reg(client, "rec-gate")
    r = client.post(
        "/api/recruiter/chat",
        json={"messages": [{"role": "user", "content": "Здравствуйте"}]},
        headers=hdr,
    )
    assert r.status_code == 409
    assert len(r.json()["detail"]["issues"]) > 0


def test_recruiter_chat_and_recommendations(client, monkeypatch):
    from tests.conftest import wait_job
    import app.services.llm_handlers as handlers

    monkeypatch.setattr(handlers, "chat_completion", _recruiter_fake_chat)

    hdr = _reg(client, "rec-chat")
    client.put("/api/resume", json=RESUME_BODY, headers=hdr)
    _solve_task(client, "rec-chat")

    r = client.post(
        "/api/recruiter/chat",
        json={"messages": [{"role": "user", "content": "Здравствуйте"}]},
        headers=hdr,
    )
    assert r.status_code == 200
    job = wait_job(client, hdr, r.json()["job_id"])
    assert job["status"] == "done" and "Алексей" in job["result"]

    hist = client.get("/api/recruiter/history", headers=hdr).json()
    assert [m["role"] for m in hist] == ["user", "assistant"]

    r = client.post("/api/recruiter/recommendations", headers=hdr)
    assert r.status_code == 200
    job = wait_job(client, hdr, r.json()["job_id"])
    assert job["status"] == "done" and "Docker" in job["result"]
    # рекомендации не попадают в историю чата
    hist = client.get("/api/recruiter/history", headers=hdr).json()
    assert [m["role"] for m in hist] == ["user", "assistant"]


def test_resume_requires_auth(client):
    assert client.get("/api/resume").status_code in (401, 403)
    assert client.post(
        "/api/recruiter/chat", json={"messages": [{"role": "user", "content": "Привет"}]}
    ).status_code in (401, 403)


# ------------------------------------------------------------------ рекрутёр: сброс и актуальность


def _ready_recruiter(client, name):
    """Новый пользователь с готовым резюме и решённой задачей; возвращает заголовок авторизации."""

    hdr = _reg(client, name)
    client.put("/api/resume", json=RESUME_BODY, headers=hdr)
    _solve_task(client, name)
    return hdr


def _chat_once(client, hdr, text="Здравствуйте!"):
    from tests.conftest import wait_job

    r = client.post(
        "/api/recruiter/chat", json={"messages": [{"role": "user", "content": text}]}, headers=hdr
    )
    assert r.status_code == 200, r.text
    job = wait_job(client, hdr, r.json()["job_id"])
    assert job["status"] == "done", job
    return job["result"]


def _recommend_once(client, hdr):
    from tests.conftest import wait_job

    r = client.post("/api/recruiter/recommendations", headers=hdr)
    assert r.status_code == 200, r.text
    job = wait_job(client, hdr, r.json()["job_id"])
    assert job["status"] == "done", job
    return job["result"]


def test_recommendation_freshness_flow(client, monkeypatch):
    import app.services.llm_handlers as handlers

    monkeypatch.setattr(handlers, "chat_completion", _recruiter_fake_chat)
    hdr = _ready_recruiter(client, "rec-fresh")
    _chat_once(client, hdr)

    assert _recommend_once(client, hdr) is not None
    # повтор без нового диалога — заблокирован
    r = client.post("/api/recruiter/recommendations", headers=hdr)
    assert r.status_code == 409 and "актуальны" in r.json()["detail"]
    # после нового сообщения — можно снова
    _chat_once(client, hdr, "Расскажите про мой проект.")
    assert _recommend_once(client, hdr) is not None


def test_get_recommendation_endpoint(client, monkeypatch):
    import app.services.llm_handlers as handlers

    monkeypatch.setattr(handlers, "chat_completion", _recruiter_fake_chat)
    hdr = _ready_recruiter(client, "rec-get")
    assert client.get("/api/recruiter/recommendation", headers=hdr).status_code == 404

    _chat_once(client, hdr)
    _recommend_once(client, hdr)
    r = client.get("/api/recruiter/recommendation", headers=hdr)
    assert r.status_code == 200
    body = r.json()
    assert "Docker" in body["reply"] and body["fresh"] is True

    _chat_once(client, hdr, "Спасибо!")
    assert client.get("/api/recruiter/recommendation", headers=hdr).json()["fresh"] is False


def test_reset_clears_history_and_recommendations(client, monkeypatch):
    import app.services.llm_handlers as handlers

    monkeypatch.setattr(handlers, "chat_completion", _recruiter_fake_chat)
    hdr = _ready_recruiter(client, "rec-reset")
    _chat_once(client, hdr)
    _recommend_once(client, hdr)
    assert len(client.get("/api/recruiter/history", headers=hdr).json()) == 2
    # прогресс обязательных вопросов тоже есть (оба заданы фейковой LLM в первом ходу)
    st = client.get("/api/recruiter/status", headers=hdr).json()
    assert len(st["questions"]) == 2 and all(q["asked"] for q in st["questions"])

    r = client.post("/api/recruiter/reset", headers=hdr)
    assert r.status_code == 200 and r.json()["ok"] is True
    assert client.get("/api/recruiter/history", headers=hdr).json() == []
    assert client.get("/api/recruiter/recommendation", headers=hdr).status_code == 404
    # прогресс вопросов сброшен — при новом диалоге сгенерируются заново
    assert client.get("/api/recruiter/status", headers=hdr).json()["questions"] == []


def test_resume_change_resets_recruiter_history(client, monkeypatch):
    import app.services.llm_handlers as handlers

    monkeypatch.setattr(handlers, "chat_completion", _recruiter_fake_chat)
    hdr = _ready_recruiter(client, "rec-autoset")
    _chat_once(client, hdr)
    _recommend_once(client, hdr)
    assert len(client.get("/api/recruiter/history", headers=hdr).json()) == 2

    # сохранение без изменений — историю не трогает
    r = client.put("/api/resume", json=RESUME_BODY, headers=hdr)
    assert r.json()["recruiter_reset"] is False
    assert len(client.get("/api/recruiter/history", headers=hdr).json()) == 2

    # изменение резюме — история, рекомендации и прогресс вопросов сбрасываются
    changed = dict(RESUME_BODY, first_name="Новое")
    r = client.put("/api/resume", json=changed, headers=hdr)
    assert r.json()["recruiter_reset"] is True
    assert client.get("/api/recruiter/history", headers=hdr).json() == []
    assert client.get("/api/recruiter/recommendation", headers=hdr).status_code == 404
    assert client.get("/api/recruiter/status", headers=hdr).json()["questions"] == []


# ------------------------------------------------------------------ рекрутёр: гейт задач и обязательные вопросы


def test_recruiter_gated_without_solved_task(client, monkeypatch):
    """Резюме готово, но ни одной решённой задачи → 409; после решения — диалог идёт."""
    import app.services.llm_handlers as handlers

    monkeypatch.setattr(handlers, "chat_completion", _recruiter_fake_chat)
    hdr = _reg(client, "rec-solved-gate")
    client.put("/api/resume", json=RESUME_BODY, headers=hdr)

    r = client.post(
        "/api/recruiter/chat",
        json={"messages": [{"role": "user", "content": "Здравствуйте"}]},
        headers=hdr,
    )
    assert r.status_code == 409
    assert any("задач" in i for i in r.json()["detail"]["issues"])

    _solve_task(client, "rec-solved-gate")
    r = client.post(
        "/api/recruiter/chat",
        json={"messages": [{"role": "user", "content": "Здравствуйте"}]},
        headers=hdr,
    )
    assert r.status_code == 200


def test_questions_generated_and_status(client, monkeypatch):
    """После первого хода сгенерированы два вопроса; в status они видны со статусом asked."""
    from tests.conftest import wait_job
    import app.services.llm_handlers as handlers

    monkeypatch.setattr(handlers, "chat_completion", _recruiter_fake_chat)
    hdr = _ready_recruiter(client, "rec-qs")  # решена two-sum-ii
    _solve_task(client, "rec-qs", slug="merge-intervals")  # и ещё merge-intervals

    r = client.post(
        "/api/recruiter/chat",
        json={"messages": [{"role": "user", "content": "Здравствуйте"}]},
        headers=hdr,
    )
    assert r.status_code == 200
    job = wait_job(client, hdr, r.json()["job_id"])
    assert job["status"] == "done"

    st = client.get("/api/recruiter/status", headers=hdr).json()
    assert st["interview_ready"] is True
    assert st["solved_count"] == 2
    qs = {q["kind"]: q for q in st["questions"]}
    assert set(qs) == {"task", "tech"}
    # фейковая LLM задала оба вопроса в первом же ответе — детекция их отметила
    assert all(q["asked"] for q in st["questions"])
    # вопрос по задаче — про одну из решённых, форма «почему … а не …»
    titles = ["Сумма двух в отсортированном", "Объединение интервалов"]
    assert any(t in qs["task"]["text"] for t in titles) and "а не" in qs["task"]["text"]
    # вопрос по технологии — из стека резюме
    techs = ["Python", "Django", "PostgreSQL", "C++", "Git", "Docker"]
    assert any(t in qs["tech"]["text"] for t in techs) and "а не" in qs["tech"]["text"]


def test_question_detection_and_recommendation_gate(client, monkeypatch):
    """Вопросы отмечаются только когда рекрутёр их реально задал; рекомендации — после обоих.

    Ответы студента на вопросы попадают в промпт рекомендаций.
    """
    from tests.conftest import wait_job
    import app.services.llm_handlers as handlers

    state = {"ask": False, "rec_content": None}

    async def fake_chat(messages, db=None, temperature=0.4, max_tokens=1200, timeout_sec=None):
        if messages[0]["content"].startswith("Ты — опытный tech-рекрутер"):
            state["rec_content"] = messages[1]["content"]
            return "Рекомендации: глубина ответов на технические вопросы хорошая."
        if not state["ask"]:
            return "Здравствуйте! Расскажите о вашем последнем проекте."
        qs = re.findall(r"^\d+\) (.+)$", messages[0]["content"], re.M)
        return "Здравствуйте! " + " ".join(qs)

    monkeypatch.setattr(handlers, "chat_completion", fake_chat)
    hdr = _ready_recruiter(client, "rec-detect")

    # ход 1: рекрутёр вопросы не задал — оба остаются unasked, рекомендации заблокированы
    r = client.post(
        "/api/recruiter/chat",
        json={"messages": [{"role": "user", "content": "Здравствуйте"}]},
        headers=hdr,
    )
    wait_job(client, hdr, r.json()["job_id"])
    st = client.get("/api/recruiter/status", headers=hdr).json()
    assert len(st["questions"]) == 2 and all(not q["asked"] for q in st["questions"])
    r = client.post("/api/recruiter/recommendations", headers=hdr)
    assert r.status_code == 409 and "технические вопросы" in r.json()["detail"]

    # ход 2: рекрутёр задал оба вопроса (дословно из промпта) — детекция отметила их
    state["ask"] = True
    r = client.post(
        "/api/recruiter/chat",
        json={"messages": [{"role": "user", "content": "Да, расскажите."}]},
        headers=hdr,
    )
    wait_job(client, hdr, r.json()["job_id"])
    st = client.get("/api/recruiter/status", headers=hdr).json()
    assert all(q["asked"] for q in st["questions"])

    # ход 3: студент отвечает на вопросы
    answer = "Потому что массив отсортирован, два указателя экономнее хеш-таблицы по памяти."
    r = client.post(
        "/api/recruiter/chat",
        json={"messages": [{"role": "user", "content": answer}]},
        headers=hdr,
    )
    wait_job(client, hdr, r.json()["job_id"])

    # рекомендации доступны, и в промпт попали вопросы + ответ студента
    r = client.post("/api/recruiter/recommendations", headers=hdr)
    assert r.status_code == 200
    job = wait_job(client, hdr, r.json()["job_id"])
    assert job["status"] == "done"
    assert "Обязательные технические вопросы" in state["rec_content"]
    assert answer in state["rec_content"]


def test_build_questions_deterministic_with_seed():
    """Генерация вопросов детерминирована при фиксированном seed; разные собеседования — разные вопросы."""
    import random

    from app.schemas import ResumeData
    from app.services.recruiter_questions import build_questions

    data = ResumeData.model_validate(RESUME_BODY)
    solved = [
        {"id": 1, "slug": "two-sum-ii", "title": "Сумма двух в отсортированном", "pattern": "two_pointers", "level": "junior"},
        {"id": 2, "slug": "merge-intervals", "title": "Объединение интервалов", "pattern": "greedy", "level": "middle"},
    ]
    a = build_questions(solved, data, rng=random.Random(42))
    b = build_questions(solved, data, rng=random.Random(42))
    assert a == b
    assert set(a) == {"task", "tech"}
    assert "а не" in a["task"]["text"] and "а не" in a["tech"]["text"]
    # без решённых задач вопрос по задаче не генерируется, по технологии — да
    c = build_questions([], data, rng=random.Random(1))
    assert "task" not in c and "tech" in c
    # для БД-технологии альтернатива конкретная, а не category-fallback
    db_body = dict(RESUME_BODY, labs=[], courses=[])
    db_body["projects"] = [{"name": "X", "problem": "Y", "tech_stack": ["PostgreSQL"]}]
    d = build_questions(solved, ResumeData.model_validate(db_body), rng=random.Random(7))
    assert "MySQL" in d["tech"]["text"], d["tech"]["text"]
