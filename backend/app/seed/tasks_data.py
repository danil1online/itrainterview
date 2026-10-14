"""Банк задач: автосборка из всех модулей bank_*.py в этом каталоге.

Каждый модуль обязан экспортировать TASKS: list[dict] со схемой
{slug, title, legend, pattern, level, hints, tests, reference_solution}.
Новые community-вклады добавляются одним новым файлом bank_community_*.py —
регистрация в этом файле не нужна (seeder идемпотентен по slug).
"""

import importlib
import pathlib
import re

_HERE = pathlib.Path(__file__).parent


def _discover_modules() -> list[str]:
    names = []
    for path in sorted(_HERE.glob("bank_*.py")):
        name = path.stem
        if not re.fullmatch(r"bank_[a-z0-9_]+", name):
            continue
        names.append(f"app.seed.{name}")
    return names


def _collect() -> list[dict]:
    tasks: list[dict] = []
    seen: dict[str, str] = {}
    for module_name in _discover_modules():
        module = importlib.import_module(module_name)
        for item in getattr(module, "TASKS", []):
            slug = item.get("slug")
            if not slug:
                raise ValueError(f"{module_name}: задача без slug")
            if slug in seen:
                raise ValueError(
                    f"Коллизия slug '{slug}': задан в {seen[slug]} и {module_name}"
                )
            seen[slug] = module_name
            tasks.append(item)
    return tasks


TASK_SEED = _collect()
