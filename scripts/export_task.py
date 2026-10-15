"""Экспорт задачи из БД как community-файла для вклада в репозиторий.

Использование (из корня репозитория, при запущенной системе):
    python scripts/export_task.py --slug two-sum-ii --author ivanov \
        [--out backend/app/seed/bank_community_ivanov_two_sum_ii.py]

Без --out файл печатается в stdout. Эталонное решение проверяется в песочнице.
"""

import argparse
import sys

sys.path.insert(0, "backend")

from app.db import SessionLocal  # noqa: E402
from app.models import Task  # noqa: E402
from app.services.contribute import ContributeError, export_task  # noqa: E402


def main() -> int:
    """Разбирает аргументы и экспортирует задачу из БД в community-файл."""
    parser = argparse.ArgumentParser(description="Экспорт задачи как community-файла")
    parser.add_argument("--slug", required=True, help="slug задачи в системе")
    parser.add_argument("--author", required=True, help="имя автора вклада")
    parser.add_argument("--out", help="путь для записи файла (иначе stdout)")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        task = db.query(Task).filter(Task.slug == args.slug).first()
        if task is None:
            print(f"Задача '{args.slug}' не найдена", file=sys.stderr)
            return 1
        result = export_task(task, args.author)
    except ContributeError as e:
        print("Валидация не пройдена:", file=sys.stderr)
        for issue in e.issues:
            print(f"  - {issue}", file=sys.stderr)
        return 2
    finally:
        db.close()

    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(result["content"])
        print(f"Файл записан: {args.out}")
    else:
        sys.stdout.write(result["content"])
    print("\nИнструкция:\n" + result["instructions"], file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
