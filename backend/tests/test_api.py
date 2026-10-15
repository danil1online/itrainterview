"""Тесты API задач: список/фильтры, run/submit, история, ИИ-помощник и фидбек."""

import json

def test_task_list_and_filters(client, student_headers):
    r = client.get("/api/tasks", headers=student_headers)
    assert r.status_code == 200
    slugs = {t["slug"] for t in r.json()}
    assert {"two-sum-ii", "merge-intervals"} <= slugs
    junior = client.get("/api/tasks?level=junior", headers=student_headers).json()
    assert all(t["level"] == "junior" for t in junior)
    pat = client.get("/api/tasks?pattern=greedy", headers=student_headers).json()
    assert {t["slug"] for t in pat} == {"merge-intervals"}


def test_task_detail_hides_nonsample_expected(client, student_headers):
    r = client.get("/api/tasks/two-sum-ii", headers=student_headers)
    assert r.status_code == 200
    data = r.json()
    assert len(data["tests"]) == 1 and data["tests"][0]["sample"] is True

    from app.seed.tasks_data import TASK_SEED

    task = next(t for t in TASK_SEED if t["slug"] == "two-sum-ii")
    hidden = [t for t in task["tests"] if not t.get("sample")]
    assert len(hidden) >= 3


def test_run_sample_only(client, student_headers):
    r = client.post(
        "/api/tasks/two-sum-ii/run",
        json={"language": "python", "code": "print('1 2')"},
        headers=student_headers,
    )
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "accepted"
    assert data["total_count"] == 1  # только sample-тест


def test_submit_accepted_and_history(client, student_headers):
    r = client.post(
        "/api/tasks/two-sum-ii/submit",
        json={"language": "python", "code": "OK", "want_feedback": False},
        headers=student_headers,
    )
    assert r.status_code == 200
    sub = r.json()
    assert sub["status"] == "accepted"
    assert sub["passed_count"] == sub["total_count"]

    hist = client.get("/api/submissions?task_slug=two-sum-ii", headers=student_headers).json()
    assert any(s["id"] == sub["id"] for s in hist)

    detail = client.get("/api/tasks/two-sum-ii", headers=student_headers).json()
    assert detail["solved"] is True


def test_submit_wrong_answer(client, student_headers):
    r = client.post(
        "/api/tasks/merge-intervals/submit",
        json={"language": "python", "code": "//failall", "want_feedback": False},
        headers=student_headers,
    )
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "wrong_answer"
    assert data["passed_count"] == 0


def test_submit_compile_error(client, student_headers):
    r = client.post(
        "/api/tasks/two-sum-ii/submit",
        json={"language": "java", "code": "//ce", "want_feedback": False},
        headers=student_headers,
    )
    assert r.json()["status"] == "compile_error"


def test_submission_visibility(client, student_headers, admin_headers):
    sub_id = client.post(
        "/api/tasks/two-sum-ii/submit",
        json={"language": "python", "code": "OK", "want_feedback": False},
        headers=student_headers,
    ).json()["id"]
    assert client.get(f"/api/submissions/{sub_id}", headers=admin_headers).status_code == 200
    from app.db import SessionLocal
    from app.models import User

    db = SessionLocal()
    other = User(email="other2@example.com", username="other2", hashed_password="x", role="student")
    db.add(other)
    db.commit()
    tok = client.post("/api/auth/register", json={"email": "o3@example.com", "username": "o3", "password": "secret123"}).json()
    db.close()
    r = client.get(f"/api/submissions/{sub_id}", headers={"Authorization": f"Bearer {tok['access_token']}"})
    assert r.status_code == 404


def test_retitle_and_variant_saved(client, student_headers, monkeypatch):
    from tests.conftest import wait_job
    import app.services.llm_handlers as handlers

    async def fake_generate(task, db=None, theme=None):
        return {"title": "Новая легенда", "legend": "Совершенно новый сюжет про задачу. Формат ввода тот же."}

    monkeypatch.setattr(handlers, "generate_variant", fake_generate)
    r = client.post("/api/tasks/two-sum-ii/retitle", json={"save": True}, headers=student_headers)
    assert r.status_code == 200
    job = wait_job(client, student_headers, r.json()["job_id"])
    assert job["status"] == "done"
    import json as _json
    assert _json.loads(job["result"])["title"] == "Новая легенда"

    detail = client.get("/api/tasks/two-sum-ii", headers=student_headers).json()
    assert detail["legend"].startswith("Совершенно новый сюжет")


