"""Tests for dossier event reducer (T023, T024, T025).

Covers spec §7.6 conformance categories:
- Reducer determinism
- Namespace collision prevention (NamespaceMixedStreamError)
- Deduplication
- Unknown event type silent skip
- Hypothesis property test for permutation invariance
"""
from __future__ import annotations

import json
from typing import Any, Dict, List

import pytest

from spec_kitty_events.conformance import load_replay_stream
from spec_kitty_events.dossier import (
    MissionDossierState,
    NamespaceMixedStreamError,
    reduce_mission_dossier,
)
from spec_kitty_events.models import Event

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _events_from_replay(fixture_id: str) -> List[Event]:
    """Load a replay stream and deserialize to Event objects."""
    raw: List[Dict[str, Any]] = load_replay_stream(fixture_id)
    return [Event(**e) for e in raw]


# ---------------------------------------------------------------------------
# T023: Unit tests for core reducer behaviour
# ---------------------------------------------------------------------------


def test_empty_stream_returns_default_state() -> None:
    """Empty event stream must return a default MissionDossierState."""
    state = reduce_mission_dossier([])
    assert state == MissionDossierState()
    assert state.parity_status == "unknown"
    assert state.event_count == 0
    assert state.namespace is None
    assert state.artifacts == {}
    assert state.anomalies == ()
    assert state.drift_history == ()
    assert state.latest_snapshot is None


def test_happy_path_stream_produces_clean_state() -> None:
    """Happy-path replay stream must produce parity_status='clean'."""
    events = _events_from_replay("dossier-replay-happy-path")
    state = reduce_mission_dossier(events)
    assert state.parity_status == "clean"
    assert state.event_count > 0
    assert state.latest_snapshot is not None
    assert len(state.artifacts) >= 3


def test_happy_path_stream_event_count() -> None:
    """Happy-path stream (6 events, no dups) must yield event_count=6."""
    events = _events_from_replay("dossier-replay-happy-path")
    state = reduce_mission_dossier(events)
    assert state.event_count == 6


def test_happy_path_stream_artifacts_present() -> None:
    """Happy-path stream must produce exactly 3 artifacts."""
    events = _events_from_replay("dossier-replay-happy-path")
    state = reduce_mission_dossier(events)
    expected_paths = {
        "kitty-specs/008-mission-dossier-parity-event-contracts/spec.md",
        "kitty-specs/008-mission-dossier-parity-event-contracts/plan.md",
        "kitty-specs/008-mission-dossier-parity-event-contracts/tasks.md",
    }
    assert set(state.artifacts.keys()) == expected_paths


def test_drift_scenario_produces_drifted_state() -> None:
    """Drift scenario replay stream must produce parity_status='drifted'."""
    events = _events_from_replay("dossier-replay-drift-scenario")
    state = reduce_mission_dossier(events)
    assert state.parity_status == "drifted"
    assert len(state.drift_history) >= 1


def test_drift_scenario_has_anomalies() -> None:
    """Drift scenario stream must produce at least one anomaly entry."""
    events = _events_from_replay("dossier-replay-drift-scenario")
    state = reduce_mission_dossier(events)
    assert len(state.anomalies) >= 1


def test_supersedes_marks_prior_artifact() -> None:
    """Supersedes logic: spec.md is in artifacts and reflects latest version."""
    events = _events_from_replay("dossier-replay-happy-path")
    state = reduce_mission_dossier(events)
    # spec.md is superseded in the happy-path stream (event 5 supersedes event 1)
    spec_path = "kitty-specs/008-mission-dossier-parity-event-contracts/spec.md"
    assert spec_path in state.artifacts
    # The entry must reflect the latest version (content_ref from event 5)
    entry = state.artifacts[spec_path]
    assert entry.content_ref.hash == "abc222def222", (
        f"Expected latest hash 'abc222def222', got '{entry.content_ref.hash}'"
    )
    # Latest version is not itself superseded
    assert entry.superseded is False


