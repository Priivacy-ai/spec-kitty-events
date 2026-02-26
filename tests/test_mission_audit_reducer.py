"""Reducer unit tests for mission_audit (T010).

Covers: happy-path pass, happy-path fail, decision checkpoint, empty stream,
deduplication, 4 anomaly scenarios, terminal clears pending, partial artifact,
3 golden-file replay scenarios.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest
from ulid import ULID

from spec_kitty_events.dossier import ContentHashRef, ProvenanceRef
from spec_kitty_events.mission_audit import (
    MISSION_AUDIT_COMPLETED,
    MISSION_AUDIT_DECISION_REQUESTED,
    MISSION_AUDIT_FAILED,
    MISSION_AUDIT_REQUESTED,
    MISSION_AUDIT_STARTED,
    AuditArtifactRef,
    AuditSeverity,
    AuditStatus,
    AuditVerdict,
    MissionAuditCompletedPayload,
    MissionAuditDecisionRequestedPayload,
    MissionAuditFailedPayload,
    MissionAuditRequestedPayload,
    MissionAuditStartedPayload,
    reduce_mission_audit_events,
)
from spec_kitty_events.models import Event

# ── Constants ──────────────────────────────────────────────────────────────────

_PROJECT_UUID = uuid.UUID("12345678-1234-5678-1234-567812345678")
_GOLDEN_DIR = Path(__file__).parent / "fixtures" / "mission_audit_golden"

_CONTENT_HASH_REF = ContentHashRef(
    hash="abcdef1234567890abcdef1234567890",
    algorithm="sha256",
)

_PROVENANCE_REF = ProvenanceRef(
    git_sha="deadbeefcafe",
    actor_id="audit-agent-1",
    actor_kind="llm",
)

_ARTIFACT_REF = AuditArtifactRef(
    report_path="/reports/audit-001.json",
    content_hash=_CONTENT_HASH_REF,
    provenance=_PROVENANCE_REF,
)

_PARTIAL_ARTIFACT_REF = AuditArtifactRef(
    report_path="/reports/partial-001.json",
    content_hash=ContentHashRef(hash="1234abcd56789abc", algorithm="sha256"),
    provenance=ProvenanceRef(git_sha="aabbcc"),
)


# ── Helper ─────────────────────────────────────────────────────────────────────

def _event(
    event_type: str,
    payload_obj: Any,
    *,
    lamport: int = 1,
    event_id: str | None = None,
) -> Event:
    """Factory for constructing test Event instances."""
    return Event(
        event_id=event_id or str(ULID()),
        event_type=event_type,
        aggregate_id="audit/run-001",
        payload=payload_obj.model_dump(),
        timestamp=datetime.now(timezone.utc),
        node_id="node-1",
        lamport_clock=lamport,
        project_uuid=_PROJECT_UUID,
        correlation_id=str(ULID()),
    )


def _requested_event(lamport: int = 1) -> Event:
    return _event(
        MISSION_AUDIT_REQUESTED,
        MissionAuditRequestedPayload(
            mission_id="m-001",
            run_id="run-001",
            feature_slug="feature-x",
            actor="agent-1",
            trigger_mode="manual",
            audit_scope=["src/a.py", "src/b.py"],
            enforcement_mode="advisory",
        ),
        lamport=lamport,
    )


def _started_event(lamport: int = 2) -> Event:
    return _event(
        MISSION_AUDIT_STARTED,
        MissionAuditStartedPayload(
            mission_id="m-001",
            run_id="run-001",
            feature_slug="feature-x",
            actor="agent-1",
            audit_scope_hash="sha256:abc123",
        ),
        lamport=lamport,
    )


def _completed_event(lamport: int = 3) -> Event:
    return _event(
        MISSION_AUDIT_COMPLETED,
        MissionAuditCompletedPayload(
            mission_id="m-001",
            run_id="run-001",
            feature_slug="feature-x",
            actor="agent-1",
            verdict=AuditVerdict.PASS,
            severity=AuditSeverity.INFO,
            findings_count=0,
            artifact_ref=_ARTIFACT_REF,
            summary="All checks passed",
        ),
        lamport=lamport,
    )


def _failed_event(lamport: int = 3, partial: bool = False) -> Event:
    return _event(
        MISSION_AUDIT_FAILED,
        MissionAuditFailedPayload(
            mission_id="m-001",
            run_id="run-001",
            feature_slug="feature-x",
            actor="agent-1",
            error_code="TIMEOUT",
            error_message="Audit timed out",
            partial_artifact_ref=_PARTIAL_ARTIFACT_REF if partial else None,
        ),
        lamport=lamport,
    )


def _decision_event(decision_id: str = "dec-001", lamport: int = 3) -> Event:
    return _event(
        MISSION_AUDIT_DECISION_REQUESTED,
        MissionAuditDecisionRequestedPayload(
            mission_id="m-001",
            run_id="run-001",
            feature_slug="feature-x",
            actor="agent-1",
            decision_id=decision_id,
            question="Proceed despite warnings?",
            context_summary="2 warnings in src/a.py",
            severity=AuditSeverity.WARNING,
        ),
        lamport=lamport,
    )


# ── Tests ─────────────────────────────────────────────────────────────────────

def test_empty_stream() -> None:
    result = reduce_mission_audit_events([])
    assert result.audit_status == AuditStatus.PENDING
    assert result.event_count == 0
    assert result.anomalies == ()
    assert result.pending_decisions == ()
    assert result.verdict is None
    assert result.mission_id is None


def test_happy_path_pass() -> None:
    events = [_requested_event(1), _started_event(2), _completed_event(3)]
    result = reduce_mission_audit_events(events)
    assert result.audit_status == AuditStatus.COMPLETED
    assert result.verdict == AuditVerdict.PASS
    assert result.artifact_ref is not None
    assert result.anomalies == ()
    assert result.event_count == 3


def test_happy_path_fail() -> None:
    events = [_requested_event(1), _started_event(2), _failed_event(3)]
    result = reduce_mission_audit_events(events)
    assert result.audit_status == AuditStatus.FAILED
    assert result.verdict is None
    assert result.error_code == "TIMEOUT"
    assert result.event_count == 3


def test_decision_checkpoint() -> None:
    dec = _decision_event("dec-1", lamport=3)
    events = [_requested_event(1), _started_event(2), dec]
    result = reduce_mission_audit_events(events)
    assert result.audit_status == AuditStatus.AWAITING_DECISION
    assert len(result.pending_decisions) == 1
    assert result.pending_decisions[0].decision_id == "dec-1"

    # Now add Completed
    comp = _completed_event(lamport=4)
    result2 = reduce_mission_audit_events(events + [comp])
    assert result2.pending_decisions == ()
    assert result2.audit_status == AuditStatus.COMPLETED


def test_deduplication() -> None:
    e1 = _requested_event(1)
    e2 = _started_event(2)
    e3 = _completed_event(3)
    original = [e1, e2, e3]
    # Double every event (same event_id = duplicate)
    doubled = [e1, e2, e3, e1, e2, e3]
    result_original = reduce_mission_audit_events(original)
    result_doubled = reduce_mission_audit_events(doubled)
    assert result_original == result_doubled
    # event_count reflects deduplicated count (3), not doubled (6)
    assert result_original.event_count == 3
    assert result_doubled.event_count == 3


def test_anomaly_event_before_requested() -> None:
    # Feed MissionAuditStarted before any MissionAuditRequested
    events = [_started_event(1)]
    result = reduce_mission_audit_events(events)
    assert len(result.anomalies) == 1
    assert result.anomalies[0].kind == "event_before_requested"


def test_anomaly_event_after_terminal() -> None:
    events = [_requested_event(1), _started_event(2), _completed_event(3)]
    # Add another started after terminal
    post_terminal = _started_event(lamport=4)
    result = reduce_mission_audit_events(events + [post_terminal])
    assert len(result.anomalies) == 1
    assert result.anomalies[0].kind == "event_after_terminal"
    # audit_status remains completed
    assert result.audit_status == AuditStatus.COMPLETED


def test_anomaly_duplicate_decision_id() -> None:
    dec1 = _decision_event("dec-001", lamport=3)
    dec2 = _decision_event("dec-001", lamport=4)  # same decision_id
    events = [_requested_event(1), _started_event(2), dec1, dec2]
    result = reduce_mission_audit_events(events)
    assert len(result.anomalies) == 1
    assert result.anomalies[0].kind == "duplicate_decision_id"
    # No duplicate entry added
    assert len(result.pending_decisions) == 1


def test_anomaly_unrecognized_type_via_filter() -> None:
    """Non-audit events are silently filtered out; they don't appear in anomalies."""
    # Build an event with a non-audit event_type
    from spec_kitty_events.lifecycle import MISSION_STARTED
    non_audit_event = Event(
        event_id=str(ULID()),
        event_type=MISSION_STARTED,  # not in MISSION_AUDIT_EVENT_TYPES
        aggregate_id="audit/run-001",
        payload={"some": "data"},
        timestamp=datetime.now(timezone.utc),
        node_id="node-1",
        lamport_clock=1,
        project_uuid=_PROJECT_UUID,
        correlation_id=str(ULID()),
    )
    events = [_requested_event(2), non_audit_event]
    result = reduce_mission_audit_events(events)
    # Non-audit event is filtered, not recorded as anomaly
    assert result.anomalies == ()
    assert result.event_count == 2  # both events counted before filter


