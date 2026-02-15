"""Unit tests for collaboration warning, communication, and session payloads."""

from __future__ import annotations

import pytest
from pydantic import ValidationError as PydanticValidationError

from spec_kitty_events.collaboration import (
    CommentPostedPayload,
    ConcurrentDriverWarningPayload,
    DecisionCapturedPayload,
    FocusTarget,
    PotentialStepCollisionDetectedPayload,
    SessionLinkedPayload,
    WarningAcknowledgedPayload,
)


# ── ConcurrentDriverWarningPayload ─────────────────────────────────────────


class TestConcurrentDriverWarningPayload:
    """Tests for the ConcurrentDriverWarningPayload model."""

    def test_valid_with_two_participants(self) -> None:
        payload = ConcurrentDriverWarningPayload(
            warning_id="warn-001",
            mission_id="mission-abc",
            participant_ids=["p-001", "p-002"],
            focus_target=FocusTarget(target_type="wp", target_id="WP01"),
            severity="warning",
        )
        assert payload.warning_id == "warn-001"
        assert payload.mission_id == "mission-abc"
        assert payload.participant_ids == ["p-001", "p-002"]
        assert payload.focus_target.target_type == "wp"
        assert payload.focus_target.target_id == "WP01"
        assert payload.severity == "warning"

    def test_valid_with_three_participants(self) -> None:
        payload = ConcurrentDriverWarningPayload(
            warning_id="warn-002",
            mission_id="mission-def",
            participant_ids=["p-001", "p-002", "p-003"],
            focus_target=FocusTarget(target_type="step", target_id="step-5"),
            severity="info",
        )
        assert len(payload.participant_ids) == 3

    def test_rejected_with_one_participant(self) -> None:
        with pytest.raises(PydanticValidationError):
            ConcurrentDriverWarningPayload(
                warning_id="warn-003",
                mission_id="mission-ghi",
                participant_ids=["p-001"],
                focus_target=FocusTarget(target_type="wp", target_id="WP02"),
                severity="warning",
            )

    def test_rejected_with_empty_participants(self) -> None:
        with pytest.raises(PydanticValidationError):
            ConcurrentDriverWarningPayload(
                warning_id="warn-004",
                mission_id="mission-jkl",
                participant_ids=[],
                focus_target=FocusTarget(target_type="wp", target_id="WP03"),
                severity="info",
            )

    def test_embedded_focus_target(self) -> None:
        payload = ConcurrentDriverWarningPayload(
            warning_id="warn-005",
            mission_id="mission-mno",
            participant_ids=["p-a", "p-b"],
            focus_target=FocusTarget(target_type="file", target_id="src/main.py"),
            severity="info",
        )
        assert payload.focus_target.target_type == "file"
        assert payload.focus_target.target_id == "src/main.py"

    def test_severity_literal_info(self) -> None:
        payload = ConcurrentDriverWarningPayload(
            warning_id="warn-006",
            mission_id="mission-pqr",
            participant_ids=["p-x", "p-y"],
            focus_target=FocusTarget(target_type="wp", target_id="WP04"),
            severity="info",
        )
        assert payload.severity == "info"

    def test_severity_literal_warning(self) -> None:
        payload = ConcurrentDriverWarningPayload(
            warning_id="warn-007",
            mission_id="mission-stu",
            participant_ids=["p-x", "p-y"],
            focus_target=FocusTarget(target_type="wp", target_id="WP05"),
            severity="warning",
        )
        assert payload.severity == "warning"

    def test_invalid_severity_rejected(self) -> None:
        with pytest.raises(PydanticValidationError):
            ConcurrentDriverWarningPayload(
                warning_id="warn-008",
                mission_id="mission-vwx",
                participant_ids=["p-a", "p-b"],
                focus_target=FocusTarget(target_type="wp", target_id="WP06"),
                severity="critical",  # type: ignore[arg-type]
            )

    def test_frozen_rejects_assignment(self) -> None:
        payload = ConcurrentDriverWarningPayload(
            warning_id="warn-009",
            mission_id="mission-yza",
            participant_ids=["p-1", "p-2"],
            focus_target=FocusTarget(target_type="wp", target_id="WP07"),
            severity="warning",
        )
        with pytest.raises(PydanticValidationError):
            payload.warning_id = "changed"  # type: ignore[misc]

    def test_round_trip(self) -> None:
        original = ConcurrentDriverWarningPayload(
            warning_id="warn-010",
            mission_id="mission-bcd",
            participant_ids=["p-alpha", "p-beta"],
            focus_target=FocusTarget(target_type="step", target_id="step-9"),
            severity="info",
        )
        data = original.model_dump()
        restored = ConcurrentDriverWarningPayload.model_validate(data)
        assert restored == original

    def test_empty_warning_id_rejected(self) -> None:
        with pytest.raises(PydanticValidationError):
            ConcurrentDriverWarningPayload(
                warning_id="",
                mission_id="mission-efg",
                participant_ids=["p-1", "p-2"],
                focus_target=FocusTarget(target_type="wp", target_id="WP08"),
                severity="warning",
            )


