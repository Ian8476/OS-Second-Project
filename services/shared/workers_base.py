"""Logica comun a todos los workers: idempotencia, locks, transiciones,
contadores y disparo del aggregator. Cada worker concreto solo
implementa el `do_work` que extrae findings.
"""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any, Callable, Iterable
from uuid import UUID

from sqlalchemy.exc import IntegrityError

from services.shared.config import settings
from services.shared.events.bus import Event, EventType, get_event_bus
from services.shared.events.counters import get_counters
from services.shared.logging_setup import get_logger
from services.shared.messaging.dispatcher import dispatch_aggregator
from services.shared.models.base import session_scope
from services.shared.models.case import Case, CaseStateHistory
from services.shared.models.enums import CaseStatus, SubtaskStatus
from services.shared.models.finding import Finding
from services.shared.models.processed_task import ProcessedTask
from services.shared.models.subtask import Subtask
from services.shared.state_machine import assert_case_transition, assert_subtask_transition

logger = get_logger("workers_base")


@dataclass
class WorkerFinding:
    category: str
    severity: int
    confidence: float
    evidence: dict


@dataclass
class WorkerContext:
    task_id: str
    subtask_id: str
    case_id: str
    storage_key: str | None
    worker_type: str
    extra: dict


@contextmanager
def _subtask_lock(subtask_id: str):
    counters = get_counters()
    with counters.subtask_lock(subtask_id) as acquired:
        yield acquired


def _already_processed(db, task_id: str) -> bool:
    return db.get(ProcessedTask, task_id) is not None


def _mark_processed(
    db, task_id: str, subtask_id: str, worker_type: str, summary: str | None
) -> None:
    record = ProcessedTask(
        task_id=task_id,
        subtask_id=UUID(subtask_id),
        worker_type=worker_type,
        result_summary=summary,
    )
    db.add(record)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()


def _ensure_case_processing(db, case: Case) -> None:
    if case.status == CaseStatus.QUEUED.value:
        assert_case_transition(case.status, CaseStatus.PROCESSING.value)
        previous = case.status
        case.status = CaseStatus.PROCESSING.value
        case.started_at = datetime.utcnow()
        db.add(
            CaseStateHistory(
                case_id=case.id,
                from_status=previous,
                to_status=case.status,
                reason="first_worker_picked_up",
            )
        )


def _transition_subtask(
    db, subtask: Subtask, new_status: str, error: str | None = None
) -> None:
    assert_subtask_transition(subtask.status, new_status)
    subtask.status = new_status
    if new_status == SubtaskStatus.PROCESSING.value:
        subtask.started_at = subtask.started_at or datetime.utcnow()
        subtask.attempts += 1
    elif new_status in {
        SubtaskStatus.COMPLETED.value,
        SubtaskStatus.FAILED.value,
        SubtaskStatus.CANCELLED.value,
    }:
        subtask.finished_at = datetime.utcnow()
    if error:
        subtask.error = error


def _persist_findings(
    db, case_id: UUID, subtask_id: UUID, items: Iterable[WorkerFinding]
) -> int:
    count = 0
    for it in items:
        db.add(
            Finding(
                case_id=case_id,
                subtask_id=subtask_id,
                category=it.category,
                severity=it.severity,
                confidence=Decimal(str(round(it.confidence, 3))),
                evidence=it.evidence,
            )
        )
        count += 1
    return count