def test_unknown_event_types_silently_skipped() -> None:
    """Non-dossier event types must be silently skipped and not counted."""
    events = _events_from_replay("dossier-replay-happy-path")
    # Inject a non-dossier event using a 26-char event_id
    fake = events[0].model_copy(
        update={
            "event_type": "SomeRandomEvent",
            "event_id": "01JNRFAKEEV000000000000001",
        }
    )
    mixed = [fake] + events
    # Should not raise; unknown events are silently skipped
    state = reduce_mission_dossier(mixed)
    assert state.event_count == len(events)  # fake event not counted


def test_namespace_populated_from_stream() -> None:
    """Reducer must populate namespace field from the first event's payload."""
    events = _events_from_replay("dossier-replay-happy-path")
    state = reduce_mission_dossier(events)
    assert state.namespace is not None
    assert state.namespace.feature_slug == "008-mission-dossier-parity-event-contracts"
    assert state.namespace.target_branch == "2.x"


def test_deduplication_same_output_as_clean_stream() -> None:
    """Reducer with duplicate events must produce identical output to clean stream."""
    events = _events_from_replay("dossier-replay-happy-path")
    # Duplicate the first event
    duplicated = [events[0]] + events
    state_clean = reduce_mission_dossier(events)
    state_duped = reduce_mission_dossier(duplicated)
    assert state_clean == state_duped


def test_deduplication_event_count_unchanged() -> None:
    """Deduplication must not inflate event_count."""
    events = _events_from_replay("dossier-replay-happy-path")
    duplicated = events + events  # all events duplicated
    state = reduce_mission_dossier(duplicated)
    assert state.event_count == len(events)


# ---------------------------------------------------------------------------
# T024: NamespaceMixedStreamError test
# ---------------------------------------------------------------------------


def test_namespace_mixed_stream_raises() -> None:
    """Reducer raises NamespaceMixedStreamError on multi-namespace input."""
    events = _events_from_replay("dossier-replay-happy-path")

    # Build a second event with a different feature_slug
    second_ns_event: Dict[str, Any] = json.loads(events[-1].model_dump_json())
    second_ns_event["event_id"] = "01JNRNS2EVENT0000000000001"
    second_ns_event["lamport_clock"] = 999
    second_ns_event["payload"]["namespace"]["feature_slug"] = (
        "999-entirely-different-feature"
    )
    different_ns_event = Event(**second_ns_event)

    mixed = list(events) + [different_ns_event]

    with pytest.raises(NamespaceMixedStreamError) as exc_info:
        reduce_mission_dossier(mixed)

    # Message must contain both namespace values
    msg = str(exc_info.value)
    assert "008-mission-dossier-parity-event-contracts" in msg or "Expected" in msg, (
        f"Expected namespace not found in error message: {msg}"
    )
    assert "999-entirely-different-feature" in msg or "Got" in msg, (
        f"Offending namespace not found in error message: {msg}"
    )


def test_namespace_mixed_stream_error_message_contains_expected_ns() -> None:
    """NamespaceMixedStreamError message must contain the expected namespace."""
    events = _events_from_replay("dossier-replay-happy-path")

    second_ns_event = json.loads(events[-1].model_dump_json())
    second_ns_event["event_id"] = "01JNRNS2EVENT0000000000002"
    second_ns_event["lamport_clock"] = 999
    second_ns_event["payload"]["namespace"]["feature_slug"] = "999-different"
    different_ns_event = Event(**second_ns_event)

    with pytest.raises(NamespaceMixedStreamError) as exc_info:
        reduce_mission_dossier(list(events) + [different_ns_event])

    msg = str(exc_info.value)
    # The message must reference both the expected and the offending feature slug
    assert "008-mission-dossier-parity-event-contracts" in msg
    assert "999-different" in msg


def test_namespace_collision_prevention() -> None:
    """Two events with identical namespace tuples must NOT raise."""
    events = _events_from_replay("dossier-replay-happy-path")
    # Same namespace throughout → should reduce cleanly
    state = reduce_mission_dossier(events)
    assert state.namespace is not None


def test_only_dossier_events_trigger_namespace_check() -> None:
    """Non-dossier events injected alongside valid dossier events must not raise."""
    events = _events_from_replay("dossier-replay-happy-path")
    # Inject a non-dossier event without any namespace field
    foreign = events[0].model_copy(
        update={
            "event_type": "WPStatusChanged",
            "event_id": "01JNRFOREIGN000000000000001",
        }
    )
    mixed = [foreign] + events
    # Non-dossier event is filtered out before namespace check
    state = reduce_mission_dossier(mixed)
    assert state.namespace is not None
    assert state.parity_status == "clean"


