"""Aggregator: cuando todas las subtasks de un caso terminan, arma el
reporte, lo sube a MinIO y marca el caso como completado/failed.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from celery import shared_task
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from services.shared.events.bus import Event, EventType, get_event_bus
from services.shared.events.counters import get_counters
from services.shared.logging_setup import get_logger
from services.shared.models.base import session_scope
from services.shared.models.case import Case, CaseStateHistory
from services.shared.models.enums import CaseStatus, SubtaskStatus
from services.shared.state_machine import assert_case_transition
from services.shared.storage.minio_client import get_storage
from services.worker_aggregator.report_builder import render_html, render_pdf

logger = get_logger("worker_aggregator")


def _final_status(case: Case) -> str:
    pending = [
        st
        for st in case.subtasks
        if st.status
        not in {
            SubtaskStatus.COMPLETED.value,
            SubtaskStatus.FAILED.value,
            SubtaskStatus.CANCELLED.value,
        }
    ]
    if pending:
        return CaseStatus.PROCESSING.value
    if case.failed_subtasks > 0 and case.completed_subtasks == 0:
        return CaseStatus.FAILED.value
    return CaseStatus.COMPLETED.value


@shared_task(
    name="worker_aggregator.aggregate_case",
    bind=True,
    acks_late=True,
)
def aggregate_case(self, *, case_id: str):
    counters = get_counters()
    bus = get_event_bus()

    with session_scope() as db:
        stmt = (
            select(Case)
            .where(Case.id == UUID(case_id))
            .options(
                selectinload(Case.subtasks),
                selectinload(Case.data_sources),
                selectinload(Case.findings),
            )
        )
        case = db.scalar(stmt)
        if case is None:
            logger.warning("aggregate_case_missing", case_id=case_id)
            return {"status": "missing"}

        if case.status in {
            CaseStatus.COMPLETED.value,
            CaseStatus.FAILED.value,
            CaseStatus.CANCELLED.value,
        }:
            logger.info(
                "aggregate_skipped_terminal",
                case_id=case_id,
                status=case.status,
            )
            return {"status": "skipped_terminal"}

        html = render_html(case)

    pdf_bytes = render_pdf(html)
    storage = get_storage()
    storage_key = f"cases/{case_id}/report/case_{case_id}.pdf"
    storage.put_bytes(storage_key, pdf_bytes, content_type="application/pdf")

    with session_scope() as db:
        stmt = (
            select(Case)
            .where(Case.id == UUID(case_id))
            .options(selectinload(Case.subtasks))
        )
        case = db.scalar(stmt)
        if case is None:
            return {"status": "missing"}

        target = _final_status(case)
        if target != case.status:
            assert_case_transition(case.status, target)
            previous = case.status
            case.status = target
            case.finished_at = datetime.utcnow()
            db.add(
                CaseStateHistory(
                    case_id=case.id,
                    from_status=previous,
                    to_status=target,
                    reason="aggregator_finalized",
                )
            )

        case.report_storage_key = storage_key

    counters.cleanup(case_id)

    bus.publish(
        Event(
            type=EventType.REPORT_READY,
            case_id=case_id,
            payload={"storage_key": storage_key},
        )
    )
    bus.publish(
        Event(
            type=EventType.CASE_COMPLETED if target == CaseStatus.COMPLETED.value else EventType.CASE_FAILED,
            case_id=case_id,
            payload={"storage_key": storage_key, "status": target},
        )
    )

    return {"status": target, "storage_key": storage_key}
