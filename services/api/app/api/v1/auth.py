"""Endpoints de autenticacion. JWT simple basado en email + password."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from services.api.app.core.db import get_db
from services.api.app.core.security import get_current_user, require_admin
from services.api.app.schemas.auth import (
    LoginRequest,
    RegisterRequest,
    TokenResponse,
)
from services.shared.models.enums import UserRole
from services.shared.models.user import User
from services.shared.security import create_access_token, hash_password, verify_password

router = APIRouter()


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Annotated[Session, Depends(get_db)]):
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid_credentials",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="user_inactive"
        )
    token = create_access_token(subject=str(user.id), role=user.role)
    return TokenResponse(access_token=token, role=user.role)


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_admin)],
)
def register(
    payload: RegisterRequest,
    db: Annotated[Session, Depends(get_db)],
):
    """Solo un admin puede crear usuarios nuevos (incluyendo otros admins)."""
    if payload.role not in {UserRole.ADMIN.value, UserRole.ANALYST.value}:
        raise HTTPException(status_code=422, detail="invalid_role")

    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(status_code=409, detail="email_taken")

    user = User(
        email=payload.email,
        password_hash=hash_password(payload.password),
        full_name=payload.full_name,
        role=payload.role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token(subject=str(user.id), role=user.role)
    return TokenResponse(access_token=token, role=user.role)


@router.get("/me")
def me(current: Annotated[User, Depends(get_current_user)]):
    return {
        "id": str(current.id),
        "email": current.email,
        "full_name": current.full_name,
        "role": current.role,
    }
