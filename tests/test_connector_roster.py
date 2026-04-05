"""Reducer roster tests for WP02: per-user connection tracking.

Covers: user_connections field, UserConnected/UserDisconnected roster updates,
anomaly for disconnected-without-connected, pre-migration (no user_id) backward
compatibility, and deterministic roster ordering.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from ulid import ULID

from spec_kitty_events.connector import (
    CONNECTOR_HEALTH_CHECKED,
    CONNECTOR_PROVISIONED,
    USER_CONNECTED,
    USER_DISCONNECTED,
    ConnectorState,
    UserConnectionStatus,
    reduce_connector_events,
)
from spec_kitty_events.models import Event

_PROJECT_UUID = uuid.UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")
_NOW = datetime(2026, 2, 27, 12, 0, 0, tzinfo=timezone.utc)


def _base_payload(lamport_offset: int = 0) -> dict[str, Any]:
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
    return Event(
        event_id=event_id or str(ULID()),
        event_type=event_type,
        aggregate_id="connector/conn-001",
        payload=payload_dict,
        timestamp=datetime(2026, 2, 27, 12, 0, lamport, tzinfo=timezone.utc),
        build_id="test-build",
        node_id="node-1",
        lamport_clock=lamport,
        project_uuid=_PROJECT_UUID,
        correlation_id=str(ULID()),
    )


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


def _user_connected_event(user_id: str, lamport: int = 10) -> Event:
    d = _base_payload(lamport)
    d["user_id"] = user_id
    return _event(USER_CONNECTED, d, lamport=lamport)


def _user_disconnected_event(
    user_id: str, lamport: int = 20, reason: str = ""
) -> Event:
    d = _base_payload(lamport)
    d["user_id"] = user_id
    d["reason"] = reason
    return _event(USER_DISCONNECTED, d, lamport=lamport)


# ── T006: user_connections field exists and defaults empty ────────────────────


def test_empty_stream_has_empty_roster() -> None:
    result = reduce_connector_events([])
    assert result.user_connections == ()


def test_binding_only_events_produce_empty_roster() -> None:
    """Pre-migration: events without user_id -> empty user_connections."""
    events = [_provisioned_event(1), _health_checked_event(2)]
    result = reduce_connector_events(events)
    assert result.user_connections == ()
    assert result.current_state == ConnectorState.HEALTHY


# ── T007: Binding-level events with user_id update roster ────────────────────


def test_binding_event_with_user_id_updates_roster() -> None:
    """A ConnectorProvisioned event with user_id populates the roster."""
    d = _base_payload(1)
    d["credentials_ref"] = "vault://secrets/gh-token"
    d["config_hash"] = "sha256:abc123"
    d["user_id"] = "user-alice"
    events = [_event(CONNECTOR_PROVISIONED, d, lamport=1)]
    result = reduce_connector_events(events)
    assert len(result.user_connections) == 1
    assert result.user_connections[0].user_id == "user-alice"
    assert result.user_connections[0].state == ConnectorState.PROVISIONED


# ── T008: UserConnected/UserDisconnected update roster only ──────────────────


def test_user_connected_updates_roster_not_binding_state() -> None:
    """UserConnected adds user to roster but does NOT change current_state."""
    events = [
        _provisioned_event(1),
        _health_checked_event(2),
        _user_connected_event("user-bob", lamport=3),
    ]
    result = reduce_connector_events(events)
    assert result.current_state == ConnectorState.HEALTHY
    assert len(result.user_connections) == 1
    assert result.user_connections[0].user_id == "user-bob"
    assert result.user_connections[0].state == ConnectorState.PROVISIONED


def test_user_disconnected_updates_roster_not_binding_state() -> None:
    """UserDisconnected updates roster but does NOT change current_state."""
    events = [
        _provisioned_event(1),
        _health_checked_event(2),
        _user_connected_event("user-carol", lamport=3),
        _user_disconnected_event("user-carol", lamport=4),
    ]
    result = reduce_connector_events(events)
    assert result.current_state == ConnectorState.HEALTHY
    assert len(result.user_connections) == 1
    assert result.user_connections[0].user_id == "user-carol"
    assert result.user_connections[0].state == ConnectorState.REVOKED


def test_user_events_do_not_appear_in_transition_log() -> None:
    """User-level events must NOT appear in binding-level transition_log."""
    events = [
        _provisioned_event(1),
        _user_connected_event("user-dave", lamport=2),
    ]
    result = reduce_connector_events(events)
    assert len(result.transition_log) == 1
    assert result.transition_log[0][1] == "provisioned"


def test_multiple_users_in_roster() -> None:
    events = [
        _provisioned_event(1),
        _user_connected_event("user-zoe", lamport=2),
        _user_connected_event("user-alice", lamport=3),
        _user_connected_event("user-mike", lamport=4),
    ]
    result = reduce_connector_events(events)
    assert len(result.user_connections) == 3
    user_ids = [uc.user_id for uc in result.user_connections]
    assert user_ids == ["user-alice", "user-mike", "user-zoe"]


def test_roster_sorted_by_user_id_deterministic() -> None:
    """Roster must be sorted by user_id regardless of event order."""
    events_fwd = [
        _provisioned_event(1),
        _user_connected_event("user-b", lamport=2),
        _user_connected_event("user-a", lamport=3),
    ]
    events_rev = [
        _provisioned_event(1),
        _user_connected_event("user-a", lamport=2),
        _user_connected_event("user-b", lamport=3),
    ]
    r1 = reduce_connector_events(events_fwd)
    r2 = reduce_connector_events(events_rev)
    assert [uc.user_id for uc in r1.user_connections] == ["user-a", "user-b"]
    assert [uc.user_id for uc in r2.user_connections] == ["user-a", "user-b"]


# ── T009: Anomaly for UserDisconnected without prior UserConnected ───────────


def test_user_disconnected_without_connected_records_anomaly() -> None:
    """Disconnecting an unknown user records an anomaly."""
    events = [
        _provisioned_event(1),
        _user_disconnected_event("user-unknown", lamport=2),
    ]
    result = reduce_connector_events(events)
    assert len(result.anomalies) == 1
    assert result.anomalies[0].kind == "invalid_transition"
    assert "user-unknown" in result.anomalies[0].message
    assert "no prior connection event" in result.anomalies[0].message
    # User still appears in roster despite anomaly
    assert len(result.user_connections) == 1
    assert result.user_connections[0].user_id == "user-unknown"
    assert result.user_connections[0].state == ConnectorState.REVOKED


def test_user_disconnected_after_connected_no_anomaly() -> None:
    """Disconnecting a known user does NOT record an anomaly."""
    events = [
        _provisioned_event(1),
        _user_connected_event("user-eve", lamport=2),
        _user_disconnected_event("user-eve", lamport=3),
    ]
    result = reduce_connector_events(events)
    assert result.anomalies == ()
    assert result.user_connections[0].state == ConnectorState.REVOKED


# ── Backward compatibility ───────────────────────────────────────────────────


def test_pre_migration_stream_identical_binding_state() -> None:
    """Events without user_id produce identical binding state + empty roster."""
    events = [
        _provisioned_event(1),
        _health_checked_event(2),
    ]
    result = reduce_connector_events(events)
    assert result.current_state == ConnectorState.HEALTHY
    assert result.connector_id == "conn-001"
    assert result.provider == "github.com"
    assert result.user_connections == ()
    assert result.anomalies == ()


# ── Frozen output ────────────────────────────────────────────────────────────


def test_user_connection_status_frozen() -> None:
    uc = UserConnectionStatus(
        user_id="u1", state=ConnectorState.PROVISIONED, last_event_at=_NOW
    )
    import pytest

    with pytest.raises(Exception):
        uc.user_id = "u2"  # type: ignore[misc]
