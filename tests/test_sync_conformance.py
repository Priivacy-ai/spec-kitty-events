"""Conformance tests for Sync lifecycle event contracts (FR-008, FR-009, FR-010).

Covers:
- Valid fixture validation (8 cases: 6 sync + 2 external-ref) -> ConformanceResult(valid=True)
- Invalid fixture rejection (4 cases) -> ConformanceResult(valid=False) with model_violations
- Sync replay stream validation + golden reducer output comparison
- Schema drift checks for sync payload models
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
from spec_kitty_events.models import Event
from spec_kitty_events.sync import (
    ExternalReferenceLinkedPayload,
    SyncDeadLetteredPayload,
    SyncIngestAcceptedPayload,
    SyncIngestRejectedPayload,
    SyncReplayCompletedPayload,
    SyncRetryScheduledPayload,
    reduce_sync_events,
)

# ---------------------------------------------------------------------------
# Load fixture cases at module level (parametrize at collection time)
# ---------------------------------------------------------------------------

_SYNC_CASES = load_fixtures("sync")
_VALID_CASES = [c for c in _SYNC_CASES if c.expected_valid]
_INVALID_CASES = [c for c in _SYNC_CASES if not c.expected_valid]

# Separate external-ref cases from sync-specific valid cases
_EXTERNAL_REF_CASES = [c for c in _VALID_CASES if c.event_type == "ExternalReferenceLinked"]
_SYNC_VALID_CASES = [c for c in _VALID_CASES if c.event_type != "ExternalReferenceLinked"]

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
    """All valid sync fixtures (including external-ref) must pass conformance validation."""
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
    """All invalid Sync fixtures must produce at least one model_violation."""
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


def test_sync_fixture_count() -> None:
    """load_fixtures('sync') must return exactly 12 cases (8 valid + 4 invalid).

    8 valid = 6 sync-specific + 2 external-ref-linked.
    """
    assert len(_SYNC_CASES) == 12


def test_sync_valid_case_count() -> None:
    """Must have exactly 8 valid sync fixture cases (6 sync + 2 external-ref)."""
    assert len(_VALID_CASES) == 8


def test_sync_invalid_case_count() -> None:
    """Must have exactly 4 invalid sync fixture cases."""
    assert len(_INVALID_CASES) == 4


def test_external_ref_linked_case_count() -> None:
    """Must have exactly 2 valid external-reference-linked fixture cases."""
    assert len(_EXTERNAL_REF_CASES) == 2


# ---------------------------------------------------------------------------
# Section 4 -- External-reference-linked fixtures pass validation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "case", _EXTERNAL_REF_CASES, ids=[c.id for c in _EXTERNAL_REF_CASES]
)
def test_external_ref_linked_valid(case: object) -> None:
    """Both ExternalReferenceLinked fixtures must pass conformance validation."""
    from spec_kitty_events.conformance.loader import FixtureCase

    assert isinstance(case, FixtureCase)
    result = validate_event(case.payload, case.event_type, strict=True)
    assert result.valid, (
        f"ExternalReferenceLinked fixture {case.id} should be valid but got violations:\n"
        f"Model: {result.model_violations}"
    )


# ---------------------------------------------------------------------------
# Section 5 -- Replay stream validation + golden comparison
# ---------------------------------------------------------------------------


def test_sync_replay_stream_validates_and_matches_golden() -> None:
    """Each JSONL line validates; sync reducer output matches committed golden file."""
    stream_id = "sync-ingest-lifecycle"
    output_id = "sync-ingest-lifecycle-output"

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
    state = reduce_sync_events(events)
    actual = state.model_dump(mode="json")
    # Normalize seen_delivery_pairs for comparison (frozenset -> sorted list)
    actual["seen_delivery_pairs"] = sorted(
        [list(p) for p in actual["seen_delivery_pairs"]]
    )

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
# Section 6 -- Schema drift checks
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "model_class,schema_name",
    [
        (SyncIngestAcceptedPayload, "sync_ingest_accepted_payload"),
        (SyncIngestRejectedPayload, "sync_ingest_rejected_payload"),
        (SyncRetryScheduledPayload, "sync_retry_scheduled_payload"),
        (SyncDeadLetteredPayload, "sync_dead_lettered_payload"),
        (SyncReplayCompletedPayload, "sync_replay_completed_payload"),
        (ExternalReferenceLinkedPayload, "external_reference_linked_payload"),
    ],
    ids=[
        "ingest_accepted",
        "ingest_rejected",
        "retry_scheduled",
        "dead_lettered",
        "replay_completed",
        "external_ref_linked",
    ],
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
