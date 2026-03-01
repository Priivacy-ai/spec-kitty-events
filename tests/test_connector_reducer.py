"""Reducer unit tests for Connector lifecycle (FR-006).

Covers: empty stream, happy-path transitions, revocation path,
invalid transition recording (anomaly, no crash), duplicate event dedup,
and deterministic ordering.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

import pytest
from ulid import ULID

from spec_kitty_events.connector import (
    CONNECTOR_DEGRADED,
    CONNECTOR_HEALTH_CHECKED,
    CONNECTOR_PROVISIONED,
    CONNECTOR_RECONNECTED,
    CONNECTOR_REVOKED,
    ConnectorState,
    reduce_connector_events,
)
from spec_kitty_events.models import Event

# ── Constants ──────────────────────────────────────────────────────────────────

_PROJECT_UUID = uuid.UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")
_NOW = datetime(2026, 2, 27, 12, 0, 0, tzinfo=timezone.utc)


# ── Payload helpers ────────────────────────────────────────────────────────────


def _base_payload(lamport_offset: int = 0) -> dict[str, Any]:
    """Return a valid connector payload dict with base fields."""
    return {
        "connector_id": "conn-001",
        "connector_type": "github",
        "provider": "github.com",
        "mission_id": "m-001",
        "project_uuid": str(_PROJECT_UUID),
        "actor_id": "human-1",
        "actor_type": "human",
        "endpoint_url": "https://api.github.com",
        "recorded_at": datetime(
            2026, 2, 27, 12, 0, lamport_offset, tzinfo=timezone.utc
        ).isoformat(),
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
        aggregate_id="connector/conn-001",
        payload=payload_dict,
        timestamp=datetime(2026, 2, 27, 12, 0, lamport, tzinfo=timezone.utc),
        node_id="node-1",
        lamport_clock=lamport,
        project_uuid=_PROJECT_UUID,
        correlation_id=str(ULID()),
    )


# ── Named event factories ─────────────────────────────────────────────────────


def _provisioned_event(lamport: int = 1) -> Event:
    d = _base_payload(lamport)
    d["credentials_ref"] = "vault://secrets/gh-token"
    d["config_hash"] = "sha256:abc123"
    return _event(CONNECTOR_PROVISIONED, d, lamport=lamport)


def _health_checked_event(lamport: int = 2) -> Event:
    d = _base_payload(lamport)
    d["health_status"] = "healthy"
    d["latency_ms"] = 42.5
    return _event(CONNECTOR_HEALTH_CHECKED, d, lamport=lamport)


def _degraded_event(lamport: int = 3) -> Event:
    d = _base_payload(lamport)
    d["degradation_reason"] = "High latency"
    d["last_healthy_at"] = _NOW.isoformat()
    return _event(CONNECTOR_DEGRADED, d, lamport=lamport)


def _revoked_event(lamport: int = 4) -> Event:
    d = _base_payload(lamport)
    d["revocation_reason"] = "Security breach"
    return _event(CONNECTOR_REVOKED, d, lamport=lamport)


def _reconnected_event(lamport: int = 5, previous_state: str = "revoked") -> Event:
    d = _base_payload(lamport)
    d["previous_state"] = previous_state
    d["reconnect_strategy"] = "automatic"
    return _event(CONNECTOR_RECONNECTED, d, lamport=lamport)


# ── Tests: Empty and basic transitions ─────────────────────────────────────────


def test_empty_stream() -> None:
    result = reduce_connector_events([])
    assert result.current_state is None
    assert result.event_count == 0
    assert result.anomalies == ()
    assert result.connector_id is None
    assert result.provider is None
    assert result.transition_log == ()


def test_happy_path_provisioned_healthy_degraded_reconnected_healthy() -> None:
    """provisioned -> healthy -> degraded -> reconnected -> healthy."""
    events = [
        _provisioned_event(1),
        _health_checked_event(2),
        _degraded_event(3),
        _reconnected_event(4, previous_state="degraded"),
        _health_checked_event(5),
    ]
    result = reduce_connector_events(events)
    assert result.current_state == ConnectorState.HEALTHY
    assert result.connector_id == "conn-001"
    assert result.provider == "github.com"
    assert result.anomalies == ()
    assert result.event_count == 5
    assert len(result.transition_log) == 5


def test_revocation_path() -> None:
    """provisioned -> revoked -> reconnected."""
    events = [
        _provisioned_event(1),
        _revoked_event(2),
        _reconnected_event(3),
    ]
    result = reduce_connector_events(events)
    assert result.current_state == ConnectorState.RECONNECTED
    assert result.anomalies == ()
    assert result.event_count == 3


def test_provisioned_to_degraded() -> None:
    """provisioned -> degraded is a valid direct transition."""
    events = [_provisioned_event(1), _degraded_event(2)]
    result = reduce_connector_events(events)
    assert result.current_state == ConnectorState.DEGRADED
    assert result.anomalies == ()


def test_healthy_to_revoked() -> None:
    """healthy -> revoked is valid."""
    events = [
        _provisioned_event(1),
        _health_checked_event(2),
        _revoked_event(3),
    ]
    result = reduce_connector_events(events)
    assert result.current_state == ConnectorState.REVOKED
    assert result.anomalies == ()


# ── Tests: Invalid transitions ─────────────────────────────────────────────────


def test_invalid_transition_records_anomaly_no_crash() -> None:
    """Trying to go from provisioned directly to reconnected is invalid."""
    events = [
        _provisioned_event(1),
        _reconnected_event(2, previous_state="provisioned"),
    ]
    result = reduce_connector_events(events)
    assert result.current_state == ConnectorState.PROVISIONED
    assert len(result.anomalies) == 1
    assert result.anomalies[0].kind == "invalid_transition"
    assert "Invalid transition" in result.anomalies[0].message


def test_invalid_transition_healthy_to_provisioned() -> None:
    """Cannot re-provision a healthy connector."""
    events = [
        _provisioned_event(1),
        _health_checked_event(2),
        _provisioned_event(3),
    ]
    result = reduce_connector_events(events)
    assert result.current_state == ConnectorState.HEALTHY
    assert len(result.anomalies) == 1
    assert result.anomalies[0].kind == "invalid_transition"


def test_invalid_transition_no_initial_health_check() -> None:
    """Cannot health-check without provisioning first."""
    events = [_health_checked_event(1)]
    result = reduce_connector_events(events)
    assert result.current_state is None
    assert len(result.anomalies) == 1
    assert result.anomalies[0].kind == "invalid_transition"


# ── Tests: Deduplication ───────────────────────────────────────────────────────


def test_deduplication() -> None:
    e1 = _provisioned_event(1)
    e2 = _health_checked_event(2)
    original = [e1, e2]
    doubled = [e1, e2, e1, e2]
    result_original = reduce_connector_events(original)
    result_doubled = reduce_connector_events(doubled)
    assert result_original == result_doubled
    assert result_original.event_count == 2
    assert result_doubled.event_count == 2


# ── Tests: Deterministic ordering ─────────────────────────────────────────────


def test_deterministic_with_reversed_input() -> None:
    """Reducer must sort by (lamport_clock, timestamp, event_id) for determinism."""
    e1 = _provisioned_event(1)
    e2 = _health_checked_event(2)
    forward = reduce_connector_events([e1, e2])
    reverse = reduce_connector_events([e2, e1])
    assert forward == reverse


# ── Tests: Malformed payloads ──────────────────────────────────────────────────


def test_malformed_payload_records_anomaly() -> None:
    """Payload missing required fields produces malformed_payload anomaly."""
    events = [
        _event(CONNECTOR_PROVISIONED, {"bad": "data"}, lamport=1),
    ]
    result = reduce_connector_events(events)
    assert result.current_state is None
    assert len(result.anomalies) == 1
    assert result.anomalies[0].kind == "malformed_payload"


def test_malformed_payload_does_not_crash() -> None:
    """Reducer continues processing after malformed payload."""
    bad = _event(CONNECTOR_PROVISIONED, {}, lamport=1)
    good = _provisioned_event(2)
    result = reduce_connector_events([bad, good])
    assert result.current_state == ConnectorState.PROVISIONED
    assert len(result.anomalies) == 1
    assert result.anomalies[0].kind == "malformed_payload"


# ── Tests: Non-connector events are filtered ──────────────────────────────────


def test_non_connector_events_filtered_silently() -> None:
    """Non-Connector events are filtered out, not recorded as anomalies."""
    non_conn = Event(
        event_id=str(ULID()),
        event_type="MissionStarted",
        aggregate_id="connector/conn-001",
        payload={"some": "data"},
        timestamp=_NOW,
        node_id="node-1",
        lamport_clock=1,
        project_uuid=_PROJECT_UUID,
        correlation_id=str(ULID()),
    )
    events = [_provisioned_event(2), non_conn]
    result = reduce_connector_events(events)
    assert result.anomalies == ()
    assert result.event_count == 2  # counted before filter


# ── Tests: Health check tracking ──────────────────────────────────────────────


def test_last_health_check_tracked() -> None:
    events = [_provisioned_event(1), _health_checked_event(2)]
    result = reduce_connector_events(events)
    assert result.last_health_check is not None


# ── Tests: Reducer output is frozen ───────────────────────────────────────────


def test_reducer_output_is_frozen() -> None:
    result = reduce_connector_events([_provisioned_event(1)])
    with pytest.raises(Exception):
        result.current_state = ConnectorState.HEALTHY  # type: ignore[misc]
