"""Тесты резюме (хранение, навыки, DOCX) и скрининга с рекрутером."""

import io
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

    async def fake_chat(messages, db=None, temperature=0.4, max_tokens=1200, timeout_sec=None):
        if messages[0]["content"].startswith("Ты — опытный tech-рекрутер"):
            return "Рекомендации: усильте Docker и Git; рассказывайте о проектах по STAR."
        return "Здравствуйте! Меня зовут Алексей, отдел кадров. Расскажите о вашем последнем проекте."

    monkeypatch.setattr(handlers, "chat_completion", fake_chat)

    hdr = _reg(client, "rec-chat")
    client.put("/api/resume", json=RESUME_BODY, headers=hdr)

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
    """Новый пользователь с готовым резюме; возвращает (hdr, fake_llm-патч через monkeypatch)."""
    import app.api.recruiter as recruiter_api

    hdr = _reg(client, name)
    client.put("/api/resume", json=RESUME_BODY, headers=hdr)
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

    async def fake_chat(messages, db=None, temperature=0.4, max_tokens=1200, timeout_sec=None):
        return "Рек: ответ" if messages[0]["role"] == "system" and "скрининг" in messages[0]["content"] else "Рекомендации: усильте тесты."

    monkeypatch.setattr(handlers, "chat_completion", fake_chat)
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

    async def fake_chat(messages, db=None, temperature=0.4, max_tokens=1200, timeout_sec=None):
        return "Рекомендации: добавьте Docker."

    monkeypatch.setattr(handlers, "chat_completion", fake_chat)
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

    async def fake_chat(messages, db=None, temperature=0.4, max_tokens=1200, timeout_sec=None):
        return "Рек: ответ" if "скрининг" in messages[0]["content"] else "Рекомендации."

    monkeypatch.setattr(handlers, "chat_completion", fake_chat)
    hdr = _ready_recruiter(client, "rec-reset")
    _chat_once(client, hdr)
    _recommend_once(client, hdr)
    assert len(client.get("/api/recruiter/history", headers=hdr).json()) == 2

    r = client.post("/api/recruiter/reset", headers=hdr)
    assert r.status_code == 200 and r.json()["ok"] is True
    assert client.get("/api/recruiter/history", headers=hdr).json() == []
    assert client.get("/api/recruiter/recommendation", headers=hdr).status_code == 404


def test_resume_change_resets_recruiter_history(client, monkeypatch):
    import app.services.llm_handlers as handlers

    async def fake_chat(messages, db=None, temperature=0.4, max_tokens=1200, timeout_sec=None):
        return "Рек: ответ" if "скрининг" in messages[0]["content"] else "Рекомендации."

    monkeypatch.setattr(handlers, "chat_completion", fake_chat)
    hdr = _ready_recruiter(client, "rec-autoset")
    _chat_once(client, hdr)
    _recommend_once(client, hdr)
    assert len(client.get("/api/recruiter/history", headers=hdr).json()) == 2

    # сохранение без изменений — историю не трогает
    r = client.put("/api/resume", json=RESUME_BODY, headers=hdr)
    assert r.json()["recruiter_reset"] is False
    assert len(client.get("/api/recruiter/history", headers=hdr).json()) == 2

    # изменение резюме — история и рекомендации сбрасываются
    changed = dict(RESUME_BODY, first_name="Новое")
    r = client.put("/api/resume", json=changed, headers=hdr)
    assert r.json()["recruiter_reset"] is True
    assert client.get("/api/recruiter/history", headers=hdr).json() == []
    assert client.get("/api/recruiter/recommendation", headers=hdr).status_code == 404
