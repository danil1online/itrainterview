"""Хеширование паролей (bcrypt) и JWT access/refresh-токены."""

from datetime import datetime, timedelta, timezone

import jwt
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Хеширует пароль bcrypt."""
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    """Сравнивает пароль с хешем."""
    return pwd_context.verify(plain, hashed)


def create_token(subject: str, token_type: str, ttl_seconds: int, role: str = "student") -> str:
    """Формирует JWT с sub/type/role и exp по ttl_seconds."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": subject,
        "type": token_type,
        "role": role,
        "iat": now,
        "exp": now + timedelta(seconds=ttl_seconds),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)


def create_access_token(user_id: int, role: str) -> str:
    """Access-токен пользователя (TTL из настроек)."""
    return create_token(str(user_id), "access", settings.access_token_ttl_min * 60, role)


def create_refresh_token(user_id: int, role: str) -> str:
    """Refresh-токен пользователя (TTL из настроек)."""
    return create_token(str(user_id), "refresh", settings.refresh_token_ttl_days * 24 * 3600, role)


def decode_token(token: str) -> dict:
    """Расшифровывает JWT; при невалидности/истечении бросает PyJWTError."""
    return jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])
