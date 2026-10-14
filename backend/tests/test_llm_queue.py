"""Тесты LLM-очереди (job + поллинг) и семафора песочницы."""

import asyncio
import threading
import time


def _submit(client, hdr, content, kind="assistant_chat"):
    r = client.post(
        "/api/llm/jobs",
        json={"kind": kind, "messages": [{"role": "user", "content": content}]},
        headers=hdr,
    )
    assert r.status_code == 202, r.text
    return r.json()["id"]


def _status(client, hdr, job_id):
    r = client.get(f"/api/llm/jobs/{job_id}", headers=hdr)
    assert r.status_code == 200, r.text
    return r.json()


def test_fifo_order_and_position(client, student_headers, monkeypatch):
    """FIFO: пока первая задача выполняется, вторая стоит в очереди с position=1."""
    from tests.conftest import wait_job
    import app.services.llm_handlers as handlers

    order = []

    async def fake_chat(messages, db=None, temperature=0.4, max_tokens=1200, timeout_sec=None):
        tag = messages[-1]["content"]
        if tag == "slow":
            await asyncio.sleep(1.5)
        order.append(tag)
        return f"ответ-{tag}"

    monkeypatch.setattr(handlers, "chat_completion", fake_chat)

    slow = _submit(client, student_headers, "slow")
    # ждём, пока медленная задача взята в работу
    deadline = time.time() + 10
    while time.time() < deadline:
        if _status(client, student_headers, slow)["status"] == "running":
            break
        time.sleep(0.1)
    assert _status(client, student_headers, slow)["status"] == "running"

    a = _submit(client, student_headers, "a")
    b = _submit(client, student_headers, "b")
    # обе pending: a — следующая (0), b — за ней (1)
    assert _status(client, student_headers, a)["position"] == 0
    assert _status(client, student_headers, b)["position"] == 1

    ja = wait_job(client, student_headers, a)
    jb = wait_job(client, student_headers, b)
    js = wait_job(client, student_headers, slow)
    assert (js["result"], ja["result"], jb["result"]) == ("ответ-slow", "ответ-a", "ответ-b")
    assert order == ["slow", "a", "b"]


def test_retries_then_success(client, student_headers, monkeypatch):
    """Сбой модели не терзает студента: ретраи до успешного ответа."""
    from tests.conftest import wait_job
    import app.services.llm_handlers as handlers
    import app.services.llm_queue as queue
    from app.services.llm import LLMError

    monkeypatch.setattr(queue, "RETRY_BACKOFFS", (0.05, 0.05, 0.05))
    calls = {"n": 0}

    async def flaky(messages, db=None, temperature=0.4, max_tokens=1200, timeout_sec=None):
        calls["n"] += 1
        if calls["n"] < 3:
            raise LLMError("модель не отвечает")
        return "готово"

    monkeypatch.setattr(handlers, "chat_completion", flaky)
    job_id = _submit(client, student_headers, "привет")
    job = wait_job(client, student_headers, job_id, timeout=30)
    assert job["status"] == "done" and job["result"] == "готово"
    assert calls["n"] == 3


def test_error_after_max_attempts(client, student_headers, monkeypatch):
    """Три неудачных попытки — job в статусе error с причиной."""
    from tests.conftest import wait_job
    import app.services.llm_handlers as handlers
    import app.services.llm_queue as queue
    from app.services.llm import LLMError

    monkeypatch.setattr(queue, "RETRY_BACKOFFS", (0.05, 0.05, 0.05))

    async def broken(messages, db=None, temperature=0.4, max_tokens=1200, timeout_sec=None):
        raise LLMError("LLM недоступен")

    monkeypatch.setattr(handlers, "chat_completion", broken)
    job_id = _submit(client, student_headers, "привет")
    job = wait_job(client, student_headers, job_id, timeout=30)
    assert job["status"] == "error"
    assert "LLM недоступен" in (job["error"] or "")


