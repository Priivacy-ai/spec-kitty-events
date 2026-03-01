"""Reducer unit tests for DecisionPoint lifecycle (FR-003).

Covers: empty stream, happy-path transitions (open -> discussing -> resolved),
open -> resolved shortcut, resolved -> overridden, deduplication, deterministic
ordering, authority-policy violations, LLM-policy violations, malformed payloads,
event-after-terminal anomaly, invalid transitions, and golden-file replay.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest
from ulid import ULID

from spec_kitty_events.decisionpoint import (
    DECISION_POINT_DISCUSSING,
    DECISION_POINT_OPENED,
    DECISION_POINT_OVERRIDDEN,
    DECISION_POINT_RESOLVED,
    DecisionAuthorityRole,
    DecisionPointDiscussingPayload,
    DecisionPointOpenedPayload,
    DecisionPointOverriddenPayload,
    DecisionPointResolvedPayload,
    DecisionPointState,
    reduce_decision_point_events,
)
from spec_kitty_events.models import Event

# ── Constants ──────────────────────────────────────────────────────────────────

_PROJECT_UUID = uuid.UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")
_NOW = datetime(2026, 2, 27, 12, 0, 0, tzinfo=timezone.utc)
_GOLDEN_DIR = Path(__file__).parent / "fixtures" / "decisionpoint_golden"


# ── Payload helpers ────────────────────────────────────────────────────────────

def _base_payload(
    *,
    actor_type: str = "human",
    authority_role: str = "mission_owner",
    mission_owner_authority_flag: bool = True,
    phase: str = "P1",
    lamport_offset: int = 0,
) -> dict[str, Any]:
    """Return a valid payload dict for any DecisionPoint event type."""
    return {
        "decision_point_id": "dp-001",
        "mission_id": "m-001",
        "run_id": "run-001",
        "feature_slug": "feature-x",
        "phase": phase,
        "actor_id": "human-1",
        "actor_type": actor_type,
        "authority_role": authority_role,
        "mission_owner_authority_flag": mission_owner_authority_flag,
        "mission_owner_authority_path": "/missions/m-001/owner",
        "rationale": "Best option after analysis",
        "alternatives_considered": ("Option A", "Option B"),
        "evidence_refs": ("ref-001",),
        "state_entered_at": datetime(2026, 2, 27, 12, 0, lamport_offset, tzinfo=timezone.utc).isoformat(),
        "recorded_at": datetime(2026, 2, 27, 12, 0, lamport_offset, tzinfo=timezone.utc).isoformat(),
    }


def _event(
    event_type: str,
    payload_dict: dict[str, Any],
    *,
    lamport: int = 1,
    event_id: str | None = None,
) -> Event:
    """Factory for constructing test Event instances."""
    return Event(
        event_id=event_id or str(ULID()),
        event_type=event_type,
        aggregate_id="dp/dp-001",
        payload=payload_dict,
        timestamp=datetime(2026, 2, 27, 12, 0, lamport, tzinfo=timezone.utc),
        node_id="node-1",
        lamport_clock=lamport,
        project_uuid=_PROJECT_UUID,
        correlation_id=str(ULID()),
    )


# ── Named event factories ─────────────────────────────────────────────────────

def _opened_event(
    lamport: int = 1,
    *,
    actor_type: str = "human",
    authority_role: str = "mission_owner",
    mission_owner_authority_flag: bool = True,
    phase: str = "P1",
) -> Event:
    return _event(
        DECISION_POINT_OPENED,
        _base_payload(
            actor_type=actor_type,
            authority_role=authority_role,
            mission_owner_authority_flag=mission_owner_authority_flag,
            phase=phase,
            lamport_offset=lamport,
        ),
        lamport=lamport,
    )


def _discussing_event(
    lamport: int = 2,
    *,
    actor_type: str = "human",
    authority_role: str = "mission_owner",
    mission_owner_authority_flag: bool = True,
    phase: str = "P1",
) -> Event:
    return _event(
        DECISION_POINT_DISCUSSING,
        _base_payload(
            actor_type=actor_type,
            authority_role=authority_role,
            mission_owner_authority_flag=mission_owner_authority_flag,
            phase=phase,
            lamport_offset=lamport,
        ),
        lamport=lamport,
    )


def _resolved_event(
    lamport: int = 3,
    *,
    actor_type: str = "human",
    authority_role: str = "mission_owner",
    mission_owner_authority_flag: bool = True,
    phase: str = "P1",
) -> Event:
    return _event(
        DECISION_POINT_RESOLVED,
        _base_payload(
            actor_type=actor_type,
            authority_role=authority_role,
            mission_owner_authority_flag=mission_owner_authority_flag,
            phase=phase,
            lamport_offset=lamport,
        ),
        lamport=lamport,
    )


def _overridden_event(
    lamport: int = 4,
    *,
    actor_type: str = "human",
    authority_role: str = "mission_owner",
    mission_owner_authority_flag: bool = True,
    phase: str = "P1",
) -> Event:
    return _event(
        DECISION_POINT_OVERRIDDEN,
        _base_payload(
            actor_type=actor_type,
            authority_role=authority_role,
            mission_owner_authority_flag=mission_owner_authority_flag,
            phase=phase,
            lamport_offset=lamport,
        ),
        lamport=lamport,
    )


# ── Tests: Empty and basic transitions ─────────────────────────────────────────

def test_empty_stream() -> None:
    result = reduce_decision_point_events([])
    assert result.state is None
    assert result.event_count == 0
    assert result.anomalies == ()
    assert result.decision_point_id is None
    assert result.mission_id is None


def test_happy_path_open_discussing_resolved() -> None:
    events = [_opened_event(1), _discussing_event(2), _resolved_event(3)]
    result = reduce_decision_point_events(events)
    assert result.state == DecisionPointState.RESOLVED
    assert result.decision_point_id == "dp-001"
    assert result.mission_id == "m-001"
    assert result.anomalies == ()
    assert result.event_count == 3


def test_happy_path_open_resolved_shortcut() -> None:
    """open -> resolved is a valid direct transition."""
    events = [_opened_event(1), _resolved_event(2)]
    result = reduce_decision_point_events(events)
    assert result.state == DecisionPointState.RESOLVED
    assert result.anomalies == ()
    assert result.event_count == 2


def test_happy_path_full_lifecycle() -> None:
    """open -> discussing -> resolved -> overridden."""
    events = [
        _opened_event(1),
        _discussing_event(2),
        _resolved_event(3),
        _overridden_event(4),
    ]
    result = reduce_decision_point_events(events)
    assert result.state == DecisionPointState.OVERRIDDEN
    assert result.anomalies == ()
    assert result.event_count == 4


def test_discussing_to_discussing() -> None:
    """discussing -> discussing is allowed (re-enter discussion)."""
    events = [_opened_event(1), _discussing_event(2), _discussing_event(3)]
    result = reduce_decision_point_events(events)
    assert result.state == DecisionPointState.DISCUSSING
    assert result.anomalies == ()
    assert result.event_count == 3


def test_only_opened_stays_open() -> None:
    events = [_opened_event(1)]
    result = reduce_decision_point_events(events)
    assert result.state == DecisionPointState.OPEN
    assert result.anomalies == ()
    assert result.event_count == 1


# ── Tests: Reducer output fields ──────────────────────────────────────────────

def test_reducer_captures_last_actor_fields() -> None:
    events = [_opened_event(1), _discussing_event(2)]
    result = reduce_decision_point_events(events)
    assert result.last_actor_id == "human-1"
    assert result.last_actor_type == "human"
    assert result.last_authority_role == DecisionAuthorityRole.MISSION_OWNER
    assert result.last_rationale == "Best option after analysis"
    assert result.last_alternatives_considered == ("Option A", "Option B")
    assert result.last_evidence_refs == ("ref-001",)
    assert result.last_state_entered_at is not None


def test_reducer_output_is_frozen() -> None:
    result = reduce_decision_point_events([_opened_event(1)])
    with pytest.raises(Exception):
        result.state = DecisionPointState.RESOLVED  # type: ignore[misc]


# ── Tests: Deduplication ───────────────────────────────────────────────────────

def test_deduplication() -> None:
    e1 = _opened_event(1)
    e2 = _discussing_event(2)
    e3 = _resolved_event(3)
    original = [e1, e2, e3]
    doubled = [e1, e2, e3, e1, e2, e3]
    result_original = reduce_decision_point_events(original)
    result_doubled = reduce_decision_point_events(doubled)
    assert result_original == result_doubled
    assert result_original.event_count == 3
    assert result_doubled.event_count == 3


# ── Tests: Deterministic ordering ─────────────────────────────────────────────

def test_deterministic_with_reversed_input() -> None:
    """Reducer must sort by (lamport_clock, timestamp, event_id) for determinism."""
    e1 = _opened_event(1)
    e2 = _discussing_event(2)
    forward = reduce_decision_point_events([e1, e2])
    reverse = reduce_decision_point_events([e2, e1])
    assert forward == reverse


# ── Tests: Authority policy (FR-003) ───────────────────────────────────────────

def test_authority_policy_resolved_requires_human_mission_owner() -> None:
    """resolved requires actor_type=human, authority_role=mission_owner, flag=True."""
    events = [
        _opened_event(1),
        _resolved_event(2, actor_type="llm", authority_role="advisory", mission_owner_authority_flag=False),
    ]
    result = reduce_decision_point_events(events)
    assert result.state == DecisionPointState.OPEN  # didn't transition
    assert len(result.anomalies) == 1
    assert result.anomalies[0].kind == "authority_policy_violation"


def test_authority_policy_overridden_requires_human_mission_owner() -> None:
    """overridden requires actor_type=human, authority_role=mission_owner, flag=True."""
    events = [
        _opened_event(1),
        _resolved_event(2),
        _overridden_event(
            3,
            actor_type="service",
            authority_role="advisory",
            mission_owner_authority_flag=False,
        ),
    ]
    result = reduce_decision_point_events(events)
    assert result.state == DecisionPointState.RESOLVED  # didn't transition
    assert len(result.anomalies) == 1
    assert result.anomalies[0].kind == "authority_policy_violation"


def test_authority_policy_human_but_wrong_role() -> None:
    """Human actor with advisory role cannot resolve."""
    events = [
        _opened_event(1),
        _resolved_event(2, authority_role="advisory", mission_owner_authority_flag=False),
    ]
    result = reduce_decision_point_events(events)
    assert result.state == DecisionPointState.OPEN
    assert len(result.anomalies) == 1
    assert result.anomalies[0].kind == "authority_policy_violation"


def test_authority_policy_human_mission_owner_but_flag_false() -> None:
    """Human mission_owner with flag=False cannot resolve."""
    events = [
        _opened_event(1),
        _resolved_event(2, mission_owner_authority_flag=False),
    ]
    result = reduce_decision_point_events(events)
    assert result.state == DecisionPointState.OPEN
    assert len(result.anomalies) == 1
    assert result.anomalies[0].kind == "authority_policy_violation"


# ── Tests: LLM policy (FR-003) ────────────────────────────────────────────────

def test_llm_allowed_in_p0_with_advisory_role() -> None:
    """LLM actors allowed in phase=P0 with advisory role and no authority flag."""
    events = [
        _opened_event(
            1,
            actor_type="llm",
            authority_role="advisory",
            mission_owner_authority_flag=False,
            phase="P0",
        ),
    ]
    result = reduce_decision_point_events(events)
    assert result.state == DecisionPointState.OPEN
    assert result.anomalies == ()


def test_llm_allowed_in_p0_with_informed_role() -> None:
    """LLM actors allowed in phase=P0 with informed role."""
    events = [
        _opened_event(
            1,
            actor_type="llm",
            authority_role="informed",
            mission_owner_authority_flag=False,
            phase="P0",
        ),
    ]
    result = reduce_decision_point_events(events)
    assert result.state == DecisionPointState.OPEN
    assert result.anomalies == ()


def test_llm_rejected_outside_p0() -> None:
    """LLM actors rejected when phase != P0."""
    events = [
        _opened_event(
            1,
            actor_type="llm",
            authority_role="advisory",
            mission_owner_authority_flag=False,
            phase="P1",
        ),
    ]
    result = reduce_decision_point_events(events)
    assert result.state is None  # didn't transition
    assert len(result.anomalies) == 1
    assert result.anomalies[0].kind == "llm_policy_violation"
    assert "phase" in result.anomalies[0].message


def test_llm_rejected_with_mission_owner_role() -> None:
    """LLM actors cannot have mission_owner authority role."""
    events = [
        _opened_event(
            1,
            actor_type="llm",
            authority_role="mission_owner",
            mission_owner_authority_flag=False,
            phase="P0",
        ),
    ]
    result = reduce_decision_point_events(events)
    assert result.state is None
    assert len(result.anomalies) == 1
    assert result.anomalies[0].kind == "llm_policy_violation"
    assert "advisory or informed" in result.anomalies[0].message


def test_llm_rejected_with_authority_flag() -> None:
    """LLM actors must not carry mission-owner authority flag."""
    events = [
        _opened_event(
            1,
            actor_type="llm",
            authority_role="advisory",
            mission_owner_authority_flag=True,
            phase="P0",
        ),
    ]
    result = reduce_decision_point_events(events)
    assert result.state is None
    assert len(result.anomalies) == 1
    assert result.anomalies[0].kind == "llm_policy_violation"
    assert "mission-owner authority" in result.anomalies[0].message


# ── Tests: Invalid transitions ─────────────────────────────────────────────────

def test_invalid_transition_discussing_before_open() -> None:
    """Cannot go to discussing without first opening."""
    events = [_discussing_event(1)]
    result = reduce_decision_point_events(events)
    assert result.state is None
    assert len(result.anomalies) == 1
    assert result.anomalies[0].kind == "invalid_transition"


def test_invalid_transition_resolved_before_open() -> None:
    """Cannot go to resolved without first opening."""
    events = [_resolved_event(1)]
    result = reduce_decision_point_events(events)
    assert result.state is None
    assert len(result.anomalies) == 1
    assert result.anomalies[0].kind == "invalid_transition"


def test_invalid_transition_overridden_before_resolved() -> None:
    """Cannot go to overridden from open (need resolved first)."""
    events = [_opened_event(1), _overridden_event(2)]
    result = reduce_decision_point_events(events)
    assert result.state == DecisionPointState.OPEN
    assert len(result.anomalies) == 1
    assert result.anomalies[0].kind == "invalid_transition"


def test_invalid_transition_open_after_open() -> None:
    """Cannot re-open an already open decision point."""
    e1 = _opened_event(1)
    e2 = _opened_event(2)
    # Must use different event IDs (different ULID)
    result = reduce_decision_point_events([e1, e2])
    assert result.state == DecisionPointState.OPEN
    assert len(result.anomalies) == 1
    assert result.anomalies[0].kind == "invalid_transition"


# ── Tests: Event after terminal ────────────────────────────────────────────────

def test_event_after_terminal_overridden() -> None:
    """No events accepted after terminal overridden state."""
    events = [
        _opened_event(1),
        _resolved_event(2),
        _overridden_event(3),
        _opened_event(4),  # should be rejected
    ]
    result = reduce_decision_point_events(events)
    assert result.state == DecisionPointState.OVERRIDDEN
    assert len(result.anomalies) == 1
    assert result.anomalies[0].kind == "event_after_terminal"


def test_multiple_events_after_terminal() -> None:
    """Multiple events after terminal each produce anomalies."""
    events = [
        _opened_event(1),
        _resolved_event(2),
        _overridden_event(3),
        _opened_event(4),
        _discussing_event(5),
    ]
    result = reduce_decision_point_events(events)
    assert result.state == DecisionPointState.OVERRIDDEN
    assert len(result.anomalies) == 2
    assert all(a.kind == "event_after_terminal" for a in result.anomalies)


# ── Tests: Malformed payloads ──────────────────────────────────────────────────

def test_malformed_payload_missing_fields() -> None:
    """Payload missing required fields produces malformed_payload anomaly."""
    events = [
        _event(DECISION_POINT_OPENED, {"bad": "data"}, lamport=1),
    ]
    result = reduce_decision_point_events(events)
    assert result.state is None
    assert len(result.anomalies) == 1
    assert result.anomalies[0].kind == "malformed_payload"


def test_malformed_payload_does_not_crash() -> None:
    """Reducer continues processing after malformed payload."""
    bad = _event(DECISION_POINT_OPENED, {}, lamport=1)
    good = _opened_event(2)
    result = reduce_decision_point_events([bad, good])
    # bad got malformed_payload, good succeeded (invalid_transition since
    # the bad one didn't advance state, but good opens from None)
    assert result.state == DecisionPointState.OPEN
    assert len(result.anomalies) == 1
    assert result.anomalies[0].kind == "malformed_payload"


# ── Tests: Non-DP events are filtered ──────────────────────────────────────────

def test_non_dp_events_filtered_silently() -> None:
    """Non-DecisionPoint events are filtered out, not recorded as anomalies."""
    non_dp = Event(
        event_id=str(ULID()),
        event_type="MissionStarted",
        aggregate_id="dp/dp-001",
        payload={"some": "data"},
        timestamp=_NOW,
        node_id="node-1",
        lamport_clock=1,
        project_uuid=_PROJECT_UUID,
        correlation_id=str(ULID()),
    )
    events = [_opened_event(2), non_dp]
    result = reduce_decision_point_events(events)
    assert result.anomalies == ()
    assert result.event_count == 2  # counted before filter


# ── Tests: Multiple anomaly accumulation ───────────────────────────────────────

def test_multiple_anomaly_types_accumulated() -> None:
    """Different anomaly types can coexist in a single reduction."""
    events = [
        _event(DECISION_POINT_OPENED, {}, lamport=1),  # malformed
        _discussing_event(2),  # invalid_transition (None -> discussing)
        _opened_event(3),  # succeeds (None -> open)
        _discussing_event(
            4,
            actor_type="llm",
            authority_role="advisory",
            mission_owner_authority_flag=False,
            phase="P1",
        ),  # llm_policy_violation (LLM not allowed outside P0)
    ]
    result = reduce_decision_point_events(events)
    assert result.state == DecisionPointState.OPEN
    kinds = {a.kind for a in result.anomalies}
    assert "malformed_payload" in kinds
    assert "invalid_transition" in kinds
    assert "llm_policy_violation" in kinds
    assert len(result.anomalies) == 3


# ── Golden-file replay ────────────────────────────────────────────────────────

def _serialize_events_jsonl(events: list[Event]) -> str:
    lines = []
    for e in events:
        lines.append(json.dumps(e.model_dump(mode="json"), sort_keys=True))
    return "\n".join(lines) + "\n"


def _load_events_from_jsonl(path: Path) -> list[Event]:
    events = []
    for line in path.read_text().strip().split("\n"):
        if line.strip():
            events.append(Event.model_validate(json.loads(line)))
    return events


def _golden_replay(
    name: str,
    events: list[Event],
) -> None:
    """Run a golden-file replay test.

    On first run (golden file absent), writes the files and marks test as skipped.
    On subsequent runs, asserts exact match against committed golden files.
    """
    _GOLDEN_DIR.mkdir(parents=True, exist_ok=True)
    input_path = _GOLDEN_DIR / f"{name}.jsonl"
    output_path = _GOLDEN_DIR / f"{name}_output.json"

    if not input_path.exists() or not output_path.exists():
        input_path.write_text(_serialize_events_jsonl(events))
        result = reduce_decision_point_events(events)
        output_data = result.model_dump(mode="json")
        output_path.write_text(
            json.dumps(output_data, sort_keys=True, indent=2) + "\n"
        )
        pytest.skip(f"Golden files written for {name!r}; run again to validate")

    loaded_events = _load_events_from_jsonl(input_path)
    result = reduce_decision_point_events(loaded_events)
    actual = result.model_dump(mode="json")
    expected = json.loads(output_path.read_text())
    assert actual == expected, (
        f"Golden replay mismatch for {name!r}. "
        f"Re-run with golden files deleted to regenerate."
    )


def test_golden_replay_full_lifecycle() -> None:
    events = [
        _opened_event(1),
        _discussing_event(2),
        _resolved_event(3),
        _overridden_event(4),
    ]
    _golden_replay("replay_full_lifecycle", events)


def test_golden_replay_open_resolved() -> None:
    events = [_opened_event(1), _resolved_event(2)]
    _golden_replay("replay_open_resolved", events)


def test_golden_replay_with_anomaly() -> None:
    events = [
        _opened_event(1),
        _resolved_event(2),
        _overridden_event(3),
        _discussing_event(4),  # event_after_terminal
    ]
    _golden_replay("replay_with_anomaly", events)
