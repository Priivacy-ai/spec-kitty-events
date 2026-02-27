"""Conformance tests for DecisionPoint lifecycle event contracts (FR-004, FR-005, FR-006).

Covers:
- Valid fixture validation (8 cases) -> ConformanceResult(valid=True)
- Invalid fixture rejection (6 cases) -> ConformanceResult(valid=False) with model_violations
- Invalid fixtures include authority-policy and missing audit field failures
- Replay stream validation + golden reducer output comparison (3 streams)
- Schema drift checks (4 payload models)
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

import pytest

from spec_kitty_events.conformance import (
    load_fixtures,
    load_replay_stream,
    validate_event,
)
from spec_kitty_events.decisionpoint import (
    DecisionPointDiscussingPayload,
    DecisionPointOpenedPayload,
    DecisionPointOverriddenPayload,
    DecisionPointResolvedPayload,
    reduce_decision_point_events,
)
from spec_kitty_events.models import Event

# ---------------------------------------------------------------------------
# Load fixture cases at module level (parametrize at collection time)
# ---------------------------------------------------------------------------

_DP_CASES = load_fixtures("decisionpoint")
_VALID_CASES = [c for c in _DP_CASES if c.expected_valid]
_INVALID_CASES = [c for c in _DP_CASES if not c.expected_valid]

_FIXTURES_DIR = (
    Path(__file__).parent.parent
    / "src"
    / "spec_kitty_events"
    / "conformance"
    / "fixtures"
)


# ---------------------------------------------------------------------------
# Section 1 -- Valid fixture validation (8 cases)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("case", _VALID_CASES, ids=[c.id for c in _VALID_CASES])
def test_valid_fixture_passes_conformance(case: object) -> None:
    """All valid DecisionPoint fixtures must pass dual-layer conformance validation."""
    from spec_kitty_events.conformance.loader import FixtureCase

    assert isinstance(case, FixtureCase)
    result = validate_event(case.payload, case.event_type, strict=True)
    assert result.valid, (
        f"Fixture {case.id} should be valid but got violations:\n"
        f"Model: {result.model_violations}\n"
        f"Schema: {result.schema_violations}"
    )


# ---------------------------------------------------------------------------
# Section 2 -- Invalid fixture rejection (6 cases)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("case", _INVALID_CASES, ids=[c.id for c in _INVALID_CASES])
def test_invalid_fixture_fails_conformance(case: object) -> None:
    """All invalid DecisionPoint fixtures must produce at least one model_violation."""
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


def test_decisionpoint_fixture_count() -> None:
    """load_fixtures('decisionpoint') must return exactly 14 cases (8 valid + 6 invalid)."""
    assert len(_DP_CASES) == 14


def test_decisionpoint_valid_case_count() -> None:
    """Must have exactly 8 valid DecisionPoint fixture cases."""
    assert len(_VALID_CASES) == 8


def test_decisionpoint_invalid_case_count() -> None:
    """Must have exactly 6 invalid DecisionPoint fixture cases."""
    assert len(_INVALID_CASES) == 6


# ---------------------------------------------------------------------------
# Section 4 -- Replay stream validation + golden comparison
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "stream_id,output_id",
    [
        (
            "decisionpoint-replay-full-lifecycle",
            "decisionpoint-replay-full-lifecycle-output",
        ),
        (
            "decisionpoint-replay-open-resolved",
            "decisionpoint-replay-open-resolved-output",
        ),
        (
            "decisionpoint-replay-with-anomaly",
            "decisionpoint-replay-with-anomaly-output",
        ),
    ],
)
def test_replay_stream_validates_and_matches_golden(
    stream_id: str, output_id: str
) -> None:
    """Each JSONL line validates; reducer output matches committed golden file."""
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
    state = reduce_decision_point_events(events)
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
# Section 5 -- Schema drift checks (4 payload models)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "model_class,schema_name",
    [
        (DecisionPointOpenedPayload, "decision_point_opened_payload"),
        (DecisionPointDiscussingPayload, "decision_point_discussing_payload"),
        (DecisionPointResolvedPayload, "decision_point_resolved_payload"),
        (DecisionPointOverriddenPayload, "decision_point_overridden_payload"),
    ],
    ids=["opened", "discussing", "resolved", "overridden"],
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
