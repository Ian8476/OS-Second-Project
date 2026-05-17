"""Maquina de estados explicita para casos y subtasks.

Centraliza las transiciones permitidas. Cualquier intento de pasar
de un estado a otro no listado lanza `InvalidTransition`.
"""

from __future__ import annotations

from services.shared.models.enums import CaseStatus, SubtaskStatus


class InvalidTransition(Exception):
    def __init__(self, from_status: str, to_status: str) -> None:
        super().__init__(
            f"Transicion invalida: {from_status!r} -> {to_status!r}"
        )
        self.from_status = from_status
        self.to_status = to_status


CASE_TRANSITIONS: dict[str, set[str]] = {
    CaseStatus.QUEUED.value: {
        CaseStatus.PROCESSING.value,
        CaseStatus.CANCELLED.value,
        CaseStatus.FAILED.value,
    },
    CaseStatus.PROCESSING.value: {
        CaseStatus.COMPLETED.value,
        CaseStatus.FAILED.value,
        CaseStatus.RETRYING.value,
        CaseStatus.CANCELLED.value,
    },
    CaseStatus.RETRYING.value: {
        CaseStatus.PROCESSING.value,
        CaseStatus.FAILED.value,
        CaseStatus.CANCELLED.value,
    },
    CaseStatus.COMPLETED.value: set(),
    CaseStatus.FAILED.value: {CaseStatus.RETRYING.value},
    CaseStatus.CANCELLED.value: set(),
}


SUBTASK_TRANSITIONS: dict[str, set[str]] = {
    SubtaskStatus.PENDING.value: {
        SubtaskStatus.PROCESSING.value,
        SubtaskStatus.CANCELLED.value,
    },
    SubtaskStatus.PROCESSING.value: {
        SubtaskStatus.COMPLETED.value,
        SubtaskStatus.FAILED.value,
        SubtaskStatus.RETRYING.value,
        SubtaskStatus.CANCELLED.value,
    },
    SubtaskStatus.RETRYING.value: {
        SubtaskStatus.PROCESSING.value,
        SubtaskStatus.FAILED.value,
        SubtaskStatus.CANCELLED.value,
    },
    SubtaskStatus.COMPLETED.value: set(),
    SubtaskStatus.FAILED.value: {SubtaskStatus.RETRYING.value},
    SubtaskStatus.CANCELLED.value: set(),
}


def assert_case_transition(from_status: str, to_status: str) -> None:
    allowed = CASE_TRANSITIONS.get(from_status, set())
    if to_status not in allowed:
        raise InvalidTransition(from_status, to_status)


def assert_subtask_transition(from_status: str, to_status: str) -> None:
    allowed = SUBTASK_TRANSITIONS.get(from_status, set())
    if to_status not in allowed:
        raise InvalidTransition(from_status, to_status)