# ── PotentialStepCollisionDetectedPayload ──────────────────────────────────


class TestPotentialStepCollisionDetectedPayload:
    """Tests for the PotentialStepCollisionDetectedPayload model."""

    def test_valid_with_two_participants(self) -> None:
        payload = PotentialStepCollisionDetectedPayload(
            warning_id="coll-001",
            mission_id="mission-abc",
            participant_ids=["p-001", "p-002"],
            step_id="step-3",
            severity="warning",
        )
        assert payload.warning_id == "coll-001"
        assert payload.mission_id == "mission-abc"
        assert payload.participant_ids == ["p-001", "p-002"]
        assert payload.step_id == "step-3"
        assert payload.wp_id is None
        assert payload.severity == "warning"

    def test_valid_with_wp_id(self) -> None:
        payload = PotentialStepCollisionDetectedPayload(
            warning_id="coll-002",
            mission_id="mission-def",
            participant_ids=["p-a", "p-b"],
            step_id="step-7",
            wp_id="WP02",
            severity="info",
        )
        assert payload.wp_id == "WP02"

    def test_rejected_with_one_participant(self) -> None:
        with pytest.raises(PydanticValidationError):
            PotentialStepCollisionDetectedPayload(
                warning_id="coll-003",
                mission_id="mission-ghi",
                participant_ids=["p-001"],
                step_id="step-1",
                severity="warning",
            )

    def test_rejected_with_empty_participants(self) -> None:
        with pytest.raises(PydanticValidationError):
            PotentialStepCollisionDetectedPayload(
                warning_id="coll-004",
                mission_id="mission-jkl",
                participant_ids=[],
                step_id="step-2",
                severity="info",
            )

    def test_severity_literal_info(self) -> None:
        payload = PotentialStepCollisionDetectedPayload(
            warning_id="coll-005",
            mission_id="mission-mno",
            participant_ids=["p-x", "p-y"],
            step_id="step-4",
            severity="info",
        )
        assert payload.severity == "info"

    def test_invalid_severity_rejected(self) -> None:
        with pytest.raises(PydanticValidationError):
            PotentialStepCollisionDetectedPayload(
                warning_id="coll-006",
                mission_id="mission-pqr",
                participant_ids=["p-a", "p-b"],
                step_id="step-5",
                severity="error",  # type: ignore[arg-type]
            )

    def test_optional_wp_id_defaults_to_none(self) -> None:
        payload = PotentialStepCollisionDetectedPayload(
            warning_id="coll-007",
            mission_id="mission-stu",
            participant_ids=["p-1", "p-2"],
            step_id="step-6",
            severity="warning",
        )
        assert payload.wp_id is None

    def test_frozen_rejects_assignment(self) -> None:
        payload = PotentialStepCollisionDetectedPayload(
            warning_id="coll-008",
            mission_id="mission-vwx",
            participant_ids=["p-a", "p-b"],
            step_id="step-8",
            severity="info",
        )
        with pytest.raises(PydanticValidationError):
            payload.step_id = "changed"  # type: ignore[misc]

    def test_round_trip(self) -> None:
        original = PotentialStepCollisionDetectedPayload(
            warning_id="coll-009",
            mission_id="mission-yza",
            participant_ids=["p-alpha", "p-beta"],
            step_id="step-10",
            wp_id="WP05",
            severity="warning",
        )
        data = original.model_dump()
        restored = PotentialStepCollisionDetectedPayload.model_validate(data)
        assert restored == original

    def test_empty_step_id_rejected(self) -> None:
        with pytest.raises(PydanticValidationError):
            PotentialStepCollisionDetectedPayload(
                warning_id="coll-010",
                mission_id="mission-bcd",
                participant_ids=["p-1", "p-2"],
                step_id="",
                severity="warning",
            )


