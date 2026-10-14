"""Экспорт задачи как community-файла для вклада в репозиторий.

Файл вкладывается в backend/app/seed/bank_community_<author>_<slug>.py —
автосборка банка подхватит его без регистрации (см. tasks_data.py).
Перед экспортом эталонное решение прогоняется в песочнице по всем тестам.
"""

import json
import re
from datetime import date

from app.models import Task
from app.seed.tasks_data import TASK_SEED
from app.services.sandbox import SandboxError, get_sandbox


class ContributeError(Exception):
    def __init__(self, issues: list[str]):
        self.issues = issues
        super().__init__("; ".join(issues))


def _known_patterns() -> set[str]:
    return {t["pattern"] for t in TASK_SEED}


def validate_task(task: Task) -> list[str]:
    """Статические проверки задачи перед вкладом."""
    issues = []
    if task.pattern not in _known_patterns():
        known = ", ".join(sorted(_known_patterns()))
        issues.append(f"Паттерн '{task.pattern}' не входит в известные: {known}")
    if len(task.tests) < 2:
        issues.append("Нужно минимум 2 теста: пример (sample) и хотя бы один скрытый")
    if not any(t.get("sample") for t in task.tests):
        issues.append("Нужен тест с sample=true — он показывается студенту как пример из условия")
    if not task.reference_solution.strip():
        issues.append("Эталонное решение обязательно: без него вклад нельзя проверить в песочнице")
    return issues


def check_reference(task: Task, timeout_sec: int = 15) -> list[str]:
    """Прогон эталонного решения по всем тестам в песочнице."""
    try:
        outcome = get_sandbox().run("python", task.reference_solution, task.tests, timeout_sec=timeout_sec)
    except SandboxError as e:
        return [f"Песочница недоступна, не удалось проверить эталон: {e}"]
    issues = []
    for r in outcome.results:
        if not r.passed:
            issues.append(
                f"Эталон не проходит тест '{r.name}': {r.status}"
                + (f", stdout={r.got_stdout[:80]!r}" if r.got_stdout else "")
                + (f", stderr={r.stderr[:120]!r}" if r.stderr else "")
            )
    return issues


def _py_literal(value, indent: int = 0) -> str:
    """Читаемый Python-литерал: строки экранируются как JSON (совместимо),
    bool — True/False (JSON true/false в Python невалидны)."""
    pad = "  " * indent
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, bool):
        return "True" if value else "False"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, list):
        if not value:
            return "[]"
        items = ",\n".join(f"{pad}  " + _py_literal(v, indent + 1) for v in value)
        return "[\n" + items + ",\n" + pad + "]"
    if isinstance(value, dict):
        if not value:
            return "{}"
        items = ",\n".join(
            f"{pad}  {json.dumps(str(k), ensure_ascii=False)}: {_py_literal(v, indent + 1)}"
            for k, v in value.items()
        )
        return "{\n" + items + ",\n" + pad + "}"
    raise TypeError(f"Неожиданный тип в задаче: {type(value)!r}")


def render_community_file(task: Task, author: str) -> tuple[str, str]:
    """Собирает самодостаточный bank-файл (валидный Python)."""
    data = [
        {
            "slug": task.slug,
            "title": task.title,
            "legend": task.legend,
            "pattern": task.pattern,
            "level": task.level,
            "hints": list(task.hints or []),
            "tests": [
                {
                    "name": t["name"],
                    "stdin": t["stdin"],
                    "expected_stdout": t["expected_stdout"],
                    "sample": bool(t.get("sample")),
                }
                for t in task.tests
            ],
            "reference_solution": task.reference_solution,
        }
    ]
    safe_author = re.sub(r"[^a-z0-9_]", "_", author.lower()) or "author"
    safe_slug = re.sub(r"[^a-z0-9_]", "_", task.slug)
    filename = f"bank_community_{safe_author}_{safe_slug}.py"
    header = (
        "# Community contribution — сгенерировано экспортом ITInterview.\n"
        f"# Автор: {author}\n"
        f"# Дата: {date.today().isoformat()}\n"
        "# Валидация: эталонное решение прошло все тесты в песочнице (без сети, с лимитами CPU/RAM).\n"
        "\n"
    )
    body = "TASKS = " + _py_literal(data) + "\n"
    return filename, header + body


INSTRUCTIONS = """Как предложить задачу в репозиторий:

1. Сохраните сгенерированный файл в локальную копию репозитория:
   backend/app/seed/<имя файла>
2. Создайте ветку и отправьте PR:
   git checkout -b community-task-<slug>
   git add backend/app/seed/<имя файла>
   git commit -m "Add community task: <title>"
   git push origin community-task-<slug>
   затем создайте Pull Request на GitHub.

Требования к вкладу (см. CONTRIBUTING.md):
- эталонное решение проходит все тесты в песочнице (проверено при экспорте);
- есть sample-тест и минимум один скрытый;
- slug уникален среди банка задач;
- паттерн — один из существующих, уровень junior/middle/senior.

Файл подхватывается автоматически: регистрация в tasks_data.py не нужна,
seeder идемпотентен по slug (новые задачи добавляются при старте)."""


def export_task(task: Task, author: str) -> dict:
    issues = validate_task(task)
    if not issues:
        issues.extend(check_reference(task))
    if issues:
        raise ContributeError(issues)
    filename, content = render_community_file(task, author)
    return {"filename": filename, "content": content, "instructions": INSTRUCTIONS}
