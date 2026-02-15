"""Unit tests for the collaboration reducer (WP06)."""

import uuid
from datetime import datetime, timezone

import pytest
from ulid import ULID

from spec_kitty_events.collaboration import (
    COLLABORATION_EVENT_TYPES,
    COMMENT_POSTED,
    CONCURRENT_DRIVER_WARNING,
    DECISION_CAPTURED,
    DRIVE_INTENT_SET,
    FOCUS_CHANGED,
    PARTICIPANT_INVITED,
    PARTICIPANT_JOINED,
    PARTICIPANT_LEFT,
    POTENTIAL_STEP_COLLISION_DETECTED,
    PRESENCE_HEARTBEAT,
    PROMPT_STEP_EXECUTION_COMPLETED,
    PROMPT_STEP_EXECUTION_STARTED,
    SESSION_LINKED,
    WARNING_ACKNOWLEDGED,
    CollaborationAnomaly,
    CommentEntry,
    DecisionEntry,
    FocusTarget,
    ParticipantIdentity,
    ReducedCollaborationState,
    UnknownParticipantError,
    WarningEntry,
    reduce_collaboration_events,
)
from spec_kitty_events.models import Event, SpecKittyEventsError

_PROJECT_UUID = uuid.UUID("12345678-1234-5678-1234-567812345678")
_CORRELATION_ID = str(ULID())


def _make_event(
    event_type: str,
    payload: dict,  # type: ignore[type-arg]
    clock: int = 0,
    event_id: str | None = None,
    timestamp: datetime | None = None,
) -> Event:
    """Helper to build a collaboration event with sensible defaults."""
    return Event(
        event_id=event_id or str(ULID()),
        event_type=event_type,
        aggregate_id="mission/M001",
        payload=payload,
        timestamp=timestamp or datetime.now(timezone.utc),
        node_id="node-1",
        lamport_clock=clock,
        project_uuid=_PROJECT_UUID,
        correlation_id=_CORRELATION_ID,
    )


def _identity(pid: str, ptype: str = "human") -> dict:  # type: ignore[type-arg]
    """Build a participant_identity dict for payloads."""
    return {
        "participant_id": pid,
        "participant_type": ptype,
        "display_name": f"Agent {pid}",
    }


def _join_event(pid: str, clock: int = 0) -> Event:
    """Shortcut: create a ParticipantJoined event."""
    return _make_event(
        PARTICIPANT_JOINED,
        {
            "participant_id": pid,
            "participant_identity": _identity(pid),
            "mission_id": "M001",
        },
        clock=clock,
    )


def _leave_event(pid: str, clock: int = 10) -> Event:
    """Shortcut: create a ParticipantLeft event."""
    return _make_event(
        PARTICIPANT_LEFT,
        {"participant_id": pid, "mission_id": "M001"},
        clock=clock,
    )


# ── Empty / filtering tests ─────────────────────────────────────────────────


class TestEmptyAndFiltering:
    """Edge cases: empty input, non-collaboration events filtered."""

    def test_empty_input_returns_minimal_state(self) -> None:
        result = reduce_collaboration_events([])
        assert result.mission_id == ""
        assert result.event_count == 0
        assert result.participants == {}
        assert result.last_processed_event_id is None

    def test_non_collaboration_events_filtered(self) -> None:
        """Events that aren't collaboration types should be ignored."""
        evt = _make_event("WPStatusChanged", {"mission_id": "M001"}, clock=1)
        result = reduce_collaboration_events([evt])
        assert result.mission_id == ""
        assert result.event_count == 0

    def test_mission_id_extracted_from_first_event(self) -> None:
        evt = _join_event("p1", clock=1)
        result = reduce_collaboration_events([evt])
        assert result.mission_id == "M001"


# ── Participant lifecycle ────────────────────────────────────────────────────