# ── WarningAcknowledgedPayload ──────────────────────────────────────────────


class TestWarningAcknowledgedPayload:
    """Tests for the WarningAcknowledgedPayload model."""

    @pytest.mark.parametrize("ack", ["continue", "hold", "reassign", "defer"])
    def test_all_acknowledgement_values(self, ack: str) -> None:
        payload = WarningAcknowledgedPayload(
            participant_id="p-001",
            mission_id="mission-abc",
            warning_id="warn-001",
            acknowledgement=ack,  # type: ignore[arg-type]
        )
        assert payload.acknowledgement == ack

    def test_invalid_acknowledgement_rejected(self) -> None:
        with pytest.raises(PydanticValidationError):
            WarningAcknowledgedPayload(
                participant_id="p-002",
                mission_id="mission-def",
                warning_id="warn-002",
                acknowledgement="ignore",  # type: ignore[arg-type]
            )

    def test_valid_construction(self) -> None:
        payload = WarningAcknowledgedPayload(
            participant_id="p-003",
            mission_id="mission-ghi",
            warning_id="warn-003",
            acknowledgement="hold",
        )
        assert payload.participant_id == "p-003"
        assert payload.mission_id == "mission-ghi"
        assert payload.warning_id == "warn-003"
        assert payload.acknowledgement == "hold"

    def test_frozen_rejects_assignment(self) -> None:
        payload = WarningAcknowledgedPayload(
            participant_id="p-004",
            mission_id="mission-jkl",
            warning_id="warn-004",
            acknowledgement="continue",
        )
        with pytest.raises(PydanticValidationError):
            payload.acknowledgement = "defer"  # type: ignore[misc]

    def test_empty_participant_id_rejected(self) -> None:
        with pytest.raises(PydanticValidationError):
            WarningAcknowledgedPayload(
                participant_id="",
                mission_id="mission-mno",
                warning_id="warn-005",
                acknowledgement="reassign",
            )

    def test_empty_warning_id_rejected(self) -> None:
        with pytest.raises(PydanticValidationError):
            WarningAcknowledgedPayload(
                participant_id="p-005",
                mission_id="mission-pqr",
                warning_id="",
                acknowledgement="defer",
            )

    def test_round_trip(self) -> None:
        original = WarningAcknowledgedPayload(
            participant_id="p-006",
            mission_id="mission-stu",
            warning_id="warn-006",
            acknowledgement="continue",
        )
        data = original.model_dump()
        restored = WarningAcknowledgedPayload.model_validate(data)
        assert restored == original


# ── CommentPostedPayload ────────────────────────────────────────────────────


