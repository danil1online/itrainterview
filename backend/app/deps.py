"""FastAPI-зависимости: текущий пользователь и права администратора."""

import jwt as pyjwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.security import decode_token
from app.db import get_db
from app.models import User

bearer_scheme = HTTPBearer(auto_error=False)

CREDENTIALS_EXC = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Требуется авторизация",
    headers={"WWW-Authenticate": "Bearer"},
)


def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Валидирует Bearer access-токен и возвращает активного пользователя, иначе 401."""
    if creds is None:
        raise CREDENTIALS_EXC
    try:
        payload = decode_token(creds.credentials)
    except pyjwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Срок токена истёк")
    except pyjwt.PyJWTError:
        raise CREDENTIALS_EXC
    if payload.get("type") != "access":
        raise CREDENTIALS_EXC
    user = db.get(User, int(payload["sub"]))
    if user is None or not user.is_active:
        raise CREDENTIALS_EXC
    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    """Пропускает только пользователей с ролью admin, иначе 403."""
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Требуются права администратора")
    return user