class TestParticipantLifecycle:
    """Join, leave, re-join, invited."""

    def test_join_adds_to_roster(self) -> None:
        result = reduce_collaboration_events([_join_event("p1")])
        assert "p1" in result.participants
        assert result.participants["p1"].participant_type == "human"

    def test_leave_moves_to_departed(self) -> None:
        events = [_join_event("p1", clock=0), _leave_event("p1", clock=1)]
        result = reduce_collaboration_events(events)
        assert "p1" not in result.participants
        assert "p1" in result.departed_participants

    def test_rejoin_after_leave(self) -> None:
        events = [
            _join_event("p1", clock=0),
            _leave_event("p1", clock=1),
            _join_event("p1", clock=2),
        ]
        result = reduce_collaboration_events(events)
        assert "p1" in result.participants
        assert "p1" not in result.departed_participants

    def test_duplicate_join_anomaly(self) -> None:
        events = [_join_event("p1", clock=0), _join_event("p1", clock=1)]
        result = reduce_collaboration_events(events, mode="permissive")
        assert len(result.anomalies) == 1
        assert "Duplicate join" in result.anomalies[0].reason

    def test_duplicate_leave_anomaly_strict(self) -> None:
        events = [
            _join_event("p1", clock=0),
            _leave_event("p1", clock=1),
            _leave_event("p1", clock=2),
        ]
        result = reduce_collaboration_events(events)
        assert len(result.anomalies) == 1
        assert "not in roster" in result.anomalies[0].reason

    def test_duplicate_leave_anomaly_permissive(self) -> None:
        events = [
            _join_event("p1", clock=0),
            _leave_event("p1", clock=1),
            _leave_event("p1", clock=2),
        ]
        result = reduce_collaboration_events(events, mode="permissive")
        assert len(result.anomalies) == 1
        assert "not in roster" in result.anomalies[0].reason

    def test_invited_does_not_activate_roster(self) -> None:
        evt = _make_event(
            PARTICIPANT_INVITED,
            {
                "participant_id": "p1",
                "participant_identity": _identity("p1"),
                "invited_by": "admin",
                "mission_id": "M001",
            },
        )
        result = reduce_collaboration_events([evt])
        assert "p1" not in result.participants
        assert len(result.anomalies) == 0

    def test_invited_then_join_has_no_duplicate_join_anomaly(self) -> None:
        events = [
            _make_event(
                PARTICIPANT_INVITED,
                {
                    "participant_id": "p1",
                    "participant_identity": _identity("p1"),
                    "invited_by": "admin",
                    "mission_id": "M001",
                },
                clock=0,
            ),
            _join_event("p1", clock=1),
        ]
        result = reduce_collaboration_events(events, mode="strict")
        assert "p1" in result.participants
        assert len(result.anomalies) == 0


# ── Strict mode ──────────────────────────────────────────────────────────────


class TestStrictMode:
    """Strict mode raises UnknownParticipantError for unknown participants."""

    def test_unknown_participant_raises(self) -> None:
        evt = _make_event(
            PRESENCE_HEARTBEAT,
            {"participant_id": "unknown", "mission_id": "M001"},
            clock=1,
        )
        with pytest.raises(UnknownParticipantError) as exc_info:
            reduce_collaboration_events([evt], mode="strict")
        assert exc_info.value.participant_id == "unknown"

    def test_seeded_roster_no_join_needed(self) -> None:
        """With seeded roster, events work without prior join events."""
        roster = {
            "p1": ParticipantIdentity(
                participant_id="p1",
                participant_type="human",
                display_name="Agent p1",
            )
        }
        evt = _make_event(
            PRESENCE_HEARTBEAT,
            {"participant_id": "p1", "mission_id": "M001"},
            clock=1,
        )
        result = reduce_collaboration_events([evt], roster=roster)
        assert "p1" in result.participants
        assert "p1" in result.presence

    def test_invited_only_is_not_active_roster_in_strict_mode(self) -> None:
        events = [
            _make_event(
                PARTICIPANT_INVITED,
                {
                    "participant_id": "p1",
                    "participant_identity": _identity("p1"),
                    "invited_by": "admin",
                    "mission_id": "M001",
                },
                clock=0,
            ),
            _make_event(
                PRESENCE_HEARTBEAT,
                {"participant_id": "p1", "mission_id": "M001"},
                clock=1,
            ),
        ]
        with pytest.raises(UnknownParticipantError):
            reduce_collaboration_events(events, mode="strict")


# ── Permissive mode ──────────────────────────────────────────────────────────