class TestCommentPostedPayload:
    """Tests for the CommentPostedPayload model."""

    def test_valid_without_reply_to(self) -> None:
        payload = CommentPostedPayload(
            participant_id="p-001",
            mission_id="mission-abc",
            comment_id="comment-001",
            content="This looks good!",
        )
        assert payload.participant_id == "p-001"
        assert payload.mission_id == "mission-abc"
        assert payload.comment_id == "comment-001"
        assert payload.content == "This looks good!"
        assert payload.reply_to is None

    def test_valid_with_reply_to(self) -> None:
        payload = CommentPostedPayload(
            participant_id="p-002",
            mission_id="mission-def",
            comment_id="comment-002",
            content="I agree with the above.",
            reply_to="comment-001",
        )
        assert payload.reply_to == "comment-001"

    def test_empty_content_rejected(self) -> None:
        with pytest.raises(PydanticValidationError):
            CommentPostedPayload(
                participant_id="p-003",
                mission_id="mission-ghi",
                comment_id="comment-003",
                content="",
            )

    def test_empty_comment_id_rejected(self) -> None:
        with pytest.raises(PydanticValidationError):
            CommentPostedPayload(
                participant_id="p-004",
                mission_id="mission-jkl",
                comment_id="",
                content="Some content",
            )

    def test_frozen_rejects_assignment(self) -> None:
        payload = CommentPostedPayload(
            participant_id="p-005",
            mission_id="mission-mno",
            comment_id="comment-005",
            content="A comment",
        )
        with pytest.raises(PydanticValidationError):
            payload.content = "changed"  # type: ignore[misc]

    def test_round_trip(self) -> None:
        original = CommentPostedPayload(
            participant_id="p-006",
            mission_id="mission-pqr",
            comment_id="comment-006",
            content="Round trip test",
            reply_to="comment-005",
        )
        data = original.model_dump()
        restored = CommentPostedPayload.model_validate(data)
        assert restored == original

    def test_reply_to_defaults_to_none(self) -> None:
        payload = CommentPostedPayload(
            participant_id="p-007",
            mission_id="mission-stu",
            comment_id="comment-007",
            content="No reply",
        )
        assert payload.reply_to is None


# ── DecisionCapturedPayload ─────────────────────────────────────────────────


class TestDecisionCapturedPayload:
    """Tests for the DecisionCapturedPayload model."""

    def test_valid_minimal(self) -> None:
        payload = DecisionCapturedPayload(
            participant_id="p-001",
            mission_id="mission-abc",
            decision_id="dec-001",
            topic="Which framework to use?",
            chosen_option="Option A",
        )
        assert payload.participant_id == "p-001"
        assert payload.decision_id == "dec-001"
        assert payload.topic == "Which framework to use?"
        assert payload.chosen_option == "Option A"
        assert payload.rationale is None
        assert payload.referenced_warning_id is None

    def test_valid_with_rationale(self) -> None:
        payload = DecisionCapturedPayload(
            participant_id="p-002",
            mission_id="mission-def",
            decision_id="dec-002",
            topic="Database choice",
            chosen_option="PostgreSQL",
            rationale="Better JSON support",
        )
        assert payload.rationale == "Better JSON support"

    def test_valid_with_referenced_warning_id(self) -> None:
        payload = DecisionCapturedPayload(
            participant_id="p-003",
            mission_id="mission-ghi",
            decision_id="dec-003",
            topic="Resolve collision",
            chosen_option="Reassign step",
            referenced_warning_id="warn-001",
        )
        assert payload.referenced_warning_id == "warn-001"

    def test_valid_with_all_optional_fields(self) -> None:
        payload = DecisionCapturedPayload(
            participant_id="p-004",
            mission_id="mission-jkl",
            decision_id="dec-004",
            topic="Architecture pattern",
            chosen_option="Event sourcing",
            rationale="Fits our audit requirements",
            referenced_warning_id="warn-002",
        )
        assert payload.rationale == "Fits our audit requirements"
        assert payload.referenced_warning_id == "warn-002"

    def test_empty_topic_rejected(self) -> None:
        with pytest.raises(PydanticValidationError):
            DecisionCapturedPayload(
                participant_id="p-005",
                mission_id="mission-mno",
                decision_id="dec-005",
                topic="",
                chosen_option="Something",
            )

    def test_empty_chosen_option_rejected(self) -> None:
        with pytest.raises(PydanticValidationError):
            DecisionCapturedPayload(
                participant_id="p-006",
                mission_id="mission-pqr",
                decision_id="dec-006",
                topic="Some topic",
                chosen_option="",
            )

    def test_frozen_rejects_assignment(self) -> None:
        payload = DecisionCapturedPayload(
            participant_id="p-007",
            mission_id="mission-stu",
            decision_id="dec-007",
            topic="Some topic",
            chosen_option="Some option",
        )
        with pytest.raises(PydanticValidationError):
            payload.topic = "changed"  # type: ignore[misc]

    def test_round_trip(self) -> None:
        original = DecisionCapturedPayload(
            participant_id="p-008",
            mission_id="mission-vwx",
            decision_id="dec-008",
            topic="Final decision",
            chosen_option="Go with plan B",
            rationale="Lower risk",
            referenced_warning_id="warn-003",
        )
        data = original.model_dump()
        restored = DecisionCapturedPayload.model_validate(data)
        assert restored == original


