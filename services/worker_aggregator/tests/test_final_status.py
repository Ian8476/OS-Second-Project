"""Tests del calculo de estado final del caso (sin BD ni MinIO)."""

from types import SimpleNamespace

from services.shared.models.enums import CaseStatus, SubtaskStatus
from services.worker_aggregator.tasks import _final_status


def _case(subtasks_statuses: list[str], completed: int, failed: int):
    return SimpleNamespace(
        subtasks=[SimpleNamespace(status=s) for s in subtasks_statuses],
        completed_subtasks=completed,
        failed_subtasks=failed,
    )


def test_all_completed_is_completed():
    case = _case([SubtaskStatus.COMPLETED.value] * 3, completed=3, failed=0)
    assert _final_status(case) == CaseStatus.COMPLETED.value


def test_some_failed_some_completed_is_completed():
    case = _case(
        [
            SubtaskStatus.COMPLETED.value,
            SubtaskStatus.FAILED.value,
            SubtaskStatus.COMPLETED.value,
        ],
        completed=2,
        failed=1,
    )
    assert _final_status(case) == CaseStatus.COMPLETED.value


def test_all_failed_is_failed():
    case = _case([SubtaskStatus.FAILED.value] * 3, completed=0, failed=3)
    assert _final_status(case) == CaseStatus.FAILED.value


def test_pending_subtask_returns_processing():
    case = _case(
        [SubtaskStatus.PROCESSING.value, SubtaskStatus.COMPLETED.value],
        completed=1,
        failed=0,
    )
    assert _final_status(case) == CaseStatus.PROCESSING.value
