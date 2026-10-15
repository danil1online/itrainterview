"""Тесты тренажёра «Вайб-кодинг»: CRUD, flow студента, мутанты, AST-гейт, чат."""


def _uniq(base: dict, name: str) -> dict:
    return dict(base, slug=base["slug"] + "-" + name)


def _reg(client, name):
    r = client.post(
        "/api/auth/register",
        json={"email": f"{name}@example.com", "username": name, "password": "secret123"},
    )
    assert r.status_code == 201, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


BUGFIX_TASK = {
    "slug": "vibe-t-null",
    "task_type": "bugfix",
    "title": "Тест null",
    "description_md": "Добейся обработки None.",
    "initial_code": "def f(x):\n    return x + 1\n",
    "hidden_tests": [
        {"name": "обычный", "code": "assert f(1) == 2"},
        {"name": "None как нуль", "code": "assert f(None) == 0"},
    ],
    "reference_solution": "def f(x):\n    if x is None:\n        return 0\n    return x + 1\n",
    "mutants": [],
    "min_mutants_caught": 0,
}

TESTS_TASK = {
    "slug": "vibe-t-tests",
    "task_type": "tests",
    "title": "Тесты для double",
    "description_md": "Напиши тесты.",
    "initial_code": (
        "def double(x):\n    return x * 2\n\n"
        "# === ВАШИ ТЕСТЫ НИЖЕ (функции test_*, внутри assert) ===\n"
    ),
    "hidden_tests": [],
    "reference_solution": "",
    "mutants": [
        {"name": "плюс два", "code": "def double(x):\n    return x + 2\n"},
        {"name": "умножить на три", "code": "def double(x):\n    return x * 3\n"},
    ],
    "min_mutants_caught": 2,
}

REFACTOR_TASK = {
    "slug": "vibe-t-ref",
    "task_type": "refactor",
    "title": "Распутай sign",
    "description_md": "Вложенность <= 2.",
    "initial_code": (
        "def sign(x):\n"
        "    if isinstance(x, int):\n"
        "        if x > 0:\n"
        "            if x >= 100:\n"
        '                return "big"\n'
        '            return "pos"\n'
        "        else:\n"
        '            return "nonpos"\n'
        '    return "bad"\n'
    ),
    "hidden_tests": [
        {"name": "pos", "code": 'assert sign(5) == "pos"'},
        {"name": "big", "code": 'assert sign(100) == "big"'},
        {"name": "nonpos", "code": 'assert sign(-1) == "nonpos"'},
        {"name": "bad", "code": 'assert sign("x") == "bad"'},
    ],
    "reference_solution": (
        "def sign(x):\n"
        "    if not isinstance(x, int):\n"
        '        return "bad"\n'
        "    if x <= 0:\n"
        '        return "nonpos"\n'
        "    if x >= 100:\n"
        '        return "big"\n'
        '    return "pos"\n'
    ),
    "mutants": [],
    "min_mutants_caught": 0,
}


# ------------------------------------------------------------------ CRUD админа


def test_admin_create_list_and_student_sees(client, admin_headers):
    r = client.post("/api/admin/vibe-tasks", json=_uniq(BUGFIX_TASK, "view"), headers=admin_headers)
    assert r.status_code == 201, r.text
    tid = r.json()["id"]

    lst = client.get("/api/admin/vibe-tasks", headers=admin_headers).json()
    assert any(t["id"] == tid for t in lst)

    hdr = _reg(client, "vibe-viewer")
    items = client.get("/api/vibe/tasks", headers=hdr).json()
    mine = [t for t in items if t["id"] == tid]
    assert mine and mine[0]["status"] is None


def test_admin_rejects_broken_reference(client, admin_headers):
    bad = dict(BUGFIX_TASK, slug="vibe-t-broken-ref", reference_solution="def f(x):\n    return x\n")
    r = client.post("/api/admin/vibe-tasks", json=bad, headers=admin_headers)
    assert r.status_code == 422
    assert "Эталон не проходит" in str(r.json()["detail"])


def test_admin_rejects_trivial_refactor(client, admin_headers):
    flat = dict(
        REFACTOR_TASK, slug="vibe-t-flat-initial",
        initial_code=REFACTOR_TASK["reference_solution"],
    )
    r = client.post("/api/admin/vibe-tasks", json=flat, headers=admin_headers)
    assert r.status_code == 422
    assert "тривиальна" in str(r.json()["detail"])


