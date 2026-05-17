"""Descarga de reportes generados por el aggregator."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from services.api.app.core.db import get_db
from services.api.app.core.security import get_current_user
from services.shared.models.case import Case
from services.shared.models.user import User
from services.shared.storage.minio_client import get_storage

router = APIRouter()


@router.get("/{case_id}/pdf")
def download_report(
    case_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
):
    case = db.get(Case, case_id)
    if case is None:
        raise HTTPException(status_code=404, detail="case_not_found")
    if not case.report_storage_key:
        raise HTTPException(status_code=409, detail="report_not_ready")

    data = get_storage().get_bytes(case.report_storage_key)

    def _iter():
        yield data

    return StreamingResponse(
        _iter(),
        media_type="application/pdf",
        headers={
            "Content-Disposition": (
                f'attachment; filename="case_{case_id}.pdf"'
            )
        },
    )


@router.get("/{case_id}/presigned")
def presigned(
    case_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
):
    case = db.get(Case, case_id)
    if case is None:
        raise HTTPException(status_code=404, detail="case_not_found")
    if not case.report_storage_key:
        raise HTTPException(status_code=409, detail="report_not_ready")

    url = get_storage().presigned_get(case.report_storage_key, expires_seconds=600)
    return {"url": url, "expires_seconds": 600}
