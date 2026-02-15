"""Unit tests for collaboration intent, focus, and execution payload models."""

from __future__ import annotations

import pytest
from pydantic import ValidationError as PydanticValidationError

from spec_kitty_events.collaboration import (
    DriveIntentSetPayload,
    FocusChangedPayload,
    FocusTarget,
    PromptStepExecutionCompletedPayload,
    PromptStepExecutionStartedPayload,
)


# ── DriveIntentSetPayload ──────────────────────────────────────────────────


class TestDriveIntentSetPayload:
    """Tests for the DriveIntentSetPayload model."""

    def test_valid_active_intent(self) -> None:
        payload = DriveIntentSetPayload(
            participant_id="p-001",
            mission_id="m-100",
            intent="active",
        )
        assert payload.participant_id == "p-001"
        assert payload.mission_id == "m-100"
        assert payload.intent == "active"

    def test_valid_inactive_intent(self) -> None:
        payload = DriveIntentSetPayload(
            participant_id="p-002",
            mission_id="m-200",
            intent="inactive",
        )
        assert payload.intent == "inactive"

    def test_invalid_intent_rejected(self) -> None:
        with pytest.raises(PydanticValidationError):
            DriveIntentSetPayload(
                participant_id="p-003",
                mission_id="m-300",
                intent="paused",  # type: ignore[arg-type]
            )

    def test_frozen_rejects_assignment(self) -> None:
        payload = DriveIntentSetPayload(
            participant_id="p-004",
            mission_id="m-400",
            intent="active",
        )
        with pytest.raises(PydanticValidationError):
            payload.intent = "inactive"  # type: ignore[misc]

    def test_empty_participant_id_rejected(self) -> None:
        with pytest.raises(PydanticValidationError):
            DriveIntentSetPayload(
                participant_id="",
                mission_id="m-500",
                intent="active",
            )

    def test_empty_mission_id_rejected(self) -> None:
        with pytest.raises(PydanticValidationError):
            DriveIntentSetPayload(
                participant_id="p-005",
                mission_id="",
                intent="active",
            )

    def test_round_trip_via_model_dump_validate(self) -> None:
        original = DriveIntentSetPayload(
            participant_id="p-006",
            mission_id="m-600",
            intent="inactive",
        )
        data = original.model_dump()
        restored = DriveIntentSetPayload.model_validate(data)
        assert restored == original

    def test_model_dump_produces_dict(self) -> None:
        payload = DriveIntentSetPayload(
            participant_id="p-007",
            mission_id="m-700",
            intent="active",
        )
        dumped = payload.model_dump()
        assert isinstance(dumped, dict)
        assert dumped["participant_id"] == "p-007"
        assert dumped["mission_id"] == "m-700"
        assert dumped["intent"] == "active"


# ── FocusChangedPayload ────────────────────────────────────────────────────