class TestPermissiveMode:
    """Permissive mode records anomalies instead of raising."""

    def test_unknown_participant_anomaly(self) -> None:
        evt = _make_event(
            PRESENCE_HEARTBEAT,
            {"participant_id": "unknown", "mission_id": "M001"},
            clock=1,
        )
        result = reduce_collaboration_events([evt], mode="permissive")
        assert len(result.anomalies) == 1
        assert "Unknown participant" in result.anomalies[0].reason

    def test_duplicate_join_anomaly(self) -> None:
        events = [_join_event("p1", clock=0), _join_event("p1", clock=1)]
        result = reduce_collaboration_events(events, mode="permissive")
        assert len(result.anomalies) == 1
        assert "Duplicate join" in result.anomalies[0].reason

    def test_departed_heartbeat_records_anomaly_and_keeps_timestamp(self) -> None:
        events = [
            _join_event("p1", clock=0),
            _leave_event("p1", clock=1),
            _make_event(
                PRESENCE_HEARTBEAT,
                {"participant_id": "p1", "mission_id": "M001"},
                clock=2,
            ),
        ]
        result = reduce_collaboration_events(events, mode="permissive")
        assert len(result.anomalies) == 1
        assert "has departed" in result.anomalies[0].reason
        assert "p1" in result.presence


# ── Drive intent ─────────────────────────────────────────────────────────────


class TestDriveIntent:
    """DriveIntentSet events."""

    def test_active_intent_adds_driver(self) -> None:
        events = [
            _join_event("p1", clock=0),
            _make_event(
                DRIVE_INTENT_SET,
                {"participant_id": "p1", "mission_id": "M001", "intent": "active"},
                clock=1,
            ),
        ]
        result = reduce_collaboration_events(events)
        assert "p1" in result.active_drivers

    def test_inactive_intent_removes_driver(self) -> None:
        events = [
            _join_event("p1", clock=0),
            _make_event(
                DRIVE_INTENT_SET,
                {"participant_id": "p1", "mission_id": "M001", "intent": "active"},
                clock=1,
            ),
            _make_event(
                DRIVE_INTENT_SET,
                {"participant_id": "p1", "mission_id": "M001", "intent": "inactive"},
                clock=2,
            ),
        ]
        result = reduce_collaboration_events(events)
        assert "p1" not in result.active_drivers

    def test_departed_participant_drive_intent_strict_raises(self) -> None:
        events = [
            _join_event("p1", clock=0),
            _leave_event("p1", clock=1),
            _make_event(
                DRIVE_INTENT_SET,
                {"participant_id": "p1", "mission_id": "M001", "intent": "active"},
                clock=2,
            ),
        ]
        # Departed participants are hard errors in strict mode.
        with pytest.raises(SpecKittyEventsError):
            reduce_collaboration_events(events, mode="strict")


# ── Focus ────────────────────────────────────────────────────────────────────


class TestFocusChanged:
    """FocusChanged events and reverse index."""

    def test_focus_set(self) -> None:
        events = [
            _join_event("p1", clock=0),
            _make_event(
                FOCUS_CHANGED,
                {
                    "participant_id": "p1",
                    "mission_id": "M001",
                    "focus_target": {"target_type": "wp", "target_id": "WP03"},
                },
                clock=1,
            ),
        ]
        result = reduce_collaboration_events(events)
        assert result.focus_by_participant["p1"].target_id == "WP03"
        assert "p1" in result.participants_by_focus["wp:WP03"]

    def test_focus_change_updates_reverse_index(self) -> None:
        events = [
            _join_event("p1", clock=0),
            _make_event(
                FOCUS_CHANGED,
                {
                    "participant_id": "p1",
                    "mission_id": "M001",
                    "focus_target": {"target_type": "wp", "target_id": "WP01"},
                },
                clock=1,
            ),
            _make_event(
                FOCUS_CHANGED,
                {
                    "participant_id": "p1",
                    "mission_id": "M001",
                    "focus_target": {"target_type": "wp", "target_id": "WP02"},
                },
                clock=2,
            ),
        ]
        result = reduce_collaboration_events(events)
        assert result.focus_by_participant["p1"].target_id == "WP02"
        # WP01 should be removed from reverse index (empty set removed)
        assert "wp:WP01" not in result.participants_by_focus
        assert "p1" in result.participants_by_focus["wp:WP02"]


# ── Warnings and acknowledgements ────────────────────────────────────────────