def test_admin_delete_conflict_and_disable(client, admin_headers):
    tid = client.post("/api/admin/vibe-tasks", json=_uniq(BUGFIX_TASK, "del"), headers=admin_headers).json()["id"]
    hdr = _reg(client, "vibe-del")
    client.post(f"/api/vibe/tasks/{tid}/session", headers=hdr)

    assert client.delete(f"/api/admin/vibe-tasks/{tid}", headers=admin_headers).status_code == 409

    upd = dict(BUGFIX_TASK, enabled=False)
    r = client.patch(f"/api/admin/vibe-tasks/{tid}", json=upd, headers=admin_headers)
    assert r.status_code == 200 and r.json()["enabled"] is False
    items = client.get("/api/vibe/tasks", headers=hdr).json()
    assert all(t["id"] != tid for t in items)


def test_student_forbidden_on_admin_endpoints(client):
    hdr = _reg(client, "vibe-student")
    assert client.get("/api/admin/vibe-tasks", headers=hdr).status_code == 403


# ------------------------------------------------------------------ flow студента


def test_student_flow_run_and_pass(client, admin_headers):
    tid = client.post("/api/admin/vibe-tasks", json=_uniq(BUGFIX_TASK, "flow"), headers=admin_headers).json()["id"]
    hdr = _reg(client, "vibe-flow")

    s = client.post(f"/api/vibe/tasks/{tid}/session", headers=hdr).json()
    assert s["code"] == BUGFIX_TASK["initial_code"]

    r = client.post(f"/api/vibe/sessions/{s['id']}/run", json={"code": s["code"]}, headers=hdr)
    body = r.json()
    assert body["passed"] is False
    assert any(not t["passed"] for t in body["results"])

    fixed = BUGFIX_TASK["reference_solution"]
    client.put(f"/api/vibe/sessions/{s['id']}/code", json={"code": fixed}, headers=hdr)
    r = client.post(f"/api/vibe/sessions/{s['id']}/run", json={"code": fixed}, headers=hdr)
    body = r.json()
    assert body["passed"] is True and body["score"] >= 70
    assert {"тесты", "итерации_диалога", "качество_промптов", "гигиена_кода"} <= set(body["breakdown"])

    # сессия сохраняется: повторный GET и resume
    again = client.post(f"/api/vibe/tasks/{tid}/session", headers=hdr).json()
    assert again["id"] == s["id"] and again["status"] == "passed" and again["code"] == fixed


def test_run_scores_prompt_quality(client, admin_headers, monkeypatch):
    from tests.conftest import wait_job
    import app.services.llm_handlers as handlers

    async def stub(messages, db=None, temperature=0.4, max_tokens=1200, timeout_sec=None):
        return "Вот исправленный код:\n```python\ndef f(x):\n    if x is None:\n        return 0\n    return x + 1\n```"

    monkeypatch.setattr(handlers, "chat_completion", stub)

    tid = client.post("/api/admin/vibe-tasks", json=_uniq(BUGFIX_TASK, "qual"), headers=admin_headers).json()["id"]
    hdr = _reg(client, "vibe-quality")
    s = client.post(f"/api/vibe/tasks/{tid}/session", headers=hdr).json()

    r = client.post(
        f"/api/vibe/sessions/{s['id']}/chat",
        json={"content": "Функция падает на None. Верни только код исправленной функции f с проверкой типа аргумента."},
        headers=hdr,
    )
    assert r.status_code == 200
    # один промпт — счётчик ровно 1 (не удваивается эндпоинтом и хендлером)
    assert r.json()["prompts_count"] == 1
    job = wait_job(client, hdr, r.json()["job_id"])
    assert job["status"] == "done" and "```" in job["result"]

    r = client.post(
        f"/api/vibe/sessions/{s['id']}/run", json={"code": BUGFIX_TASK["reference_solution"]}, headers=hdr
    )
    body = r.json()
    assert body["passed"] is True
    # 1 из 1 промптов содержательный (длинный + сигнальные слова) → качество полное
    assert body["breakdown"]["качество_промптов"] == 15
    assert body["breakdown"]["число_промптов"] == 1