class TestFocusChangedPayload:
    """Tests for the FocusChangedPayload model."""

    def test_valid_with_nested_focus_target(self) -> None:
        target = FocusTarget(target_type="wp", target_id="WP01")
        payload = FocusChangedPayload(
            participant_id="p-010",
            mission_id="m-100",
            focus_target=target,
        )
        assert payload.focus_target.target_type == "wp"
        assert payload.focus_target.target_id == "WP01"

    def test_previous_focus_target_defaults_to_none(self) -> None:
        payload = FocusChangedPayload(
            participant_id="p-011",
            mission_id="m-110",
            focus_target=FocusTarget(target_type="step", target_id="step-1"),
        )
        assert payload.previous_focus_target is None

    def test_previous_focus_target_accepted(self) -> None:
        prev = FocusTarget(target_type="file", target_id="src/old.py")
        curr = FocusTarget(target_type="file", target_id="src/new.py")
        payload = FocusChangedPayload(
            participant_id="p-012",
            mission_id="m-120",
            focus_target=curr,
            previous_focus_target=prev,
        )
        assert payload.previous_focus_target is not None
        assert payload.previous_focus_target.target_id == "src/old.py"

    def test_round_trip_preserves_nested_model(self) -> None:
        prev = FocusTarget(target_type="wp", target_id="WP01")
        curr = FocusTarget(target_type="wp", target_id="WP02")
        original = FocusChangedPayload(
            participant_id="p-013",
            mission_id="m-130",
            focus_target=curr,
            previous_focus_target=prev,
        )
        data = original.model_dump()
        restored = FocusChangedPayload.model_validate(data)
        assert restored == original
        assert restored.focus_target.target_id == "WP02"
        assert restored.previous_focus_target is not None
        assert restored.previous_focus_target.target_id == "WP01"

    def test_round_trip_with_none_previous(self) -> None:
        original = FocusChangedPayload(
            participant_id="p-014",
            mission_id="m-140",
            focus_target=FocusTarget(target_type="step", target_id="step-5"),
        )
        data = original.model_dump()
        restored = FocusChangedPayload.model_validate(data)
        assert restored == original
        assert restored.previous_focus_target is None

    def test_nested_model_serialization(self) -> None:
        payload = FocusChangedPayload(
            participant_id="p-015",
            mission_id="m-150",
            focus_target=FocusTarget(target_type="file", target_id="README.md"),
            previous_focus_target=FocusTarget(target_type="wp", target_id="WP03"),
        )
        dumped = payload.model_dump()
        assert dumped["focus_target"] == {"target_type": "file", "target_id": "README.md"}
        assert dumped["previous_focus_target"] == {"target_type": "wp", "target_id": "WP03"}

    def test_frozen_rejects_assignment(self) -> None:
        payload = FocusChangedPayload(
            participant_id="p-016",
            mission_id="m-160",
            focus_target=FocusTarget(target_type="wp", target_id="WP01"),
        )
        with pytest.raises(PydanticValidationError):
            payload.mission_id = "changed"  # type: ignore[misc]

    def test_empty_participant_id_rejected(self) -> None:
        with pytest.raises(PydanticValidationError):
            FocusChangedPayload(
                participant_id="",
                mission_id="m-170",
                focus_target=FocusTarget(target_type="wp", target_id="WP01"),
            )

    def test_empty_mission_id_rejected(self) -> None:
        with pytest.raises(PydanticValidationError):
            FocusChangedPayload(
                participant_id="p-017",
                mission_id="",
                focus_target=FocusTarget(target_type="wp", target_id="WP01"),
            )


# ── PromptStepExecutionStartedPayload ─────────────────────────────────────


class TestPromptStepExecutionStartedPayload:
    """Tests for the PromptStepExecutionStartedPayload model."""

    def test_valid_with_all_fields(self) -> None:
        payload = PromptStepExecutionStartedPayload(
            participant_id="p-020",
            mission_id="m-200",
            step_id="step-1",
            wp_id="WP01",
            step_description="Run unit tests",
        )
        assert payload.participant_id == "p-020"
        assert payload.mission_id == "m-200"
        assert payload.step_id == "step-1"
        assert payload.wp_id == "WP01"
        assert payload.step_description == "Run unit tests"

    def test_valid_without_optional_fields(self) -> None:
        payload = PromptStepExecutionStartedPayload(
            participant_id="p-021",
            mission_id="m-210",
            step_id="step-2",
        )
        assert payload.wp_id is None
        assert payload.step_description is None

    def test_frozen_rejects_assignment(self) -> None:
        payload = PromptStepExecutionStartedPayload(
            participant_id="p-022",
            mission_id="m-220",
            step_id="step-3",
        )
        with pytest.raises(PydanticValidationError):
            payload.step_id = "changed"  # type: ignore[misc]

    def test_empty_participant_id_rejected(self) -> None:
        with pytest.raises(PydanticValidationError):
            PromptStepExecutionStartedPayload(
                participant_id="",
                mission_id="m-230",
                step_id="step-4",
            )

    def test_empty_mission_id_rejected(self) -> None:
        with pytest.raises(PydanticValidationError):
            PromptStepExecutionStartedPayload(
                participant_id="p-023",
                mission_id="",
                step_id="step-4",
            )

    def test_empty_step_id_rejected(self) -> None:
        with pytest.raises(PydanticValidationError):
            PromptStepExecutionStartedPayload(
                participant_id="p-024",
                mission_id="m-240",
                step_id="",
            )

    def test_round_trip_via_model_dump_validate(self) -> None:
        original = PromptStepExecutionStartedPayload(
            participant_id="p-025",
            mission_id="m-250",
            step_id="step-5",
            wp_id="WP03",
            step_description="Build artifacts",
        )
        data = original.model_dump()
        restored = PromptStepExecutionStartedPayload.model_validate(data)
        assert restored == original

    def test_round_trip_without_optionals(self) -> None:
        original = PromptStepExecutionStartedPayload(
            participant_id="p-026",
            mission_id="m-260",
            step_id="step-6",
        )
        data = original.model_dump()
        restored = PromptStepExecutionStartedPayload.model_validate(data)
        assert restored == original
        assert restored.wp_id is None
        assert restored.step_description is None