def test_isolation_between_users(client, monkeypatch):
    """Чужие job'ы не видны и не отменяются."""
    from tests.conftest import wait_job
    import app.services.llm_handlers as handlers

    async def fake_chat(messages, db=None, temperature=0.4, max_tokens=1200, timeout_sec=None):
        return "ok"

    monkeypatch.setattr(handlers, "chat_completion", fake_chat)
    hdr_a = _reg(client, "q-iso-a")
    job_id = _submit(client, hdr_a, "секрет")
    wait_job(client, hdr_a, job_id)

    tok = client.post(
        "/api/auth/register", json={"email": "q-iso-b@example.com", "username": "q-isob", "password": "secret123"}
    ).json()
    hdr_b = {"Authorization": f"Bearer {tok['access_token']}"}

    assert client.get(f"/api/llm/jobs/{job_id}", headers=hdr_b).status_code == 404
    assert client.delete(f"/api/llm/jobs/{job_id}", headers=hdr_b).status_code == 404
    batch = client.get(f"/api/llm/jobs?ids={job_id}", headers=hdr_b).json()
    assert batch == []


def test_cancel_pending_job(client, student_headers, monkeypatch):
    """Отмена ожидающей задачи: воркер её не выполнит."""
    import app.services.llm_handlers as handlers

    ran = []

    async def fake_chat(messages, db=None, temperature=0.4, max_tokens=1200, timeout_sec=None):
        tag = messages[-1]["content"]
        if tag == "blocker":
            await asyncio.sleep(2.0)
        ran.append(tag)
        return f"ответ-{tag}"

    monkeypatch.setattr(handlers, "chat_completion", fake_chat)

    blocker = _submit(client, student_headers, "blocker")
    deadline = time.time() + 10
    while time.time() < deadline:
        if _status(client, student_headers, blocker)["status"] == "running":
            break
        time.sleep(0.1)

    victim = _submit(client, student_headers, "victim")
    assert client.delete(f"/api/llm/jobs/{victim}", headers=student_headers).status_code == 200
    assert _status(client, student_headers, victim)["status"] == "cancelled"

    # дожидаемся освобождения очереди
    deadline = time.time() + 15
    while time.time() < deadline:
        if _status(client, student_headers, blocker)["status"] == "done":
            break
        time.sleep(0.2)
    time.sleep(1.0)  # даём воркеру время — отменённая не должна быть взята
    assert ran.count("victim") == 0
    assert _status(client, student_headers, victim)["status"] == "cancelled"


def test_batch_get_jobs(client, student_headers, monkeypatch):
    """Пакетный статус: свои job'ы возвращаются, чужие — нет, мусор — 422."""
    from tests.conftest import wait_job
    import app.services.llm_handlers as handlers

    async def fake_chat(messages, db=None, temperature=0.4, max_tokens=1200, timeout_sec=None):
        return "ok"

    monkeypatch.setattr(handlers, "chat_completion", fake_chat)
    j1 = _submit(client, student_headers, "один")
    j2 = _submit(client, student_headers, "два")
    wait_job(client, student_headers, j1)
    wait_job(client, student_headers, j2)

    body = client.get(f"/api/llm/jobs?ids={j1},{j2}", headers=student_headers).json()
    assert [x["id"] for x in body] == [j1, j2]
    assert all(x["status"] == "done" for x in body)

    assert client.get("/api/llm/jobs?ids=abc", headers=student_headers).status_code == 422
    assert client.get("/api/llm/jobs?ids=", headers=student_headers).status_code == 422


def _reg(client, name):
    r = client.post(
        "/api/auth/register",
        json={"email": f"{name}@example.com", "username": name, "password": "secret123"},
    )
    assert r.status_code in (200, 201), r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_sandbox_slot_limit(client, monkeypatch):
    """Семафор: при лимите 1 второй acquire ждёт освобождения слота."""
    from app.db import SessionLocal
    from app.models import SystemSetting
    import app.services.sandbox as sandbox

    db = SessionLocal()
    row = db.get(SystemSetting, "sandbox_max_concurrent")
    if row is None:
        db.add(SystemSetting(key="sandbox_max_concurrent", value="1"))
    else:
        row.value = "1"
    db.commit()
    db.close()

    # сбросим кэш семафора, чтобы он пересоздался под новый лимит
    with sandbox._sem_lock:
        sandbox._sem = None
        sandbox._sem_limit = None

    got_second = threading.Event()

    def second():
        sandbox.slot_acquire()
        got_second.set()
        sandbox.slot_release()

    t = threading.Thread(target=second, daemon=True)
    sandbox.slot_acquire()  # занимаем единственный слот
    t.start()
    assert not got_second.wait(1.0), "второй acquire не заблокирован при лимите 1"
    sandbox.slot_release()
    assert got_second.wait(3.0), "освобождение слота не разблокировало ожидание"