class TestWarnings:
    """Warning creation and acknowledgement."""

    def test_concurrent_driver_warning(self) -> None:
        events = [
            _join_event("p1", clock=0),
            _join_event("p2", clock=0),
            _make_event(
                CONCURRENT_DRIVER_WARNING,
                {
                    "warning_id": "w1",
                    "mission_id": "M001",
                    "participant_ids": ["p1", "p2"],
                    "focus_target": {"target_type": "wp", "target_id": "WP03"},
                    "severity": "warning",
                },
                clock=1,
            ),
        ]
        result = reduce_collaboration_events(events)
        assert len(result.warnings) == 1
        assert result.warnings[0].warning_id == "w1"
        assert result.warnings[0].warning_type == CONCURRENT_DRIVER_WARNING
        assert result.warnings[0].participant_ids == ("p1", "p2")

    def test_step_collision_warning(self) -> None:
        events = [
            _join_event("p1", clock=0),
            _join_event("p2", clock=0),
            _make_event(
                POTENTIAL_STEP_COLLISION_DETECTED,
                {
                    "warning_id": "w2",
                    "mission_id": "M001",
                    "participant_ids": ["p1", "p2"],
                    "step_id": "step1",
                    "severity": "info",
                },
                clock=1,
            ),
        ]
        result = reduce_collaboration_events(events)
        assert len(result.warnings) == 1
        assert result.warnings[0].warning_type == POTENTIAL_STEP_COLLISION_DETECTED

    def test_warning_acknowledged(self) -> None:
        events = [
            _join_event("p1", clock=0),
            _join_event("p2", clock=0),
            _make_event(
                CONCURRENT_DRIVER_WARNING,
                {
                    "warning_id": "w1",
                    "mission_id": "M001",
                    "participant_ids": ["p1", "p2"],
                    "focus_target": {"target_type": "wp", "target_id": "WP03"},
                    "severity": "warning",
                },
                clock=1,
            ),
            _make_event(
                WARNING_ACKNOWLEDGED,
                {
                    "participant_id": "p1",
                    "mission_id": "M001",
                    "warning_id": "w1",
                    "acknowledgement": "continue",
                },
                clock=2,
            ),
        ]
        result = reduce_collaboration_events(events)
        assert result.warnings[0].acknowledgements == {"p1": "continue"}

    def test_ack_nonexistent_warning_strict_raises(self) -> None:
        events = [
            _join_event("p1", clock=0),
            _make_event(
                WARNING_ACKNOWLEDGED,
                {
                    "participant_id": "p1",
                    "mission_id": "M001",
                    "warning_id": "nonexistent",
                    "acknowledgement": "continue",
                },
                clock=1,
            ),
        ]
        with pytest.raises(SpecKittyEventsError):
            reduce_collaboration_events(events, mode="strict")

    def test_ack_nonexistent_warning_permissive_anomaly(self) -> None:
        events = [
            _join_event("p1", clock=0),
            _make_event(
                WARNING_ACKNOWLEDGED,
                {
                    "participant_id": "p1",
                    "mission_id": "M001",
                    "warning_id": "nonexistent",
                    "acknowledgement": "continue",
                },
                clock=1,
            ),
        ]
        result = reduce_collaboration_events(events, mode="permissive")
        assert len(result.anomalies) == 1
        assert "not found" in result.anomalies[0].reason


# ── Execution tracking ───────────────────────────────────────────────────────