def test_generate_set_batch(client, student_headers, monkeypatch):
    """Комплект: по job'у на задачу, все легенды обновляются в очереди."""
    from tests.conftest import wait_job
    import app.services.llm_handlers as handlers

    async def fake_generate(task, db=None, theme=None):
        return {"title": f"Сюжет: {task.slug}", "legend": f"Новый сюжет про {task.slug}. Формат ввода тот же."}

    monkeypatch.setattr(handlers, "generate_variant", fake_generate)
    r = client.post(
        "/api/tasks/generate-set",
        json={"slugs": ["two-sum-ii", "merge-intervals"], "theme": None},
        headers=student_headers,
    )
    assert r.status_code == 200
    job_ids = r.json()["job_ids"]
    assert len(job_ids) == 2

    for jid in job_ids:
        job = wait_job(client, student_headers, jid)
        assert job["status"] == "done", job

    d1 = client.get("/api/tasks/two-sum-ii", headers=student_headers).json()
    d2 = client.get("/api/tasks/merge-intervals", headers=student_headers).json()
    assert d1["legend"].startswith("Новый сюжет про two-sum-ii")
    assert d2["legend"].startswith("Новый сюжет про merge-intervals")


def test_generate_set_fallback_skips_inactive(client, admin_headers, student_headers, monkeypatch):
    """Fallback «всех задач» не включает деактивированные (мягко удалённые)."""
    from tests.conftest import wait_job
    import app.services.llm_handlers as handlers
    from app.db import SessionLocal
    from app.models import Task

    async def fake_generate(task, db=None, theme=None):
        return {"title": f"Сюжет: {task.slug}", "legend": f"Новый сюжет про {task.slug}. Формат ввода тот же."}

    monkeypatch.setattr(handlers, "generate_variant", fake_generate)

    # оставляем активными только две задачи — остальные мягко удаляем
    db = SessionLocal()
    keep = {t.id for t in db.query(Task).all() if t.slug in ("two-sum-ii", "merge-intervals")}
    for t in db.query(Task).all():
        if t.id not in keep:
            t.is_active = False
    db.commit()
    db.close()

    r = client.post("/api/tasks/generate-set", json={}, headers=student_headers)
    assert r.status_code == 200
    job_ids = r.json()["job_ids"]
    assert len(job_ids) == 2
    for jid in job_ids:
        assert wait_job(client, student_headers, jid)["status"] == "done"


def test_limit_clamped_not_500(client, student_headers):
    """Отрицательный limit не даёт 500 — клампится к 1."""
    assert client.get("/api/assistant/history?task_slug=two-sum-ii&limit=-1", headers=student_headers).status_code == 200
    assert client.get("/api/submissions?limit=-1", headers=student_headers).status_code == 200
    assert client.get("/api/recruiter/history?limit=-5", headers=student_headers).status_code == 200


def test_retitle_llm_error(client, student_headers, monkeypatch):
    from tests.conftest import wait_job
    import app.services.llm_handlers as handlers
    from app.services.llm import LLMError

    async def broken(task, db=None, theme=None):
        raise LLMError("LLM недоступен")

    monkeypatch.setattr(handlers, "generate_variant", broken)
    r = client.post("/api/tasks/two-sum-ii/retitle", json={"save": False}, headers=student_headers)
    assert r.status_code == 200
    job = wait_job(client, student_headers, r.json()["job_id"], timeout=60)
    assert job["status"] == "error"
    assert "LLM недоступен" in (job["error"] or "")


def test_assistant_chat_and_history(client, student_headers, monkeypatch):
    from tests.conftest import wait_job
    import app.services.llm_handlers as handlers

    async def fake_chat(messages, db=None, temperature=0.4, max_tokens=1200, timeout_sec=None):
        assert messages[0]["role"] == "system"
        return "Попробуй два указателя."

    monkeypatch.setattr(handlers, "chat_completion", fake_chat)
    r = client.post(
        "/api/assistant/chat",
        json={
            "task_slug": "two-sum-ii",
            "messages": [{"role": "user", "content": "С чего начать?"}],
            "code": "print(1)",
            "language": "python",
            "mode": "hint",
        },
        headers=student_headers,
    )
    assert r.status_code == 200
    job = wait_job(client, student_headers, r.json()["job_id"])
    assert job["status"] == "done" and job["result"] == "Попробуй два указателя."

    hist = client.get("/api/assistant/history?task_slug=two-sum-ii", headers=student_headers).json()
    roles = [m["role"] for m in hist]
    assert roles == ["user", "assistant"]


def test_feedback_generation(client, student_headers, monkeypatch):
    from tests.conftest import wait_job
    import app.services.grading as grading_mod

    async def fake_chat(messages, db=None, temperature=0.4, max_tokens=1200, timeout_sec=None):
        return "Ошибка в граничном случае."

    monkeypatch.setattr(grading_mod, "chat_completion", fake_chat)
    sub = client.post(
        "/api/tasks/two-sum-ii/submit",
        json={"language": "python", "code": "//failfirst", "want_feedback": True},
        headers=student_headers,
    ).json()
    # сабмит отвечает сразу; фидбек ещё генерируется в очереди
    assert sub["feedback_job_id"] is not None
    job = wait_job(client, student_headers, sub["feedback_job_id"])
    assert job["status"] == "done" and job["result"] == "Ошибка в граничном случае."
    sub = client.get(f"/api/submissions/{sub['id']}", headers=student_headers).json()
    assert sub["ai_feedback"] == "Ошибка в граничном случае."


