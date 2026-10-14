from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.db import get_db
from app.deps import get_current_user
from app.models import User, get_setting
from app.schemas import LoginRequest, RefreshRequest, TokenPair, UserCreate, UserOut

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _tokens(user: User) -> TokenPair:
    return TokenPair(
        access_token=create_access_token(user.id, user.role),
        refresh_token=create_refresh_token(user.id, user.role),
    )


@router.post("/register", response_model=TokenPair, status_code=201)
def register(payload: UserCreate, db: Session = Depends(get_db)):
    if get_setting(db, "allow_self_registration", "true").lower() == "false":
        raise HTTPException(403, "Самостоятельная регистрация отключена администратором")
    if db.scalar(select(User).where(User.email == payload.email.lower())):
        raise HTTPException(409, "Email уже зарегистрирован")
    if db.scalar(select(User).where(User.username == payload.username)):
        raise HTTPException(409, "Имя пользователя занято")
    user = User(
        email=payload.email.lower(),
        username=payload.username,
        hashed_password=hash_password(payload.password),
        role="student",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return _tokens(user)


@router.post("/login", response_model=TokenPair)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.scalar(
        select(User).where(
            or_(User.email == payload.login.lower(), User.username == payload.login)
        )
    )
    if user is None or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(401, "Неверный логин или пароль")
    if not user.is_active:
        raise HTTPException(403, "Аккаунт заблокирован")
    return _tokens(user)


@router.post("/refresh", response_model=TokenPair)
def refresh(payload: RefreshRequest, db: Session = Depends(get_db)):
    import jwt as pyjwt

    try:
        data = decode_token(payload.refresh_token)
    except pyjwt.PyJWTError:
        raise HTTPException(401, "Некорректный refresh-токен")
    if data.get("type") != "refresh":
        raise HTTPException(401, "Некорректный refresh-токен")
    user = db.get(User, int(data["sub"]))
    if user is None or not user.is_active:
        raise HTTPException(401, "Пользователь недоступен")
    return _tokens(user)


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user