# ── PromptStepExecutionCompletedPayload ───────────────────────────────────


class TestPromptStepExecutionCompletedPayload:
    """Tests for the PromptStepExecutionCompletedPayload model."""

    def test_valid_success_outcome(self) -> None:
        payload = PromptStepExecutionCompletedPayload(
            participant_id="p-030",
            mission_id="m-300",
            step_id="step-1",
            outcome="success",
        )
        assert payload.outcome == "success"

    def test_valid_failure_outcome(self) -> None:
        payload = PromptStepExecutionCompletedPayload(
            participant_id="p-031",
            mission_id="m-310",
            step_id="step-2",
            outcome="failure",
        )
        assert payload.outcome == "failure"

    def test_valid_skipped_outcome(self) -> None:
        payload = PromptStepExecutionCompletedPayload(
            participant_id="p-032",
            mission_id="m-320",
            step_id="step-3",
            outcome="skipped",
        )
        assert payload.outcome == "skipped"

    def test_invalid_outcome_rejected(self) -> None:
        with pytest.raises(PydanticValidationError):
            PromptStepExecutionCompletedPayload(
                participant_id="p-033",
                mission_id="m-330",
                step_id="step-4",
                outcome="timeout",  # type: ignore[arg-type]
            )

    def test_frozen_rejects_assignment(self) -> None:
        payload = PromptStepExecutionCompletedPayload(
            participant_id="p-034",
            mission_id="m-340",
            step_id="step-5",
            outcome="success",
        )
        with pytest.raises(PydanticValidationError):
            payload.outcome = "failure"  # type: ignore[misc]

    def test_optional_wp_id_defaults_to_none(self) -> None:
        payload = PromptStepExecutionCompletedPayload(
            participant_id="p-035",
            mission_id="m-350",
            step_id="step-6",
            outcome="success",
        )
        assert payload.wp_id is None

    def test_wp_id_accepted(self) -> None:
        payload = PromptStepExecutionCompletedPayload(
            participant_id="p-036",
            mission_id="m-360",
            step_id="step-7",
            wp_id="WP02",
            outcome="failure",
        )
        assert payload.wp_id == "WP02"

    def test_empty_participant_id_rejected(self) -> None:
        with pytest.raises(PydanticValidationError):
            PromptStepExecutionCompletedPayload(
                participant_id="",
                mission_id="m-370",
                step_id="step-8",
                outcome="success",
            )

    def test_empty_mission_id_rejected(self) -> None:
        with pytest.raises(PydanticValidationError):
            PromptStepExecutionCompletedPayload(
                participant_id="p-037",
                mission_id="",
                step_id="step-8",
                outcome="success",
            )

    def test_empty_step_id_rejected(self) -> None:
        with pytest.raises(PydanticValidationError):
            PromptStepExecutionCompletedPayload(
                participant_id="p-038",
                mission_id="m-380",
                step_id="",
                outcome="success",
            )

    def test_round_trip_via_model_dump_validate(self) -> None:
        original = PromptStepExecutionCompletedPayload(
            participant_id="p-039",
            mission_id="m-390",
            step_id="step-9",
            wp_id="WP05",
            outcome="skipped",
        )
        data = original.model_dump()
        restored = PromptStepExecutionCompletedPayload.model_validate(data)
        assert restored == original

    def test_round_trip_without_wp_id(self) -> None:
        original = PromptStepExecutionCompletedPayload(
            participant_id="p-040",
            mission_id="m-400",
            step_id="step-10",
            outcome="success",
        )
        data = original.model_dump()
        restored = PromptStepExecutionCompletedPayload.model_validate(data)
        assert restored == original
        assert restored.wp_id is None

    def test_model_dump_produces_dict(self) -> None:
        payload = PromptStepExecutionCompletedPayload(
            participant_id="p-041",
            mission_id="m-410",
            step_id="step-11",
            outcome="failure",
        )
        dumped = payload.model_dump()
        assert isinstance(dumped, dict)
        assert dumped["outcome"] == "failure"
        assert dumped["step_id"] == "step-11"
