"""Conformance tests for Connector lifecycle event contracts (FR-008, FR-009, FR-010).

Covers:
- Valid fixture validation (6 cases) -> ConformanceResult(valid=True)
- Invalid fixture rejection (4 cases) -> ConformanceResult(valid=False) with model_violations
- Connector replay stream validation + golden reducer output comparison
- Schema drift checks for connector payload models
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from spec_kitty_events.conformance import (
    load_fixtures,
    load_replay_stream,
    validate_event,
)
from spec_kitty_events.connector import (
    ConnectorDegradedPayload,
    ConnectorHealthCheckedPayload,
    ConnectorProvisionedPayload,
    ConnectorReconnectedPayload,
    ConnectorRevokedPayload,
    reduce_connector_events,
)
from spec_kitty_events.models import Event

# ---------------------------------------------------------------------------
# Load fixture cases at module level (parametrize at collection time)
# ---------------------------------------------------------------------------

_CONN_CASES = load_fixtures("connector")
_VALID_CASES = [c for c in _CONN_CASES if c.expected_valid]
_INVALID_CASES = [c for c in _CONN_CASES if not c.expected_valid]

_FIXTURES_DIR = (
    Path(__file__).parent.parent
    / "src"
    / "spec_kitty_events"
    / "conformance"
    / "fixtures"
)


# ---------------------------------------------------------------------------
# Section 1 -- Valid fixture validation (6 cases)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("case", _VALID_CASES, ids=[c.id for c in _VALID_CASES])
def test_valid_fixture_passes_conformance(case: object) -> None:
    """All valid Connector fixtures must pass dual-layer conformance validation."""
    from spec_kitty_events.conformance.loader import FixtureCase

    assert isinstance(case, FixtureCase)
    result = validate_event(case.payload, case.event_type, strict=True)
    assert result.valid, (
        f"Fixture {case.id} should be valid but got violations:\n"
        f"Model: {result.model_violations}\n"
        f"Schema: {result.schema_violations}"
    )


# ---------------------------------------------------------------------------
# Section 2 -- Invalid fixture rejection (4 cases)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("case", _INVALID_CASES, ids=[c.id for c in _INVALID_CASES])
def test_invalid_fixture_fails_conformance(case: object) -> None:
    """All invalid Connector fixtures must produce at least one model_violation."""
    from spec_kitty_events.conformance.loader import FixtureCase

    assert isinstance(case, FixtureCase)
    result = validate_event(case.payload, case.event_type, strict=True)
    assert not result.valid, (
        f"Fixture {case.id} should be invalid but passed validation"
    )
    assert len(result.model_violations) >= 1, (
        f"Fixture {case.id} is invalid but no model_violations were reported"
    )


# ---------------------------------------------------------------------------
# Section 3 -- Fixture count assertions
# ---------------------------------------------------------------------------


def test_connector_fixture_count() -> None:
    """load_fixtures('connector') must return exactly 10 cases (6 valid + 4 invalid)."""
    assert len(_CONN_CASES) == 10


def test_connector_valid_case_count() -> None:
    """Must have exactly 6 valid Connector fixture cases."""
    assert len(_VALID_CASES) == 6


def test_connector_invalid_case_count() -> None:
    """Must have exactly 4 invalid Connector fixture cases."""
    assert len(_INVALID_CASES) == 4


# ---------------------------------------------------------------------------
# Section 4 -- Replay stream validation + golden comparison
# ---------------------------------------------------------------------------


def test_connector_replay_stream_validates_and_matches_golden() -> None:
    """Each JSONL line validates; connector reducer output matches committed golden file."""
    stream_id = "connector-lifecycle-full"
    output_id = "connector-lifecycle-full-output"

    raw = load_replay_stream(stream_id)
    # Validate each event's payload
    for event_dict in raw:
        event_type = event_dict["event_type"]
        payload = event_dict["payload"]
        result = validate_event(payload, event_type, strict=True)
        assert result.valid, (
            f"Event {event_dict['event_id']!r} in stream {stream_id!r} "
            f"failed validation: {result.model_violations}"
        )

    # Reduce to state
    events = [Event(**e) for e in raw]
    state = reduce_connector_events(events)
    actual = state.model_dump(mode="json")

    # Load golden file from manifest
    from spec_kitty_events.conformance.loader import (
        _FIXTURES_DIR as FIXTURES_DIR,
        _MANIFEST_PATH,
    )

    manifest = json.loads(_MANIFEST_PATH.read_text())
    golden_entry = next(
        (e for e in manifest["fixtures"] if e["id"] == output_id), None
    )
    assert golden_entry is not None, f"Golden manifest entry not found: {output_id}"
    golden_path = FIXTURES_DIR / golden_entry["path"]
    assert golden_path.exists(), f"Golden file not found: {golden_path}"
    expected = json.loads(golden_path.read_text())
    assert actual == expected, (
        f"Reducer output for {stream_id!r} does not match golden file {golden_path}.\n"
        f"Actual: {json.dumps(actual, sort_keys=True, indent=2)}\n"
        f"Expected: {json.dumps(expected, sort_keys=True, indent=2)}"
    )


# ---------------------------------------------------------------------------
# Section 5 -- Schema drift checks
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "model_class,schema_name",
    [
        (ConnectorProvisionedPayload, "connector_provisioned_payload"),
        (ConnectorHealthCheckedPayload, "connector_health_checked_payload"),
        (ConnectorDegradedPayload, "connector_degraded_payload"),
        (ConnectorRevokedPayload, "connector_revoked_payload"),
        (ConnectorReconnectedPayload, "connector_reconnected_payload"),
    ],
    ids=["provisioned", "health_checked", "degraded", "revoked", "reconnected"],
)
def test_schema_drift(model_class: type, schema_name: str) -> None:
    """Generated schema must match the committed JSON schema file (no drift)."""
    from spec_kitty_events.schemas import load_schema
    from spec_kitty_events.schemas.generate import generate_schema

    generated = generate_schema(schema_name, model_class)
    committed = load_schema(schema_name)
    assert generated == committed, (
        f"Schema drift detected for {schema_name}!\n"
        f"Generated keys: {sorted(generated.keys())}\n"
        f"Committed keys: {sorted(committed.keys())}"
    )
