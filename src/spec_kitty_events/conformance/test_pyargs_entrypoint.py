"""Conformance test suite for spec-kitty-events.

Run: pytest --pyargs spec_kitty_events.conformance
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

import pytest

from spec_kitty_events.conformance.pytest_helpers import (
    assert_lane_mapping,
)
from spec_kitty_events.conformance.validators import (
    _EVENT_TYPE_TO_MODEL,
    validate_event,
)
from spec_kitty_events.schemas import list_schemas, load_schema
from spec_kitty_events.status import Lane, SyncLaneV1, CANONICAL_TO_SYNC_V1
from spec_kitty_events.validation_errors import ValidationErrorCode


# --- Manifest-driven fixture tests ---

_FIXTURES_DIR = Path(__file__).parent / "fixtures"
_MANIFEST: Dict[str, Any] = json.loads(
    (_FIXTURES_DIR / "manifest.json").read_text(encoding="utf-8")
)


# Wrapper-shape detection (mission canonical-producer-contracts-legacy-envelope-01KS7JM3).
# Class-taxonomy and historical-row fixtures use a wrapper schema
# {class, expected, input, notes, [expected_error_code, expected_reason,
# legacy_shape]}. The raw event lives under .input. The pyargs test must
# extract input before calling validate_event; otherwise the wrapper keys
# (class, expected, notes, ...) appear as extras on the model and cause false
# failures.
_WRAPPER_KEYS = frozenset(
    {
        "class",
        "expected",
        "input",
        "notes",
        "expected_error_code",
        "expected_reason",
        "legacy_shape",
    }
)


def _is_wrapper_shape(obj: Any) -> bool:
    """Return True if obj is a class_taxonomy / historical_row / legacy /
    similar wrapper that nests the actual event envelope under ``.input``.
    """
    return (
        isinstance(obj, dict)
        and "input" in obj
        and isinstance(obj["input"], dict)
        and obj.keys() <= _WRAPPER_KEYS
    )


def _event_fixture_entries() -> List[Dict[str, Any]]:
    """Return manifest entries that are event-type fixtures.

    Excludes:
    - LaneMapping fixtures (handled by lane-mapping parametrized tests).
    - Special fixture_type kinds (replay_stream, reducer_output,
      timestamp_semantics) that are not raw envelope payloads to validate.
    - Forbidden-key class fixtures: they assert rejection with code
      FORBIDDEN_KEY from the recursive walker
      (forbidden_keys.find_forbidden_keys), enforced by the strict profile;
      the shipped assertion lives in
      test_strict_profile_rejects_forbidden_key_class_fixtures below --
      this generic, lenient entrypoint does not run the walker.
    - Cutover-boundary strict-profile fixtures
      (cutover_boundary/rejected_by_strict_profile/): they assert
      validate_strict_envelope rejections on envelopes that validate_event
      deliberately accepts since 8.0.0 removed the cutover gate; routing
      them through this generic test would produce false failures.
    - Diagnostic-taxonomy fixtures whose event_type is a sentinel (e.g.
      "<missing>", "<wrong>") used only to label the class; the
      class-taxonomy suite asserts on them via a different code path.
    - zeitgeist_attrs codec documents (E2): a document there is a
      {payload, expected_attrs, envelope?} codec specification, not an
      event envelope — validating the document itself as its named event
      would fail every entry. Both codec directions are exercised by
      test_zeitgeist_attrs_codec.py (packaged, alongside this module) and
      by tests/test_zeitgeist_attrs_conformance.py (in-repo only), both via
      load_fixtures("zeitgeist_attrs").
    """

    def _included(f: dict[str, Any]) -> bool:
        if f["event_type"] == "LaneMapping":
            return False
        if f["path"].startswith("zeitgeist_attrs/"):
            return False
        if f.get("fixture_type") in (
            "replay_stream",
            "reducer_output",
            "timestamp_semantics",
            # envelope_strict_journal (F1-T1) class_taxonomy fixtures: these
            # assert strict-profile-only rejections (e.g. an envelope-level
            # extra key, a naive timestamp) that the lenient Event model /
            # validate_event() deliberately do NOT reject (decision 3,
            # COMPATIBILITY.md) -- routing them through this generic,
            # weaker-validator entrypoint would produce false failures (or
            # false passes that test nothing). They are validated by
            # spec_kitty_events.strict.validate_strict_envelope in
            # tests/test_envelope_strict_journal_class.py instead.
            "strict_profile_only",
        ):
            return False
        if f["path"].startswith("class_taxonomy/envelope_invalid_forbidden_key/"):
            return False
        if f["path"].startswith("cutover_boundary/rejected_by_strict_profile/"):
            return False
        return f["event_type"] in _EVENT_TYPE_TO_MODEL

    return [f for f in _MANIFEST["fixtures"] if _included(f)]


def _event_fixture_ids() -> List[str]:
    return [f["id"] for f in _event_fixture_entries()]


def test_zeitgeist_attrs_codec_fixtures_stay_out_of_the_event_gate() -> None:
    """Regression guard for the zeitgeist_attrs exclusion above.

    The filter is load-bearing for every downstream consumer: if it regresses,
    both the in-repo suite and the packaged
    ``test_zeitgeist_attrs_codec.py`` runner stay green (they read codec
    documents through ``load_fixtures("zeitgeist_attrs")`` and never collect
    this module's event tests against them) while ``pytest --pyargs
    spec_kitty_events.conformance`` fails every codec entry by validating a
    ``{payload, expected_attrs}`` document as an event envelope. Both halves
    are pinned: the category exists in the manifest, and none of it is
    collected here.
    """
    manifest_paths = {
        f["path"] for f in _MANIFEST["fixtures"] if f["path"].startswith("zeitgeist_attrs/")
    }
    assert manifest_paths, (
        "zeitgeist_attrs codec fixtures vanished from the manifest; if the "
        "category was renamed on purpose, update this guard with it"
    )
    collected_paths = {f["path"] for f in _event_fixture_entries()}
    leaked = sorted(manifest_paths & collected_paths)
    assert not leaked, (
        "codec fixtures reached the event gate; validating them as envelopes "
        "turns the packaged conformance entrypoint red for every consumer: "
        f"{leaked}"
    )


def _event_fixture_params() -> List[Dict[str, Any]]:
    params: List[Dict[str, Any]] = []
    for entry in _event_fixture_entries():
        fixture_path = _FIXTURES_DIR / entry["path"]
        payload: Any = json.loads(fixture_path.read_text(encoding="utf-8"))
        if _is_wrapper_shape(payload):
            payload = payload["input"]
        params.append({**entry, "payload": payload})
    return params


def _lane_mapping_fixture_entries() -> List[Dict[str, Any]]:
    """Return manifest entries for lane mapping fixtures."""
    return [f for f in _MANIFEST["fixtures"] if f["event_type"] == "LaneMapping"]


def _lane_mapping_fixture_ids() -> List[str]:
    return [f["id"] for f in _lane_mapping_fixture_entries()]


def _lane_mapping_fixture_params() -> List[Dict[str, Any]]:
    params: List[Dict[str, Any]] = []
    for entry in _lane_mapping_fixture_entries():
        fixture_path = _FIXTURES_DIR / entry["path"]
        payload: Any = json.loads(fixture_path.read_text(encoding="utf-8"))
        params.append({**entry, "payload": payload})
    return params


# --- Event fixture conformance tests ---


@pytest.mark.parametrize("case", _event_fixture_params(), ids=_event_fixture_ids())
def test_fixture_conformance(case: Dict[str, Any]) -> None:
    """Validate each event fixture against its expected result.

    Uses dual-layer validation. For expected-valid fixtures the Pydantic
    model layer must pass; schema-only violations (e.g. alias values
    that Pydantic normalises but JSON Schema rejects) are permitted.
    For expected-invalid fixtures both layers are checked.
    """
    result = validate_event(case["payload"], case["event_type"])
    if case["expected_result"] == "valid":
        # Pydantic model layer must accept the payload
        if result.model_violations:
            violations = [f"  Model: {v.field} \u2014 {v.message}" for v in result.model_violations]
            raise AssertionError(
                f"Payload for {case['event_type']!r} (fixture {case['id']}) "
                f"failed model conformance:\n" + "\n".join(violations)
            )
    else:
        # At least one layer must reject the payload
        if result.valid:
            raise AssertionError(
                f"Payload for {case['event_type']!r} (fixture {case['id']}) "
                f"was expected to fail but passed conformance."
            )


# --- Lane mapping fixture conformance tests ---


@pytest.mark.parametrize("case", _lane_mapping_fixture_params(), ids=_lane_mapping_fixture_ids())
def test_lane_mapping_fixture_conformance(case: Dict[str, Any]) -> None:
    """Validate lane mapping fixtures against expected results."""
    mappings: Any = case["payload"]
    assert isinstance(mappings, list), f"Lane mapping fixture {case['id']} payload must be a list"
    if case["expected_result"] == "valid":
        for mapping in mappings:
            assert_lane_mapping(mapping["canonical"], mapping["expected_sync"])
    else:
        # Invalid lane mapping: at least one entry should fail
        failures = 0
        for mapping in mappings:
            try:
                Lane(mapping["canonical"])
            except ValueError:
                failures += 1
        assert failures > 0, (
            f"Lane mapping fixture {case['id']} expected invalid entries "
            f"but all passed Lane construction"
        )


# --- Lane mapping completeness tests ---


def test_lane_mapping_v1_completeness() -> None:
    """All canonical lanes have a sync mapping."""
    assert set(CANONICAL_TO_SYNC_V1.keys()) == set(Lane)


def test_lane_mapping_v1_output_type() -> None:
    """All mapping outputs are SyncLaneV1 members."""
    for sync_lane in CANONICAL_TO_SYNC_V1.values():
        assert isinstance(sync_lane, SyncLaneV1)


@pytest.mark.parametrize("lane", list(Lane), ids=[each.value for each in Lane])
def test_lane_mapping_v1_each_lane(lane: Lane) -> None:
    """Each canonical lane maps to a SyncLaneV1."""
    result = CANONICAL_TO_SYNC_V1[lane]
    assert isinstance(result, SyncLaneV1)


# --- Schema integrity tests ---


def test_all_schemas_present() -> None:
    """All expected schemas exist."""
    schemas = list_schemas()
    assert len(schemas) >= 11


@pytest.mark.parametrize("name", list_schemas())
def test_schema_is_valid_json_schema(name: str) -> None:
    """Each schema file is a valid JSON Schema document."""
    schema = load_schema(name)
    assert "$schema" in schema
    assert "$id" in schema


# --- Cutover-boundary conformance tests (8.0.0) ---
#
# 8.0.0 deleted spec_kitty_events.cutover and with it the envelope-level
# gate validate_event() used to apply (missing/wrong schema_version,
# forbidden legacy keys/names, aggregate prefixes). contracts/
# versioning-and-compatibility.md item 5 ("Required artifacts on a major
# bump") requires fixtures covering that moved accept/reject boundary,
# shipped in this packaged entrypoint -- not only in the repo-only test
# tree, which downstream consumers running
# `pytest --pyargs spec_kitty_events.conformance` never see.
#
# The fixtures live under cutover_boundary/:
#
# - accepted_by_validate_event/: envelopes the removed gate used to reject
#   and validate_event now accepts. Each one differs from the canonical
#   MissionCreated baseline by exactly the moved property.
# - rejected_by_strict_profile/: full strict-profile envelopes (all 14
#   STRICT_ENVELOPE_KEYS) carrying exactly one boundary defect, which
#   validate_strict_envelope must reject with a pinned error-code list.

_ACCEPT_DIR = "cutover_boundary/accepted_by_validate_event/"
_STRICT_REJECT_DIR = "cutover_boundary/rejected_by_strict_profile/"
_FORBIDDEN_KEY_CLASS_DIR = "class_taxonomy/envelope_invalid_forbidden_key/"


def _manifest_entries(path_prefix: str) -> list[dict[str, Any]]:
    return [f for f in _MANIFEST["fixtures"] if f["path"].startswith(path_prefix)]


def _read_fixture(entry: dict[str, Any]) -> dict[str, Any]:
    fixture_path = _FIXTURES_DIR / entry["path"]
    payload: Any = json.loads(fixture_path.read_text(encoding="utf-8"))
    if _is_wrapper_shape(payload):
        payload = payload["input"]
    assert isinstance(payload, dict)
    return payload


@pytest.mark.parametrize(
    "entry",
    _manifest_entries(_ACCEPT_DIR),
    ids=[e["id"] for e in _manifest_entries(_ACCEPT_DIR)],
)
def test_cutover_boundary_accepted_by_validate_event(entry: dict[str, Any]) -> None:
    """Envelopes the removed cutover gate rejected are accepted since 8.0.0.

    Pins the new accept side of the boundary in both validation layers:
    zero model violations AND zero schema violations (the generic
    manifest-driven test above tolerates schema-layer noise for valid
    fixtures; these boundary pins do not).
    """
    payload = _read_fixture(entry)
    result = validate_event(payload, entry["event_type"])
    assert result.valid, (
        f"Fixture {entry['path']} must be accepted by validate_event since "
        f"8.0.0 removed the cutover gate; violations: "
        f"{[v.message for v in result.model_violations]} / "
        f"{[v.message for v in result.schema_violations]}"
    )
    assert not result.model_violations
    assert not result.schema_violations


@pytest.mark.parametrize(
    "entry",
    _manifest_entries(_STRICT_REJECT_DIR),
    ids=[e["id"] for e in _manifest_entries(_STRICT_REJECT_DIR)],
)
def test_cutover_boundary_rejected_by_strict_profile(entry: dict[str, Any]) -> None:
    """validate_strict_envelope still fails closed on the moved boundary.

    The fixture file carries ``expected_error_codes`` -- the exact,
    deterministic code list validate_strict_envelope returns for that
    single-defect envelope -- and the assertion is equality, so an
    envelope that starts failing for some additional reason fails here.
    """
    from spec_kitty_events.strict import validate_strict_envelope

    fixture_path = _FIXTURES_DIR / entry["path"]
    wrapper: dict[str, Any] = json.loads(fixture_path.read_text(encoding="utf-8"))
    expected_codes = wrapper["expected_error_codes"]
    errors = validate_strict_envelope(wrapper["input"])
    actual_codes = [error.code.value for error in errors]
    assert actual_codes == expected_codes, (
        f"Fixture {entry['path']}: expected strict-profile codes "
        f"{expected_codes}, got {actual_codes}"
    )


@pytest.mark.parametrize(
    "entry",
    [e for e in _MANIFEST["classes"]["entries"] if e["path"].startswith(_FORBIDDEN_KEY_CLASS_DIR)],
    ids=[
        e["id"]
        for e in _MANIFEST["classes"]["entries"]
        if e["path"].startswith(_FORBIDDEN_KEY_CLASS_DIR)
    ],
)
def test_strict_profile_rejects_forbidden_key_class_fixtures(entry: dict[str, Any]) -> None:
    """The forbidden-key class taxonomy stays enforced under the strict profile.

    The four class fixtures carry forbidden legacy keys at top level,
    nested, at depth >= 10, and inside an array element. validate_event()
    does not run the walker since 8.0.0, so their rejection assertion must
    come from validate_strict_envelope -- here in the shipped gate, where
    consumers running `pytest --pyargs` can see it (their envelope shapes
    predate the strict profile's closed key set, so FORBIDDEN_KEY is
    asserted as present rather than as the sole error).
    """
    from spec_kitty_events.strict import validate_strict_envelope

    fixture = _read_fixture(entry)
    errors = validate_strict_envelope(fixture)
    actual_codes = {error.code.value for error in errors}
    assert ValidationErrorCode.FORBIDDEN_KEY.value in actual_codes, (
        f"Fixture {entry['path']} must be rejected with FORBIDDEN_KEY by "
        f"validate_strict_envelope; got {sorted(actual_codes)}"
    )


# --- Round-trip serialization tests ---


def test_event_round_trip() -> None:
    """Event model round-trips through JSON."""
    from datetime import datetime, timezone
    from uuid import UUID

    from spec_kitty_events.models import Event

    event = Event(
        event_id="01JMXXXXXXXXXXXXXXXXXXXXXX",
        event_type="TestEvent",
        aggregate_id="agg-001",
        timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc),
        build_id="build-test-conformance",
        node_id="node-1",
        lamport_clock=1,
        causation_id=None,
        project_uuid=UUID("550e8400-e29b-41d4-a716-446655440000"),
        project_slug=None,
        correlation_id="01JMYYYYYYYYYYYYYYYYYYYYYY",
    )
    data = event.model_dump(mode="json")
    restored = Event.model_validate(data)
    assert restored == event
