"""Прогон эталонных решений всех задач банка в песочнице. Использование:
    SANDBOX_LOCAL_DIR=/tmp/sandbox-work python scripts/validate_seed.py [python|javascript|java|cpp]
"""

import sys
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, "backend")

from app.seed.tasks_data import TASK_SEED  # noqa: E402
from app.services.sandbox import DockerSandbox, SandboxError  # noqa: E402


def main() -> int:
    """Прогоняет эталоны всех задач банка в песочнице; печатает провалы, код возврата 1 при ошибках."""
    language = sys.argv[1] if len(sys.argv) > 1 else "python"
    sandbox = DockerSandbox()
    failures = []

    def check(task):
        """Прогоняет эталон одной задачи, провалы собирает в failures."""
        code = task["reference_solution"]
        if language != "python":
            print(f"пропуск {task['slug']}: нет эталона на {language}")
            return
        try:
            outcome = sandbox.run(language, code, task["tests"], timeout_sec=10)
        except SandboxError as e:
            failures.append((task["slug"], "sandbox", str(e)[:200]))
            print(f"FAIL(sandbox) {task['slug']}: {e}")
            return
        for r in outcome.results:
            if not r.passed:
                failures.append((task["slug"], r.name, f"{r.status} got={r.got_stdout[:100]!r} err={r.stderr[:200]!r}"))
                print(f"FAIL {task['slug']}/{r.name}: {r.status} got={r.got_stdout[:80]!r} err={r.stderr[:150]!r}")

    with ThreadPoolExecutor(max_workers=6) as pool:
        list(pool.map(check, TASK_SEED))

    total_tests = sum(len(t["tests"]) for t in TASK_SEED)
    print(f"\n{len(TASK_SEED)} задач, {total_tests} тестов; ошибок: {len(failures)}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
