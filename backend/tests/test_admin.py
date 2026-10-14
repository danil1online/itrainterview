def test_admin_access_denied_for_student(client, student_headers):
    assert client.get("/api/admin/users", headers=student_headers).status_code == 403
    assert client.get("/api/admin/stats").status_code == 401


def test_admin_users_list(client, admin_headers):
    r = client.get("/api/admin/users", headers=admin_headers)
    assert r.status_code == 200
    users = {u["username"]: u for u in r.json()}
    assert "admin1" in users and users["admin1"]["role"] == "admin"
    assert "submissions" in users["student1"]


def test_admin_cannot_block_self(client, admin_headers):
    from app.db import SessionLocal
    from app.models import User

    db = SessionLocal()
    aid = db.query(User).filter_by(username="admin1").first().id
    db.close()
    assert client.patch(f"/api/admin/users/{aid}", json={"is_active": False}, headers=admin_headers).status_code == 400


def test_admin_reset_password(client, admin_headers):
    from app.db import SessionLocal
    from app.models import User

    db = SessionLocal()
    uid = db.query(User).filter_by(username="student1").first().id
    db.close()
    r = client.post(f"/api/admin/users/{uid}/reset_password?new_password=brandnew1", headers=admin_headers)
    assert r.status_code == 200
    assert client.post("/api/auth/login", json={"login": "student1", "password": "brandnew1"}).status_code == 200
    # вернуть как было
    client.post(f"/api/admin/users/{uid}/reset_password?new_password=studentpass1", headers=admin_headers)


def test_admin_task_crud(client, admin_headers):
    payload = {
        "slug": "brand-new-task",
        "title": "Новая задача тест",
        "legend": "Описание новой тестовой задачи для админского CRUD.",
        "pattern": "dp",
        "level": "junior",
        "hints": [],
        "tests": [{"name": "t1", "stdin": "1\n", "expected_stdout": "1", "sample": True}],
        "reference_solution": "",
        "is_active": True,
    }
    r = client.post("/api/admin/tasks", json=payload, headers=admin_headers)
    assert r.status_code == 201
    tid = r.json()["id"]
    assert client.post("/api/admin/tasks", json=payload, headers=admin_headers).status_code == 409

    payload["title"] = "Обновлённая задача"
    r = client.put(f"/api/admin/tasks/{tid}", json=payload, headers=admin_headers)
    assert r.status_code == 200 and r.json()["title"] == "Обновлённая задача"

    assert client.delete(f"/api/admin/tasks/{tid}", headers=admin_headers).status_code == 200
    # студент не видит деактивированную задачу
    from tests.conftest import _login

    hdr = _login(client, "admin@example.com", "adminpass1")
    assert "brand-new-task" not in {t["slug"] for t in client.get("/api/tasks", headers=hdr).json()}


def test_admin_settings(client, admin_headers):
    r = client.put(
        "/api/admin/settings",
        json={"values": {"llm_model": "custom-model.gguf", "sandbox_timeout_sec": "7"}},
        headers=admin_headers,
    )
    assert r.status_code == 200
    s = client.get("/api/admin/settings", headers=admin_headers).json()
    assert s["llm_model"] == "custom-model.gguf"
    assert s["sandbox_timeout_sec"] == "7"

    assert client.put("/api/admin/settings", json={"values": {"evil_key": "1"}}, headers=admin_headers).status_code == 400
    assert client.put("/api/admin/settings", json={"values": {"sandbox_timeout_sec": "999"}}, headers=admin_headers).status_code == 400


def test_admin_results_and_stats(client, admin_headers):
    hdr = admin_headers
    client.post(
        "/api/tasks/two-sum-ii/submit",
        json={"language": "python", "code": "OK", "want_feedback": False},
        headers=hdr,
    )
    r = client.get("/api/admin/results", headers=hdr)
    assert r.status_code == 200
    rows = r.json()
    assert len(rows) >= 1
    assert {"username", "task_slug", "status", "language"} <= set(rows[0].keys())

    stats = client.get("/api/admin/stats", headers=hdr).json()
    for key in ("total_users", "total_tasks", "total_submissions", "by_pattern", "top_solvers", "per_day"):
        assert key in stats

    csv_resp = client.get("/api/admin/export/submissions.csv", headers=hdr)
    assert csv_resp.status_code == 200
    assert "user;task_slug" in csv_resp.text


