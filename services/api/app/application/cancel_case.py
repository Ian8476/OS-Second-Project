"""Caso de uso: cancelar un caso en curso.

No interrumpe tareas ya en ejecucion (eso requeriria signals); marca el
caso y subtasks como cancelados para que el aggregator no los espere.
"""

import uuid

from sqlalchemy.orm import Session

from services.api.app.core.exceptions import (
    CaseAlreadyTerminal,
    CaseNotFound,
)
from services.shared.events.bus import Event, EventType, get_event_bus
from services.shared.models.case import Case, CaseStateHistory
from services.shared.models.enums import CaseStatus, SubtaskStatus
from services.shared.state_machine import assert_case_transition


_TERMINAL = {
    CaseStatus.COMPLETED.value,
    CaseStatus.FAILED.value,
    CaseStatus.CANCELLED.value,
}


def execute(case_id: uuid.UUID, reason: str | None, *, db: Session) -> Case:
    case = db.get(Case, case_id)
    if case is None:
        raise CaseNotFound(f"case {case_id} no encontrado")

    if case.status in _TERMINAL:
        raise CaseAlreadyTerminal(
            f"case {case_id} en estado terminal {case.status}"
        )

    previous = case.status
    assert_case_transition(previous, CaseStatus.CANCELLED.value)

    case.status = CaseStatus.CANCELLED.value
    db.add(
        CaseStateHistory(
            case_id=case.id,
            from_status=previous,
            to_status=CaseStatus.CANCELLED.value,
            reason=reason or "user_cancelled",
        )
    )

    for st in case.subtasks:
        if st.status not in {
            SubtaskStatus.COMPLETED.value,
            SubtaskStatus.FAILED.value,
            SubtaskStatus.CANCELLED.value,
        }:
            st.status = SubtaskStatus.CANCELLED.value

    db.commit()

    get_event_bus().publish(
        Event(
            type=EventType.CASE_CANCELLED,
            case_id=str(case.id),
            payload={"reason": reason},
        )
    )
    return case
