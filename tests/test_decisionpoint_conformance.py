"""Conformance tests for DecisionPoint lifecycle event contracts (FR-004, FR-005, FR-006).

Covers:
- Valid fixture validation (18 cases: 8 legacy ADR + 10 V1) -> ConformanceResult(valid=True)
- Invalid fixture rejection (11 cases: 6 legacy + 5 V1) -> ConformanceResult(valid=False)
- Invalid fixtures include authority-policy, missing audit field, and V1 cross-field failures
- Replay stream validation + golden reducer output comparison (3 streams)
- Schema drift checks (5 payload models including V1 Widened)
- V1-specific conformance: valid fixtures pass both schema and Pydantic (T021)
- V1-specific conformance: invalid fixtures fail schema or Pydantic (T021)
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
    DecisionPointWidenedPayload,
    DecisionPointResolvedInterviewPayload,
    _OPENED_ADAPTER,
    _DISCUSSING_ADAPTER,
    _RESOLVED_ADAPTER,
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

# V1 fixture IDs (for targeted parametrize lists)
_V1_VALID_IDS = [
    "decisionpoint-v1-opened-adr-valid",
    "decisionpoint-v1-opened-interview-valid",
    "decisionpoint-v1-widened-valid",
    "decisionpoint-v1-discussing-interview-valid",
    "decisionpoint-v1-resolved-interview-resolved-valid",
    "decisionpoint-v1-resolved-interview-resolved-other-valid",
    "decisionpoint-v1-resolved-interview-deferred-valid",
    "decisionpoint-v1-resolved-interview-canceled-valid",
    "decisionpoint-v1-resolved-interview-closed-locally-valid",
    "decisionpoint-v1-participant-identity-external-refs-valid",
]

_V1_INVALID_IDS = [
    "decisionpoint-v1-resolved-missing-terminal-outcome",
    "decisionpoint-v1-widened-missing-thread-ref",
    "decisionpoint-v1-opened-interview-missing-origin-flow",
    "decisionpoint-v1-participant-identity-empty-external-refs",
    "decisionpoint-v1-resolved-interview-deferred-with-final-answer",
]

_V1_VALID_CASES = [c for c in _VALID_CASES if c.id in _V1_VALID_IDS]
_V1_INVALID_CASES = [c for c in _INVALID_CASES if c.id in _V1_INVALID_IDS]


# ---------------------------------------------------------------------------
# Section 1 -- Valid fixture validation (all cases)
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
# Section 2 -- Invalid fixture rejection (all cases)
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
    assert len(result.model_violations) >= 1 or len(result.schema_violations) >= 1, (
        f"Fixture {case.id} is invalid but no violations were reported"
    )


# ---------------------------------------------------------------------------
# Section 3 -- Fixture count assertions
# ---------------------------------------------------------------------------


def test_decisionpoint_fixture_count() -> None:
    """load_fixtures('decisionpoint') must return at least 29 cases (18 valid + 11 invalid)."""
    assert len(_DP_CASES) >= 29


def test_decisionpoint_valid_case_count() -> None:
    """Must have at least 18 valid DecisionPoint fixture cases (8 legacy ADR + 10 V1)."""
    assert len(_VALID_CASES) >= 18


def test_decisionpoint_invalid_case_count() -> None:
    """Must have at least 11 invalid DecisionPoint fixture cases (6 legacy + 5 V1)."""
    assert len(_INVALID_CASES) >= 11


def test_v1_valid_fixture_count() -> None:
    """Must have exactly 10 V1 valid fixture cases."""
    assert len(_V1_VALID_CASES) == 10, (
        f"Expected 10 V1 valid fixtures, got {len(_V1_VALID_CASES)}: "
        f"{[c.id for c in _V1_VALID_CASES]}"
    )


def test_v1_invalid_fixture_count() -> None:
    """Must have exactly 5 V1 invalid fixture cases."""
    assert len(_V1_INVALID_CASES) == 5, (
        f"Expected 5 V1 invalid fixtures, got {len(_V1_INVALID_CASES)}: "
        f"{[c.id for c in _V1_INVALID_CASES]}"
    )


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
        result = validate_event(event_dict, event_type, strict=True)
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
# Section 5 -- Schema drift checks (5 payload models)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "adapter_or_model,schema_name",
    [
        (_OPENED_ADAPTER, "decision_point_opened_payload"),
        (_DISCUSSING_ADAPTER, "decision_point_discussing_payload"),
        (_RESOLVED_ADAPTER, "decision_point_resolved_payload"),
        (DecisionPointOverriddenPayload, "decision_point_overridden_payload"),
        (DecisionPointWidenedPayload, "decision_point_widened_payload"),
    ],
    ids=["opened", "discussing", "resolved", "overridden", "widened"],
)
def test_schema_drift(adapter_or_model: Any, schema_name: str) -> None:
    """Generated schema must match the committed JSON schema file (no drift)."""
    from pydantic import TypeAdapter
    from spec_kitty_events.schemas import load_schema

    if isinstance(adapter_or_model, TypeAdapter):
        # Discriminated union — use TypeAdapter.json_schema()
        generated = adapter_or_model.json_schema(mode="serialization")
    else:
        # Concrete Pydantic model
        generated = adapter_or_model.model_json_schema(mode="serialization")

    generated["$schema"] = "https://json-schema.org/draft/2020-12/schema"
    generated["$id"] = f"spec-kitty-events/{schema_name}"

    committed = load_schema(schema_name)
    assert generated == committed, (
        f"Schema drift detected for {schema_name}!\n"
        f"Generated keys: {sorted(generated.keys())}\n"
        f"Committed keys: {sorted(committed.keys())}"
    )


# ---------------------------------------------------------------------------
# Section 6 -- T021: V1 valid fixtures pass both schema AND Pydantic
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "case", _V1_VALID_CASES, ids=[c.id for c in _V1_VALID_CASES]
)
def test_v1_valid_fixture_passes_both_schema_and_pydantic(case: object) -> None:
    """Each V1 valid fixture must validate against its JSON Schema AND its Pydantic model."""
    from spec_kitty_events.conformance.loader import FixtureCase

    assert isinstance(case, FixtureCase)
    result = validate_event(case.payload, case.event_type, strict=True)
    assert result.valid, (
        f"V1 fixture {case.id} should be valid but got violations:\n"
        f"Model: {result.model_violations}\n"
        f"Schema: {result.schema_violations}"
    )
    # Verify schema check was not skipped
    assert not result.schema_check_skipped, (
        f"V1 fixture {case.id}: schema validation was skipped (jsonschema not installed?)"
    )
    # Verify no model violations (Pydantic layer)
    assert len(result.model_violations) == 0, (
        f"V1 fixture {case.id}: Pydantic validation failed: {result.model_violations}"
    )
    # Verify no schema violations (JSON Schema layer)
    assert len(result.schema_violations) == 0, (
        f"V1 fixture {case.id}: JSON Schema validation failed: {result.schema_violations}"
    )


# ---------------------------------------------------------------------------
# Section 7 -- T021: V1 invalid fixtures fail schema or Pydantic
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "case",
    [c for c in _V1_INVALID_CASES if c.id != "decisionpoint-v1-resolved-interview-deferred-with-final-answer"],
    ids=[c.id for c in _V1_INVALID_CASES if c.id != "decisionpoint-v1-resolved-interview-deferred-with-final-answer"],
)
def test_v1_invalid_fixture_fails_schema(case: object) -> None:
    """Each V1 invalid fixture (except cross-field case) must fail schema or Pydantic validation."""
    from spec_kitty_events.conformance.loader import FixtureCase

    assert isinstance(case, FixtureCase)
    result = validate_event(case.payload, case.event_type, strict=True)
    assert not result.valid, (
        f"V1 fixture {case.id} should be invalid but passed validation"
    )
    assert len(result.model_violations) >= 1 or len(result.schema_violations) >= 1, (
        f"V1 fixture {case.id} is invalid but no violations were reported"
    )


def test_v1_resolved_interview_deferred_with_final_answer_rejected() -> None:
    """Cross-field invalid fixture must be rejected by Pydantic model_validate.

    The JSON Schema may or may not catch this cross-field rule (depends on whether
    Pydantic emitted if/then/else constraints). Regardless, Pydantic must reject it.
    """
    import jsonschema
    from pydantic import ValidationError
    from spec_kitty_events.schemas import load_schema

    fixture_path = (
        _FIXTURES_DIR
        / "decisionpoint"
        / "invalid"
        / "v1_resolved_interview_deferred_with_final_answer.json"
    )
    assert fixture_path.exists(), f"Fixture not found: {fixture_path}"
    payload = json.loads(fixture_path.read_text())

    # Remove __comment key before validation
    validation_payload = {k: v for k, v in payload.items() if k != "__comment"}

    # Pydantic MUST reject it (cross-field rule)
    with pytest.raises(ValidationError) as exc_info:
        DecisionPointResolvedInterviewPayload.model_validate(validation_payload)

    errors = exc_info.value.errors()
    error_fields = {".".join(str(loc) for loc in e["loc"]) for e in errors}
    error_messages = " ".join(e["msg"] for e in errors)

    # Must mention final_answer or terminal_outcome in the rejection
    assert (
        any("final_answer" in f or "terminal_outcome" in f for f in error_fields)
        or "final_answer" in error_messages
        or "terminal_outcome" in error_messages
    ), (
        f"Expected error mentioning final_answer or terminal_outcome, "
        f"but got: fields={error_fields}, messages={error_messages}"
    )

    # JSON Schema path: may or may not reject (document the behavior)
    schema = load_schema("decision_point_resolved_payload")
    validator = jsonschema.Draft202012Validator(schema)
    schema_valid = validator.is_valid(validation_payload)
    # We accept either outcome from JSON Schema; the Pydantic check above is authoritative
    # If schema rejects it too, that's a bonus — both are correct behavior
    _ = schema_valid  # explicit: we don't assert on schema_valid here