def test_run_saves_runlog_for_assistant(client, student_headers, monkeypatch):
    """Запуск (run) сохраняется и попадает в контекст ИИ-помощника со stderr."""
    from tests.conftest import wait_job
    import app.services.llm_handlers as handlers

    r = client.post(
        "/api/tasks/two-sum-ii/run",
        json={"language": "python", "code": "//failall"},
        headers=student_headers,
    )
    assert r.status_code == 200 and r.json()["status"] == "wrong_answer"

    captured = {}

    async def fake_chat(messages, db=None, temperature=0.4, max_tokens=1200, timeout_sec=None):
        captured["messages"] = messages
        return "ok"

    monkeypatch.setattr(handlers, "chat_completion", fake_chat)
    r = client.post(
        "/api/assistant/chat",
        json={
            "task_slug": "two-sum-ii",
            "messages": [{"role": "user", "content": "В чем ошибка?"}],
            "code": "print('0 0')",
            "language": "python",
            "mode": "explain",
        },
        headers=student_headers,
    )
    assert wait_job(client, student_headers, r.json()["job_id"])["status"] == "done"
    context = "\n".join(m["content"] for m in captured["messages"])
    assert "Последний запуск" in context
    assert "язык=python" in context
    assert "wrong_answer" in context


def test_assistant_warns_on_wrong_interpreter(client, student_headers, monkeypatch):
    """Java-код в python-интерпретаторе: контекст содержит предупреждение о несоответствии."""
    from tests.conftest import wait_job
    import app.services.llm_handlers as handlers

    captured = {}

    async def fake_chat(messages, db=None, temperature=0.4, max_tokens=1200, timeout_sec=None):
        captured["messages"] = messages
        return "ok"

    monkeypatch.setattr(handlers, "chat_completion", fake_chat)
    r = client.post(
        "/api/assistant/chat",
        json={
            "task_slug": "two-sum-ii",
            "messages": [{"role": "user", "content": "В чем ошибка в программе?"}],
            "code": "public class Main { public static void main(String[] a) {} }",
            "language": "python",
            "mode": "explain",
        },
        headers=student_headers,
    )
    assert wait_job(client, student_headers, r.json()["job_id"])["status"] == "done"
    context = "\n".join(m["content"] for m in captured["messages"])
    assert "маркеры языка java" in context
    assert "не в том интерпретаторе" in context


def test_retitle_theme_forwarded(client, student_headers, monkeypatch):
    from tests.conftest import wait_job
    import app.services.llm_handlers as handlers

    captured = {}

    async def fake_generate(task, db=None, theme=None):
        captured["theme"] = theme
        return {"title": "Новая легенда", "legend": "Совершенно новый сюжет про задачу. Формат ввода тот же."}

    monkeypatch.setattr(handlers, "generate_variant", fake_generate)
    r = client.post(
        "/api/tasks/two-sum-ii/retitle",
        json={"save": False, "theme": "космос"},
        headers=student_headers,
    )
    assert r.status_code == 200
    assert wait_job(client, student_headers, r.json()["job_id"])["status"] == "done"
    assert captured["theme"] == "космос"


def test_retitle_appends_missing_format(client, student_headers, monkeypatch):
    """Слабая модель уронила разделы формата — они доклеиваются из оригинала."""
    from tests.conftest import wait_job
    import app.services.assistant as assistant_svc

    async def fake_chat(messages, db=None, temperature=0.9, max_tokens=1500, timeout_sec=None):
        return json.dumps(
            {"title": "Космический транзит", "legend": "Курьер в космосе должен найти пару цен. Ограничения те же."},
            ensure_ascii=False,
        )

    monkeypatch.setattr(assistant_svc, "chat_completion", fake_chat)
    r = client.post("/api/tasks/merge-intervals/retitle", json={"save": False}, headers=student_headers)
    assert r.status_code == 200
    job = wait_job(client, student_headers, r.json()["job_id"])
    assert job["status"] == "done"
    legend = json.loads(job["result"])["legend"]
    assert "Формат ввода" in legend and "Формат вывода" in legend


def test_retitle_retries_on_llm_error(client, student_headers, monkeypatch):
    from tests.conftest import wait_job
    import app.services.assistant as assistant_svc
    from app.services.llm import LLMError

    calls = {"n": 0}

    async def flaky_chat(messages, db=None, temperature=0.9, max_tokens=1500, timeout_sec=None):
        calls["n"] += 1
        if calls["n"] == 1:
            raise LLMError("Модель вернула некорректный JSON")
        return json.dumps(
            {"title": "Новый сюжет", "legend": "Совершенно новый сюжет про задачу. Формат ввода тот же."},
            ensure_ascii=False,
        )

    monkeypatch.setattr(assistant_svc, "chat_completion", flaky_chat)
    r = client.post("/api/tasks/two-sum-ii/retitle", json={"save": False}, headers=student_headers)
    assert r.status_code == 200
    job = wait_job(client, student_headers, r.json()["job_id"])
    assert job["status"] == "done"
    assert calls["n"] == 2