# ---------------------------------------------------------------------------
# P1 regression: step_id variance and malformed-first-event
# ---------------------------------------------------------------------------


def test_optional_step_id_variance_does_not_raise() -> None:
    """Two events with identical 5-field namespace but different step_id must not raise.

    Regression test for P1: step_id is optional context, not part of namespace
    identity.  Events from the same mission can carry different step_id values.
    """
    ns_base = _make_valid_namespace_dict()
    # Event 1: no step_id
    event1 = _make_bare_dossier_event(
        event_type="MissionDossierArtifactIndexed",
        event_id="01JNRSTEPV0000000000000001",
        lamport_clock=1,
        payload={
            "namespace": ns_base,
            "artifact_id": {
                "mission_key": "software-dev",
                "path": "some/artifact.md",
                "artifact_class": "input",
            },
            "content_ref": {"hash": "aabb0001", "algorithm": "sha256"},
            "indexed_at": "2026-02-21T14:00:00Z",
        },
    )
    # Event 2: same 5-field namespace, step_id set
    ns_with_step = {**ns_base, "step_id": "step-02"}
    event2 = _make_bare_dossier_event(
        event_type="MissionDossierArtifactIndexed",
        event_id="01JNRSTEPV0000000000000002",
        lamport_clock=2,
        payload={
            "namespace": ns_with_step,
            "artifact_id": {
                "mission_key": "software-dev",
                "path": "other/artifact.md",
                "artifact_class": "output",
            },
            "content_ref": {"hash": "aabb0002", "algorithm": "sha256"},
            "indexed_at": "2026-02-21T14:01:00Z",
        },
    )
    # Must not raise; both events share the same logical namespace
    state = reduce_mission_dossier([event1, event2])
    assert state.event_count == 2
    assert len(state.artifacts) == 2
    assert state.namespace is not None


def test_mixed_step_ids_normalize_to_none() -> None:
    """When multiple distinct step_ids appear, state.namespace.step_id must be None."""
    ns_base = _make_valid_namespace_dict()
    # Event 1: step_id="step-A"
    ns_a = {**ns_base, "step_id": "step-A"}
    event1 = _make_bare_dossier_event(
        event_type="MissionDossierArtifactIndexed",
        event_id="01JNRSTEPNRM000000000000A1",
        lamport_clock=1,
        payload={
            "namespace": ns_a,
            "artifact_id": {
                "mission_key": "software-dev",
                "path": "some/artifact-a.md",
                "artifact_class": "input",
            },
            "content_ref": {"hash": "aabb0001", "algorithm": "sha256"},
            "indexed_at": "2026-02-21T14:00:00Z",
        },
    )
    # Event 2: step_id="step-B"
    ns_b = {**ns_base, "step_id": "step-B"}
    event2 = _make_bare_dossier_event(
        event_type="MissionDossierArtifactIndexed",
        event_id="01JNRSTEPNRM000000000000A2",
        lamport_clock=2,
        payload={
            "namespace": ns_b,
            "artifact_id": {
                "mission_key": "software-dev",
                "path": "some/artifact-b.md",
                "artifact_class": "output",
            },
            "content_ref": {"hash": "aabb0002", "algorithm": "sha256"},
            "indexed_at": "2026-02-21T14:01:00Z",
        },
    )
    state = reduce_mission_dossier([event1, event2])
    # Mixed step_ids → normalized to None
    assert state.namespace is not None
    assert state.namespace.step_id is None
    # 5-field identity preserved
    assert state.namespace.project_uuid == ns_base["project_uuid"]
    assert state.namespace.feature_slug == ns_base["feature_slug"]
    assert state.namespace.target_branch == ns_base["target_branch"]
    assert state.namespace.mission_key == ns_base["mission_key"]
    assert state.namespace.manifest_version == ns_base["manifest_version"]
    assert state.event_count == 2
    assert len(state.artifacts) == 2