def run_subtask(
    *,
    task_id: str,
    subtask_id: str,
    case_id: str,
    storage_key: str | None,
    worker_type: str,
    extra: dict,
    do_work: Callable[[WorkerContext], list[WorkerFinding]],
) -> dict[str, Any]:
    """Orquesta una unidad de trabajo de un worker.

    Garantiza:
    - Lock distribuido por subtask
    - Idempotencia via tabla `processed_tasks`
    - Transiciones de estado auditadas
    - Publicacion de eventos
    - Disparo del aggregator cuando el caso completa
    """
    ctx = WorkerContext(
        task_id=task_id,
        subtask_id=subtask_id,
        case_id=case_id,
        storage_key=storage_key,
        worker_type=worker_type,
        extra=extra,
    )
    bus = get_event_bus()
    counters = get_counters()

    with _subtask_lock(subtask_id) as acquired:
        if not acquired:
            logger.info(
                "subtask_skipped_already_locked",
                subtask_id=subtask_id,
                worker_type=worker_type,
            )
            return {"status": "skipped_locked"}

        with session_scope() as db:
            if _already_processed(db, task_id):
                logger.info(
                    "subtask_skipped_idempotent",
                    task_id=task_id,
                    subtask_id=subtask_id,
                )
                return {"status": "skipped_idempotent"}

            subtask = db.get(Subtask, UUID(subtask_id))
            if subtask is None:
                logger.warning("subtask_not_found", subtask_id=subtask_id)
                return {"status": "missing"}

            if subtask.status == SubtaskStatus.CANCELLED.value:
                logger.info("subtask_was_cancelled", subtask_id=subtask_id)
                return {"status": "cancelled"}

            case = db.get(Case, UUID(case_id))
            if case is None or case.status == CaseStatus.CANCELLED.value:
                _transition_subtask(db, subtask, SubtaskStatus.CANCELLED.value)
                return {"status": "case_missing_or_cancelled"}

            _ensure_case_processing(db, case)
            _transition_subtask(db, subtask, SubtaskStatus.PROCESSING.value)

        bus.publish(
            Event(
                type=EventType.SUBTASK_STARTED,
                case_id=case_id,
                payload={
                    "subtask_id": subtask_id,
                    "worker_type": worker_type,
                },
            )
        )

        try:
            findings = do_work(ctx)
        except Exception as exc:  # noqa: BLE001 - re-elevamos al final
            with session_scope() as db:
                subtask = db.get(Subtask, UUID(subtask_id))
                if subtask is not None:
                    _transition_subtask(
                        db, subtask, SubtaskStatus.FAILED.value, error=str(exc)
                    )
                case = db.get(Case, UUID(case_id))
                if case is not None:
                    case.failed_subtasks += 1
            counters.increment_failed(case_id)
            bus.publish(
                Event(
                    type=EventType.SUBTASK_FAILED,
                    case_id=case_id,
                    payload={
                        "subtask_id": subtask_id,
                        "worker_type": worker_type,
                        "error": str(exc),
                    },
                )
            )
            _maybe_finalize_case(case_id)
            raise

        with session_scope() as db:
            subtask = db.get(Subtask, UUID(subtask_id))
            case = db.get(Case, UUID(case_id))
            if subtask is None or case is None:
                return {"status": "vanished"}

            summary = _persist_findings(db, case.id, subtask.id, findings)
            subtask.result = {
                "findings_count": summary,
                "worker": worker_type,
            }
            _transition_subtask(db, subtask, SubtaskStatus.COMPLETED.value)
            case.completed_subtasks += 1
            _mark_processed(
                db,
                task_id=task_id,
                subtask_id=subtask_id,
                worker_type=worker_type,
                summary=f"{summary} findings",
            )
            high_severity = any(f.severity >= 4 for f in findings)

        done = counters.increment_done(case_id)
        bus.publish(
            Event(
                type=EventType.SUBTASK_COMPLETED,
                case_id=case_id,
                payload={
                    "subtask_id": subtask_id,
                    "worker_type": worker_type,
                    "findings_count": summary,
                },
            )
        )
        bus.publish(
            Event(
                type=EventType.CASE_PROGRESS,
                case_id=case_id,
                payload={"done": done},
            )
        )
        if high_severity:
            bus.publish(
                Event(
                    type=EventType.ALERT_HIGH_SEVERITY,
                    case_id=case_id,
                    payload={"subtask_id": subtask_id, "worker_type": worker_type},
                )
            )

        _maybe_finalize_case(case_id)

        return {
            "status": "completed",
            "findings": summary,
            "subtask_id": subtask_id,
        }


def _maybe_finalize_case(case_id: str) -> None:
    """Si todos los subtasks terminaron, lanzar el aggregator.

    Usa una clave Redis (SET NX) como semaforo para que solo un worker
    encole el aggregator aunque varios lleguen al mismo punto.
    """
    counters = get_counters()
    if not counters.is_complete(case_id):
        return
    if not counters.raw.set(f"case:{case_id}:aggregator_dispatched", "1", nx=True, ex=600):
        return

    with session_scope() as db:
        case = db.get(Case, UUID(case_id))
        priority = case.priority if case else 5

    dispatch_aggregator(case_id=case_id, priority=priority)
    logger.info("aggregator_dispatched", case_id=case_id)