class TestExecutionTracking:
    """PromptStepExecution start/complete pairing."""

    def test_execution_start(self) -> None:
        events = [
            _join_event("p1", clock=0),
            _make_event(
                PROMPT_STEP_EXECUTION_STARTED,
                {
                    "participant_id": "p1",
                    "mission_id": "M001",
                    "step_id": "step1",
                },
                clock=1,
            ),
        ]
        result = reduce_collaboration_events(events)
        assert "p1" in result.active_executions
        assert "step1" in result.active_executions["p1"]

    def test_execution_complete_removes_step(self) -> None:
        events = [
            _join_event("p1", clock=0),
            _make_event(
                PROMPT_STEP_EXECUTION_STARTED,
                {
                    "participant_id": "p1",
                    "mission_id": "M001",
                    "step_id": "step1",
                },
                clock=1,
            ),
            _make_event(
                PROMPT_STEP_EXECUTION_COMPLETED,
                {
                    "participant_id": "p1",
                    "mission_id": "M001",
                    "step_id": "step1",
                    "outcome": "success",
                },
                clock=2,
            ),
        ]
        result = reduce_collaboration_events(events)
        assert result.active_executions.get("p1", []) == []

    def test_complete_without_start_strict_raises(self) -> None:
        events = [
            _join_event("p1", clock=0),
            _make_event(
                PROMPT_STEP_EXECUTION_COMPLETED,
                {
                    "participant_id": "p1",
                    "mission_id": "M001",
                    "step_id": "step1",
                    "outcome": "success",
                },
                clock=1,
            ),
        ]
        with pytest.raises(SpecKittyEventsError):
            reduce_collaboration_events(events, mode="strict")

    def test_complete_without_start_permissive_anomaly(self) -> None:
        events = [
            _join_event("p1", clock=0),
            _make_event(
                PROMPT_STEP_EXECUTION_COMPLETED,
                {
                    "participant_id": "p1",
                    "mission_id": "M001",
                    "step_id": "step1",
                    "outcome": "success",
                },
                clock=1,
            ),
        ]
        result = reduce_collaboration_events(events, mode="permissive")
        assert len(result.anomalies) == 1
        assert "No matching PromptStepExecutionStarted" in result.anomalies[0].reason


# ── Comments and decisions ───────────────────────────────────────────────────


class TestCommentsAndDecisions:
    """CommentPosted and DecisionCaptured events."""

    def test_comment_posted(self) -> None:
        events = [
            _join_event("p1", clock=0),
            _make_event(
                COMMENT_POSTED,
                {
                    "participant_id": "p1",
                    "mission_id": "M001",
                    "comment_id": "c1",
                    "content": "Hello world",
                },
                clock=1,
            ),
        ]
        result = reduce_collaboration_events(events)
        assert len(result.comments) == 1
        assert result.comments[0].comment_id == "c1"
        assert result.comments[0].content == "Hello world"

    def test_decision_captured(self) -> None:
        events = [
            _join_event("p1", clock=0),
            _make_event(
                DECISION_CAPTURED,
                {
                    "participant_id": "p1",
                    "mission_id": "M001",
                    "decision_id": "d1",
                    "topic": "Architecture",
                    "chosen_option": "Microservices",
                },
                clock=1,
            ),
        ]
        result = reduce_collaboration_events(events)
        assert len(result.decisions) == 1
        assert result.decisions[0].decision_id == "d1"
        assert result.decisions[0].chosen_option == "Microservices"

    def test_comment_with_reply_to(self) -> None:
        events = [
            _join_event("p1", clock=0),
            _make_event(
                COMMENT_POSTED,
                {
                    "participant_id": "p1",
                    "mission_id": "M001",
                    "comment_id": "c1",
                    "content": "First",
                },
                clock=1,
            ),
            _make_event(
                COMMENT_POSTED,
                {
                    "participant_id": "p1",
                    "mission_id": "M001",
                    "comment_id": "c2",
                    "content": "Reply",
                    "reply_to": "c1",
                },
                clock=2,
            ),
        ]
        result = reduce_collaboration_events(events)
        assert len(result.comments) == 2
        assert result.comments[1].reply_to == "c1"


# ── Session linking ──────────────────────────────────────────────────────────


class TestSessionLinking:
    """SessionLinked events."""

    def test_session_linked(self) -> None:
        events = [
            _join_event("p1", clock=0),
            _make_event(
                SESSION_LINKED,
                {
                    "participant_id": "p1",
                    "mission_id": "M001",
                    "primary_session_id": "s1",
                    "linked_session_id": "s2",
                    "link_type": "cli_to_saas",
                },
                clock=1,
            ),
        ]
        result = reduce_collaboration_events(events)
        assert "p1" in result.linked_sessions
        assert "s2" in result.linked_sessions["p1"]


# ── Full lifecycle integration ───────────────────────────────────────────────


