"""DTOs para creacion y consulta de casos."""

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from services.shared.models.enums import Priority


class CaseCreateResponse(BaseModel):
    id: uuid.UUID
    title: str
    status: str
    priority: int
    total_subtasks: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DataSourceOut(BaseModel):
    id: uuid.UUID
    type: str
    storage_key: str
    original_filename: str | None
    mime_type: str | None
    size_bytes: int

    model_config = ConfigDict(from_attributes=True)


class SubtaskOut(BaseModel):
    id: uuid.UUID
    worker_type: str
    status: str
    attempts: int
    priority: int
    started_at: datetime | None
    finished_at: datetime | None
    error: str | None

    model_config = ConfigDict(from_attributes=True)


class FindingOut(BaseModel):
    id: uuid.UUID
    category: str
    severity: int
    confidence: Decimal
    evidence: dict
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CaseDetailOut(BaseModel):
    id: uuid.UUID
    title: str
    description: str | None
    status: str
    priority: int
    total_subtasks: int
    completed_subtasks: int
    failed_subtasks: int
    report_storage_key: str | None
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
    data_sources: list[DataSourceOut]
    subtasks: list[SubtaskOut]
    findings: list[FindingOut]

    model_config = ConfigDict(from_attributes=True)


class CaseListItem(BaseModel):
    id: uuid.UUID
    title: str
    status: str
    priority: int
    total_subtasks: int
    completed_subtasks: int
    failed_subtasks: int
    created_at: datetime
    finished_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class CaseListResponse(BaseModel):
    items: list[CaseListItem]
    total: int
    page: int
    page_size: int


class CancelCaseRequest(BaseModel):
    reason: str | None = Field(default=None, max_length=500)
