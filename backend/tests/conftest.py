import os
import tempfile

_tmpdir = tempfile.mkdtemp(prefix="itraint-test-")
os.environ.setdefault("DATABASE_URL", f"sqlite:///{_tmpdir}/test.sqlite3")
os.environ["SECRET_KEY"] = "test-secret-key-0123456789abcdef0123456789abcdef"
os.environ["SEED_ON_START"] = "false"
os.environ["CORS_ORIGINS"] = ""

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.core.security import hash_password  # noqa: E402
from app.db import Base, SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Task, User  # noqa: E402
from app.seed.tasks_data import TASK_SEED  # noqa: E402
from app.services.sandbox import RunOutcome, TestOutcome  # noqa: E402

SEED_SLUGS = ["two-sum-ii", "merge-intervals"]


class FakeSandbox:
    """Заменяет docker: поведение кодируется префиксом кода."""

    def run(self, language, code, tests, timeout_sec=None, memory_mb=None):
        results = []
        for i, t in enumerate(tests):
            if code.startswith("//ce"):
                r = TestOutcome(name=t["name"], status="compile_error", stderr="fake compile error")
            elif code.startswith("//timeout") and i == 0:
                r = TestOutcome(name=t["name"], status="timeout")
            elif code.startswith("//failall"):
                r = TestOutcome(name=t["name"], status="wrong_answer", got_stdout="bad")
            elif code.startswith("//failfirst") and i == 0:
                r = TestOutcome(name=t["name"], status="wrong_answer", got_stdout="bad")
            else:
                r = TestOutcome(
                    name=t["name"], passed=True, status="ok",
                    got_stdout=t["expected_stdout"], time_ms=5,
                )
            results.append(r)
        if code.startswith("//ce"):
            status = "compile_error"
        elif any(not r.passed for r in results):
            status = next(r.status for r in results if not r.passed)
        else:
            status = "accepted"
        return RunOutcome(status=status, results=results, time_ms=sum(r.time_ms for r in results))

    def run_script(self, language, code, timeout_sec=None, memory_mb=None):
        """Для вайб-кодинга: реально исполняем собранный код (он из тестов)."""
        import contextlib
        import io

        if code.startswith("//timeout"):
            return {"status": "timeout", "exit_code": None, "stdout": "", "stderr": "timeout"}
        if code.startswith("//ce"):
            return {"status": "runtime_error", "exit_code": 1, "stdout": "", "stderr": "SyntaxError: fake"}
        buf = io.StringIO()
        try:
            with contextlib.redirect_stdout(buf):
                exec(compile(code, "main.py", "exec"), {"__name": "__main__"})
            return {"status": "ok", "exit_code": 0, "stdout": buf.getvalue(), "stderr": ""}
        except Exception as e:
            return {
                "status": "runtime_error", "exit_code": 1,
                "stdout": buf.getvalue(), "stderr": type(e).__name__ + ": " + str(e),
            }


@pytest.fixture(autouse=True)
def fake_sandbox(monkeypatch):
    import app.services.contribute as contribute_mod
    import app.services.grading as grading_mod
    import app.services.vibe_runner as vibe_mod

    monkeypatch.setattr(grading_mod, "get_sandbox", lambda: FakeSandbox())
    monkeypatch.setattr(contribute_mod, "get_sandbox", lambda: FakeSandbox())
    monkeypatch.setattr(vibe_mod, "get_sandbox", lambda: FakeSandbox())


@pytest.fixture(scope="session", autouse=True)
def _db():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        for item in TASK_SEED:
            if item["slug"] in SEED_SLUGS and not db.query(Task).filter_by(slug=item["slug"]).first():
                db.add(Task(**item))
        if not db.query(User).filter_by(email="admin@example.com").first():
            db.add(User(email="admin@example.com", username="admin1",
                        hashed_password=hash_password("adminpass1"), role="admin"))
        if not db.query(User).filter_by(email="stud@example.com").first():
            db.add(User(email="stud@example.com", username="student1",
                        hashed_password=hash_password("studentpass1"), role="student"))
        db.commit()
    finally:
        db.close()
    yield


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def _login(client, login, password):
    r = client.post("/api/auth/login", json={"login": login, "password": password})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture
def student_headers(client):
    return _login(client, "student1", "studentpass1")


@pytest.fixture
def admin_headers(client):
    return _login(client, "admin@example.com", "adminpass1")


def wait_job(client, headers, job_id, timeout: float = 20.0) -> dict:
    """Дождаться завершения LLM-job'а (воркер обрабатывает его асинхронно)."""
    import time

    deadline = time.time() + timeout
    body: dict = {}
    while time.time() < deadline:
        r = client.get(f"/api/llm/jobs/{job_id}", headers=headers)
        assert r.status_code == 200, r.text
        body = r.json()
        if body["status"] in ("done", "error"):
            return body
        time.sleep(0.15)
    raise AssertionError(f"job {job_id} не завершился за {timeout}s: {body}")