def test_terminal_clears_pending_decisions() -> None:
    dec = _decision_event("dec-001", lamport=3)
    comp = _completed_event(lamport=4)
    events = [_requested_event(1), _started_event(2), dec, comp]
    result = reduce_mission_audit_events(events)
    assert result.pending_decisions == ()
    assert result.audit_status == AuditStatus.COMPLETED


def test_partial_artifact_on_failure() -> None:
    events = [_requested_event(1), _started_event(2), _failed_event(3, partial=True)]
    result = reduce_mission_audit_events(events)
    assert result.partial_artifact_ref is not None
    assert result.verdict is None
    assert result.audit_status == AuditStatus.FAILED


# ── Golden-file replay ─────────────────────────────────────────────────────────

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
        # First run (or incomplete prior run): write golden files
        input_path.write_text(_serialize_events_jsonl(events))
        result = reduce_mission_audit_events(events)
        output_data = result.model_dump(mode="json")
        output_path.write_text(
            json.dumps(output_data, sort_keys=True, indent=2) + "\n"
        )
        pytest.skip(f"Golden files written for {name!r}; run again to validate")

    # Subsequent runs: load events from JSONL and compare
    loaded_events = _load_events_from_jsonl(input_path)
    result = reduce_mission_audit_events(loaded_events)
    actual = result.model_dump(mode="json")
    expected = json.loads(output_path.read_text())
    assert actual == expected, (
        f"Golden replay mismatch for {name!r}. "
        f"Re-run with golden files deleted to regenerate."
    )


def test_golden_replay_pass() -> None:
    events = [_requested_event(1), _started_event(2), _completed_event(3)]
    _golden_replay("replay_pass", events)


def test_golden_replay_fail() -> None:
    events = [_requested_event(1), _started_event(2), _failed_event(3)]
    _golden_replay("replay_fail", events)


def test_golden_replay_decision_checkpoint() -> None:
    events = [
        _requested_event(1),
        _started_event(2),
        _decision_event("dec-001", lamport=3),
        _completed_event(lamport=4),
    ]
    _golden_replay("replay_decision_checkpoint", events)
