"""Tests for spec_kitty_events.legacy.LegacyEnvelopeNormalizer.

Covers FR-006..FR-009, NFR-003 (determinism), and the idempotency / non-mutation
guarantees declared by the contract.
"""
from __future__ import annotations

import json
from pathlib import Path

from spec_kitty_events.legacy import (
    LEGACY_ENVELOPE_CONTRACT_NAME,
    LegacyEnvelopeNormalizer,
    NormalizedEnvelope,
    RECOGNIZED_LEGACY_SHAPES,
    UnnormalizableLegacyDiagnostic,
)

# Resolve repository root → fixtures directory.
_FIXTURES = (
    Path(__file__).resolve().parents[2]
    / "src"
    / "spec_kitty_events"
    / "conformance"
    / "fixtures"
    / "legacy"
)


def _read_fixture(name: str) -> dict:
    return json.loads((_FIXTURES / name).read_text(encoding="utf-8"))


def test_contract_name_is_legacy_envelope_v1() -> None:
    assert LEGACY_ENVELOPE_CONTRACT_NAME == "legacy_envelope_v1"


def test_recognized_shapes_is_frozenset() -> None:
    assert isinstance(RECOGNIZED_LEGACY_SHAPES, frozenset)
    assert RECOGNIZED_LEGACY_SHAPES == frozenset(
        {"pre_3_0_envelope", "feature_keys_envelope", "awaiting_review_synonym"}
    )


def test_normalize_pre_3_0_envelope_synthesizes_canonical() -> None:
    fixture = _read_fixture("pre_3_0_envelope_normalizes.json")
    raw = fixture["input"]
    result = LegacyEnvelopeNormalizer().normalize(raw)
    assert isinstance(result, NormalizedEnvelope)
    assert result.legacy_shape == "pre_3_0_envelope"
    assert "project_uuid" in result.canonical
    assert result.canonical["schema_version"] == "3.0.0"
    assert result.canonical["correlation_id"] == raw["event_id"]
    assert result.raw == raw


def test_normalize_pre_3_0_uuid_is_deterministic() -> None:
    """NFR-003: same input always yields the same uuid5."""
    fixture = _read_fixture("pre_3_0_envelope_normalizes.json")
    a = LegacyEnvelopeNormalizer().normalize(fixture["input"])
    b = LegacyEnvelopeNormalizer().normalize(fixture["input"])
    assert isinstance(a, NormalizedEnvelope)
    assert isinstance(b, NormalizedEnvelope)
    assert a.canonical["project_uuid"] == b.canonical["project_uuid"]


def test_normalize_pre_3_0_missing_identity_surfaces_diagnostic() -> None:
    raw = {
        "event_type": "MissionCreated",
        "payload": {"mission_slug": "demo"},
        "event_id": "01J0000000000000000000F001",
        # missing node_id and build_id
    }
    result = LegacyEnvelopeNormalizer().normalize(raw)
    assert isinstance(result, UnnormalizableLegacyDiagnostic)
    assert result.reason == "pre_3_0_envelope_missing_identity"
    assert "missing node_id" in result.shape_hints
    assert "missing build_id" in result.shape_hints
    assert result.raw == raw


def test_normalize_feature_keys_envelope_maps_to_mission_keys() -> None:
    raw = {
        "event_type": "MissionClosed",
        "feature_slug": "demo",
        "feature_number": 5,
        "payload": {
            "feature_slug": "demo",
            "feature_number": 5,
            "mission_type": "software-dev",
        },
        "project_uuid": "00000000-0000-0000-0000-000000000001",
        "event_id": "01J0000000000000000000F002",
        "build_id": "b",
        "node_id": "n",
        "lamport_clock": 1,
        "schema_version": "3.0.0",
        "correlation_id": "01J0000000000000000000C002",
        "timestamp": "2026-01-01T00:00:00+00:00",
    }
    result = LegacyEnvelopeNormalizer().normalize(raw)
    assert isinstance(result, NormalizedEnvelope)
    assert result.legacy_shape == "feature_keys_envelope"
    assert "feature_slug" not in result.canonical
    assert "feature_number" not in result.canonical
    assert result.canonical["mission_slug"] == "demo"
    assert result.canonical["mission_number"] == 5
    assert result.canonical["payload"]["mission_slug"] == "demo"
    assert result.canonical["payload"]["mission_number"] == 5
    assert "feature_slug" not in result.canonical["payload"]


def test_normalize_awaiting_review_synonym_maps_to_in_review() -> None:
    raw = {
        "event_type": "WPStatusChanged",
        "payload": {
            "wp_id": "WP01",
            "from_lane": "for_review",
            "to_lane": "awaiting-review",
            "actor": "user",
            "execution_mode": "worktree",
            "mission_slug": "demo",
        },
        "project_uuid": "00000000-0000-0000-0000-000000000001",
        "event_id": "01J0000000000000000000F003",
        "build_id": "b",
        "node_id": "n",
        "lamport_clock": 1,
        "schema_version": "3.0.0",
        "correlation_id": "01J0000000000000000000C003",
        "timestamp": "2026-01-01T00:00:00+00:00",
    }
    result = LegacyEnvelopeNormalizer().normalize(raw)
    assert isinstance(result, NormalizedEnvelope)
    assert result.legacy_shape == "awaiting_review_synonym"
    assert result.canonical["payload"]["to_lane"] == "in_review"
    # Raw input is preserved verbatim.
    assert result.raw["payload"]["to_lane"] == "awaiting-review"


def test_normalize_unrecognized_surfaces_diagnostic() -> None:
    fixture = _read_fixture("unrecognized_legacy_diagnostic.json")
    raw = fixture["input"]
    result = LegacyEnvelopeNormalizer().normalize(raw)
    assert isinstance(result, UnnormalizableLegacyDiagnostic)
    assert result.reason == "unrecognized_legacy_shape"
    assert result.raw == raw


def test_normalize_canonical_envelope_is_idempotent_unrecognized() -> None:
    """Idempotency guarantee (DIR-001): a fully-canonical envelope is NOT
    silently passed through; the normalizer reports it as unrecognized so
    callers keep the canonical-vs-legacy boundary explicit."""
    canonical = {
        "event_id": "01J0000000000000000000F004",
        "event_type": "MissionCreated",
        "payload": {"mission_slug": "demo"},
        "project_uuid": "00000000-0000-0000-0000-000000000001",
        "build_id": "b",
        "node_id": "n",
        "lamport_clock": 1,
        "schema_version": "3.0.0",
        "correlation_id": "01J0000000000000000000C004",
        "timestamp": "2026-01-01T00:00:00+00:00",
    }
    result = LegacyEnvelopeNormalizer().normalize(canonical)
    assert isinstance(result, UnnormalizableLegacyDiagnostic)
    assert result.reason == "unrecognized_legacy_shape"


def test_normalizer_does_not_mutate_input() -> None:
    raw = {
        "event_type": "MissionCreated",
        "payload": {"mission_slug": "demo"},
        "event_id": "01J0000000000000000000F005",
        "build_id": "b",
        "node_id": "n",
    }
    raw_copy = dict(raw)
    _ = LegacyEnvelopeNormalizer().normalize(raw)
    assert raw == raw_copy


def test_result_variants_use_frozen_extra_forbid() -> None:
    """Both result types must be frozen and reject extras."""
    assert NormalizedEnvelope.model_config.get("frozen") is True
    assert NormalizedEnvelope.model_config.get("extra") == "forbid"
    assert UnnormalizableLegacyDiagnostic.model_config.get("frozen") is True
    assert UnnormalizableLegacyDiagnostic.model_config.get("extra") == "forbid"
