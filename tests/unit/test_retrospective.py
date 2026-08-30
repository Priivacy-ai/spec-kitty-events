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
    RETROSPECTIVE_COMPLETED_EVENT,
    RETROSPECTIVE_COMPLETED,
    RETROSPECTIVE_EVENT_TYPES,
    RETROSPECTIVE_EVENT_NAMES,
    RETROSPECTIVE_FAILED_EVENT,
    RETROSPECTIVE_PROPOSAL_APPLIED_EVENT,
    RETROSPECTIVE_PROPOSAL_GENERATED_EVENT,
    RETROSPECTIVE_PROPOSAL_REJECTED_EVENT,
    RETROSPECTIVE_REQUESTED_EVENT,
    RETROSPECTIVE_SCHEMA_VERSION,
    RETROSPECTIVE_SKIPPED_EVENT,
    RETROSPECTIVE_SKIPPED,
    RETROSPECTIVE_STARTED_EVENT,
    RetrospectiveActorRef,
    RetrospectiveCompletedPayload,
    RetrospectiveFailedPayload,
    RetrospectiveLifecycleCompletedPayload,
    RetrospectiveLifecycleSkippedPayload,
    RetrospectiveMode,
    RetrospectiveModeSourceSignal,
    RetrospectiveProposalAppliedPayload,
    RetrospectiveProposalGeneratedPayload,
    RetrospectiveProposalRejectedPayload,
    RetrospectiveRequestedPayload,
    RetrospectiveSkippedPayload,
    RetrospectiveStartedPayload,
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

    @pytest.mark.parametrize(
        "completed_at,reshaped",
        [
            pytest.param(
                "2026-04-13T10:00:00.123456789Z",
                "2026-04-13T10:00:00.123456+00:00",
                id="z-suffix-nanosecond-fraction",
            ),
            pytest.param(
                "20260413T100000Z",
                "2026-04-13T10:00:00+00:00",
                id="basic-format-z-suffix",
            ),
            pytest.param(
                "20260413T100000+0200",
                "2026-04-13T10:00:00+02:00",
                id="basic-format-numeric-offset",
            ),
            pytest.param(
                "2026-04-13T10:00Z",
                "2026-04-13T10:00:00+00:00",
                id="extended-minute-precision-z-suffix",
            ),
            pytest.param(
                "2026-04-13T10Z",
                "2026-04-13T10:00:00+00:00",
                id="extended-hour-precision-z-suffix",
            ),
            pytest.param(
                "20260413T1000Z",
                "2026-04-13T10:00:00+00:00",
                id="basic-format-minute-precision-z-suffix",
            ),
            pytest.param(
                "20260413T10Z",
                "2026-04-13T10:00:00+00:00",
                id="basic-format-hour-precision-z-suffix",
            ),
        ],
    )
    def test_completed_timestamp_shapes_that_split_by_python_version_accepted(
        self, completed_at: str, reshaped: str
    ) -> None:
        """spec-kitty-events#135: ``datetime.fromisoformat`` on 3.10 rejects
        an arbitrary-precision fractional-second part (3.10 only accepts
        0/3/6 digits) and basic (no ``-``/``:``) format, both accepted on
        3.11+ for the same wire bytes. ``_assert_iso8601_timestamp`` must
        accept these identically regardless of the interpreter running it.

        Also asserts ``_normalize_iso8601_shape``'s exact output (squad
        finding, 2026-08-27): asserting only that the payload round-trips
        passes identically with the reshape deleted, on any interpreter
        that already tolerates the shape natively — this repo's own test
        runner included.

        The four reduced-precision cases (squad pass 2 MAJOR, 2026-08-27)
        guard against the seconds component having been mandatory in
        ``_ISO8601_SHAPE_RE``, which made the trailing-``Z`` rewrite
        conditional on a full match and reintroduced a 3.10-only rejection
        for reduced-precision completion timestamps — reachable here
        because ``test_completed_plain_date_no_time_raises`` above already
        establishes that a bare date is in-contract for ``completed_at``,
        so nothing mandates second precision either."""
        from spec_kitty_events.retrospective import _normalize_iso8601_shape

        assert _normalize_iso8601_shape(completed_at) == reshaped
        payload = _make_completed(completed_at=completed_at)
        assert payload.completed_at == completed_at

    def test_completed_timestamp_still_rejects_doubled_z_at_reduced_precision(
        self,
    ) -> None:
        """Guards the incidental gain the squad flagged as worth keeping
        (pass 2, 2026-08-27): closing the reduced-precision gap above must
        not resurrect acceptance of a doubled trailing ``Z`` at any
        precision. ``_normalize_iso8601_shape``'s case-folded residual
        guard (mirrors #132's ``_normalize_occurred_at``, controller-qa
        finding 2026-08-28) now raises directly on a doubled/mixed-case
        trailing designator, before the reshape regex ever runs."""
        from spec_kitty_events.retrospective import _normalize_iso8601_shape

        for value in (
            "2026-04-13T10:00:00ZZ",
            "2026-04-13T10:00ZZ",
            "2026-04-13T10ZZ",
            "2026-04-13T10:00:00zZ",
        ):
            with pytest.raises(ValueError):
                _normalize_iso8601_shape(value)
            with pytest.raises(ValidationError):
                _make_completed(completed_at=value)

    @pytest.mark.parametrize(
        "completed_at,reshaped",
        [
            pytest.param(
                "2026-04-13t10:00:00Z",
                "2026-04-13t10:00:00+00:00",
                id="lowercase-t-separator",
            ),
            pytest.param(
                "2026-04-13T10:00:00 Z",
                "2026-04-13T10:00:00 +00:00",
                id="space-before-z",
            ),
        ],
    )
    def test_completed_timestamp_does_not_newly_split_shapes_the_regex_does_not_match(
        self, completed_at: str, reshaped: str
    ) -> None:
        """Controller-qa finding, 2026-08-28: a shape the reshape regex
        doesn't match (lowercase ``t`` separator, stray space before
        ``Z``) must still go through the unconditional ``Z``-strip that
        runs before the regex, exactly as ``main`` always did — never
        worse off than before this PR's regex-based reshape existed."""
        from spec_kitty_events.retrospective import _normalize_iso8601_shape

        assert _normalize_iso8601_shape(completed_at) == reshaped
        payload = _make_completed(completed_at=completed_at)
        assert payload.completed_at == completed_at

    def test_completed_rejects_a_doubled_trailing_z_timestamp(self) -> None:
        """A doubled trailing "Z" must be rejected on every interpreter version.

        Stripping only the final "Z" and appending "+00:00" would otherwise
        turn this into "...00Z+00:00", which Python 3.10's laxer
        ``fromisoformat`` accepts even though it is not a valid ISO-8601
        timestamp (spec-kitty-events#55/#107).
        """
        with pytest.raises(ValidationError):
            _make_completed(completed_at="2026-04-13T10:00:00ZZ")

    def test_completed_mixed_case_doubled_z_raises(self) -> None:
        """A doubled UTC designator must be rejected regardless of case: a
        case-sensitive residual check misses a lowercase "z" left behind by
        a mixed-case doubled designator (e.g. "...00zZ"), which would
        otherwise launder it into "...00z+00:00" (spec-kitty-events#124)."""
        with pytest.raises(ValidationError):
            _make_completed(completed_at="2026-04-13T10:00:00zZ")


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
        assert RETROSPECTIVE_EVENT_NAMES == frozenset(
            {
                "retrospective.requested",
                "retrospective.started",
                "retrospective.completed",
                "retrospective.skipped",
                "retrospective.failed",
                "retrospective.proposal.generated",
                "retrospective.proposal.applied",
                "retrospective.proposal.rejected",
            }
        )
        assert RETROSPECTIVE_EVENT_TYPES == frozenset(
            {
                "RetrospectiveCompleted",
                "RetrospectiveSkipped",
                *RETROSPECTIVE_EVENT_NAMES,
            }
        )
        assert len(RETROSPECTIVE_EVENT_TYPES) == 10

    def test_schema_version(self) -> None:
        assert RETROSPECTIVE_SCHEMA_VERSION == "4.1.0"

    def test_no_reducer_exists(self) -> None:
        """C-008: Retrospective is terminal signals only — no reducer."""
        import spec_kitty_events.retrospective as mod

        members = inspect.getmembers(mod, inspect.isfunction)
        reducer_names = [name for name, _ in members if name.startswith("reduce_")]
        assert reducer_names == [], f"Unexpected reducer functions: {reducer_names}"

    def test_event_type_constants_match_frozenset(self) -> None:
        assert RETROSPECTIVE_COMPLETED in RETROSPECTIVE_EVENT_TYPES
        assert RETROSPECTIVE_SKIPPED in RETROSPECTIVE_EVENT_TYPES
        assert RETROSPECTIVE_REQUESTED_EVENT in RETROSPECTIVE_EVENT_NAMES
        assert RETROSPECTIVE_STARTED_EVENT in RETROSPECTIVE_EVENT_NAMES
        assert RETROSPECTIVE_COMPLETED_EVENT in RETROSPECTIVE_EVENT_NAMES
        assert RETROSPECTIVE_SKIPPED_EVENT in RETROSPECTIVE_EVENT_NAMES
        assert RETROSPECTIVE_FAILED_EVENT in RETROSPECTIVE_EVENT_NAMES
        assert RETROSPECTIVE_PROPOSAL_GENERATED_EVENT in RETROSPECTIVE_EVENT_NAMES
        assert RETROSPECTIVE_PROPOSAL_APPLIED_EVENT in RETROSPECTIVE_EVENT_NAMES
        assert RETROSPECTIVE_PROPOSAL_REJECTED_EVENT in RETROSPECTIVE_EVENT_NAMES


