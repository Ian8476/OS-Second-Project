"""Caso de uso: crear caso de analisis.

Responsabilidades:
1) Subir cada archivo a MinIO.
2) Crear Case + N data_sources + N subtasks en una transaccion.
3) Inicializar el contador atomico en Redis.
4) Encolar una tarea Celery por subtask con prioridad.
5) Publicar evento `case.queued`.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from io import BytesIO
from typing import BinaryIO

from sqlalchemy.orm import Session

from services.api.app.domain.worker_routing import classify_source, routing_for
from services.shared.events.bus import Event, EventType, get_event_bus
from services.shared.events.counters import get_counters
from services.shared.messaging.dispatcher import dispatch_subtask
from services.shared.models.case import Case, CaseStateHistory
from services.shared.models.data_source import DataSource
from services.shared.models.enums import (
    CaseStatus,
    PRIORITY_TO_NUMERIC,
    Priority,
    SubtaskStatus,
)
from services.shared.models.subtask import Subtask
from services.shared.storage.minio_client import MinioStorage


@dataclass
class UploadedFile:
    filename: str
    mime_type: str | None
    content: bytes


@dataclass
class CreateCaseInput:
    title: str
    description: str | None
    priority: Priority
    owner_id: uuid.UUID | None
    files: list[UploadedFile]


def execute(
    inp: CreateCaseInput, *, db: Session, storage: MinioStorage
) -> Case:
    if not inp.files:
        raise ValueError("Un caso debe traer al menos un archivo.")

    case = Case(
        id=uuid.uuid4(),
        owner_id=inp.owner_id,
        title=inp.title,
        description=inp.description,
        priority=PRIORITY_TO_NUMERIC[inp.priority],
        status=CaseStatus.QUEUED.value,
    )

    subtasks: list[Subtask] = []

    for f in inp.files:
        source_type = classify_source(f.mime_type, f.filename)
        data_source_id = uuid.uuid4()
        storage_key = f"cases/{case.id}/{data_source_id}/{f.filename}"
        storage.put_object(
            storage_key,
            BytesIO(f.content),
            size=len(f.content),
            content_type=f.mime_type,
        )

        ds = DataSource(
            id=data_source_id,
            case_id=case.id,
            type=source_type.value,
            storage_key=storage_key,
            original_filename=f.filename,
            mime_type=f.mime_type,
            size_bytes=len(f.content),
            extra={},
        )
        case.data_sources.append(ds)

        worker_type, _, _ = routing_for(source_type)
        st = Subtask(
            id=uuid.uuid4(),
            case_id=case.id,
            data_source_id=ds.id,
            worker_type=worker_type.value,
            status=SubtaskStatus.PENDING.value,
            priority=case.priority,
            enqueued_at=datetime.utcnow(),
        )
        subtasks.append(st)
        case.subtasks.append(st)

    case.total_subtasks = len(subtasks)

    db.add(case)
    db.add(
        CaseStateHistory(
            case_id=case.id,
            from_status=None,
            to_status=CaseStatus.QUEUED.value,
            reason="case_created",
        )
    )
    db.flush()

    counters = get_counters()
    counters.set_total(str(case.id), len(subtasks))

    for st in subtasks:
        source = next(
            (ds for ds in case.data_sources if ds.id == st.data_source_id),
            None,
        )
        if source is None:
            continue
        _, queue, task_name = routing_for(classify_source(source.mime_type, source.original_filename))
        dispatch_subtask(
            task_name=task_name,
            subtask_id=str(st.id),
            case_id=str(case.id),
            storage_key=source.storage_key,
            priority=case.priority,
            queue=queue,
            extra={"mime_type": source.mime_type, "filename": source.original_filename},
        )

    db.commit()
    db.refresh(case)

    get_event_bus().publish(
        Event(
            type=EventType.CASE_QUEUED,
            case_id=str(case.id),
            payload={
                "title": case.title,
                "priority": case.priority,
                "total_subtasks": case.total_subtasks,
            },
        )
    )

    return case
