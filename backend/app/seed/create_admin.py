"""Создание первого администратора из переменных окружения ADMIN_EMAIL/ADMIN_PASSWORD."""

import os

from sqlalchemy import select

from app.core.security import hash_password
from app.db import SessionLocal
from app.models import User


def create_admin() -> None:
    email = (os.getenv("ADMIN_EMAIL") or "").strip().lower()
    password = os.getenv("ADMIN_PASSWORD") or ""
    username = (os.getenv("ADMIN_USERNAME") or "admin").strip()
    if not email or not password:
        print("[admin] ADMIN_EMAIL/ADMIN_PASSWORD не заданы — пропуск")
        return
    db = SessionLocal()
    try:
        exists = db.scalar(select(User).where(User.email == email))
        if exists is not None:
            print(f"[admin] пользователь {email} уже существует — пропуск")
            return
        db.add(
            User(
                email=email,
                username=username,
                hashed_password=hash_password(password),
                role="admin",
            )
        )
        db.commit()
        print(f"[admin] создан администратор {email}")
    finally:
        db.close()


if __name__ == "__main__":
    create_admin()
