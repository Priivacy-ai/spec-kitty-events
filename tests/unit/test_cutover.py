"""Unit tests for the authoritative cutover artifact helpers."""

import pytest

from spec_kitty_events.cutover import (
    CUTOVER_ARTIFACT,
    assert_canonical_cutover_signal,
    canonical_signal_field_name,
    canonical_signal_location,
    forbidden_legacy_aggregate_names,
    forbidden_legacy_event_names,
    forbidden_legacy_keys,
    is_pre_cutover_payload,
    load_cutover_artifact,
    read_cutover_signal,
)


def _canonical_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "event_type": "MissionCreated",
        "aggregate_id": "mission/M001",
        "schema_version": CUTOVER_ARTIFACT.cutover_contract_version,
        "payload": {"mission_slug": "mission-001", "mission_type": "delivery"},
    }
    payload.update(overrides)
    return payload


def test_cutover_artifact_is_authoritative_and_machine_readable() -> None:
    artifact = load_cutover_artifact()

    assert artifact is CUTOVER_ARTIFACT
    assert canonical_signal_field_name() == "schema_version"
    assert canonical_signal_location() == "event_envelope"
    assert artifact.accepted_major == 3
    assert artifact.forbidden_legacy_keys == ("feature_slug", "feature_number", "mission_key")


def test_canonical_payload_passes_cutover_checks() -> None:
    payload = _canonical_payload()

    assert read_cutover_signal(payload) == "3.0.0"
    assert not is_pre_cutover_payload(payload)
    assert_canonical_cutover_signal(payload)


def test_missing_signal_is_classified_as_pre_cutover() -> None:
    payload = _canonical_payload()
    payload.pop("schema_version")

    assert is_pre_cutover_payload(payload)
    with pytest.raises(ValueError, match="missing canonical cutover signal"):
        assert_canonical_cutover_signal(payload)


def test_wrong_accepted_major_is_classified_as_pre_cutover() -> None:
    payload = _canonical_payload(schema_version="2.9.0")

    assert is_pre_cutover_payload(payload)
    with pytest.raises(ValueError, match="unsupported cutover major version"):
        assert_canonical_cutover_signal(payload)


def test_forbidden_key_fails_independently() -> None:
    payload = _canonical_payload(payload={"mission_slug": "mission-001", "feature_slug": "legacy"})

    assert forbidden_legacy_keys(payload) == {"feature_slug"}
    assert is_pre_cutover_payload(payload)
    with pytest.raises(ValueError, match="forbidden legacy keys"):
        assert_canonical_cutover_signal(payload)


def test_forbidden_event_name_fails_independently() -> None:
    payload = _canonical_payload(event_type="FeatureCreated")

    assert forbidden_legacy_event_names(payload) == {"FeatureCreated"}
    assert is_pre_cutover_payload(payload)
    with pytest.raises(ValueError, match="forbidden legacy event names"):
        assert_canonical_cutover_signal(payload)


def test_forbidden_aggregate_name_fails_independently() -> None:
    payload = _canonical_payload(aggregate_id="feature/M001")

    assert forbidden_legacy_aggregate_names(payload) == {"feature"}
    assert is_pre_cutover_payload(payload)
    with pytest.raises(ValueError, match="forbidden legacy aggregate names"):
        assert_canonical_cutover_signal(payload)


# ---------------------------------------------------------------------------
# Issue 2 regression tests: the public cutover gate must route through the
# recursive forbidden-key walker (spec_kitty_events.forbidden_keys), not a
# top-level-only check. Pre-fix behaviour: a deeply nested or array-element
# forbidden key would silently pass the public gate.
# ---------------------------------------------------------------------------


def test_recursive_walker_catches_nested_feature_slug() -> None:
    """Nested ``feature_slug`` inside ``payload.metadata.tags[2]`` must fail."""

    payload = _canonical_payload(
        payload={
            "mission_slug": "mission-001",
            "metadata": {
                "tags": [
                    "ok-1",
                    "ok-2",
                    {"feature_slug": "leaked-deep"},
                ],
            },
        },
    )

    assert "feature_slug" in forbidden_legacy_keys(payload)
    assert is_pre_cutover_payload(payload)
    with pytest.raises(ValueError, match="forbidden legacy keys"):
        assert_canonical_cutover_signal(payload)


def test_recursive_walker_catches_nested_feature_number() -> None:
    payload = _canonical_payload(
        payload={
            "mission_slug": "mission-001",
            "extra": {"deep": {"feature_number": 42}},
        },
    )

    assert "feature_number" in forbidden_legacy_keys(payload)
    with pytest.raises(ValueError, match="forbidden legacy keys"):
        assert_canonical_cutover_signal(payload)


def test_recursive_walker_catches_nested_mission_key() -> None:
    payload = _canonical_payload(
        payload={
            "mission_slug": "mission-001",
            "audit_trail": [{"mission_key": "legacy"}],
        },
    )

    assert "mission_key" in forbidden_legacy_keys(payload)
    with pytest.raises(ValueError, match="forbidden legacy keys"):
        assert_canonical_cutover_signal(payload)


def test_recursive_walker_catches_legacy_aggregate_id() -> None:
    """``legacy_aggregate_id`` is in the SSOT FORBIDDEN_LEGACY_KEYS set
    (added per epic #920 historical-row survey). The cutover gate must
    reject it even though it is not in the cutover artifact's own
    3-tuple ``forbidden_legacy_keys`` field."""

    payload = _canonical_payload(
        payload={
            "mission_slug": "mission-001",
            "extra": {"legacy_aggregate_id": "01J0000000000000000000LEG1"},
        },
    )

    assert "legacy_aggregate_id" in forbidden_legacy_keys(payload)
    with pytest.raises(ValueError, match="forbidden legacy keys"):
        assert_canonical_cutover_signal(payload)


def test_recursive_walker_accepts_value_equal_to_forbidden_name() -> None:
    """Key-only invariant: a string VALUE equal to ``feature_slug`` is
    accepted; only KEY hits fail."""

    payload = _canonical_payload(
        payload={
            "mission_slug": "mission-001",
            "description": "see feature_slug docs",
            "tags": ["feature_slug", "feature_number", "mission_key"],
        },
    )

    assert forbidden_legacy_keys(payload) == set()
    assert not is_pre_cutover_payload(payload)
    # Should not raise — clean envelope by the key-only invariant.
    assert_canonical_cutover_signal(payload)


def test_legacy_top_level_helper_remains_internal_diagnostic() -> None:
    """The deprecated top-level-only helper still exists for
    diagnostics; it must NOT find the deeply nested key (that's why
    it's deprecated and replaced by the recursive form)."""

    from spec_kitty_events.cutover import _legacy_top_level_forbidden_check

    payload = _canonical_payload(
        payload={
            "mission_slug": "mission-001",
            "metadata": {"feature_slug": "deep"},
        },
    )

    # Deprecated helper only sees top-level + payload-level keys.
    assert _legacy_top_level_forbidden_check(payload) == set()
    # Public recursive helper does see it.
    assert "feature_slug" in forbidden_legacy_keys(payload)