def test_admin_retitle_updates_task(client, admin_headers, monkeypatch):
    from tests.conftest import wait_job
    import app.services.llm_handlers as handlers

    async def fake_generate(task, db=None, theme=None):
        return {"title": "Админ ретайт", "legend": "Обновлённая легенда от админа. Формат ввода прежний."}

    monkeypatch.setattr(handlers, "generate_variant", fake_generate)
    from app.db import SessionLocal
    from app.models import Task

    db = SessionLocal()
    tid = db.query(Task).filter_by(slug="two-sum-ii").first().id
    db.close()
    r = client.post(f"/api/admin/tasks/{tid}/retitle", headers=admin_headers)
    assert r.status_code == 200
    job = wait_job(client, admin_headers, r.json()["job_id"])
    assert job["status"] == "done"
    hdr = admin_headers
    detail = client.get("/api/tasks/two-sum-ii", headers=hdr).json()
    assert detail["legend"].startswith("Обновлённая легенда от админа")


# ---------- Экспорт community-вклада ----------


def _export_payload(slug="community-test-task", tests=None, reference="print('ok')"):
    return {
        "slug": slug,
        "title": "Community тестовая задача",
        "legend": "Тестовая легенда для проверки экспорта community-вклада.",
        "pattern": "dp",
        "level": "junior",
        "hints": [],
        "tests": tests or [
            {"name": "sample", "stdin": "1\n", "expected_stdout": "1", "sample": True},
            {"name": "t2", "stdin": "2\n", "expected_stdout": "2", "sample": False},
        ],
        "reference_solution": reference,
        "is_active": True,
    }


def test_export_community_success(client, admin_headers):
    r = client.post("/api/admin/tasks", json=_export_payload(), headers=admin_headers)
    assert r.status_code == 201
    tid = r.json()["id"]
    r = client.post(
        f"/api/admin/tasks/{tid}/export-community",
        json={"author": "ivanov"},
        headers=admin_headers,
    )
    assert r.status_code == 200
    body = r.json()
    assert body["filename"].startswith("bank_community_ivanov_")
    assert body["filename"].endswith(".py")
    assert "TASKS" in body["content"] and "community-test-task" in body["content"]
    # сгенерированный файл — валидный Python со схемой банка
    ns = {}
    exec(body["content"], ns)  # noqa: S102 — контролируемый тестовый контент
    task = ns["TASKS"][0]
    assert task["slug"] == "community-test-task"
    assert any(t["sample"] for t in task["tests"])
    assert task["reference_solution"].strip()


def test_export_community_requires_sample(client, admin_headers):
    payload = _export_payload(slug="community-nosample")
    payload["tests"] = [
        {"name": "t1", "stdin": "1\n", "expected_stdout": "1", "sample": False},
        {"name": "t2", "stdin": "2\n", "expected_stdout": "2", "sample": False},
    ]
    tid = client.post("/api/admin/tasks", json=payload, headers=admin_headers).json()["id"]
    r = client.post(f"/api/admin/tasks/{tid}/export-community", json={"author": "a"}, headers=admin_headers)
    assert r.status_code == 422
    assert any("sample" in i for i in r.json()["detail"]["issues"])


def test_export_community_requires_reference(client, admin_headers):
    payload = _export_payload(slug="community-noref", reference="")
    tid = client.post("/api/admin/tasks", json=payload, headers=admin_headers).json()["id"]
    r = client.post(f"/api/admin/tasks/{tid}/export-community", json={"author": "a"}, headers=admin_headers)
    assert r.status_code == 422
    assert any("Эталон" in i for i in r.json()["detail"]["issues"])


def test_export_community_unknown_pattern(client, admin_headers):
    payload = _export_payload(slug="community-badpattern")
    payload["pattern"] = "unknown_pattern_xyz"
    tid = client.post("/api/admin/tasks", json=payload, headers=admin_headers).json()["id"]
    r = client.post(f"/api/admin/tasks/{tid}/export-community", json={"author": "a"}, headers=admin_headers)
    assert r.status_code == 422
    assert any("Паттерн" in i for i in r.json()["detail"]["issues"])


def test_export_community_reference_fails_sandbox(client, admin_headers):
    # FakeSandbox: код с префиксом //failall роняет все тесты
    payload = _export_payload(slug="community-badref", reference="//failall")
    tid = client.post("/api/admin/tasks", json=payload, headers=admin_headers).json()["id"]
    r = client.post(f"/api/admin/tasks/{tid}/export-community", json={"author": "a"}, headers=admin_headers)
    assert r.status_code == 422
    assert any("Эталон не проходит" in i for i in r.json()["detail"]["issues"])


def test_export_community_student_forbidden(client, student_headers):
    tid = client.post("/api/admin/tasks", json=_export_payload(slug="community-forbidden"), headers=student_headers)
    # студенту нельзя создать задачу — используем существующую из сида
    from app.db import SessionLocal
    from app.models import Task

    db = SessionLocal()
    tid = db.query(Task).filter_by(slug="two-sum-ii").first().id
    db.close()
    r = client.post(f"/api/admin/tasks/{tid}/export-community", json={"author": "a"}, headers=student_headers)
    assert r.status_code in (401, 403)