def test_malformed_first_event_does_not_poison_valid_stream() -> None:
    """A malformed first event (bad namespace) must be skipped, not poison subsequent
    valid events.

    Regression test for P1: _extract_namespace returns None for malformed events;
    the reducer must not raise NamespaceMixedStreamError when a malformed event
    precedes valid ones (None != real_ns was the bug).
    """
    ns = _make_valid_namespace_dict()
    # First event: malformed namespace missing required fields
    malformed_event = _make_bare_dossier_event(
        event_type="MissionDossierArtifactIndexed",
        event_id="01JNRC0BAD0000000000000001",
        lamport_clock=1,
        payload={"namespace": {"bad_key": "no_required_fields"}},
    )
    # Second event: fully valid
    valid_event = _make_bare_dossier_event(
        event_type="MissionDossierArtifactIndexed",
        event_id="01JNRC0BAD0000000000000002",
        lamport_clock=2,
        payload={
            "namespace": ns,
            "artifact_id": {
                "mission_key": "software-dev",
                "path": "some/artifact.md",
                "artifact_class": "input",
            },
            "content_ref": {"hash": "aabb1234", "algorithm": "sha256"},
            "indexed_at": "2026-02-21T14:00:00Z",
        },
    )
    # Must not raise; malformed event skipped, valid event processed
    state = reduce_mission_dossier([malformed_event, valid_event])
    assert state.event_count == 2  # both pass filter + dedup
    assert len(state.artifacts) == 1  # malformed payload skipped in fold
    assert state.namespace is not None
    assert state.namespace.feature_slug == "008-mission-dossier-parity-event-contracts"


# ---------------------------------------------------------------------------
# T025: Hypothesis property test — reducer determinism across permutations
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Coverage branch tests: malformed payloads and edge cases
# ---------------------------------------------------------------------------


def _make_bare_dossier_event(
    event_type: str,
    event_id: str,
    lamport_clock: int,
    payload: Dict[str, Any],
) -> Event:
    """Build a minimal dossier Event with a valid namespace but arbitrary payload."""
    from uuid import UUID
    return Event(
        event_id=event_id,
        event_type=event_type,
        aggregate_id="mission-software-dev",
        timestamp="2026-02-21T14:00:00.000Z",
        node_id="test-node",
        lamport_clock=lamport_clock,
        project_uuid=UUID("a1b2c3d4-e5f6-7890-abcd-ef1234567890"),
        correlation_id="01JNRC0RR00000000000000001",
        payload=payload,
    )


def _make_valid_namespace_dict() -> Dict[str, Any]:
    return {
        "project_uuid": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
        "feature_slug": "008-mission-dossier-parity-event-contracts",
        "target_branch": "2.x",
        "mission_key": "software-dev",
        "manifest_version": "1.0.0",
    }


def test_extract_namespace_returns_none_when_namespace_key_missing() -> None:
    """_extract_namespace returns None when event payload has no 'namespace' key.

    This exercises line 265 in dossier.py.
    """
    from spec_kitty_events.dossier import _extract_namespace

    event = _make_bare_dossier_event(
        event_type="MissionDossierArtifactIndexed",
        event_id="01JNRC0VNS0000000000000001",
        lamport_clock=1,
        payload={},  # No 'namespace' key
    )
    result = _extract_namespace(event)
    assert result is None


def test_extract_namespace_returns_none_for_malformed_namespace() -> None:
    """_extract_namespace returns None when namespace dict is malformed.

    This exercises lines 268-269 in dossier.py.
    """
    from spec_kitty_events.dossier import _extract_namespace

    event = _make_bare_dossier_event(
        event_type="MissionDossierArtifactIndexed",
        event_id="01JNRC0VNS0000000000000002",
        lamport_clock=2,
        payload={"namespace": {"bad_key": "no_required_fields"}},
    )
    result = _extract_namespace(event)
    assert result is None


def test_malformed_artifact_indexed_payload_is_skipped() -> None:
    """Malformed MissionDossierArtifactIndexed payload must be skipped silently.

    This exercises lines 326-327 in dossier.py.
    """
    ns = _make_valid_namespace_dict()
    bad_event = _make_bare_dossier_event(
        event_type="MissionDossierArtifactIndexed",
        event_id="01JNRC0VBAD000000000000001",
        lamport_clock=1,
        payload={"namespace": ns},  # Missing artifact_id, content_ref, indexed_at
    )
    state = reduce_mission_dossier([bad_event])
    # Bad event is skipped; no artifacts are indexed
    assert state.event_count == 1  # event passes dedup, is counted
    assert state.artifacts == {}


