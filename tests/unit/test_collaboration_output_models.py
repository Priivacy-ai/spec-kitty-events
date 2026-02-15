"""Unit tests for collaboration reducer output models (Section 4)."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError as PydanticValidationError

from spec_kitty_events.collaboration import (
    CollaborationAnomaly,
    CommentEntry,
    DecisionEntry,
    FocusTarget,
    ParticipantIdentity,
    ReducedCollaborationState,
    WarningEntry,
)


# ── CollaborationAnomaly ───────────────────────────────────────────────────


class TestCollaborationAnomaly:
    """Tests for the CollaborationAnomaly model."""

    def test_valid_construction(self) -> None:
        anomaly = CollaborationAnomaly(
            event_id="evt-001",
            event_type="ParticipantJoined",
            reason="Unknown participant in roster",
        )
        assert anomaly.event_id == "evt-001"
        assert anomaly.event_type == "ParticipantJoined"
        assert anomaly.reason == "Unknown participant in roster"

    def test_frozen_rejects_assignment(self) -> None:
        anomaly = CollaborationAnomaly(
            event_id="evt-002",
            event_type="FocusChanged",
            reason="Focus on unknown target",
        )
        with pytest.raises(PydanticValidationError):
            anomaly.event_id = "changed"  # type: ignore[misc]

    def test_field_access(self) -> None:
        anomaly = CollaborationAnomaly(
            event_id="evt-003",
            event_type="DriveIntentSet",
            reason="Duplicate drive intent",
        )
        assert isinstance(anomaly.event_id, str)
        assert isinstance(anomaly.event_type, str)
        assert isinstance(anomaly.reason, str)

    def test_round_trip_via_model_dump_validate(self) -> None:
        original = CollaborationAnomaly(
            event_id="evt-004",
            event_type="PresenceHeartbeat",
            reason="Heartbeat from departed participant",
        )
        data = original.model_dump()
        restored = CollaborationAnomaly.model_validate(data)
        assert restored == original

    def test_model_dump_produces_dict(self) -> None:
        anomaly = CollaborationAnomaly(
            event_id="evt-005",
            event_type="SessionLinked",
            reason="Session already linked",
        )
        dumped = anomaly.model_dump()
        assert isinstance(dumped, dict)
        assert dumped["event_id"] == "evt-005"
        assert dumped["event_type"] == "SessionLinked"
        assert dumped["reason"] == "Session already linked"


# ── WarningEntry ───────────────────────────────────────────────────────────


class TestWarningEntry:
    """Tests for the WarningEntry model."""

    def test_valid_construction(self) -> None:
        warning = WarningEntry(
            warning_id="warn-001",
            event_id="evt-010",
            warning_type="ConcurrentDriverWarning",
            participant_ids=("p-001", "p-002"),
        )
        assert warning.warning_id == "warn-001"
        assert warning.event_id == "evt-010"
        assert warning.warning_type == "ConcurrentDriverWarning"
        assert warning.participant_ids == ("p-001", "p-002")
        assert warning.acknowledgements == {}

    def test_with_acknowledgements(self) -> None:
        warning = WarningEntry(
            warning_id="warn-002",
            event_id="evt-011",
            warning_type="PotentialStepCollisionDetected",
            participant_ids=("p-003",),
            acknowledgements={"p-003": "proceed"},
        )
        assert warning.acknowledgements == {"p-003": "proceed"}

    def test_frozen_rejects_assignment(self) -> None:
        warning = WarningEntry(
            warning_id="warn-003",
            event_id="evt-012",
            warning_type="ConcurrentDriverWarning",
            participant_ids=("p-004",),
        )
        with pytest.raises(PydanticValidationError):
            warning.warning_id = "changed"  # type: ignore[misc]

    def test_round_trip_via_model_dump_validate(self) -> None:
        original = WarningEntry(
            warning_id="warn-004",
            event_id="evt-013",
            warning_type="PotentialStepCollisionDetected",
            participant_ids=("p-005", "p-006"),
            acknowledgements={"p-005": "abort", "p-006": "continue"},
        )
        data = original.model_dump()
        restored = WarningEntry.model_validate(data)
        assert restored == original

    def test_participant_ids_is_tuple(self) -> None:
        warning = WarningEntry(
            warning_id="warn-005",
            event_id="evt-014",
            warning_type="ConcurrentDriverWarning",
            participant_ids=("p-007", "p-008", "p-009"),
        )
        assert isinstance(warning.participant_ids, tuple)
        assert len(warning.participant_ids) == 3

    def test_acknowledgements_default_empty_dict(self) -> None:
        warning = WarningEntry(
            warning_id="warn-006",
            event_id="evt-015",
            warning_type="ConcurrentDriverWarning",
            participant_ids=("p-010",),
        )
        assert warning.acknowledgements == {}
        assert isinstance(warning.acknowledgements, dict)


# ── DecisionEntry ──────────────────────────────────────────────────────────


class TestDecisionEntry:
    """Tests for the DecisionEntry model."""

    def test_valid_construction_with_warning_ref(self) -> None:
        decision = DecisionEntry(
            decision_id="dec-001",
            event_id="evt-020",
            participant_id="p-001",
            topic="Step ordering",
            chosen_option="sequential",
            referenced_warning_id="warn-001",
        )
        assert decision.decision_id == "dec-001"
        assert decision.event_id == "evt-020"
        assert decision.participant_id == "p-001"
        assert decision.topic == "Step ordering"
        assert decision.chosen_option == "sequential"
        assert decision.referenced_warning_id == "warn-001"

    def test_valid_construction_without_warning_ref(self) -> None:
        decision = DecisionEntry(
            decision_id="dec-002",
            event_id="evt-021",
            participant_id="p-002",
            topic="Architecture pattern",
            chosen_option="event-sourced",
        )
        assert decision.referenced_warning_id is None

    def test_frozen_rejects_assignment(self) -> None:
        decision = DecisionEntry(
            decision_id="dec-003",
            event_id="evt-022",
            participant_id="p-003",
            topic="Language choice",
            chosen_option="Python",
        )
        with pytest.raises(PydanticValidationError):
            decision.topic = "changed"  # type: ignore[misc]

    def test_round_trip_via_model_dump_validate(self) -> None:
        original = DecisionEntry(
            decision_id="dec-004",
            event_id="evt-023",
            participant_id="p-004",
            topic="Deployment target",
            chosen_option="Fly.io",
            referenced_warning_id="warn-002",
        )
        data = original.model_dump()
        restored = DecisionEntry.model_validate(data)
        assert restored == original

    def test_round_trip_without_warning_ref(self) -> None:
        original = DecisionEntry(
            decision_id="dec-005",
            event_id="evt-024",
            participant_id="p-005",
            topic="Test framework",
            chosen_option="pytest",
        )
        data = original.model_dump()
        restored = DecisionEntry.model_validate(data)
        assert restored == original
        assert restored.referenced_warning_id is None


# ── CommentEntry ───────────────────────────────────────────────────────────


class TestCommentEntry:
    """Tests for the CommentEntry model."""

    def test_valid_construction_with_reply(self) -> None:
        comment = CommentEntry(
            comment_id="cmt-001",
            event_id="evt-030",
            participant_id="p-001",
            content="Looks good to me.",
            reply_to="cmt-000",
        )
        assert comment.comment_id == "cmt-001"
        assert comment.event_id == "evt-030"
        assert comment.participant_id == "p-001"
        assert comment.content == "Looks good to me."
        assert comment.reply_to == "cmt-000"

    def test_valid_construction_without_reply(self) -> None:
        comment = CommentEntry(
            comment_id="cmt-002",
            event_id="evt-031",
            participant_id="p-002",
            content="Starting implementation now.",
        )
        assert comment.reply_to is None

    def test_frozen_rejects_assignment(self) -> None:
        comment = CommentEntry(
            comment_id="cmt-003",
            event_id="evt-032",
            participant_id="p-003",
            content="Original content.",
        )
        with pytest.raises(PydanticValidationError):
            comment.content = "modified"  # type: ignore[misc]

    def test_round_trip_via_model_dump_validate(self) -> None:
        original = CommentEntry(
            comment_id="cmt-004",
            event_id="evt-033",
            participant_id="p-004",
            content="Replying to the thread.",
            reply_to="cmt-001",
        )
        data = original.model_dump()
        restored = CommentEntry.model_validate(data)
        assert restored == original

    def test_round_trip_without_reply(self) -> None:
        original = CommentEntry(
            comment_id="cmt-005",
            event_id="evt-034",
            participant_id="p-005",
            content="Top-level comment.",
        )
        data = original.model_dump()
        restored = CommentEntry.model_validate(data)
        assert restored == original
        assert restored.reply_to is None


# ── ReducedCollaborationState ──────────────────────────────────────────────


class TestReducedCollaborationState:
    """Tests for the ReducedCollaborationState model."""

    def _make_populated_state(self) -> ReducedCollaborationState:
        """Build a representative populated state for reuse across tests."""
        p1 = ParticipantIdentity(
            participant_id="p-001",
            participant_type="human",
            display_name="Alice",
        )
        p2 = ParticipantIdentity(
            participant_id="p-002",
            participant_type="llm_context",
            display_name="Claude",
        )
        departed = ParticipantIdentity(
            participant_id="p-003",
            participant_type="human",
            display_name="Bob",
        )
        now = datetime(2025, 6, 15, 12, 0, 0, tzinfo=timezone.utc)
        focus_wp03 = FocusTarget(target_type="wp", target_id="WP03")

        warning = WarningEntry(
            warning_id="warn-001",
            event_id="evt-100",
            warning_type="ConcurrentDriverWarning",
            participant_ids=("p-001", "p-002"),
            acknowledgements={"p-001": "proceed"},
        )
        decision = DecisionEntry(
            decision_id="dec-001",
            event_id="evt-101",
            participant_id="p-001",
            topic="Step ordering",
            chosen_option="sequential",
            referenced_warning_id="warn-001",
        )
        comment = CommentEntry(
            comment_id="cmt-001",
            event_id="evt-102",
            participant_id="p-002",
            content="Acknowledged.",
        )
        anomaly = CollaborationAnomaly(
            event_id="evt-103",
            event_type="PresenceHeartbeat",
            reason="Heartbeat from departed participant p-003",
        )

        return ReducedCollaborationState(
            mission_id="mission-abc",
            participants={"p-001": p1, "p-002": p2},
            departed_participants={"p-003": departed},
            presence={"p-001": now, "p-002": now},
            active_drivers=frozenset({"p-001"}),
            focus_by_participant={"p-001": focus_wp03},
            participants_by_focus={"wp:WP03": frozenset({"p-001"})},
            warnings=(warning,),
            decisions=(decision,),
            comments=(comment,),
            active_executions={"p-001": ["step-1", "step-2"]},
            linked_sessions={"p-002": ["sess-xyz"]},
            anomalies=(anomaly,),
            event_count=15,
            last_processed_event_id="evt-103",
        )

    def test_populated_construction(self) -> None:
        state = self._make_populated_state()
        assert state.mission_id == "mission-abc"
        assert len(state.participants) == 2
        assert "p-001" in state.participants
        assert "p-002" in state.participants
        assert state.participants["p-001"].display_name == "Alice"
        assert len(state.departed_participants) == 1
        assert "p-003" in state.departed_participants
        assert len(state.presence) == 2
        assert state.active_drivers == frozenset({"p-001"})
        assert "p-001" in state.focus_by_participant
        assert state.focus_by_participant["p-001"].target_type == "wp"
        assert state.focus_by_participant["p-001"].target_id == "WP03"
        assert "wp:WP03" in state.participants_by_focus
        assert state.participants_by_focus["wp:WP03"] == frozenset({"p-001"})
        assert len(state.warnings) == 1
        assert len(state.decisions) == 1
        assert len(state.comments) == 1
        assert state.active_executions["p-001"] == ["step-1", "step-2"]
        assert state.linked_sessions["p-002"] == ["sess-xyz"]
        assert len(state.anomalies) == 1
        assert state.event_count == 15
        assert state.last_processed_event_id == "evt-103"

    def test_default_factory_values(self) -> None:
        state = ReducedCollaborationState(mission_id="mission-empty")
        assert state.mission_id == "mission-empty"
        assert state.participants == {}
        assert state.departed_participants == {}
        assert state.presence == {}
        assert state.active_drivers == frozenset()
        assert state.focus_by_participant == {}
        assert state.participants_by_focus == {}
        assert state.warnings == ()
        assert state.decisions == ()
        assert state.comments == ()
        assert state.active_executions == {}
        assert state.linked_sessions == {}
        assert state.anomalies == ()
        assert state.event_count == 0
        assert state.last_processed_event_id is None

    def test_frozen_rejects_assignment(self) -> None:
        state = ReducedCollaborationState(mission_id="mission-frozen")
        with pytest.raises(PydanticValidationError):
            state.mission_id = "changed"  # type: ignore[misc]

    def test_round_trip_via_model_dump_validate(self) -> None:
        original = self._make_populated_state()
        data = original.model_dump()
        restored = ReducedCollaborationState.model_validate(data)
        assert restored.mission_id == original.mission_id
        assert restored.event_count == original.event_count
        assert restored.last_processed_event_id == original.last_processed_event_id
        assert len(restored.participants) == len(original.participants)
        assert len(restored.warnings) == len(original.warnings)
        assert len(restored.decisions) == len(original.decisions)
        assert len(restored.comments) == len(original.comments)
        assert len(restored.anomalies) == len(original.anomalies)
        assert restored.active_executions == original.active_executions
        assert restored.linked_sessions == original.linked_sessions

    def test_participants_by_focus_with_string_keys(self) -> None:
        state = ReducedCollaborationState(
            mission_id="mission-focus",
            participants_by_focus={
                "wp:WP03": frozenset({"p-001"}),
                "step:step-5": frozenset({"p-002", "p-003"}),
                "file:src/main.py": frozenset({"p-004"}),
            },
        )
        assert state.participants_by_focus["wp:WP03"] == frozenset({"p-001"})
        assert state.participants_by_focus["step:step-5"] == frozenset(
            {"p-002", "p-003"}
        )
        assert state.participants_by_focus["file:src/main.py"] == frozenset(
            {"p-004"}
        )

    def test_active_drivers_is_frozenset(self) -> None:
        state = ReducedCollaborationState(
            mission_id="mission-drivers",
            active_drivers=frozenset({"p-001", "p-002"}),
        )
        assert isinstance(state.active_drivers, frozenset)
        assert len(state.active_drivers) == 2

    def test_warnings_tuple_ordering_preserved(self) -> None:
        w1 = WarningEntry(
            warning_id="warn-A",
            event_id="evt-200",
            warning_type="ConcurrentDriverWarning",
            participant_ids=("p-001",),
        )
        w2 = WarningEntry(
            warning_id="warn-B",
            event_id="evt-201",
            warning_type="PotentialStepCollisionDetected",
            participant_ids=("p-002",),
        )
        state = ReducedCollaborationState(
            mission_id="mission-ordered",
            warnings=(w1, w2),
        )
        assert state.warnings[0].warning_id == "warn-A"
        assert state.warnings[1].warning_id == "warn-B"

    def test_model_dump_produces_dict(self) -> None:
        state = ReducedCollaborationState(mission_id="mission-dump")
        dumped = state.model_dump()
        assert isinstance(dumped, dict)
        assert dumped["mission_id"] == "mission-dump"
        assert dumped["event_count"] == 0
        assert dumped["participants"] == {}

    def test_mission_id_is_required(self) -> None:
        with pytest.raises(PydanticValidationError):
            ReducedCollaborationState()  # type: ignore[call-arg]
