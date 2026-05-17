"""Tests de la maquina de estados."""

import pytest

from services.shared.models.enums import CaseStatus, SubtaskStatus
from services.shared.state_machine import (
    InvalidTransition,
    assert_case_transition,
    assert_subtask_transition,
)


def test_case_queued_to_processing_is_allowed():
    assert_case_transition(CaseStatus.QUEUED.value, CaseStatus.PROCESSING.value)


def test_case_completed_is_terminal():
    with pytest.raises(InvalidTransition):
        assert_case_transition(
            CaseStatus.COMPLETED.value, CaseStatus.PROCESSING.value
        )


def test_subtask_failed_can_be_retried():
    assert_subtask_transition(
        SubtaskStatus.FAILED.value, SubtaskStatus.RETRYING.value
    )


def test_subtask_completed_cannot_go_back_to_processing():
    with pytest.raises(InvalidTransition):
        assert_subtask_transition(
            SubtaskStatus.COMPLETED.value, SubtaskStatus.PROCESSING.value
        )