def test_malformed_artifact_missing_payload_is_skipped() -> None:
    """Malformed MissionDossierArtifactMissing payload must be skipped silently.

    This exercises lines 356-357 in dossier.py.
    """
    ns = _make_valid_namespace_dict()
    bad_event = _make_bare_dossier_event(
        event_type="MissionDossierArtifactMissing",
        event_id="01JNRC0VBAD000000000000002",
        lamport_clock=1,
        payload={"namespace": ns},  # Missing expected_identity, manifest_step, checked_at
    )
    state = reduce_mission_dossier([bad_event])
    assert state.anomalies == ()


def test_malformed_snapshot_computed_payload_is_skipped() -> None:
    """Malformed MissionDossierSnapshotComputed payload must be skipped silently.

    This exercises lines 373-374 in dossier.py.
    """
    ns = _make_valid_namespace_dict()
    bad_event = _make_bare_dossier_event(
        event_type="MissionDossierSnapshotComputed",
        event_id="01JNRC0VBAD000000000000003",
        lamport_clock=1,
        payload={"namespace": ns},  # Missing snapshot_hash, artifact_count, etc.
    )
    state = reduce_mission_dossier([bad_event])
    assert state.latest_snapshot is None
    # No snapshot -> parity_status must be "unknown"
    assert state.parity_status == "unknown"


def test_malformed_parity_drift_detected_payload_is_skipped() -> None:
    """Malformed MissionDossierParityDriftDetected payload must be skipped silently.

    This exercises lines 393-394 in dossier.py.
    """
    ns = _make_valid_namespace_dict()
    bad_event = _make_bare_dossier_event(
        event_type="MissionDossierParityDriftDetected",
        event_id="01JNRC0VBAD000000000000004",
        lamport_clock=1,
        payload={"namespace": ns},  # Missing expected_hash, actual_hash, drift_kind, detected_at
    )
    state = reduce_mission_dossier([bad_event])
    assert state.drift_history == ()


def test_no_snapshot_no_drift_produces_unknown_parity_status() -> None:
    """A stream with only indexed artifacts (no snapshot) yields parity_status='unknown'.

    This exercises line 411 in dossier.py.
    """
    ns = _make_valid_namespace_dict()
    event = _make_bare_dossier_event(
        event_type="MissionDossierArtifactIndexed",
        event_id="01JNR2NKST0000000000000001",
        lamport_clock=1,
        payload={
            "namespace": ns,
            "artifact_id": {
                "mission_key": "software-dev",
                "path": "some/artifact.md",
                "artifact_class": "input",
            },
            "content_ref": {"hash": "aabbccdd", "algorithm": "sha256"},
            "indexed_at": "2026-02-21T14:00:00Z",
        },
    )
    state = reduce_mission_dossier([event])
    # Artifact indexed, no snapshot → parity_status must be "unknown"
    assert state.parity_status == "unknown"
    assert len(state.artifacts) == 1


from hypothesis import given, settings, strategies as st  # noqa: E402

_HAPPY_PATH_EVENTS = _events_from_replay("dossier-replay-happy-path")
_CANONICAL_STATE = reduce_mission_dossier(_HAPPY_PATH_EVENTS)


@given(st.permutations(_HAPPY_PATH_EVENTS))
@settings(max_examples=200)
def test_reducer_determinism_across_permutations(
    permuted_events: List[Event],
) -> None:
    """Reducer must produce identical output for all event orderings.

    The sort key (lamport_clock, timestamp, event_id) guarantees a stable
    total order before reduction, so any permutation produces the same state.
    """
    state = reduce_mission_dossier(permuted_events)
    assert state == _CANONICAL_STATE, (
        f"Reducer produced different output for a permutation.\n"
        f"Expected parity_status={_CANONICAL_STATE.parity_status}, "
        f"got parity_status={state.parity_status}\n"
        f"Expected event_count={_CANONICAL_STATE.event_count}, "
        f"got event_count={state.event_count}"
    )
