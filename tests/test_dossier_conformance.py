"""Tests for dossier event contract conformance (T020, T021, T022).

Covers spec §7.6 conformance categories:
- Missing-artifact anomaly detection
- Parity drift detection
- Namespace collision prevention
- Round-trip schema conformance
"""
from __future__ import annotations

import pytest

from spec_kitty_events.conformance import (
    load_fixtures,
    load_replay_stream,
    validate_event,
)

# ---------------------------------------------------------------------------
# T020: Fixture-driven parametrized conformance tests
# ---------------------------------------------------------------------------

_DOSSIER_CASES = load_fixtures("dossier")
_VALID_CASES = [c for c in _DOSSIER_CASES if c.expected_valid]
_INVALID_CASES = [c for c in _DOSSIER_CASES if not c.expected_valid]


@pytest.mark.parametrize("case", _VALID_CASES, ids=[c.id for c in _VALID_CASES])
def test_valid_fixture_passes_conformance(case: object) -> None:
    """All valid dossier fixtures must pass dual-layer conformance validation."""
    from spec_kitty_events.conformance.loader import FixtureCase
    assert isinstance(case, FixtureCase)
    result = validate_event(case.payload, case.event_type, strict=True)
    assert result.valid, (
        f"Fixture {case.id} should be valid but got violations:\n"
        f"Model: {result.model_violations}\n"
        f"Schema: {result.schema_violations}"
    )


@pytest.mark.parametrize("case", _INVALID_CASES, ids=[c.id for c in _INVALID_CASES])
def test_invalid_fixture_fails_conformance(case: object) -> None:
    """All invalid dossier fixtures must produce at least one violation."""
    from spec_kitty_events.conformance.loader import FixtureCase
    assert isinstance(case, FixtureCase)
    result = validate_event(case.payload, case.event_type, strict=True)
    assert not result.valid, (
        f"Fixture {case.id} should be invalid but passed validation"
    )
    total_violations = len(result.model_violations) + len(result.schema_violations)
    assert total_violations >= 1, (
        f"Fixture {case.id} is invalid but no violations were reported"
    )


# ---------------------------------------------------------------------------
# T021: Category coverage — 13 cases + 2 replay streams loadable
# ---------------------------------------------------------------------------


def test_dossier_fixture_count() -> None:
    """Loader must return exactly 13 dossier fixture cases (not replay streams)."""
    cases = load_fixtures("dossier")
    assert len(cases) == 13, f"Expected 13 cases, got {len(cases)}"


def test_dossier_valid_case_count() -> None:
    """Loader must return exactly 10 valid dossier fixture cases."""
    assert len(_VALID_CASES) == 10, (
        f"Expected 10 valid cases, got {len(_VALID_CASES)}: "
        f"{[c.id for c in _VALID_CASES]}"
    )


def test_dossier_invalid_case_count() -> None:
    """Loader must return exactly 3 invalid dossier fixture cases."""
    assert len(_INVALID_CASES) == 3, (
        f"Expected 3 invalid cases, got {len(_INVALID_CASES)}: "
        f"{[c.id for c in _INVALID_CASES]}"
    )


def test_happy_path_replay_stream_loads() -> None:
    """Happy-path replay stream loads without error and has sufficient events."""
    events = load_replay_stream("dossier-replay-happy-path")
    assert len(events) >= 5, f"Happy path stream too short: {len(events)} events"
    assert all("event_type" in e for e in events)


def test_drift_scenario_replay_stream_loads() -> None:
    """Drift scenario replay stream loads without error and has sufficient events."""
    events = load_replay_stream("dossier-replay-drift-scenario")
    assert len(events) >= 4, f"Drift stream too short: {len(events)} events"
    assert all("event_type" in e for e in events)


def test_happy_path_replay_stream_has_expected_count() -> None:
    """Happy-path stream must have exactly 6 events per manifest notes."""
    events = load_replay_stream("dossier-replay-happy-path")
    assert len(events) == 6, f"Expected 6 events, got {len(events)}"


def test_drift_scenario_replay_stream_has_expected_count() -> None:
    """Drift scenario stream must have exactly 5 events per manifest notes."""
    events = load_replay_stream("dossier-replay-drift-scenario")
    assert len(events) == 5, f"Expected 5 events, got {len(events)}"


# ---------------------------------------------------------------------------
# T022: Round-trip schema conformance — both layers checked
# ---------------------------------------------------------------------------


def test_valid_fixtures_pass_both_layers() -> None:
    """Valid fixtures must produce zero model AND zero schema violations."""
    for case in _VALID_CASES:
        result = validate_event(case.payload, case.event_type, strict=True)
        assert len(result.model_violations) == 0, (
            f"{case.id}: unexpected model violations: {result.model_violations}"
        )
        assert not result.schema_check_skipped, (
            f"{case.id}: schema layer was skipped; install conformance extras"
        )
        assert len(result.schema_violations) == 0, (
            f"{case.id}: unexpected schema violations: {result.schema_violations}"
        )


def test_invalid_fixtures_produce_violations_in_at_least_one_layer() -> None:
    """Invalid fixtures must produce >= 1 violation in model OR schema layer."""
    for case in _INVALID_CASES:
        result = validate_event(case.payload, case.event_type, strict=True)
        total = len(result.model_violations) + len(result.schema_violations)
        assert total >= 1, (
            f"{case.id}: invalid fixture produced zero violations in both layers"
        )


def test_all_valid_fixture_event_types_are_known() -> None:
    """All valid fixture event_types must be recognised by the validator."""
    for case in _VALID_CASES:
        # validate_event raises ValueError for unknown types;
        # if it returns a result the type is known
        result = validate_event(case.payload, case.event_type, strict=True)
        assert result.event_type == case.event_type
