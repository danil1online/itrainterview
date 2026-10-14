"""Заполнение банка задач. Идемпотентно: новые вставляются, существующие не трогаются
(если не передан флаг --force — тогда обновляет легенду/тесты/эталон)."""

import argparse

from sqlalchemy import select

from app.db import SessionLocal
from app.models import Task, VibeTask
from app.seed.tasks_data import TASK_SEED
from app.seed.vibe_data import VIBE_TASKS


def seed(force: bool = False) -> None:
    db = SessionLocal()
    try:
        created = updated = skipped = 0
        for item in TASK_SEED:
            task = db.scalar(select(Task).where(Task.slug == item["slug"]))
            if task is None:
                db.add(Task(**item))
                created += 1
            elif force:
                for key, value in item.items():
                    setattr(task, key, value)
                updated += 1
            else:
                skipped += 1
        db.commit()
        print(f"[seed] создано: {created}, обновлено: {updated}, пропущено: {skipped}")
    finally:
        db.close()


def seed_vibe(force: bool = False) -> None:
    db = SessionLocal()
    try:
        created = updated = skipped = 0
        for item in VIBE_TASKS:
            task = db.scalar(select(VibeTask).where(VibeTask.slug == item["slug"]))
            if task is None:
                db.add(VibeTask(**item))
                created += 1
            elif force:
                for key, value in item.items():
                    setattr(task, key, value)
                updated += 1
            else:
                skipped += 1
        db.commit()
        print(f"[seed-vibe] создано: {created}, обновлено: {updated}, пропущено: {skipped}")
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true", help="обновить существующие задачи")
    args = parser.parse_args()
    seed(force=args.force)
    seed_vibe(force=args.force)
