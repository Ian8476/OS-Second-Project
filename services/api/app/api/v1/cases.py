"""Endpoints de casos: crear, listar, ver detalle, cancelar."""

import uuid
from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from sqlalchemy.orm import Session

from services.api.app.application import cancel_case, create_case, get_case
from services.api.app.application.create_case import CreateCaseInput, UploadedFile
from services.api.app.core.db import get_db
from services.api.app.core.security import get_current_user
from services.api.app.schemas.cases import (
    CancelCaseRequest,
    CaseCreateResponse,
    CaseDetailOut,
    CaseListItem,
    CaseListResponse,
)
from services.shared.models.enums import Priority
from services.shared.models.user import User
from services.shared.storage.minio_client import get_storage

router = APIRouter()

_MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB

_ALLOWED_MIMES = {
    "text/plain",
    "text/csv",
    "application/json",
    "audio/mpeg",
    "audio/mp4",
    "audio/wav",
    "audio/x-wav",
    "audio/ogg",
    "audio/flac",
    "audio/webm",
    "image/jpeg",
    "image/png",
    "image/gif",
    "image/webp",
    "image/bmp",
    "image/tiff",
}


@router.post(
    "",
    response_model=CaseCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create(
    title: Annotated[str, Form()],
    description: Annotated[str | None, Form()] = None,
    priority: Annotated[Priority, Form()] = Priority.MEDIUM,
    files: Annotated[list[UploadFile], File()] = ...,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not files:
        raise HTTPException(status_code=422, detail="no_files")

    uploaded: list[UploadedFile] = []
    for f in files:
        if f.content_type and f.content_type not in _ALLOWED_MIMES:
            raise HTTPException(
                status_code=415,
                detail=f"mime_not_allowed:{f.content_type}",
            )
        content = await f.read()
        if len(content) > _MAX_FILE_SIZE:
            raise HTTPException(
                status_code=413, detail=f"file_too_large:{f.filename}"
            )
        uploaded.append(
            UploadedFile(
                filename=f.filename or "unnamed",
                mime_type=f.content_type,
                content=content,
            )
        )

    case = create_case.execute(
        CreateCaseInput(
            title=title,
            description=description,
            priority=priority,
            owner_id=current.id,
            files=uploaded,
        ),
        db=db,
        storage=get_storage(),
    )
    return case


@router.get("", response_model=CaseListResponse)
def list_cases(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
    status_filter: Annotated[str | None, Query(alias="status")] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
):
    items, total = get_case.list_cases(
        db, status=status_filter, page=page, page_size=page_size
    )
    return CaseListResponse(
        items=[CaseListItem.model_validate(c) for c in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{case_id}", response_model=CaseDetailOut)
def get_detail(
    case_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
):
    case = get_case.detail(case_id, db)
    return CaseDetailOut.model_validate(case)


@router.post(
    "/{case_id}/cancel",
    response_model=CaseDetailOut,
)
def cancel(
    case_id: uuid.UUID,
    payload: CancelCaseRequest,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
):
    cancel_case.execute(case_id, payload.reason, db=db)
    case = get_case.detail(case_id, db)
    return CaseDetailOut.model_validate(case)
