"""Dependencia de FastAPI para obtener una sesion de SQLAlchemy."""

from collections.abc import Generator

from sqlalchemy.orm import Session

from services.shared.models.base import SessionLocal


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