class TestRuntimeRetrospectivePayloads:
    def test_requested_payload_shape(self) -> None:
        actor = RetrospectiveActorRef(kind="human", id="operator-1")
        mode = RetrospectiveMode(
            value="human_in_command",
            source_signal=RetrospectiveModeSourceSignal(
                kind="explicit_flag",
                evidence="--mode human_in_command",
            ),
        )
        payload = RetrospectiveRequestedPayload(
            mode=mode,
            terminus_step_id="accept",
            requested_by=actor,
        )
        assert payload.mode.value == "human_in_command"
        assert payload.requested_by.id == "operator-1"

    def test_runtime_payloads_reject_extra_fields(self) -> None:
        with pytest.raises(ValidationError):
            RetrospectiveStartedPayload(
                facilitator_profile_id="retrospective-facilitator",
                action_id="retrospect",
                extra="nope",
            )

    def test_completed_payload_shape(self) -> None:
        payload = RetrospectiveLifecycleCompletedPayload(
            record_path=".kittify/missions/01TEST/retrospective.yaml",
            record_hash="sha256:abc",
            findings_summary={"helped": 1, "not_helpful": 2, "gaps": 0},
            proposals_count=3,
        )
        assert payload.proposals_count == 3

    def test_completed_payload_rejects_negative_proposal_count(self) -> None:
        with pytest.raises(ValidationError):
            RetrospectiveLifecycleCompletedPayload(
                record_path=".kittify/missions/01TEST/retrospective.yaml",
                record_hash="sha256:abc",
                findings_summary={},
                proposals_count=-1,
            )

    def test_skipped_payload_shape(self) -> None:
        payload = RetrospectiveLifecycleSkippedPayload(
            record_path=".kittify/missions/01TEST/retrospective.yaml",
            skip_reason="operator declined",
            skipped_by=RetrospectiveActorRef(kind="human", id="operator-1"),
        )
        assert payload.skipped_by.kind == "human"

    def test_failed_payload_shape(self) -> None:
        payload = RetrospectiveFailedPayload(
            failure_code="facilitator_not_configured",
            message="No facilitator profile configured",
        )
        assert payload.record_path is None

    def test_proposal_payload_shapes(self) -> None:
        actor = RetrospectiveActorRef(kind="agent", id="synthesizer")
        generated = RetrospectiveProposalGeneratedPayload(
            proposal_id="01TESTPROPOSAL",
            kind="synthesize_directive",
            record_path=".kittify/missions/01TEST/retrospective.yaml",
        )
        applied = RetrospectiveProposalAppliedPayload(
            proposal_id=generated.proposal_id,
            kind=generated.kind,
            target_urn="doctrine:directive:DIRECTIVE_001",
            provenance_ref="mission/01TEST/proposals/01TESTPROPOSAL",
            applied_by=actor,
        )
        rejected = RetrospectiveProposalRejectedPayload(
            proposal_id=generated.proposal_id,
            kind=generated.kind,
            reason="conflict",
            detail="target changed",
            rejected_by=actor,
        )
        assert applied.target_urn == "doctrine:directive:DIRECTIVE_001"
        assert rejected.reason == "conflict"