class TestFullLifecycle:
    """End-to-end: join -> drive intent -> focus -> warning -> ack -> verify."""

    def test_strict_mode_full_history(self) -> None:
        events = [
            _join_event("p1", clock=0),
            _join_event("p2", clock=0),
            _make_event(
                DRIVE_INTENT_SET,
                {"participant_id": "p1", "mission_id": "M001", "intent": "active"},
                clock=1,
            ),
            _make_event(
                DRIVE_INTENT_SET,
                {"participant_id": "p2", "mission_id": "M001", "intent": "active"},
                clock=1,
            ),
            _make_event(
                FOCUS_CHANGED,
                {
                    "participant_id": "p1",
                    "mission_id": "M001",
                    "focus_target": {"target_type": "wp", "target_id": "WP03"},
                },
                clock=2,
            ),
            _make_event(
                FOCUS_CHANGED,
                {
                    "participant_id": "p2",
                    "mission_id": "M001",
                    "focus_target": {"target_type": "wp", "target_id": "WP03"},
                },
                clock=2,
            ),
            _make_event(
                CONCURRENT_DRIVER_WARNING,
                {
                    "warning_id": "w1",
                    "mission_id": "M001",
                    "participant_ids": ["p1", "p2"],
                    "focus_target": {"target_type": "wp", "target_id": "WP03"},
                    "severity": "warning",
                },
                clock=3,
            ),
            _make_event(
                WARNING_ACKNOWLEDGED,
                {
                    "participant_id": "p1",
                    "mission_id": "M001",
                    "warning_id": "w1",
                    "acknowledgement": "continue",
                },
                clock=4,
            ),
            _make_event(
                WARNING_ACKNOWLEDGED,
                {
                    "participant_id": "p2",
                    "mission_id": "M001",
                    "warning_id": "w1",
                    "acknowledgement": "hold",
                },
                clock=4,
            ),
        ]
        result = reduce_collaboration_events(events, mode="strict")

        # Verify participants
        assert "p1" in result.participants
        assert "p2" in result.participants

        # Verify drivers
        assert result.active_drivers == frozenset({"p1", "p2"})

        # Verify focus
        assert result.focus_by_participant["p1"].target_id == "WP03"
        assert result.focus_by_participant["p2"].target_id == "WP03"
        assert result.participants_by_focus["wp:WP03"] == frozenset({"p1", "p2"})

        # Verify warnings
        assert len(result.warnings) == 1
        assert result.warnings[0].acknowledgements == {
            "p1": "continue",
            "p2": "hold",
        }

        # No anomalies
        assert len(result.anomalies) == 0

        # Counters
        assert result.event_count == 9
        assert result.mission_id == "M001"

    def test_leave_cleans_up_driver_and_focus(self) -> None:
        """When a participant leaves, their driver and focus state is cleared."""
        events = [
            _join_event("p1", clock=0),
            _make_event(
                DRIVE_INTENT_SET,
                {"participant_id": "p1", "mission_id": "M001", "intent": "active"},
                clock=1,
            ),
            _make_event(
                FOCUS_CHANGED,
                {
                    "participant_id": "p1",
                    "mission_id": "M001",
                    "focus_target": {"target_type": "wp", "target_id": "WP01"},
                },
                clock=2,
            ),
            _leave_event("p1", clock=3),
        ]
        result = reduce_collaboration_events(events)
        assert "p1" not in result.active_drivers
        assert "p1" not in result.focus_by_participant
        assert "wp:WP01" not in result.participants_by_focus

    def test_event_count_and_last_processed(self) -> None:
        eid = str(ULID())
        events = [
            _join_event("p1", clock=0),
            _make_event(
                PRESENCE_HEARTBEAT,
                {"participant_id": "p1", "mission_id": "M001"},
                clock=1,
                event_id=eid,
            ),
        ]
        result = reduce_collaboration_events(events)
        assert result.event_count == 2
        # Last processed should be the heartbeat (higher clock)
        assert result.last_processed_event_id == eid

    def test_deduplication(self) -> None:
        """Duplicate event_ids should be deduplicated."""
        eid = str(ULID())
        events = [
            _join_event("p1", clock=0),
            _make_event(
                PRESENCE_HEARTBEAT,
                {"participant_id": "p1", "mission_id": "M001"},
                clock=1,
                event_id=eid,
            ),
            _make_event(
                PRESENCE_HEARTBEAT,
                {"participant_id": "p1", "mission_id": "M001"},
                clock=1,
                event_id=eid,
            ),
        ]
        result = reduce_collaboration_events(events)
        # Only 2 unique events (join + 1 heartbeat after dedup)
        assert result.event_count == 2


# ── All 14 event types ──────────────────────────────────────────────────────


