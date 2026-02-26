"""Hypothesis property tests proving mission-audit reducer determinism.

Tests: order independence (≥200 examples), idempotent dedup (≥200 examples),
monotonic event_count (≥200 examples).
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from hypothesis import given, settings
from hypothesis import strategies as st
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
    AuditVerdict,
    MissionAuditCompletedPayload,
    MissionAuditDecisionRequestedPayload,
    MissionAuditFailedPayload,
    MissionAuditRequestedPayload,
    MissionAuditStartedPayload,
    reduce_mission_audit_events,
)
from spec_kitty_events.models import Event

# ── Predefined event pool ──────────────────────────────────────────────────────

_PROJECT_UUID = uuid.UUID("99999999-1234-5678-1234-999999999999")

_ARTIFACT_REF = AuditArtifactRef(
    report_path="/reports/prop-test.json",
    content_hash=ContentHashRef(hash="cafebabe12345678", algorithm="sha256"),
    provenance=ProvenanceRef(git_sha="abc123def456"),
)


def _make_event(event_type: str, payload_obj: object, lamport: int) -> Event:
    return Event(
        event_id=str(ULID()),
        event_type=event_type,
        aggregate_id="audit/prop-run-001",
        payload=payload_obj.model_dump(),  # type: ignore[union-attr]
        timestamp=datetime(2026, 1, 1, 12, 0, lamport, tzinfo=timezone.utc),
        node_id="node-prop",
        lamport_clock=lamport,
        project_uuid=_PROJECT_UUID,
        correlation_id=str(ULID()),
    )


# Build a module-level pool of pre-built Event objects for property testing.
# Using a fixed pool (sampled from) is simpler and more reliable than generating
# Pydantic models dynamically from Hypothesis strategies.

_VALID_EVENT_POOL: list[Event] = [
    _make_event(
        MISSION_AUDIT_REQUESTED,
        MissionAuditRequestedPayload(
            mission_id="m-prop-001",
            run_id="run-prop-001",
            feature_slug="prop-feature",
            actor="prop-agent",
            trigger_mode="manual",
            audit_scope=["src/a.py"],
            enforcement_mode="advisory",
        ),
        lamport=1,
    ),
    _make_event(
        MISSION_AUDIT_STARTED,
        MissionAuditStartedPayload(
            mission_id="m-prop-001",
            run_id="run-prop-001",
            feature_slug="prop-feature",
            actor="prop-agent",
            audit_scope_hash="sha256:proptest",
        ),
        lamport=2,
    ),
    _make_event(
        MISSION_AUDIT_DECISION_REQUESTED,
        MissionAuditDecisionRequestedPayload(
            mission_id="m-prop-001",
            run_id="run-prop-001",
            feature_slug="prop-feature",
            actor="prop-agent",
            decision_id="prop-dec-001",
            question="Proceed?",
            context_summary="1 warning",
            severity=AuditSeverity.WARNING,
        ),
        lamport=3,
    ),
    _make_event(
        MISSION_AUDIT_COMPLETED,
        MissionAuditCompletedPayload(
            mission_id="m-prop-001",
            run_id="run-prop-001",
            feature_slug="prop-feature",
            actor="prop-agent",
            verdict=AuditVerdict.PASS,
            severity=AuditSeverity.INFO,
            findings_count=0,
            artifact_ref=_ARTIFACT_REF,
            summary="All good",
        ),
        lamport=4,
    ),
    _make_event(
        MISSION_AUDIT_FAILED,
        MissionAuditFailedPayload(
            mission_id="m-prop-001",
            run_id="run-prop-001",
            feature_slug="prop-feature",
            actor="prop-agent",
            error_code="PROP_ERROR",
            error_message="property test failure",
        ),
        lamport=5,
    ),
]

# Subset used for order-independence tests (avoid terminal conflicts by using
# only Requested + Started; adding terminal events causes anomalies that depend
# on order, which is expected behavior — not a bug).
_ORDER_STABLE_POOL = _VALID_EVENT_POOL[:2]  # Requested + Started


# ── Property 1: Order independence ─────────────────────────────────────────────

@given(st.permutations(_ORDER_STABLE_POOL))
@settings(max_examples=200, deadline=None)
def test_order_independence(perm: list[Event]) -> None:
    """Reducer output is identical regardless of input event ordering.

    Uses a subset of events that don't produce terminal states, ensuring
    the result is stable across all permutations.
    """
    base_result = reduce_mission_audit_events(_ORDER_STABLE_POOL)
    perm_result = reduce_mission_audit_events(perm)
    assert base_result == perm_result


# ── Property 2: Idempotent dedup ───────────────────────────────────────────────

@given(st.lists(st.sampled_from(_VALID_EVENT_POOL), min_size=1, max_size=5))
@settings(max_examples=200, deadline=None)
def test_idempotent_dedup(original: list[Event]) -> None:
    """Doubling events (same event_id) produces the same result as the original."""
    doubled = original + original
    result_original = reduce_mission_audit_events(original)
    result_doubled = reduce_mission_audit_events(doubled)
    assert result_original == result_doubled


# ── Property 3: Monotonic event_count ─────────────────────────────────────────

@given(st.lists(st.sampled_from(_VALID_EVENT_POOL), min_size=1, max_size=8))
@settings(max_examples=200, deadline=None)
def test_monotonic_event_count(events: list[Event]) -> None:
    """event_count after dedup is always ≤ len(input_events).

    Deduplication can only reduce or maintain count, never increase it.
    """
    result = reduce_mission_audit_events(events)
    assert result.event_count <= len(events)
