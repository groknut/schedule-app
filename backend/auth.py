"""
Модуль авторизации и ролевой модели.
=====================================
Реализует:
  - Хеширование паролей через bcrypt
  - JWT-токены (access + refresh)
  - Зависимости FastAPI: get_current_user, require_manager, require_admin
  - Эндпоинты: POST /auth/login, POST /auth/refresh, GET /auth/me

Ролевая модель:
  employee  — видит и редактирует только свои смены
  manager   — видит все смены команды, подтверждает план/факт
  admin     — полный доступ ко всем ресурсам
"""

import os
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
import bcrypt as _bcrypt
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from models import Employee, EmployeeRole

# ─── Конфигурация ─────────────────────────────────────────────────────────────

SECRET_KEY = os.getenv("SECRET_KEY", "CHANGE_ME_IN_PRODUCTION_use_openssl_rand_hex_32")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

router = APIRouter(prefix="/auth", tags=["Auth"])


# ─── Pydantic-схемы ────────────────────────────────────────────────────────────

class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class MeOut(BaseModel):
    id: int
    name: str
    email: str
    role: EmployeeRole
    team_id: Optional[int]
    position: Optional[str]

    class Config:
        from_attributes = True


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


# ─── Утилиты паролей ──────────────────────────────────────────────────────────

def hash_password(plain: str) -> str:
    """Хешируем пароль через bcrypt."""
    return _bcrypt.hashpw(plain.encode(), _bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    """Проверяем пароль против bcrypt-хеша."""
    try:
        return _bcrypt.checkpw(plain.encode(), hashed.encode())
    except Exception:
        return False


# ─── Утилиты JWT ──────────────────────────────────────────────────────────────

def _create_token(data: dict, expires_delta: timedelta) -> str:
    payload = data.copy()
    payload["exp"] = datetime.now(timezone.utc) + expires_delta
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def create_access_token(employee_id: int, role: str) -> str:
    return _create_token(
        {"sub": str(employee_id), "role": role, "type": "access"},
        timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    )


def create_refresh_token(employee_id: int) -> str:
    return _create_token(
        {"sub": str(employee_id), "type": "refresh"},
        timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
    )


def _decode_token(token: str, expected_type: str) -> dict:
    """Декодируем и валидируем JWT. Бросает HTTPException при любой ошибке."""
    credentials_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Токен недействителен или истёк",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise credentials_exc

    if payload.get("type") != expected_type:
        raise credentials_exc
    if payload.get("sub") is None:
        raise credentials_exc

    return payload


# ─── FastAPI зависимости ───────────────────────────────────────────────────────

def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> Employee:
    """
    Зависимость: извлекает текущего авторизованного сотрудника.
    Используется во всех защищённых роутах.
    """
    payload = _decode_token(token, "access")
    emp_id = int(payload["sub"])

    emp = db.query(Employee).filter_by(id=emp_id, is_active=True).first()
    if not emp:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Пользователь не найден или деактивирован",
        )
    return emp


def require_manager(current_user: Employee = Depends(get_current_user)) -> Employee:
    """
    Зависимость: доступ только для manager и admin.
    Используется на эндпоинтах подтверждения смен и просмотра всей команды.
    """
    if current_user.role not in (EmployeeRole.MANAGER, EmployeeRole.ADMIN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав. Требуется роль менеджера или администратора.",
        )
    return current_user


def require_admin(current_user: Employee = Depends(get_current_user)) -> Employee:
    """
    Зависимость: доступ только для admin.
    Используется на эндпоинтах управления организациями, командами, сотрудниками.
    """
    if current_user.role != EmployeeRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав. Требуется роль администратора.",
        )
    return current_user


# ─── Эндпоинты ────────────────────────────────────────────────────────────────

@router.post("/login", response_model=TokenPair, summary="Вход в систему")
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    """
    Принимает email (в поле username) и пароль.
    Возвращает пару access + refresh токенов.
    """
    emp = db.query(Employee).filter_by(email=form_data.username, is_active=True).first()

    # Единое сообщение об ошибке — не раскрываем, существует ли email
    if not emp or not emp.password_hash:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный email или пароль",
        )
    if not verify_password(form_data.password, emp.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный email или пароль",
        )

    return TokenPair(
        access_token=create_access_token(emp.id, emp.role.value),
        refresh_token=create_refresh_token(emp.id),
    )


@router.post("/refresh", response_model=TokenPair, summary="Обновление токена")
def refresh(body: RefreshRequest, db: Session = Depends(get_db)):
    """
    Принимает refresh-токен, возвращает новую пару токенов.
    Старый refresh-токен после этого больше не действителен (rotate strategy).
    """
    payload = _decode_token(body.refresh_token, "refresh")
    emp_id = int(payload["sub"])

    emp = db.query(Employee).filter_by(id=emp_id, is_active=True).first()
    if not emp:
        raise HTTPException(status_code=401, detail="Пользователь не найден")

    return TokenPair(
        access_token=create_access_token(emp.id, emp.role.value),
        refresh_token=create_refresh_token(emp.id),
    )


@router.get("/me", response_model=MeOut, summary="Текущий пользователь")
def me(current_user: Employee = Depends(get_current_user)):
    """Возвращает данные текущего авторизованного пользователя."""
    return current_user


@router.post("/change-password", summary="Смена пароля")
def change_password(
    body: ChangePasswordRequest,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Позволяет пользователю сменить свой пароль."""
    if not verify_password(body.current_password, current_user.password_hash):
        raise HTTPException(status_code=400, detail="Текущий пароль неверен")
    if len(body.new_password) < 8:
        raise HTTPException(status_code=400, detail="Пароль должен содержать минимум 8 символов")
    current_user.password_hash = hash_password(body.new_password)
    db.commit()
    return {"ok": True, "message": "Пароль успешно изменён"}
