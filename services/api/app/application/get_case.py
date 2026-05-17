"""Lectura: detalle y listado de casos."""

import uuid

from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session, selectinload

from services.api.app.core.exceptions import CaseNotFound
from services.shared.models.case import Case


def detail(case_id: uuid.UUID, db: Session) -> Case:
    stmt = (
        select(Case)
        .where(Case.id == case_id)
        .options(
            selectinload(Case.data_sources),
            selectinload(Case.subtasks),
            selectinload(Case.findings),
        )
    )
    case = db.scalar(stmt)
    if case is None:
        raise CaseNotFound(f"case {case_id} no encontrado")
    return case


def list_cases(
    db: Session,
    *,
    status: str | None,
    page: int,
    page_size: int,
) -> tuple[list[Case], int]:
    base = select(Case)
    if status:
        base = base.where(Case.status == status)

    total = db.scalar(select(func.count()).select_from(base.subquery())) or 0
    items = list(
        db.scalars(
            base.order_by(desc(Case.created_at))
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    )
    return items, int(total)
