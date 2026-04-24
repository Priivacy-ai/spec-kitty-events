"""Reducer unit tests for DecisionPoint lifecycle (FR-003).

Covers: empty stream, happy-path transitions (open -> discussing -> resolved),
open -> resolved shortcut, resolved -> overridden, deduplication, deterministic
ordering, authority-policy violations, LLM-policy violations, malformed payloads,
event-after-terminal anomaly, invalid transitions, golden-file replay, and V1
interview-origin transitions with anomaly coverage.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest
from ulid import ULID

from spec_kitty_events.decision_moment import (
    OriginFlow,
    OriginSurface,
    TerminalOutcome,
)
from spec_kitty_events.decisionpoint import (
    DECISION_POINT_DISCUSSING,
    DECISION_POINT_OPENED,
    DECISION_POINT_OVERRIDDEN,
    DECISION_POINT_RESOLVED,
    DECISION_POINT_WIDENED,
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
        "mission_slug": "mission-x",
        "mission_type": "software-dev",
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
        build_id="test-build",
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
    assert result.mission_slug == "mission-x"
    assert result.mission_type == "software-dev"
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
        build_id="test-build",
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
            raw = json.loads(line)
            payload = raw.get("payload")
            if isinstance(payload, dict):
                if "feature_slug" in payload and "mission_slug" not in payload:
                    payload["mission_slug"] = payload.pop("feature_slug")
                if "mission_type" not in payload:
                    payload["mission_type"] = "software-dev"
            raw.setdefault("build_id", "test-build")
            events.append(Event.model_validate(raw))
    return events


def _canonicalize_output(data: dict[str, Any]) -> dict[str, Any]:
    canonical = dict(data)
    if "feature_slug" in canonical and "mission_slug" not in canonical:
        canonical["mission_slug"] = canonical.pop("feature_slug")
    canonical.setdefault("mission_type", "software-dev")
    return canonical


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
    expected = _canonicalize_output(json.loads(output_path.read_text()))
    assert actual == expected, (
        f"Golden replay mismatch for {name!r}. "
        f"Re-run with golden files deleted to regenerate."
    )


def test_legacy_feature_slug_payload_is_rejected() -> None:
    payload = _base_payload()
    payload["feature_slug"] = "legacy-feature"
    result = reduce_decision_point_events([_event(DECISION_POINT_OPENED, payload, lamport=1)])
    assert result.state is None
    assert len(result.anomalies) == 1
    assert result.anomalies[0].kind == "malformed_payload"


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


# ── V1 reducer coverage (Decision Moment V1) ──────────────────────────────────
#
# The V1 reducer extends the state machine with:
#   - discriminated-union payloads keyed on origin_surface
#   - a new WIDENED state (FR-014)
#   - interview-origin Resolved projection fields
#   - origin_mismatch and invalid_transition (closed_locally_without_widening) anomalies
#
# All payloads here are plain dicts so the validator path is exercised.


_DP_ID = "dp-v1-001"
_MISSION_ID = "m-v1-001"
_RUN_ID = "run-v1-001"
_MISSION_SLUG = "v1-mission"


def _ts(lamport: int) -> str:
    """Return an ISO-8601 UTC timestamp string for a given lamport offset."""
    return datetime(2026, 3, 1, 10, 0, lamport, tzinfo=timezone.utc).isoformat()


def _make_event(
    event_type: str,
    payload: dict[str, Any],
    *,
    lamport: int,
) -> Event:
    """Build an Event wrapping a plain payload dict (exercises validator path)."""
    return Event(
        event_id=str(ULID()),
        event_type=event_type,
        aggregate_id=f"dp/{_DP_ID}",
        payload=payload,
        timestamp=datetime(2026, 3, 1, 10, 0, lamport, tzinfo=timezone.utc),
        build_id="test-build",
        node_id="node-v1",
        lamport_clock=lamport,
        project_uuid=_PROJECT_UUID,
        correlation_id=str(ULID()),
    )


def _interview_opened_payload(
    *,
    origin_flow: str = "plan",
    question: str = "Which DB?",
    options: tuple[str, ...] = ("PostgreSQL", "SQLite"),
    input_key: str = "db_choice",
    step_id: str = "step-001",
    lamport: int = 1,
) -> dict[str, Any]:
    return {
        "origin_surface": "planning_interview",
        "decision_point_id": _DP_ID,
        "mission_id": _MISSION_ID,
        "run_id": _RUN_ID,
        "mission_slug": _MISSION_SLUG,
        "mission_type": "software-dev",
        "phase": "P1",
        "origin_flow": origin_flow,
        "question": question,
        "options": list(options),
        "input_key": input_key,
        "step_id": step_id,
        "actor_id": "human-v1",
        "actor_type": "human",
        "state_entered_at": _ts(lamport),
        "recorded_at": _ts(lamport),
    }


def _adr_opened_payload(*, lamport: int = 1) -> dict[str, Any]:
    return {
        "origin_surface": "adr",
        "decision_point_id": _DP_ID,
        "mission_id": _MISSION_ID,
        "run_id": _RUN_ID,
        "mission_slug": _MISSION_SLUG,
        "mission_type": "software-dev",
        "phase": "P1",
        "actor_id": "human-v1",
        "actor_type": "human",
        "authority_role": "mission_owner",
        "mission_owner_authority_flag": True,
        "mission_owner_authority_path": "/missions/m-v1-001/owner",
        "rationale": "ADR rationale",
        "alternatives_considered": ["A", "B"],
        "evidence_refs": ["ref-001"],
        "state_entered_at": _ts(lamport),
        "recorded_at": _ts(lamport),
    }


def _widened_payload(*, lamport: int = 2) -> dict[str, Any]:
    return {
        "origin_surface": "planning_interview",
        "decision_point_id": _DP_ID,
        "mission_id": _MISSION_ID,
        "run_id": _RUN_ID,
        "mission_slug": _MISSION_SLUG,
        "mission_type": "software-dev",
        "channel": "slack",
        "teamspace_ref": {"teamspace_id": "ts-001", "name": "Engineering"},
        "default_channel_ref": {"channel_id": "ch-001", "name": "#decisions"},
        "thread_ref": {
            "slack_team_id": "T-001",
            "channel_id": "ch-001",
            "thread_ts": "1700000000.123456",
            "url": "https://slack.com/archives/ch-001/p1700000000123456",
        },
        "invited_participants": [
            {"participant_id": "p-001", "participant_type": "human"},
        ],
        "widened_by": "p-owner-001",
        "widened_at": _ts(lamport),
        "recorded_at": _ts(lamport),
    }


def _summary_block(text: str) -> dict[str, Any]:
    """Build a minimal valid SummaryBlock dict for use in resolved payloads."""
    return {
        "text": text,
        "source": "manual",
        "extracted_at": None,
        "candidate_answer": None,
    }


def _interview_resolved_payload(
    *,
    terminal_outcome: str = "resolved",
    final_answer: str | None = "PostgreSQL",
    other_answer: bool = False,
    rationale: str | None = None,
    summary: dict[str, Any] | None = None,
    closed_locally_while_widened: bool = False,
    actual_participants: list[dict[str, Any]] | None = None,
    lamport: int = 3,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "origin_surface": "planning_interview",
        "decision_point_id": _DP_ID,
        "mission_id": _MISSION_ID,
        "run_id": _RUN_ID,
        "mission_slug": _MISSION_SLUG,
        "mission_type": "software-dev",
        "terminal_outcome": terminal_outcome,
        "other_answer": other_answer,
        "resolved_by": "p-owner-001",
        "closed_locally_while_widened": closed_locally_while_widened,
        "actual_participants": actual_participants or [],
        "state_entered_at": _ts(lamport),
        "recorded_at": _ts(lamport),
    }
    if final_answer is not None:
        payload["final_answer"] = final_answer
    if rationale is not None:
        payload["rationale"] = rationale
    if summary is not None:
        payload["summary"] = summary
    return payload


def _interview_discussing_payload(*, lamport: int = 3) -> dict[str, Any]:
    return {
        "origin_surface": "planning_interview",
        "decision_point_id": _DP_ID,
        "mission_id": _MISSION_ID,
        "run_id": _RUN_ID,
        "mission_slug": _MISSION_SLUG,
        "mission_type": "software-dev",
        "snapshot_kind": "participant_contribution",
        "contributions": ["Option A looks best", "Consider cost"],
        "actor_id": "service-saas",
        "actor_type": "service",
        "state_entered_at": _ts(lamport),
        "recorded_at": _ts(lamport),
    }


def _adr_resolved_payload(*, lamport: int = 3) -> dict[str, Any]:
    return {
        "origin_surface": "adr",
        "decision_point_id": _DP_ID,
        "mission_id": _MISSION_ID,
        "run_id": _RUN_ID,
        "mission_slug": _MISSION_SLUG,
        "mission_type": "software-dev",
        "phase": "P1",
        "actor_id": "human-v1",
        "actor_type": "human",
        "authority_role": "mission_owner",
        "mission_owner_authority_flag": True,
        "mission_owner_authority_path": "/missions/m-v1-001/owner",
        "rationale": "Resolved with consensus",
        "alternatives_considered": ["A", "B"],
        "evidence_refs": ["ref-001"],
        "state_entered_at": _ts(lamport),
        "recorded_at": _ts(lamport),
    }


def _overridden_payload(*, lamport: int = 4) -> dict[str, Any]:
    return {
        "origin_surface": "planning_interview",
        "decision_point_id": _DP_ID,
        "mission_id": _MISSION_ID,
        "run_id": _RUN_ID,
        "mission_slug": _MISSION_SLUG,
        "mission_type": "software-dev",
        "phase": "P1",
        "actor_id": "human-v1",
        "actor_type": "human",
        "authority_role": "mission_owner",
        "mission_owner_authority_flag": True,
        "mission_owner_authority_path": "/missions/m-v1-001/owner",
        "rationale": "Override after new evidence",
        "alternatives_considered": ["A", "B"],
        "evidence_refs": ["ref-001"],
        "state_entered_at": _ts(lamport),
        "recorded_at": _ts(lamport),
    }


# ── T013 Tests ─────────────────────────────────────────────────────────────────


def test_reducer_opened_interview_only_projects_ask_time_state() -> None:
    """Single interview Opened event projects V1 ask-time fields; ADR fields are None."""
    events = [_make_event(DECISION_POINT_OPENED, _interview_opened_payload(lamport=1), lamport=1)]
    result = reduce_decision_point_events(events)

    assert result.state == DecisionPointState.OPEN
    assert result.origin_surface == OriginSurface.PLANNING_INTERVIEW
    assert result.origin_flow == OriginFlow.PLAN
    assert result.question == "Which DB?"
    assert result.options == ("PostgreSQL", "SQLite")
    assert result.input_key == "db_choice"
    assert result.step_id == "step-001"
    assert result.anomalies == ()
    # ADR-specific fields must be None for interview-origin Opened
    assert result.last_rationale is None
    assert result.last_alternatives_considered is None
    assert result.last_evidence_refs is None


def test_reducer_opened_interview_then_resolved_resolved() -> None:
    """Opened(interview) → Resolved(resolved): terminal_outcome=RESOLVED, final_answer preserved."""
    events = [
        _make_event(DECISION_POINT_OPENED, _interview_opened_payload(lamport=1), lamport=1),
        _make_event(
            DECISION_POINT_RESOLVED,
            _interview_resolved_payload(terminal_outcome="resolved", final_answer="X", lamport=2),
            lamport=2,
        ),
    ]
    result = reduce_decision_point_events(events)

    assert result.state == DecisionPointState.RESOLVED
    assert result.terminal_outcome == TerminalOutcome.RESOLVED
    assert result.final_answer == "X"
    assert result.other_answer is False
    assert result.anomalies == ()


def test_reducer_opened_interview_then_resolved_deferred() -> None:
    """Opened(interview) → Resolved(deferred): final_answer is None, other_answer=False."""
    events = [
        _make_event(DECISION_POINT_OPENED, _interview_opened_payload(lamport=1), lamport=1),
        _make_event(
            DECISION_POINT_RESOLVED,
            _interview_resolved_payload(
                terminal_outcome="deferred",
                final_answer=None,
                rationale="Not enough info yet",
                lamport=2,
            ),
            lamport=2,
        ),
    ]
    result = reduce_decision_point_events(events)

    assert result.state == DecisionPointState.RESOLVED
    assert result.terminal_outcome == TerminalOutcome.DEFERRED
    assert result.final_answer is None
    assert result.other_answer is False
    assert result.anomalies == ()


def test_reducer_opened_interview_then_resolved_canceled() -> None:
    """Opened(interview) → Resolved(canceled): terminal_outcome=CANCELED, final_answer is None."""
    events = [
        _make_event(DECISION_POINT_OPENED, _interview_opened_payload(lamport=1), lamport=1),
        _make_event(
            DECISION_POINT_RESOLVED,
            _interview_resolved_payload(
                terminal_outcome="canceled",
                final_answer=None,
                rationale="Decision no longer relevant",
                lamport=2,
            ),
            lamport=2,
        ),
    ]
    result = reduce_decision_point_events(events)

    assert result.state == DecisionPointState.RESOLVED
    assert result.terminal_outcome == TerminalOutcome.CANCELED
    assert result.final_answer is None
    assert result.other_answer is False
    assert result.anomalies == ()


def test_reducer_opened_interview_then_widened_resolved_resolved() -> None:
    """Opened → Widened → Resolved: state OPEN→WIDENED→RESOLVED; widening projection populated."""
    resolved_payload = _interview_resolved_payload(
        terminal_outcome="resolved",
        final_answer="PostgreSQL",
        summary=_summary_block("Team agreed on PostgreSQL after Slack discussion."),
        actual_participants=[{"participant_id": "p-001", "participant_type": "human"}],
        lamport=3,
    )
    events = [
        _make_event(DECISION_POINT_OPENED, _interview_opened_payload(lamport=1), lamport=1),
        _make_event(DECISION_POINT_WIDENED, _widened_payload(lamport=2), lamport=2),
        _make_event(DECISION_POINT_RESOLVED, resolved_payload, lamport=3),
    ]
    result = reduce_decision_point_events(events)

    assert result.state == DecisionPointState.RESOLVED
    assert result.anomalies == ()
    assert result.widening is not None
    assert result.widening.channel == "slack"
    assert result.widening.teamspace_ref.teamspace_id == "ts-001"
    assert result.widening.thread_ref.channel_id == "ch-001"
    assert len(result.widening.invited_participants) == 1
    assert len(result.actual_participants) == 1
    assert result.actual_participants[0].participant_id == "p-001"


def test_reducer_widened_then_discussing_then_resolved() -> None:
    """Full Slack flow: Opened → Widened → Discussing → Resolved. Final state RESOLVED."""
    events = [
        _make_event(DECISION_POINT_OPENED, _interview_opened_payload(lamport=1), lamport=1),
        _make_event(DECISION_POINT_WIDENED, _widened_payload(lamport=2), lamport=2),
        _make_event(
            DECISION_POINT_DISCUSSING,
            _interview_discussing_payload(lamport=3),
            lamport=3,
        ),
        _make_event(
            DECISION_POINT_RESOLVED,
            _interview_resolved_payload(
                terminal_outcome="resolved",
                final_answer="SQLite",
                summary=_summary_block("SQLite chosen after team discussion."),
                lamport=4,
            ),
            lamport=4,
        ),
    ]
    result = reduce_decision_point_events(events)

    assert result.state == DecisionPointState.RESOLVED
    assert result.anomalies == ()
    assert result.widening is not None
    assert result.terminal_outcome == TerminalOutcome.RESOLVED
    assert result.final_answer == "SQLite"


def test_reducer_duplicate_widened_is_idempotent() -> None:
    """Opened → Widened → Widened → Resolved: second Widened is silently absorbed, no anomaly."""
    events = [
        _make_event(DECISION_POINT_OPENED, _interview_opened_payload(lamport=1), lamport=1),
        _make_event(DECISION_POINT_WIDENED, _widened_payload(lamport=2), lamport=2),
        _make_event(DECISION_POINT_WIDENED, _widened_payload(lamport=3), lamport=3),
        _make_event(
            DECISION_POINT_RESOLVED,
            _interview_resolved_payload(
                terminal_outcome="resolved",
                final_answer="A",
                summary=_summary_block("Option A selected after dedup widening."),
                lamport=4,
            ),
            lamport=4,
        ),
    ]
    result = reduce_decision_point_events(events)

    assert result.state == DecisionPointState.RESOLVED
    assert result.anomalies == ()
    # widening is projected exactly once (from the first Widened)
    assert result.widening is not None
    assert result.widening.teamspace_ref.teamspace_id == "ts-001"


def test_reducer_closed_locally_while_widened_true_sets_field() -> None:
    """Opened → Widened → Resolved(closed_locally_while_widened=True): field set, no anomaly."""
    events = [
        _make_event(DECISION_POINT_OPENED, _interview_opened_payload(lamport=1), lamport=1),
        _make_event(DECISION_POINT_WIDENED, _widened_payload(lamport=2), lamport=2),
        _make_event(
            DECISION_POINT_RESOLVED,
            _interview_resolved_payload(
                terminal_outcome="resolved",
                final_answer="PostgreSQL",
                summary=_summary_block("Resolved locally while widening was active."),
                closed_locally_while_widened=True,
                lamport=3,
            ),
            lamport=3,
        ),
    ]
    result = reduce_decision_point_events(events)

    assert result.state == DecisionPointState.RESOLVED
    assert result.closed_locally_while_widened is True
    assert result.anomalies == ()


def test_reducer_closed_locally_while_widened_without_prior_widening_raises_anomaly() -> None:
    """Resolved with closed_locally_while_widened=True but no prior Widened → invalid_transition anomaly."""
    events = [
        _make_event(DECISION_POINT_OPENED, _interview_opened_payload(lamport=1), lamport=1),
        _make_event(
            DECISION_POINT_RESOLVED,
            _interview_resolved_payload(
                terminal_outcome="resolved",
                final_answer="PostgreSQL",
                closed_locally_while_widened=True,
                lamport=2,
            ),
            lamport=2,
        ),
    ]
    result = reduce_decision_point_events(events)

    assert result.closed_locally_while_widened is False
    assert len(result.anomalies) == 1
    assert result.anomalies[0].kind == "invalid_transition"


def test_reducer_origin_mismatch_across_events_produces_anomaly() -> None:
    """Opened(ADR) → Resolved(interview): origin_mismatch anomaly, events still applied."""
    adr_resolved = _adr_resolved_payload(lamport=2)
    # Swap origin_surface to interview to create a mismatch
    interview_resolved = _interview_resolved_payload(
        terminal_outcome="resolved", final_answer="PostgreSQL", lamport=2
    )
    events = [
        _make_event(DECISION_POINT_OPENED, _adr_opened_payload(lamport=1), lamport=1),
        _make_event(DECISION_POINT_RESOLVED, interview_resolved, lamport=2),
    ]
    result = reduce_decision_point_events(events)

    origin_mismatch_anomalies = [a for a in result.anomalies if a.kind == "origin_mismatch"]
    assert len(origin_mismatch_anomalies) == 1
    # Events are still applied: state should be RESOLVED
    assert result.state == DecisionPointState.RESOLVED


def test_reducer_other_answer_true_preserves_final_answer() -> None:
    """other_answer=True with free-text final_answer: both fields preserved."""
    events = [
        _make_event(
            DECISION_POINT_OPENED,
            _interview_opened_payload(
                options=("A", "B", "Other"),
                lamport=1,
            ),
            lamport=1,
        ),
        _make_event(
            DECISION_POINT_RESOLVED,
            _interview_resolved_payload(
                terminal_outcome="resolved",
                final_answer="custom text",
                other_answer=True,
                lamport=2,
            ),
            lamport=2,
        ),
    ]
    result = reduce_decision_point_events(events)

    assert result.other_answer is True
    assert result.final_answer == "custom text"
    assert result.anomalies == ()


def test_reducer_overridden_after_resolved_still_works_interview() -> None:
    """Opened(interview) → Resolved(interview) → Overridden: state=OVERRIDDEN, fields preserved."""
    events = [
        _make_event(DECISION_POINT_OPENED, _interview_opened_payload(lamport=1), lamport=1),
        _make_event(
            DECISION_POINT_RESOLVED,
            _interview_resolved_payload(terminal_outcome="resolved", final_answer="PostgreSQL", lamport=2),
            lamport=2,
        ),
        _make_event(DECISION_POINT_OVERRIDDEN, _overridden_payload(lamport=3), lamport=3),
    ]
    result = reduce_decision_point_events(events)

    assert result.state == DecisionPointState.OVERRIDDEN
    # V1 projection fields from the Resolved event are preserved
    assert result.terminal_outcome == TerminalOutcome.RESOLVED
    assert result.final_answer == "PostgreSQL"
    assert result.anomalies == ()


def test_reducer_widened_skipped_for_adr_origin() -> None:
    """Opened(ADR) → Widened: Widened requires planning_interview; produces malformed_payload anomaly.

    The DecisionPointWidenedPayload has origin_surface=Literal[PLANNING_INTERVIEW], so
    attempting to validate a Widened payload against an ADR-origin stream fails at the
    schema level (malformed_payload) before any transition logic fires.
    """
    # Build a Widened payload that references an ADR-origin context.
    # The reducer will attempt to validate DecisionPointWidenedPayload.
    # Since DecisionPointWidenedPayload always requires origin_surface=planning_interview,
    # we deliberately omit origin_surface to exercise the "unexpected origin" code path,
    # which the reducer rejects as malformed_payload.
    widened_no_surface = {
        "decision_point_id": _DP_ID,
        "mission_id": _MISSION_ID,
        "run_id": _RUN_ID,
        "mission_slug": _MISSION_SLUG,
        "mission_type": "software-dev",
        "channel": "slack",
        "teamspace_ref": {"teamspace_id": "ts-001"},
        "default_channel_ref": {"channel_id": "ch-001"},
        "thread_ref": {"channel_id": "ch-001", "thread_ts": "1700000000.1"},
        "invited_participants": [],
        "widened_by": "p-owner-001",
        "widened_at": _ts(2),
        "recorded_at": _ts(2),
    }
    events = [
        _make_event(DECISION_POINT_OPENED, _adr_opened_payload(lamport=1), lamport=1),
        _make_event(DECISION_POINT_WIDENED, widened_no_surface, lamport=2),
    ]
    result = reduce_decision_point_events(events)

    anomaly_kinds = {a.kind for a in result.anomalies}
    assert "malformed_payload" in anomaly_kinds or "invalid_transition" in anomaly_kinds


def test_reducer_widened_then_resolved_without_summary_produces_anomaly() -> None:
    """FR-009: summary is required after widening. Reducer records missing_summary anomaly."""
    events = [
        _make_event(DECISION_POINT_OPENED, _interview_opened_payload(lamport=1), lamport=1),
        _make_event(DECISION_POINT_WIDENED, _widened_payload(lamport=2), lamport=2),
        _make_event(
            DECISION_POINT_RESOLVED,
            _interview_resolved_payload(
                terminal_outcome="resolved",
                final_answer="oauth2",
                # summary intentionally omitted
            ),
            lamport=3,
        ),
    ]
    state = reduce_decision_point_events(events)
    assert state.state == DecisionPointState.RESOLVED
    missing_summary_anomalies = [a for a in state.anomalies if a.kind == "missing_summary"]
    assert len(missing_summary_anomalies) == 1, (
        f"Expected 1 missing_summary anomaly, got {state.anomalies}"
    )


def test_reducer_widened_then_resolved_with_summary_produces_no_anomaly() -> None:
    """FR-009 positive control: summary present after widening produces no missing_summary anomaly."""
    events = [
        _make_event(DECISION_POINT_OPENED, _interview_opened_payload(lamport=1), lamport=1),
        _make_event(DECISION_POINT_WIDENED, _widened_payload(lamport=2), lamport=2),
        _make_event(
            DECISION_POINT_RESOLVED,
            _interview_resolved_payload(
                terminal_outcome="resolved",
                final_answer="oauth2",
                summary=_summary_block("Team agreed on oauth2 after Slack discussion."),
            ),
            lamport=3,
        ),
    ]
    state = reduce_decision_point_events(events)
    assert state.state == DecisionPointState.RESOLVED
    missing_summary_anomalies = [a for a in state.anomalies if a.kind == "missing_summary"]
    assert len(missing_summary_anomalies) == 0, (
        f"Expected 0 missing_summary anomalies, got {state.anomalies}"
    )