def test_chat_locked_after_pass_and_history_budget(client, admin_headers, monkeypatch):
    from tests.conftest import wait_job
    import app.api.vibe as vibe_api
    import app.services.llm_handlers as handlers

    captured = []

    async def stub(messages, db=None, temperature=0.4, max_tokens=1200, timeout_sec=None):
        captured.append(list(messages))
        return "ок"

    monkeypatch.setattr(handlers, "chat_completion", stub)
    tid = client.post("/api/admin/vibe-tasks", json=_uniq(BUGFIX_TASK, "budget"), headers=admin_headers).json()["id"]
    hdr = _reg(client, "vibe-budget")
    s = client.post(f"/api/vibe/tasks/{tid}/session", headers=hdr).json()
    for i in range(15):
        r = client.post(
            f"/api/vibe/sessions/{s['id']}/chat",
            json={"content": "длинный вопрос номер " + str(i) + ": " + "x" * 2000},
            headers=hdr,
        )
        assert r.status_code == 200
        # ждём ответ модели, прежде чем слать следующий промпт (FIFO-очередь)
        assert wait_job(client, hdr, r.json()["job_id"])["status"] == "done"
    last = captured[-1]
    assert len(last) == 1 + vibe_api.HISTORY_LIMIT  # system + последние N
    assert all(len(m["content"]) <= vibe_api.MSG_TRUNCATE for m in last[1:])

    # проходим задачу и проверяем блокировку чата
    client.post(
        f"/api/vibe/sessions/{s['id']}/run",
        json={"code": BUGFIX_TASK["reference_solution"]}, headers=hdr,
    )
    r = client.post(f"/api/vibe/sessions/{s['id']}/chat", json={"content": "ещё?"}, headers=hdr)
    assert r.status_code == 409


# ------------------------------------------------------------------ тип tests (мутанты)

GOOD_TESTS = (
    "\ndef test_zero():\n    assert double(0) == 0\n"
    "\ndef test_two():\n    assert double(2) == 4\n"
    "\ndef test_neg():\n    assert double(-1) == -2\n"
)

WEAK_TESTS = (
    "\ndef test_zero():\n    assert double(0) == 0\n"
    "\ndef test_float_zero():\n    assert double(0.0) == 0.0\n"
    "\ndef test_neg_zero():\n    assert double(-0) == 0\n"
)


def _start_tests_task(client, admin_headers, name):
    tid = client.post("/api/admin/vibe-tasks", json=_uniq(TESTS_TASK, name), headers=admin_headers).json()["id"]
    hdr = _reg(client, name)
    s = client.post(f"/api/vibe/tasks/{tid}/session", headers=hdr).json()
    return hdr, s


def test_mutation_flow_pass(client, admin_headers):
    hdr, s = _start_tests_task(client, admin_headers, "vibe-mut-pass")
    code = TESTS_TASK["initial_code"] + GOOD_TESTS
    r = client.post(f"/api/vibe/sessions/{s['id']}/run", json={"code": code}, headers=hdr)
    body = r.json()
    assert body["passed"] is True
    assert body["mutation"]["caught_count"] == 2


def test_mutation_flow_weak_tests(client, admin_headers):
    hdr, s = _start_tests_task(client, admin_headers, "vibe-mut-weak")
    code = TESTS_TASK["initial_code"] + WEAK_TESTS
    r = client.post(f"/api/vibe/sessions/{s['id']}/run", json={"code": code}, headers=hdr)
    body = r.json()
    assert body["passed"] is False
    assert body["mutation"]["caught_count"] == 1


def test_tests_type_requires_marker_and_min_count(client, admin_headers):
    hdr, s = _start_tests_task(client, admin_headers, "vibe-mut-marker")
    # без маркера
    r = client.post(f"/api/vibe/sessions/{s['id']}/run", json={"code": "def double(x):\n    return x * 2\n"}, headers=hdr)
    assert r.json()["passed"] is False and "маркер" in r.json()["mutation"]["note"]
    # маркер есть, но один тривиальный тест — не проходит по минимуму
    weak1 = TESTS_TASK["initial_code"] + "\ndef test_zero():\n    assert double(0) == 0\n"
    r = client.post(f"/api/vibe/sessions/{s['id']}/run", json={"code": weak1}, headers=hdr)
    body = r.json()
    assert body["passed"] is False and "минимум" in body["mutation"]["note"]


