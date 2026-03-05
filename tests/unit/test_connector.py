"""Unit tests for Connector payload models, constants, and enums (FR-001, FR-002).

Covers: constant values, enum members, payload validation, mandatory fields,
and frozen model immutability.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from spec_kitty_events.connector import (
    CONNECTOR_DEGRADED,
    CONNECTOR_EVENT_TYPES,
    CONNECTOR_HEALTH_CHECKED,
    CONNECTOR_PROVISIONED,
    CONNECTOR_RECONNECTED,
    CONNECTOR_REVOKED,
    CONNECTOR_SCHEMA_VERSION,
    USER_CONNECTED,
    USER_DISCONNECTED,
    ConnectorDegradedPayload,
    ConnectorHealthCheckedPayload,
    ConnectorProvisionedPayload,
    ConnectorReconnectedPayload,
    ConnectorRevokedPayload,
    ConnectorState,
    HealthStatus,
    ReconnectStrategy,
    UserConnectedPayload,
    UserConnectionStatus,
    UserDisconnectedPayload,
)

# ── Constants tests (FR-001) ────────────────────────────────────────────────


class TestConstants:
    def test_event_type_values(self) -> None:
        assert CONNECTOR_PROVISIONED == "ConnectorProvisioned"
        assert CONNECTOR_HEALTH_CHECKED == "ConnectorHealthChecked"
        assert CONNECTOR_DEGRADED == "ConnectorDegraded"
        assert CONNECTOR_REVOKED == "ConnectorRevoked"
        assert CONNECTOR_RECONNECTED == "ConnectorReconnected"

    def test_user_event_type_values(self) -> None:
        assert USER_CONNECTED == "UserConnected"
        assert USER_DISCONNECTED == "UserDisconnected"

    def test_event_types_frozenset(self) -> None:
        assert isinstance(CONNECTOR_EVENT_TYPES, frozenset)
        assert CONNECTOR_EVENT_TYPES == frozenset({
            "ConnectorProvisioned",
            "ConnectorHealthChecked",
            "ConnectorDegraded",
            "ConnectorRevoked",
            "ConnectorReconnected",
            "UserConnected",
            "UserDisconnected",
        })
        assert len(CONNECTOR_EVENT_TYPES) == 7

    def test_schema_version(self) -> None:
        assert CONNECTOR_SCHEMA_VERSION == "2.8.0"


# ── Enum tests (FR-001) ─────────────────────────────────────────────────────


class TestEnums:
    def test_connector_state_members(self) -> None:
        assert ConnectorState.PROVISIONED.value == "provisioned"
        assert ConnectorState.HEALTHY.value == "healthy"
        assert ConnectorState.DEGRADED.value == "degraded"
        assert ConnectorState.REVOKED.value == "revoked"
        assert ConnectorState.RECONNECTED.value == "reconnected"
        assert len(ConnectorState) == 5

    def test_health_status_members(self) -> None:
        assert HealthStatus.HEALTHY.value == "healthy"
        assert HealthStatus.DEGRADED.value == "degraded"
        assert HealthStatus.UNREACHABLE.value == "unreachable"
        assert len(HealthStatus) == 3

    def test_reconnect_strategy_members(self) -> None:
        assert ReconnectStrategy.AUTOMATIC.value == "automatic"
        assert ReconnectStrategy.MANUAL.value == "manual"
        assert ReconnectStrategy.BACKOFF.value == "backoff"
        assert len(ReconnectStrategy) == 3

    def test_state_is_str_enum(self) -> None:
        assert isinstance(ConnectorState.PROVISIONED, str)
        assert ConnectorState.PROVISIONED == "provisioned"

    def test_health_status_is_str_enum(self) -> None:
        assert isinstance(HealthStatus.HEALTHY, str)
        assert HealthStatus.HEALTHY == "healthy"


# ── Payload test helpers ─────────────────────────────────────────────────────

_NOW = datetime.now(timezone.utc)
_PROJECT_UUID = uuid.UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")


def _base_fields() -> dict:
    """Return a dict of common base fields shared by all connector payloads."""
    return {
        "connector_id": "conn-001",
        "connector_type": "github",
        "provider": "github.com",
        "mission_id": "m-001",
        "project_uuid": str(_PROJECT_UUID),
        "actor_id": "human-1",
        "actor_type": "human",
        "endpoint_url": "https://api.github.com",
        "recorded_at": _NOW.isoformat(),
    }


def _provisioned_payload() -> dict:
    d = _base_fields()
    d["credentials_ref"] = "vault://secrets/gh-token"
    d["config_hash"] = "sha256:abc123"
    return d


def _health_checked_payload() -> dict:
    d = _base_fields()
    d["health_status"] = "healthy"
    d["latency_ms"] = 42.5
    return d


def _degraded_payload() -> dict:
    d = _base_fields()
    d["degradation_reason"] = "High latency detected"
    d["last_healthy_at"] = _NOW.isoformat()
    return d


def _revoked_payload() -> dict:
    d = _base_fields()
    d["revocation_reason"] = "Security breach"
    return d


def _reconnected_payload() -> dict:
    d = _base_fields()
    d["previous_state"] = "revoked"
    d["reconnect_strategy"] = "automatic"
    return d


# ── Payload validation tests (FR-002) ───────────────────────────────────────


class TestPayloadValidation:
    """Test that all payload models validate mandatory fields."""

    def test_provisioned_valid(self) -> None:
        p = ConnectorProvisionedPayload.model_validate(_provisioned_payload())
        assert p.connector_id == "conn-001"
        assert p.credentials_ref == "vault://secrets/gh-token"
        assert p.config_hash == "sha256:abc123"

    def test_health_checked_valid(self) -> None:
        p = ConnectorHealthCheckedPayload.model_validate(_health_checked_payload())
        assert p.connector_id == "conn-001"
        assert p.health_status == HealthStatus.HEALTHY
        assert p.latency_ms == 42.5

    def test_degraded_valid(self) -> None:
        p = ConnectorDegradedPayload.model_validate(_degraded_payload())
        assert p.connector_id == "conn-001"
        assert p.degradation_reason == "High latency detected"

    def test_revoked_valid(self) -> None:
        p = ConnectorRevokedPayload.model_validate(_revoked_payload())
        assert p.connector_id == "conn-001"
        assert p.revocation_reason == "Security breach"

    def test_reconnected_valid(self) -> None:
        p = ConnectorReconnectedPayload.model_validate(_reconnected_payload())
        assert p.connector_id == "conn-001"
        assert p.previous_state == ConnectorState.REVOKED
        assert p.reconnect_strategy == ReconnectStrategy.AUTOMATIC

    @pytest.mark.parametrize("missing_field", [
        "connector_id",
        "connector_type",
        "provider",
        "mission_id",
        "project_uuid",
        "actor_id",
        "actor_type",
        "endpoint_url",
        "recorded_at",
        "credentials_ref",
        "config_hash",
    ])
    def test_provisioned_missing_mandatory_field_raises(self, missing_field: str) -> None:
        data = _provisioned_payload()
        del data[missing_field]
        with pytest.raises(ValidationError):
            ConnectorProvisionedPayload.model_validate(data)

    @pytest.mark.parametrize("missing_field", [
        "connector_id",
        "connector_type",
        "provider",
        "mission_id",
        "project_uuid",
        "actor_id",
        "actor_type",
        "endpoint_url",
        "recorded_at",
        "health_status",
        "latency_ms",
    ])
    def test_health_checked_missing_mandatory_field_raises(self, missing_field: str) -> None:
        data = _health_checked_payload()
        del data[missing_field]
        with pytest.raises(ValidationError):
            ConnectorHealthCheckedPayload.model_validate(data)

    def test_negative_latency_raises(self) -> None:
        data = _health_checked_payload()
        data["latency_ms"] = -1.0
        with pytest.raises(ValidationError):
            ConnectorHealthCheckedPayload.model_validate(data)

    def test_invalid_actor_type_raises(self) -> None:
        data = _provisioned_payload()
        data["actor_type"] = "robot"
        with pytest.raises(ValidationError):
            ConnectorProvisionedPayload.model_validate(data)

    def test_empty_string_fields_raise(self) -> None:
        for field in ["connector_id", "connector_type", "provider", "mission_id", "actor_id"]:
            data = _provisioned_payload()
            data[field] = ""
            with pytest.raises(ValidationError):
                ConnectorProvisionedPayload.model_validate(data)


# ── Frozen immutability tests ────────────────────────────────────────────────


class TestFrozenModels:
    def test_provisioned_is_frozen(self) -> None:
        p = ConnectorProvisionedPayload.model_validate(_provisioned_payload())
        with pytest.raises(ValidationError):
            p.connector_id = "changed"  # type: ignore[misc]

    def test_all_payload_types_frozen(self) -> None:
        payloads = [
            (ConnectorProvisionedPayload, _provisioned_payload()),
            (ConnectorHealthCheckedPayload, _health_checked_payload()),
            (ConnectorDegradedPayload, _degraded_payload()),
            (ConnectorRevokedPayload, _revoked_payload()),
            (ConnectorReconnectedPayload, _reconnected_payload()),
        ]
        for cls, data in payloads:
            payload = cls.model_validate(data)
            assert payload.model_config.get("frozen") is True


# ── user_id on existing payloads (FR-003) ─────────────────────────────────


class TestExistingPayloadsUserIdField:
    def test_provisioned_user_id_default_none(self) -> None:
        p = ConnectorProvisionedPayload.model_validate(_provisioned_payload())
        assert p.user_id is None

    def test_provisioned_user_id_set(self) -> None:
        data = _provisioned_payload()
        data["user_id"] = "user-123"
        p = ConnectorProvisionedPayload.model_validate(data)
        assert p.user_id == "user-123"

    def test_health_checked_user_id_default_none(self) -> None:
        p = ConnectorHealthCheckedPayload.model_validate(_health_checked_payload())
        assert p.user_id is None

    def test_health_checked_user_id_set(self) -> None:
        data = _health_checked_payload()
        data["user_id"] = "user-456"
        p = ConnectorHealthCheckedPayload.model_validate(data)
        assert p.user_id == "user-456"

    def test_degraded_user_id_default_none(self) -> None:
        p = ConnectorDegradedPayload.model_validate(_degraded_payload())
        assert p.user_id is None

    def test_degraded_user_id_set(self) -> None:
        data = _degraded_payload()
        data["user_id"] = "user-789"
        p = ConnectorDegradedPayload.model_validate(data)
        assert p.user_id == "user-789"

    def test_revoked_user_id_default_none(self) -> None:
        p = ConnectorRevokedPayload.model_validate(_revoked_payload())
        assert p.user_id is None

    def test_revoked_user_id_set(self) -> None:
        data = _revoked_payload()
        data["user_id"] = "user-abc"
        p = ConnectorRevokedPayload.model_validate(data)
        assert p.user_id == "user-abc"

    def test_reconnected_user_id_default_none(self) -> None:
        p = ConnectorReconnectedPayload.model_validate(_reconnected_payload())
        assert p.user_id is None

    def test_reconnected_user_id_set(self) -> None:
        data = _reconnected_payload()
        data["user_id"] = "user-def"
        p = ConnectorReconnectedPayload.model_validate(data)
        assert p.user_id == "user-def"


# ── UserConnectedPayload tests ────────────────────────────────────────────


def _user_connected_payload() -> dict:
    d = _base_fields()
    d["user_id"] = "user-123"
    return d


def _user_disconnected_payload() -> dict:
    d = _base_fields()
    d["user_id"] = "user-123"
    d["reason"] = "session_expired"
    return d


class TestUserConnectedPayload:
    def test_valid_payload(self) -> None:
        p = UserConnectedPayload.model_validate(_user_connected_payload())
        assert p.user_id == "user-123"
        assert p.connector_id == "conn-001"

    def test_user_id_required(self) -> None:
        data = _user_connected_payload()
        del data["user_id"]
        with pytest.raises(ValidationError):
            UserConnectedPayload.model_validate(data)

    def test_user_id_empty_raises(self) -> None:
        data = _user_connected_payload()
        data["user_id"] = ""
        with pytest.raises(ValidationError):
            UserConnectedPayload.model_validate(data)

    def test_frozen(self) -> None:
        p = UserConnectedPayload.model_validate(_user_connected_payload())
        with pytest.raises(ValidationError):
            p.user_id = "other"  # type: ignore[misc]


class TestUserDisconnectedPayload:
    def test_valid_payload(self) -> None:
        p = UserDisconnectedPayload.model_validate(_user_disconnected_payload())
        assert p.user_id == "user-123"
        assert p.reason == "session_expired"

    def test_reason_default_empty(self) -> None:
        data = _user_connected_payload()  # no reason field
        p = UserDisconnectedPayload.model_validate(data)
        assert p.reason == ""

    def test_user_id_required(self) -> None:
        data = _user_disconnected_payload()
        del data["user_id"]
        with pytest.raises(ValidationError):
            UserDisconnectedPayload.model_validate(data)

    def test_frozen(self) -> None:
        p = UserDisconnectedPayload.model_validate(_user_disconnected_payload())
        with pytest.raises(ValidationError):
            p.user_id = "other"  # type: ignore[misc]


# ── UserConnectionStatus tests ────────────────────────────────────────────


class TestUserConnectionStatus:
    def test_valid(self) -> None:
        status = UserConnectionStatus(
            user_id="user-123",
            state=ConnectorState.PROVISIONED,
        )
        assert status.user_id == "user-123"
        assert status.state == ConnectorState.PROVISIONED
        assert status.last_event_at is None

    def test_with_timestamp(self) -> None:
        status = UserConnectionStatus(
            user_id="user-123",
            state=ConnectorState.HEALTHY,
            last_event_at=_NOW,
        )
        assert status.last_event_at == _NOW

    def test_frozen(self) -> None:
        status = UserConnectionStatus(
            user_id="user-123",
            state=ConnectorState.PROVISIONED,
        )
        with pytest.raises(ValidationError):
            status.user_id = "other"  # type: ignore[misc]