class TestAll14EventTypes:
    """Ensure all 14 collaboration event types produce correct mutations."""

    def test_all_event_types_covered(self) -> None:
        """Verify the 14 event types in COLLABORATION_EVENT_TYPES."""
        assert len(COLLABORATION_EVENT_TYPES) == 14

    def test_full_event_type_coverage(self) -> None:
        """Process one of each event type and verify no crashes."""
        events = [
            # 1. ParticipantInvited
            _make_event(
                PARTICIPANT_INVITED,
                {
                    "participant_id": "p0",
                    "participant_identity": _identity("p0"),
                    "invited_by": "admin",
                    "mission_id": "M001",
                },
                clock=0,
            ),
            # 2. ParticipantJoined
            _join_event("p1", clock=1),
            # (extra join so warning payload uses active participants only)
            _join_event("p2", clock=1),
            # 3. PresenceHeartbeat
            _make_event(
                PRESENCE_HEARTBEAT,
                {"participant_id": "p1", "mission_id": "M001"},
                clock=2,
            ),
            # 4. DriveIntentSet
            _make_event(
                DRIVE_INTENT_SET,
                {"participant_id": "p1", "mission_id": "M001", "intent": "active"},
                clock=3,
            ),
            # 5. FocusChanged
            _make_event(
                FOCUS_CHANGED,
                {
                    "participant_id": "p1",
                    "mission_id": "M001",
                    "focus_target": {"target_type": "wp", "target_id": "WP01"},
                },
                clock=4,
            ),
            # 6. PromptStepExecutionStarted
            _make_event(
                PROMPT_STEP_EXECUTION_STARTED,
                {"participant_id": "p1", "mission_id": "M001", "step_id": "s1"},
                clock=5,
            ),
            # 7. PromptStepExecutionCompleted
            _make_event(
                PROMPT_STEP_EXECUTION_COMPLETED,
                {
                    "participant_id": "p1",
                    "mission_id": "M001",
                    "step_id": "s1",
                    "outcome": "success",
                },
                clock=6,
            ),
            # 8. ConcurrentDriverWarning
            _make_event(
                CONCURRENT_DRIVER_WARNING,
                {
                    "warning_id": "w1",
                    "mission_id": "M001",
                    "participant_ids": ["p1", "p2"],
                    "focus_target": {"target_type": "wp", "target_id": "WP01"},
                    "severity": "warning",
                },
                clock=7,
            ),
            # 9. PotentialStepCollisionDetected
            _make_event(
                POTENTIAL_STEP_COLLISION_DETECTED,
                {
                    "warning_id": "w2",
                    "mission_id": "M001",
                    "participant_ids": ["p1", "p2"],
                    "step_id": "s1",
                    "severity": "info",
                },
                clock=8,
            ),
            # 10. WarningAcknowledged
            _make_event(
                WARNING_ACKNOWLEDGED,
                {
                    "participant_id": "p1",
                    "mission_id": "M001",
                    "warning_id": "w1",
                    "acknowledgement": "continue",
                },
                clock=9,
            ),
            # 11. CommentPosted
            _make_event(
                COMMENT_POSTED,
                {
                    "participant_id": "p1",
                    "mission_id": "M001",
                    "comment_id": "c1",
                    "content": "Test comment",
                },
                clock=10,
            ),
            # 12. DecisionCaptured
            _make_event(
                DECISION_CAPTURED,
                {
                    "participant_id": "p1",
                    "mission_id": "M001",
                    "decision_id": "d1",
                    "topic": "Design",
                    "chosen_option": "Option A",
                },
                clock=11,
            ),
            # 13. SessionLinked
            _make_event(
                SESSION_LINKED,
                {
                    "participant_id": "p1",
                    "mission_id": "M001",
                    "primary_session_id": "sess1",
                    "linked_session_id": "sess2",
                    "link_type": "cli_to_saas",
                },
                clock=12,
            ),
            # 14. ParticipantLeft
            _leave_event("p2", clock=13),
        ]
        result = reduce_collaboration_events(events, mode="strict")
        assert result.event_count == 15
        assert len(result.anomalies) == 0
        assert "p1" in result.participants
        assert "p2" in result.departed_participants
        assert len(result.warnings) == 2
        assert len(result.comments) == 1
        assert len(result.decisions) == 1
        assert "p1" in result.linked_sessions