def test_mutation_crash_is_caught(client, admin_headers):
    """Мутант, который крашится, считается пойманным (программа не отработала чисто)."""
    task = _uniq(TESTS_TASK, "crash-mut")
    task["mutants"] = [
        {"name": "плюс два", "code": "def double(x):\n    return x + 2\n"},
        {"name": "краш", "code": "def double(x):\n    return x * 2\nraise RuntimeError('boom')\n"},
    ]
    task["min_mutants_caught"] = 2
    tid = client.post("/api/admin/vibe-tasks", json=task, headers=admin_headers).json()["id"]
    hdr = _reg(client, "vibe-crash-mut")
    s = client.post(f"/api/vibe/tasks/{tid}/session", headers=hdr).json()
    code = TESTS_TASK["initial_code"] + GOOD_TESTS
    r = client.post(f"/api/vibe/sessions/{s['id']}/run", json={"code": code}, headers=hdr)
    body = r.json()
    muts = {m["name"]: m for m in body["mutation"]["mutants"]}
    assert muts["краш"]["caught"] is True and "краш/таймаут" in muts["краш"]["note"]
    assert body["mutation"]["caught_count"] == 2


def test_mutation_checked_against_reference(client, admin_headers):
    """Тесты валидируются на эталоне: изменил функцию под слабые тесты — не зачтено."""
    hdr, s = _start_tests_task(client, admin_headers, "vibe-ref-check")
    # Студент поменял double() ВЫШЕ маркера: его тест проходит на его коде (1+2=3),
    # но падает на корректной реализации (1*2=2).
    code = (
        "def double(x):\n    return x + 2\n\n"
        "# === ВАШИ ТЕСТЫ НИЖЕ (функции test_*, внутри assert) ===\n"
        "\ndef test_one():\n    assert double(1) == 3\n"
    )
    r = client.post(f"/api/vibe/sessions/{s['id']}/run", json={"code": code}, headers=hdr)
    body = r.json()
    assert body["passed"] is False
    assert "корректном коде" in body["mutation"]["note"]


def test_failed_assert_shows_expression(client, admin_headers):
    """Голый assert без сообщения: в detail видно упавшее выражение, а не пустой текст."""
    tid = client.post("/api/admin/vibe-tasks", json=_uniq(BUGFIX_TASK, "detail"), headers=admin_headers).json()["id"]
    hdr = _reg(client, "vibe-detail")
    s = client.post(f"/api/vibe/tasks/{tid}/session", headers=hdr).json()
    # f(None) == 1 вместо 0.0 — голый assert падает без сообщения
    code = "def f(x):\n    if x is None:\n        return 1\n    return x + 1\n"
    r = client.post(f"/api/vibe/sessions/{s['id']}/run", json={"code": code}, headers=hdr)
    body = r.json()
    failed = [t for t in body["results"] if not t["passed"]]
    assert failed, "ожидался падающий кейс"
    assert any("assert f(None) == 0" in (t["detail"] or "") for t in failed), [t["detail"] for t in failed]


# ------------------------------------------------------------------ тип refactor (AST)


def test_refactor_ast_gate(client, admin_headers):
    tid = client.post("/api/admin/vibe-tasks", json=_uniq(REFACTOR_TASK, "ast"), headers=admin_headers).json()["id"]
    hdr = _reg(client, "vibe-ref")
    s = client.post(f"/api/vibe/tasks/{tid}/session", headers=hdr).json()

    # поведение верное, но вложенность 3 → не зачтено
    r = client.post(f"/api/vibe/sessions/{s['id']}/run", json={"code": REFACTOR_TASK["initial_code"]}, headers=hdr)
    body = r.json()
    assert all(t["passed"] for t in body["results"])
    assert body["passed"] is False
    assert body["breakdown"]["вложенность_if_for_while"] == 3

    # плоский эталон → зачтено
    r = client.post(f"/api/vibe/sessions/{s['id']}/run", json={"code": REFACTOR_TASK["reference_solution"]}, headers=hdr)
    assert r.json()["passed"] is True


def test_run_runtime_error_feedback(client, admin_headers):
    tid = client.post("/api/admin/vibe-tasks", json=_uniq(BUGFIX_TASK, "crash"), headers=admin_headers).json()["id"]
    hdr = _reg(client, "vibe-crash")
    s = client.post(f"/api/vibe/tasks/{tid}/session", headers=hdr).json()
    # код с синтаксической ошибкой на уровне модуля — тесты не доходят
    broken = "def f(x):\n    return x +\n"
    r = client.post(f"/api/vibe/sessions/{s['id']}/run", json={"code": broken}, headers=hdr)
    body = r.json()
    assert body["passed"] is False
    assert any("завершилась" in t["detail"] or not t["passed"] for t in body["results"])
