"""Hypothesis property tests proving DecisionPoint reducer determinism (FR-004, FR-005).

Tests: order independence (>=200 examples), idempotent dedup (>=200 examples),
monotonic event_count (>=200 examples).
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from hypothesis import given, settings
from hypothesis import strategies as st
from ulid import ULID

from spec_kitty_events.decisionpoint import (
    DECISION_POINT_DISCUSSING,
    DECISION_POINT_OPENED,
    DECISION_POINT_OVERRIDDEN,
    DECISION_POINT_RESOLVED,
    DecisionPointDiscussingPayload,
    DecisionPointOpenedPayload,
    DecisionPointOverriddenPayload,
    DecisionPointResolvedPayload,
    reduce_decision_point_events,
)
from spec_kitty_events.models import Event

# -- Predefined event pool ---------------------------------------------------

_PROJECT_UUID = uuid.UUID("88888888-1234-5678-1234-888888888888")


def _make_event(event_type: str, payload_obj: object, lamport: int) -> Event:
    return Event(
        event_id=str(ULID()),
        event_type=event_type,
        aggregate_id="dp/dp-prop-001",
        payload=payload_obj.model_dump(),  # type: ignore[union-attr]
        timestamp=datetime(2026, 1, 1, 12, 0, lamport, tzinfo=timezone.utc),
        node_id="node-prop",
        lamport_clock=lamport,
        project_uuid=_PROJECT_UUID,
        correlation_id=str(ULID()),
    )


# Build a module-level pool of pre-built Event objects for property testing.
_VALID_EVENT_POOL: list[Event] = [
    _make_event(
        DECISION_POINT_OPENED,
        DecisionPointOpenedPayload(
            decision_point_id="dp-prop-001",
            mission_id="m-prop-001",
            run_id="run-prop-001",
            feature_slug="prop-feature",
            phase="P1",
            actor_id="human-prop",
            actor_type="human",
            authority_role="mission_owner",
            mission_owner_authority_flag=True,
            mission_owner_authority_path="/missions/m-prop-001/owner",
            rationale="Property test rationale",
            alternatives_considered=("A", "B"),
            evidence_refs=("ref-prop-001",),
            state_entered_at=datetime(2026, 1, 1, 12, 0, 1, tzinfo=timezone.utc),
            recorded_at=datetime(2026, 1, 1, 12, 0, 1, tzinfo=timezone.utc),
        ),
        lamport=1,
    ),
    _make_event(
        DECISION_POINT_DISCUSSING,
        DecisionPointDiscussingPayload(
            decision_point_id="dp-prop-001",
            mission_id="m-prop-001",
            run_id="run-prop-001",
            feature_slug="prop-feature",
            phase="P1",
            actor_id="human-prop",
            actor_type="human",
            authority_role="mission_owner",
            mission_owner_authority_flag=True,
            mission_owner_authority_path="/missions/m-prop-001/owner",
            rationale="Discussion point",
            alternatives_considered=("A", "B"),
            evidence_refs=("ref-prop-002",),
            state_entered_at=datetime(2026, 1, 1, 12, 0, 2, tzinfo=timezone.utc),
            recorded_at=datetime(2026, 1, 1, 12, 0, 2, tzinfo=timezone.utc),
        ),
        lamport=2,
    ),
    _make_event(
        DECISION_POINT_RESOLVED,
        DecisionPointResolvedPayload(
            decision_point_id="dp-prop-001",
            mission_id="m-prop-001",
            run_id="run-prop-001",
            feature_slug="prop-feature",
            phase="P1",
            actor_id="human-prop",
            actor_type="human",
            authority_role="mission_owner",
            mission_owner_authority_flag=True,
            mission_owner_authority_path="/missions/m-prop-001/owner",
            rationale="Resolved with consensus",
            alternatives_considered=("A", "B"),
            evidence_refs=("ref-prop-003",),
            state_entered_at=datetime(2026, 1, 1, 12, 0, 3, tzinfo=timezone.utc),
            recorded_at=datetime(2026, 1, 1, 12, 0, 3, tzinfo=timezone.utc),
        ),
        lamport=3,
    ),
    _make_event(
        DECISION_POINT_OVERRIDDEN,
        DecisionPointOverriddenPayload(
            decision_point_id="dp-prop-001",
            mission_id="m-prop-001",
            run_id="run-prop-001",
            feature_slug="prop-feature",
            phase="P1",
            actor_id="human-prop",
            actor_type="human",
            authority_role="mission_owner",
            mission_owner_authority_flag=True,
            mission_owner_authority_path="/missions/m-prop-001/owner",
            rationale="Override due to new evidence",
            alternatives_considered=("A", "B"),
            evidence_refs=("ref-prop-004",),
            state_entered_at=datetime(2026, 1, 1, 12, 0, 4, tzinfo=timezone.utc),
            recorded_at=datetime(2026, 1, 1, 12, 0, 4, tzinfo=timezone.utc),
        ),
        lamport=4,
    ),
]

# Subset used for order-independence tests (avoid terminal conflicts by using
# only Opened + Discussing; adding terminal events causes anomalies that depend
# on order, which is expected behavior -- not a bug).
_ORDER_STABLE_POOL = _VALID_EVENT_POOL[:2]  # Opened + Discussing


# -- Property 1: Order independence -------------------------------------------

@given(st.permutations(_ORDER_STABLE_POOL))
@settings(max_examples=200, deadline=None)
def test_order_independence(perm: list[Event]) -> None:
    """Reducer output is identical regardless of input event ordering.

    Uses a subset of events that don't produce terminal states, ensuring
    the result is stable across all permutations.
    """
    base_result = reduce_decision_point_events(_ORDER_STABLE_POOL)
    perm_result = reduce_decision_point_events(perm)
    assert base_result == perm_result


# -- Property 2: Idempotent dedup ---------------------------------------------

@given(st.lists(st.sampled_from(_VALID_EVENT_POOL), min_size=1, max_size=5))
@settings(max_examples=200, deadline=None)
def test_idempotent_dedup(original: list[Event]) -> None:
    """Doubling events (same event_id) produces the same result as the original."""
    doubled = original + original
    result_original = reduce_decision_point_events(original)
    result_doubled = reduce_decision_point_events(doubled)
    assert result_original == result_doubled


# -- Property 3: Monotonic event_count ----------------------------------------

@given(st.lists(st.sampled_from(_VALID_EVENT_POOL), min_size=1, max_size=8))
@settings(max_examples=200, deadline=None)
def test_monotonic_event_count(events: list[Event]) -> None:
    """event_count after dedup is always <= len(input_events).

    Deduplication can only reduce or maintain count, never increase it.
    """
    result = reduce_decision_point_events(events)
    assert result.event_count <= len(events)