# ── SessionLinkedPayload ────────────────────────────────────────────────────


class TestSessionLinkedPayload:
    """Tests for the SessionLinkedPayload model."""

    def test_valid_cli_to_saas(self) -> None:
        payload = SessionLinkedPayload(
            participant_id="p-001",
            mission_id="mission-abc",
            primary_session_id="sess-cli-001",
            linked_session_id="sess-saas-001",
            link_type="cli_to_saas",
        )
        assert payload.participant_id == "p-001"
        assert payload.primary_session_id == "sess-cli-001"
        assert payload.linked_session_id == "sess-saas-001"
        assert payload.link_type == "cli_to_saas"

    def test_valid_saas_to_cli(self) -> None:
        payload = SessionLinkedPayload(
            participant_id="p-002",
            mission_id="mission-def",
            primary_session_id="sess-saas-002",
            linked_session_id="sess-cli-002",
            link_type="saas_to_cli",
        )
        assert payload.link_type == "saas_to_cli"

    def test_invalid_link_type_rejected(self) -> None:
        with pytest.raises(PydanticValidationError):
            SessionLinkedPayload(
                participant_id="p-003",
                mission_id="mission-ghi",
                primary_session_id="sess-a",
                linked_session_id="sess-b",
                link_type="peer_to_peer",  # type: ignore[arg-type]
            )

    def test_empty_primary_session_id_rejected(self) -> None:
        with pytest.raises(PydanticValidationError):
            SessionLinkedPayload(
                participant_id="p-004",
                mission_id="mission-jkl",
                primary_session_id="",
                linked_session_id="sess-c",
                link_type="cli_to_saas",
            )

    def test_empty_linked_session_id_rejected(self) -> None:
        with pytest.raises(PydanticValidationError):
            SessionLinkedPayload(
                participant_id="p-005",
                mission_id="mission-mno",
                primary_session_id="sess-d",
                linked_session_id="",
                link_type="saas_to_cli",
            )

    def test_frozen_rejects_assignment(self) -> None:
        payload = SessionLinkedPayload(
            participant_id="p-006",
            mission_id="mission-pqr",
            primary_session_id="sess-e",
            linked_session_id="sess-f",
            link_type="cli_to_saas",
        )
        with pytest.raises(PydanticValidationError):
            payload.link_type = "saas_to_cli"  # type: ignore[misc]

    def test_round_trip(self) -> None:
        original = SessionLinkedPayload(
            participant_id="p-007",
            mission_id="mission-stu",
            primary_session_id="sess-g",
            linked_session_id="sess-h",
            link_type="saas_to_cli",
        )
        data = original.model_dump()
        restored = SessionLinkedPayload.model_validate(data)
        assert restored == original

    def test_empty_participant_id_rejected(self) -> None:
        with pytest.raises(PydanticValidationError):
            SessionLinkedPayload(
                participant_id="",
                mission_id="mission-vwx",
                primary_session_id="sess-i",
                linked_session_id="sess-j",
                link_type="cli_to_saas",
            )
