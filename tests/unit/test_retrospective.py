"""Unit tests for retrospective module — payload validation, immutability, edge cases.

Covers WP02 subtask T009: comprehensive tests for RetrospectiveCompletedPayload,
RetrospectiveSkippedPayload, module-level constants, and C-008 (no reducer).
"""
from __future__ import annotations

import inspect

import pytest
from pydantic import ValidationError

from spec_kitty_events.dossier import ProvenanceRef
from spec_kitty_events.retrospective import (
    RETROSPECTIVE_COMPLETED,
    RETROSPECTIVE_EVENT_TYPES,
    RETROSPECTIVE_SCHEMA_VERSION,
    RETROSPECTIVE_SKIPPED,
    RetrospectiveCompletedPayload,
    RetrospectiveSkippedPayload,
)


# ── Shared helpers ────────────────────────────────────────────────────────────


def _make_completed(**overrides: object) -> RetrospectiveCompletedPayload:
    defaults: dict[str, object] = {
        "mission_id": "test-mission",
        "actor": "operator-1",
        "trigger_source": "operator",
        "completed_at": "2026-04-13T10:00:00Z",
    }
    defaults.update(overrides)
    return RetrospectiveCompletedPayload(**defaults)  # type: ignore[arg-type]


def _make_skipped(**overrides: object) -> RetrospectiveSkippedPayload:
    defaults: dict[str, object] = {
        "mission_id": "test-mission",
        "actor": "operator-1",
        "trigger_source": "runtime",
        "skip_reason": "trivial mission, no retro needed",
        "skipped_at": "2026-04-13T10:00:00Z",
    }
    defaults.update(overrides)
    return RetrospectiveSkippedPayload(**defaults)  # type: ignore[arg-type]


# ── RetrospectiveCompletedPayload tests ───────────────────────────────────────


class TestRetrospectiveCompletedPayload:
    def test_completed_minimal(self) -> None:
        payload = _make_completed()
        assert payload.mission_id == "test-mission"
        assert payload.actor == "operator-1"
        assert payload.trigger_source == "operator"
        assert payload.artifact_ref is None
        assert payload.completed_at == "2026-04-13T10:00:00Z"

    def test_completed_with_artifact(self) -> None:
        ref = ProvenanceRef(git_sha="abc123")
        payload = _make_completed(artifact_ref=ref)
        assert payload.artifact_ref is not None
        assert payload.artifact_ref.git_sha == "abc123"

    def test_completed_missing_actor_raises(self) -> None:
        with pytest.raises(ValidationError):
            RetrospectiveCompletedPayload(
                mission_id="m-1",
                trigger_source="runtime",
                completed_at="2026-04-13T10:00:00Z",
            )  # type: ignore[call-arg]

    def test_completed_invalid_trigger_source_raises(self) -> None:
        with pytest.raises(ValidationError):
            _make_completed(trigger_source="auto")

    def test_completed_valid_trigger_source_runtime(self) -> None:
        payload = _make_completed(trigger_source="runtime")
        assert payload.trigger_source == "runtime"

    def test_completed_valid_trigger_source_operator(self) -> None:
        payload = _make_completed(trigger_source="operator")
        assert payload.trigger_source == "operator"

    def test_completed_valid_trigger_source_policy(self) -> None:
        payload = _make_completed(trigger_source="policy")
        assert payload.trigger_source == "policy"

    def test_completed_frozen(self) -> None:
        payload = _make_completed()
        with pytest.raises(ValidationError):
            payload.mission_id = "changed"  # type: ignore[misc]

    def test_completed_extra_forbid(self) -> None:
        with pytest.raises(ValidationError):
            _make_completed(unexpected_field="nope")

    def test_completed_roundtrip(self) -> None:
        ref = ProvenanceRef(git_sha="abc123")
        original = _make_completed(artifact_ref=ref)
        dumped = original.model_dump()
        restored = RetrospectiveCompletedPayload.model_validate(dumped)
        assert restored == original

    def test_completed_empty_mission_id_raises(self) -> None:
        with pytest.raises(ValidationError):
            _make_completed(mission_id="")

    def test_completed_empty_completed_at_raises(self) -> None:
        with pytest.raises(ValidationError):
            _make_completed(completed_at="")

    def test_completed_invalid_timestamp_raises(self) -> None:
        with pytest.raises(ValidationError):
            _make_completed(completed_at="not-a-date")

    def test_completed_plain_date_no_time_raises(self) -> None:
        """A date without time component should still parse as ISO 8601."""
        payload = _make_completed(completed_at="2026-04-13")
        assert payload.completed_at == "2026-04-13"


# ── RetrospectiveSkippedPayload tests ─────────────────────────────────────────


class TestRetrospectiveSkippedPayload:
    def test_skipped_valid(self) -> None:
        payload = _make_skipped()
        assert payload.mission_id == "test-mission"
        assert payload.actor == "operator-1"
        assert payload.trigger_source == "runtime"
        assert payload.skip_reason == "trivial mission, no retro needed"
        assert payload.skipped_at == "2026-04-13T10:00:00Z"

    def test_skipped_empty_reason_raises(self) -> None:
        with pytest.raises(ValidationError):
            _make_skipped(skip_reason="")

    def test_skipped_missing_reason_raises(self) -> None:
        with pytest.raises(ValidationError):
            RetrospectiveSkippedPayload(
                mission_id="m-1",
                actor="operator-1",
                trigger_source="runtime",
                skipped_at="2026-04-13T10:00:00Z",
            )  # type: ignore[call-arg]

    def test_skipped_invalid_trigger_source_raises(self) -> None:
        with pytest.raises(ValidationError):
            _make_skipped(trigger_source="manual")

    def test_skipped_frozen(self) -> None:
        payload = _make_skipped()
        with pytest.raises(ValidationError):
            payload.skip_reason = "changed"  # type: ignore[misc]

    def test_skipped_extra_forbid(self) -> None:
        with pytest.raises(ValidationError):
            _make_skipped(unknown_field="nope")

    def test_skipped_invalid_timestamp_raises(self) -> None:
        with pytest.raises(ValidationError):
            _make_skipped(skipped_at="not-a-date")

    def test_skipped_roundtrip(self) -> None:
        original = _make_skipped()
        dumped = original.model_dump()
        restored = RetrospectiveSkippedPayload.model_validate(dumped)
        assert restored == original


# ── Module-level tests ────────────────────────────────────────────────────────


class TestModuleLevel:
    def test_event_types_frozenset(self) -> None:
        assert RETROSPECTIVE_EVENT_TYPES == frozenset({
            "RetrospectiveCompleted",
            "RetrospectiveSkipped",
        })
        assert len(RETROSPECTIVE_EVENT_TYPES) == 2

    def test_schema_version(self) -> None:
        assert RETROSPECTIVE_SCHEMA_VERSION == "3.1.0"

    def test_no_reducer_exists(self) -> None:
        """C-008: Retrospective is terminal signals only — no reducer."""
        import spec_kitty_events.retrospective as mod
        members = inspect.getmembers(mod, inspect.isfunction)
        reducer_names = [name for name, _ in members if name.startswith("reduce_")]
        assert reducer_names == [], f"Unexpected reducer functions: {reducer_names}"

    def test_event_type_constants_match_frozenset(self) -> None:
        assert RETROSPECTIVE_COMPLETED in RETROSPECTIVE_EVENT_TYPES
        assert RETROSPECTIVE_SKIPPED in RETROSPECTIVE_EVENT_TYPES
