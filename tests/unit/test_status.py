"""Unit tests for status state model contracts."""

import uuid
from datetime import datetime, timezone, timedelta

import pydantic
import pytest

from spec_kitty_events import (
    DoneEvidence,
    Event,
    ExecutionMode,
    ForceMetadata,
    Lane,
    ReducedStatus,
    RepoEvidence,
    ReviewVerdict,
    StatusTransitionPayload,
    TransitionAnomaly,
    TransitionError,
    TransitionValidationResult,
    VerificationEntry,
    WPState,
    dedup_events,
    normalize_lane,
    reduce_status_events,
    status_event_sort_key,
    validate_transition,
    LANE_ALIASES,
    TERMINAL_LANES,
    WP_STATUS_CHANGED,
    SpecKittyEventsError,
    ValidationError,
)
from spec_kitty_events.status import _ALLOWED_TRANSITIONS


# ---------------------------------------------------------------------------
# Fixtures / shared data
# ---------------------------------------------------------------------------

VALID_REPO_EVIDENCE: dict = {
    "repo": "org/my-repo",
    "branch": "feat/branch",
    "commit": "abc123def",
}

VALID_REVIEW_VERDICT: dict = {
    "reviewer": "alice",
    "verdict": "approved",
}

VALID_DONE_EVIDENCE: dict = {
    "repos": [VALID_REPO_EVIDENCE],
    "review": VALID_REVIEW_VERDICT,
}

VALID_TRANSITION_DATA: dict = {
    "feature_slug": "003-status",
    "wp_id": "WP01",
    "from_lane": "planned",
    "to_lane": "claimed",
    "actor": "agent-1",
    "execution_mode": "worktree",
}


# ---------------------------------------------------------------------------
# Lane enum
# ---------------------------------------------------------------------------


class TestLane:
    """Test Lane enum members and string behavior."""

    def test_planned_value(self) -> None:
        assert Lane.PLANNED.value == "planned"

    def test_claimed_value(self) -> None:
        assert Lane.CLAIMED.value == "claimed"

    def test_in_progress_value(self) -> None:
        assert Lane.IN_PROGRESS.value == "in_progress"

    def test_for_review_value(self) -> None:
        assert Lane.FOR_REVIEW.value == "for_review"

    def test_done_value(self) -> None:
        assert Lane.DONE.value == "done"

    def test_blocked_value(self) -> None:
        assert Lane.BLOCKED.value == "blocked"

    def test_canceled_value(self) -> None:
        assert Lane.CANCELED.value == "canceled"

    def test_all_seven_members(self) -> None:
        assert len(Lane) == 7

    def test_string_equality(self) -> None:
        assert Lane.PLANNED == "planned"
        assert Lane.DONE == "done"

    def test_iteration_yields_all(self) -> None:
        values = [m.value for m in Lane]
        assert "planned" in values
        assert "canceled" in values
        assert len(values) == 7

    def test_from_value(self) -> None:
        assert Lane("planned") is Lane.PLANNED
        assert Lane("in_progress") is Lane.IN_PROGRESS

    def test_invalid_value_raises(self) -> None:
        with pytest.raises(ValueError):
            Lane("nonexistent")


# ---------------------------------------------------------------------------
# ExecutionMode enum
# ---------------------------------------------------------------------------


class TestExecutionMode:
    """Test ExecutionMode enum members."""

    def test_worktree_value(self) -> None:
        assert ExecutionMode.WORKTREE.value == "worktree"

    def test_direct_repo_value(self) -> None:
        assert ExecutionMode.DIRECT_REPO.value == "direct_repo"

    def test_from_value(self) -> None:
        assert ExecutionMode("worktree") is ExecutionMode.WORKTREE
        assert ExecutionMode("direct_repo") is ExecutionMode.DIRECT_REPO

    def test_two_members(self) -> None:
        assert len(ExecutionMode) == 2


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------


class TestConstants:
    """Test module-level constants."""

    def test_terminal_lanes_contains_done(self) -> None:
        assert Lane.DONE in TERMINAL_LANES

    def test_terminal_lanes_contains_canceled(self) -> None:
        assert Lane.CANCELED in TERMINAL_LANES

    def test_terminal_lanes_size(self) -> None:
        assert len(TERMINAL_LANES) == 2

    def test_lane_aliases_doing(self) -> None:
        assert LANE_ALIASES["doing"] is Lane.IN_PROGRESS

    def test_wp_status_changed(self) -> None:
        assert WP_STATUS_CHANGED == "WPStatusChanged"


# ---------------------------------------------------------------------------
# normalize_lane
# ---------------------------------------------------------------------------


class TestNormalizeLane:
    """Test normalize_lane function."""

    @pytest.mark.parametrize("value", [
        "planned", "claimed", "in_progress", "for_review",
        "done", "blocked", "canceled",
    ])
    def test_canonical_values(self, value: str) -> None:
        result = normalize_lane(value)
        assert result.value == value

    def test_alias_doing_maps_to_in_progress(self) -> None:
        result = normalize_lane("doing")
        assert result is Lane.IN_PROGRESS

    def test_unknown_raises_validation_error(self) -> None:
        with pytest.raises(ValidationError, match="Unknown lane value"):
            normalize_lane("nonexistent")

    def test_error_is_spec_kitty_events_error_subclass(self) -> None:
        with pytest.raises(SpecKittyEventsError):
            normalize_lane("bogus")

    def test_empty_string_raises(self) -> None:
        with pytest.raises(ValidationError):
            normalize_lane("")


# ---------------------------------------------------------------------------
# RepoEvidence
# ---------------------------------------------------------------------------


class TestRepoEvidence:
    """Test RepoEvidence model."""

    def test_construction(self) -> None:
        r = RepoEvidence(**VALID_REPO_EVIDENCE)
        assert r.repo == "org/my-repo"
        assert r.branch == "feat/branch"
        assert r.commit == "abc123def"
        assert r.files_touched is None

    def test_frozen(self) -> None:
        r = RepoEvidence(**VALID_REPO_EVIDENCE)
        with pytest.raises(pydantic.ValidationError):
            r.repo = "changed"  # type: ignore[misc]

    def test_files_touched_optional(self) -> None:
        r = RepoEvidence(**VALID_REPO_EVIDENCE, files_touched=["a.py", "b.py"])
        assert r.files_touched == ["a.py", "b.py"]

    def test_empty_repo_rejected(self) -> None:
        with pytest.raises(pydantic.ValidationError):
            RepoEvidence(repo="", branch="b", commit="c")

    def test_empty_branch_rejected(self) -> None:
        with pytest.raises(pydantic.ValidationError):
            RepoEvidence(repo="r", branch="", commit="c")

    def test_empty_commit_rejected(self) -> None:
        with pytest.raises(pydantic.ValidationError):
            RepoEvidence(repo="r", branch="b", commit="")

    def test_round_trip(self) -> None:
        r = RepoEvidence(**VALID_REPO_EVIDENCE, files_touched=["x.py"])
        dumped = r.model_dump()
        reconstructed = RepoEvidence.model_validate(dumped)
        assert reconstructed == r


# ---------------------------------------------------------------------------
# VerificationEntry
# ---------------------------------------------------------------------------


class TestVerificationEntry:
    """Test VerificationEntry model."""

    def test_construction(self) -> None:
        v = VerificationEntry(command="pytest", result="passed")
        assert v.command == "pytest"
        assert v.result == "passed"
        assert v.summary is None

    def test_frozen(self) -> None:
        v = VerificationEntry(command="pytest", result="passed")
        with pytest.raises(pydantic.ValidationError):
            v.command = "changed"  # type: ignore[misc]

    def test_optional_summary(self) -> None:
        v = VerificationEntry(command="pytest", result="ok", summary="All green")
        assert v.summary == "All green"

    def test_empty_command_rejected(self) -> None:
        with pytest.raises(pydantic.ValidationError):
            VerificationEntry(command="", result="ok")

    def test_empty_result_rejected(self) -> None:
        with pytest.raises(pydantic.ValidationError):
            VerificationEntry(command="pytest", result="")

    def test_round_trip(self) -> None:
        v = VerificationEntry(command="mypy", result="clean", summary="No errors")
        dumped = v.model_dump()
        reconstructed = VerificationEntry.model_validate(dumped)
        assert reconstructed == v


# ---------------------------------------------------------------------------
# ReviewVerdict
# ---------------------------------------------------------------------------


class TestReviewVerdict:
    """Test ReviewVerdict model."""

    def test_construction(self) -> None:
        r = ReviewVerdict(**VALID_REVIEW_VERDICT)
        assert r.reviewer == "alice"
        assert r.verdict == "approved"
        assert r.reference is None

    def test_frozen(self) -> None:
        r = ReviewVerdict(**VALID_REVIEW_VERDICT)
        with pytest.raises(pydantic.ValidationError):
            r.reviewer = "changed"  # type: ignore[misc]

    def test_optional_reference(self) -> None:
        r = ReviewVerdict(reviewer="bob", verdict="approved", reference="PR#42")
        assert r.reference == "PR#42"

    def test_empty_reviewer_rejected(self) -> None:
        with pytest.raises(pydantic.ValidationError):
            ReviewVerdict(reviewer="", verdict="ok")

    def test_empty_verdict_rejected(self) -> None:
        with pytest.raises(pydantic.ValidationError):
            ReviewVerdict(reviewer="alice", verdict="")

    def test_round_trip(self) -> None:
        r = ReviewVerdict(reviewer="alice", verdict="approved", reference="url")
        dumped = r.model_dump()
        reconstructed = ReviewVerdict.model_validate(dumped)
        assert reconstructed == r


# ---------------------------------------------------------------------------
# DoneEvidence
# ---------------------------------------------------------------------------


class TestDoneEvidence:
    """Test DoneEvidence model."""

    def test_construction(self) -> None:
        d = DoneEvidence(**VALID_DONE_EVIDENCE)
        assert len(d.repos) == 1
        assert d.repos[0].repo == "org/my-repo"
        assert d.verification == []
        assert d.review.reviewer == "alice"

    def test_repos_required_nonempty(self) -> None:
        with pytest.raises(pydantic.ValidationError):
            DoneEvidence(repos=[], review=VALID_REVIEW_VERDICT)

    def test_verification_defaults_empty(self) -> None:
        d = DoneEvidence(**VALID_DONE_EVIDENCE)
        assert d.verification == []

    def test_verification_with_entries(self) -> None:
        d = DoneEvidence(
            repos=[VALID_REPO_EVIDENCE],
            verification=[{"command": "pytest", "result": "ok"}],
            review=VALID_REVIEW_VERDICT,
        )
        assert len(d.verification) == 1

    def test_round_trip(self) -> None:
        d = DoneEvidence(
            repos=[VALID_REPO_EVIDENCE],
            verification=[{"command": "pytest", "result": "ok"}],
            review=VALID_REVIEW_VERDICT,
        )
        dumped = d.model_dump()
        reconstructed = DoneEvidence.model_validate(dumped)
        assert reconstructed == d


# ---------------------------------------------------------------------------
# ForceMetadata
# ---------------------------------------------------------------------------


class TestForceMetadata:
    """Test ForceMetadata model."""

    def test_construction(self) -> None:
        f = ForceMetadata(actor="admin", reason="emergency fix")
        assert f.force is True
        assert f.actor == "admin"
        assert f.reason == "emergency fix"

    def test_actor_required_nonempty(self) -> None:
        with pytest.raises(pydantic.ValidationError):
            ForceMetadata(actor="", reason="reason")

    def test_reason_required_nonempty(self) -> None:
        with pytest.raises(pydantic.ValidationError):
            ForceMetadata(actor="admin", reason="")

    def test_frozen(self) -> None:
        f = ForceMetadata(actor="admin", reason="reason")
        with pytest.raises(pydantic.ValidationError):
            f.actor = "changed"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# StatusTransitionPayload
# ---------------------------------------------------------------------------


class TestStatusTransitionPayload:
    """Test StatusTransitionPayload model."""

    def test_basic_construction(self) -> None:
        p = StatusTransitionPayload(**VALID_TRANSITION_DATA)
        assert p.feature_slug == "003-status"
        assert p.wp_id == "WP01"
        assert p.from_lane is Lane.PLANNED
        assert p.to_lane is Lane.CLAIMED
        assert p.actor == "agent-1"
        assert p.force is False
        assert p.reason is None
        assert p.execution_mode is ExecutionMode.WORKTREE
        assert p.review_ref is None
        assert p.evidence is None

    def test_alias_normalization_from_lane(self) -> None:
        data = {**VALID_TRANSITION_DATA, "from_lane": "doing"}
        p = StatusTransitionPayload(**data)
        assert p.from_lane is Lane.IN_PROGRESS

    def test_alias_normalization_to_lane(self) -> None:
        data = {**VALID_TRANSITION_DATA, "to_lane": "doing"}
        p = StatusTransitionPayload(**data)
        assert p.to_lane is Lane.IN_PROGRESS

    def test_from_lane_none_is_valid(self) -> None:
        data = {**VALID_TRANSITION_DATA, "from_lane": None}
        p = StatusTransitionPayload(**data)
        assert p.from_lane is None

    def test_force_requires_reason(self) -> None:
        data = {**VALID_TRANSITION_DATA, "force": True}
        with pytest.raises(pydantic.ValidationError, match="force=True requires"):
            StatusTransitionPayload(**data)

    def test_force_with_reason_valid(self) -> None:
        data = {
            **VALID_TRANSITION_DATA,
            "force": True,
            "reason": "emergency rollback",
        }
        p = StatusTransitionPayload(**data)
        assert p.force is True
        assert p.reason == "emergency rollback"

    def test_force_with_empty_reason_rejected(self) -> None:
        data = {
            **VALID_TRANSITION_DATA,
            "force": True,
            "reason": "  ",
        }
        with pytest.raises(pydantic.ValidationError, match="force=True requires"):
            StatusTransitionPayload(**data)

    def test_done_requires_evidence(self) -> None:
        data = {**VALID_TRANSITION_DATA, "to_lane": "done"}
        with pytest.raises(pydantic.ValidationError, match="requires evidence"):
            StatusTransitionPayload(**data)

    def test_done_with_evidence_valid(self) -> None:
        data = {
            **VALID_TRANSITION_DATA,
            "to_lane": "done",
            "evidence": VALID_DONE_EVIDENCE,
        }
        p = StatusTransitionPayload(**data)
        assert p.to_lane is Lane.DONE
        assert p.evidence is not None
        assert len(p.evidence.repos) == 1

    def test_forced_done_still_requires_evidence(self) -> None:
        data = {
            **VALID_TRANSITION_DATA,
            "to_lane": "done",
            "force": True,
            "reason": "override",
        }
        with pytest.raises(pydantic.ValidationError, match="requires evidence"):
            StatusTransitionPayload(**data)

    def test_forced_done_with_evidence_valid(self) -> None:
        data = {
            **VALID_TRANSITION_DATA,
            "to_lane": "done",
            "force": True,
            "reason": "override",
            "evidence": VALID_DONE_EVIDENCE,
        }
        p = StatusTransitionPayload(**data)
        assert p.force is True
        assert p.to_lane is Lane.DONE

    def test_round_trip(self) -> None:
        data = {
            **VALID_TRANSITION_DATA,
            "to_lane": "done",
            "evidence": VALID_DONE_EVIDENCE,
        }
        p = StatusTransitionPayload(**data)
        dumped = p.model_dump()
        reconstructed = StatusTransitionPayload.model_validate(dumped)
        assert reconstructed == p

    def test_frozen(self) -> None:
        p = StatusTransitionPayload(**VALID_TRANSITION_DATA)
        with pytest.raises(pydantic.ValidationError):
            p.actor = "changed"  # type: ignore[misc]

    def test_empty_feature_slug_rejected(self) -> None:
        data = {**VALID_TRANSITION_DATA, "feature_slug": ""}
        with pytest.raises(pydantic.ValidationError):
            StatusTransitionPayload(**data)

    def test_empty_wp_id_rejected(self) -> None:
        data = {**VALID_TRANSITION_DATA, "wp_id": ""}
        with pytest.raises(pydantic.ValidationError):
            StatusTransitionPayload(**data)

    def test_empty_actor_rejected(self) -> None:
        data = {**VALID_TRANSITION_DATA, "actor": ""}
        with pytest.raises(pydantic.ValidationError):
            StatusTransitionPayload(**data)


# ---------------------------------------------------------------------------
# TransitionError
# ---------------------------------------------------------------------------


class TestTransitionError:
    """Test TransitionError exception."""

    def test_construction_with_violations(self) -> None:
        err = TransitionError(violations=("rule-1 violated", "rule-2 violated"))
        assert err.violations == ("rule-1 violated", "rule-2 violated")
        assert "rule-1 violated" in str(err)
        assert "rule-2 violated" in str(err)
        assert "Invalid transition" in str(err)

    def test_is_spec_kitty_events_error(self) -> None:
        err = TransitionError(violations=("oops",))
        assert isinstance(err, SpecKittyEventsError)

    def test_single_violation(self) -> None:
        err = TransitionError(violations=("only-one",))
        assert err.violations == ("only-one",)
        assert "only-one" in str(err)


# ---------------------------------------------------------------------------
# Helpers for validation tests
# ---------------------------------------------------------------------------


def _make_payload(
    from_lane: Lane | None = Lane.PLANNED,
    to_lane: Lane = Lane.CLAIMED,
    force: bool = False,
    reason: str | None = None,
    review_ref: str | None = None,
    evidence: DoneEvidence | None = None,
) -> StatusTransitionPayload:
    return StatusTransitionPayload(
        feature_slug="test-feature",
        wp_id="WP01",
        from_lane=from_lane,
        to_lane=to_lane,
        actor="test-actor",
        force=force,
        reason=reason,
        execution_mode=ExecutionMode.WORKTREE,
        review_ref=review_ref,
        evidence=evidence,
    )


def _make_evidence() -> DoneEvidence:
    return DoneEvidence(
        repos=[RepoEvidence(repo="test", branch="main", commit="abc123")],
        verification=[],
        review=ReviewVerdict(reviewer="alice", verdict="approved"),
    )


# ---------------------------------------------------------------------------
# TransitionValidationResult
# ---------------------------------------------------------------------------


class TestTransitionValidationResult:
    """Test TransitionValidationResult dataclass."""

    def test_valid_result(self) -> None:
        r = TransitionValidationResult(valid=True)
        assert r.valid is True
        assert r.violations == ()

    def test_invalid_result_with_violations(self) -> None:
        r = TransitionValidationResult(valid=False, violations=("bad",))
        assert r.valid is False
        assert r.violations == ("bad",)

    def test_frozen(self) -> None:
        r = TransitionValidationResult(valid=True)
        with pytest.raises(AttributeError):
            r.valid = False  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Transition matrix — legal transitions
# ---------------------------------------------------------------------------


class TestTransitionMatrix:
    """Every legal transition should be accepted."""

    @pytest.mark.parametrize(
        "from_lane,to_lane,kwargs",
        [
            (None, Lane.PLANNED, {}),
            (Lane.PLANNED, Lane.CLAIMED, {}),
            (Lane.CLAIMED, Lane.IN_PROGRESS, {}),
            (Lane.IN_PROGRESS, Lane.FOR_REVIEW, {}),
            (
                Lane.FOR_REVIEW,
                Lane.DONE,
                {"evidence": None},  # placeholder, replaced below
            ),
            (
                Lane.FOR_REVIEW,
                Lane.IN_PROGRESS,
                {"review_ref": "PR#42"},
            ),
            (
                Lane.IN_PROGRESS,
                Lane.PLANNED,
                {"reason": "Reassigning"},
            ),
            (Lane.BLOCKED, Lane.IN_PROGRESS, {}),
            (Lane.PLANNED, Lane.BLOCKED, {}),
            (Lane.IN_PROGRESS, Lane.CANCELED, {}),
        ],
        ids=[
            "initial",
            "claim",
            "start",
            "submit",
            "approve",
            "rollback",
            "abandon",
            "unblock",
            "block",
            "cancel",
        ],
    )
    def test_legal_transition(
        self,
        from_lane: Lane | None,
        to_lane: Lane,
        kwargs: dict,  # type: ignore[type-arg]
    ) -> None:
        # Special handling for DONE which needs real evidence
        if to_lane is Lane.DONE:
            kwargs["evidence"] = _make_evidence()
        payload = _make_payload(from_lane=from_lane, to_lane=to_lane, **kwargs)
        result = validate_transition(payload)
        assert result.valid is True, f"Expected valid, got violations: {result.violations}"


# ---------------------------------------------------------------------------
# All illegal transitions
# ---------------------------------------------------------------------------


def _build_legal_set() -> set[tuple[Lane | None, Lane]]:
    """Build the full set of legal (from, to) pairs including dynamic ones."""
    legal: set[tuple[Lane | None, Lane]] = set(_ALLOWED_TRANSITIONS)
    non_terminal = [l for l in Lane if l not in TERMINAL_LANES]
    for src in non_terminal:
        legal.add((src, Lane.BLOCKED))
        legal.add((src, Lane.CANCELED))
    return legal


class TestIllegalTransitions:
    """Every transition NOT in the legal set should be rejected."""

    def test_all_illegal_transitions(self) -> None:
        legal = _build_legal_set()
        all_sources: list[Lane | None] = [None] + list(Lane)
        illegal_count = 0
        for src in all_sources:
            for dst in Lane:
                if (src, dst) in legal:
                    continue
                # Build payload — some combos need special handling
                # Skip combos that would fail Pydantic validation
                # (e.g. force without reason, done without evidence)
                kwargs: dict[str, object] = {
                    "from_lane": src,
                    "to_lane": dst,
                }
                if dst is Lane.DONE:
                    kwargs["evidence"] = _make_evidence()
                payload = _make_payload(**kwargs)  # type: ignore[arg-type]
                result = validate_transition(payload)
                assert result.valid is False, (
                    f"Expected ({src} -> {dst}) to be rejected but it was accepted"
                )
                illegal_count += 1
        # Sanity: we tested at least some illegal combos
        assert illegal_count > 0


# ---------------------------------------------------------------------------
# Guard conditions
# ---------------------------------------------------------------------------


class TestGuardConditions:
    """Test guard conditions on transitions."""

    def test_for_review_to_in_progress_without_review_ref(self) -> None:
        payload = _make_payload(
            from_lane=Lane.FOR_REVIEW,
            to_lane=Lane.IN_PROGRESS,
        )
        result = validate_transition(payload)
        assert result.valid is False
        assert any("review_ref" in v for v in result.violations)

    def test_for_review_to_in_progress_with_review_ref(self) -> None:
        payload = _make_payload(
            from_lane=Lane.FOR_REVIEW,
            to_lane=Lane.IN_PROGRESS,
            review_ref="PR#42",
        )
        result = validate_transition(payload)
        assert result.valid is True

    def test_in_progress_to_planned_without_reason(self) -> None:
        payload = _make_payload(
            from_lane=Lane.IN_PROGRESS,
            to_lane=Lane.PLANNED,
        )
        result = validate_transition(payload)
        assert result.valid is False
        assert any("reason" in v for v in result.violations)

    def test_in_progress_to_planned_with_reason(self) -> None:
        payload = _make_payload(
            from_lane=Lane.IN_PROGRESS,
            to_lane=Lane.PLANNED,
            reason="Reassigning to another agent",
        )
        result = validate_transition(payload)
        assert result.valid is True

    def test_force_exit_from_done(self) -> None:
        payload = _make_payload(
            from_lane=Lane.DONE,
            to_lane=Lane.IN_PROGRESS,
            force=True,
            reason="Reopening",
        )
        result = validate_transition(payload)
        assert result.valid is True

    def test_force_exit_from_canceled(self) -> None:
        payload = _make_payload(
            from_lane=Lane.CANCELED,
            to_lane=Lane.PLANNED,
            force=True,
            reason="Un-canceling",
        )
        result = validate_transition(payload)
        assert result.valid is True

    def test_no_force_exit_from_done(self) -> None:
        payload = _make_payload(
            from_lane=Lane.DONE,
            to_lane=Lane.IN_PROGRESS,
        )
        result = validate_transition(payload)
        assert result.valid is False
        assert any("terminal" in v for v in result.violations)

    def test_force_allows_nonstandard_transition(self) -> None:
        payload = _make_payload(
            from_lane=Lane.PLANNED,
            to_lane=Lane.FOR_REVIEW,
            force=True,
            reason="Skip",
        )
        result = validate_transition(payload)
        assert result.valid is True

    def test_multiple_violations_collected(self) -> None:
        # DONE -> IN_PROGRESS without force: terminal violation + matrix violation
        payload = _make_payload(
            from_lane=Lane.DONE,
            to_lane=Lane.IN_PROGRESS,
        )
        result = validate_transition(payload)
        assert result.valid is False
        assert len(result.violations) > 1

    def test_self_transition_rejected(self) -> None:
        payload = _make_payload(
            from_lane=Lane.PLANNED,
            to_lane=Lane.PLANNED,
        )
        result = validate_transition(payload)
        assert result.valid is False


# ---------------------------------------------------------------------------
# Helpers for Section 5 & 6 tests
# ---------------------------------------------------------------------------

_PROJECT_UUID = uuid.UUID("12345678-1234-1234-1234-123456789012")


def _make_event(
    event_id: str,
    wp_id: str,
    from_lane: Lane | None,
    to_lane: Lane,
    lamport_clock: int,
    timestamp: datetime | None = None,
    **kwargs: object,
) -> Event:
    """Helper to create status events for testing."""
    payload = StatusTransitionPayload(
        feature_slug="test-feature",
        wp_id=wp_id,
        from_lane=from_lane,
        to_lane=to_lane,
        actor="test-actor",
        execution_mode=ExecutionMode.WORKTREE,
        **kwargs,  # type: ignore[arg-type]
    )
    return Event(
        event_id=event_id,
        event_type=WP_STATUS_CHANGED,
        aggregate_id=f"test-feature/{wp_id}",
        payload=payload.model_dump(),
        timestamp=timestamp or datetime.now(timezone.utc),
        node_id="test-node",
        lamport_clock=lamport_clock,
        project_uuid=_PROJECT_UUID,
    )


# ---------------------------------------------------------------------------
# Section 5: Ordering tests
# ---------------------------------------------------------------------------


class TestStatusEventSortKey:
    """Test status_event_sort_key function."""

    def test_sort_by_lamport_clock(self) -> None:
        e1 = _make_event("01HV0000000000000000000001", "WP01", None, Lane.PLANNED, 1)
        e2 = _make_event("01HV0000000000000000000002", "WP01", Lane.PLANNED, Lane.CLAIMED, 2)
        assert status_event_sort_key(e1) < status_event_sort_key(e2)

    def test_tiebreak_by_timestamp(self) -> None:
        t1 = datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        t2 = datetime(2026, 1, 1, 0, 0, 1, tzinfo=timezone.utc)
        e1 = _make_event("01HV0000000000000000000002", "WP01", None, Lane.PLANNED, 1, timestamp=t1)
        e2 = _make_event("01HV0000000000000000000001", "WP01", Lane.PLANNED, Lane.CLAIMED, 1, timestamp=t2)
        assert status_event_sort_key(e1) < status_event_sort_key(e2)

    def test_tiebreak_by_event_id(self) -> None:
        t = datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        e1 = _make_event("01HV0000000000000000000001", "WP01", None, Lane.PLANNED, 1, timestamp=t)
        e2 = _make_event("01HV0000000000000000000002", "WP01", Lane.PLANNED, Lane.CLAIMED, 1, timestamp=t)
        assert status_event_sort_key(e1) < status_event_sort_key(e2)


class TestDedupEvents:
    """Test dedup_events function."""

    def test_removes_duplicates(self) -> None:
        e1 = _make_event("01HV0000000000000000000001", "WP01", None, Lane.PLANNED, 1)
        e2 = _make_event("01HV0000000000000000000001", "WP01", None, Lane.PLANNED, 1)
        result = dedup_events([e1, e2])
        assert len(result) == 1
        assert result[0] is e1

    def test_preserves_first_occurrence(self) -> None:
        t1 = datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        t2 = datetime(2026, 1, 1, 0, 0, 1, tzinfo=timezone.utc)
        e1 = _make_event("01HV0000000000000000000001", "WP01", None, Lane.PLANNED, 1, timestamp=t1)
        e2 = _make_event("01HV0000000000000000000001", "WP01", None, Lane.PLANNED, 2, timestamp=t2)
        result = dedup_events([e1, e2])
        assert len(result) == 1
        assert result[0].timestamp == t1

    def test_no_duplicates_passthrough(self) -> None:
        e1 = _make_event("01HV0000000000000000000001", "WP01", None, Lane.PLANNED, 1)
        e2 = _make_event("01HV0000000000000000000002", "WP01", Lane.PLANNED, Lane.CLAIMED, 2)
        result = dedup_events([e1, e2])
        assert len(result) == 2

    def test_empty_input(self) -> None:
        result = dedup_events([])
        assert result == []


# ---------------------------------------------------------------------------
# Section 6: Reducer tests
# ---------------------------------------------------------------------------


class TestReduceStatusEvents:
    """Test reduce_status_events function."""

    def test_happy_path_full_lifecycle(self) -> None:
        """planned -> claimed -> in_progress -> for_review -> done."""
        base_t = datetime(2026, 1, 1, tzinfo=timezone.utc)
        evidence = DoneEvidence(
            repos=[RepoEvidence(repo="test", branch="main", commit="abc123")],
            verification=[],
            review=ReviewVerdict(reviewer="alice", verdict="approved"),
        )
        events = [
            _make_event("01HV0000000000000000000001", "WP01", None, Lane.PLANNED, 1, timestamp=base_t),
            _make_event("01HV0000000000000000000002", "WP01", Lane.PLANNED, Lane.CLAIMED, 2, timestamp=base_t + timedelta(seconds=1)),
            _make_event("01HV0000000000000000000003", "WP01", Lane.CLAIMED, Lane.IN_PROGRESS, 3, timestamp=base_t + timedelta(seconds=2)),
            _make_event("01HV0000000000000000000004", "WP01", Lane.IN_PROGRESS, Lane.FOR_REVIEW, 4, timestamp=base_t + timedelta(seconds=3)),
            _make_event(
                "01HV0000000000000000000005", "WP01", Lane.FOR_REVIEW, Lane.DONE, 5,
                timestamp=base_t + timedelta(seconds=4),
                evidence=evidence,
            ),
        ]
        result = reduce_status_events(events)
        assert "WP01" in result.wp_states
        state = result.wp_states["WP01"]
        assert state.current_lane == Lane.DONE
        assert state.last_event_id == "01HV0000000000000000000005"
        assert state.evidence is not None
        assert result.anomalies == []
        assert result.event_count == 5

    def test_multiple_wps(self) -> None:
        """Interleaved events for WP01 and WP02."""
        base_t = datetime(2026, 1, 1, tzinfo=timezone.utc)
        events = [
            _make_event("01HV0000000000000000000001", "WP01", None, Lane.PLANNED, 1, timestamp=base_t),
            _make_event("01HV0000000000000000000002", "WP02", None, Lane.PLANNED, 2, timestamp=base_t + timedelta(seconds=1)),
            _make_event("01HV0000000000000000000003", "WP01", Lane.PLANNED, Lane.CLAIMED, 3, timestamp=base_t + timedelta(seconds=2)),
            _make_event("01HV0000000000000000000004", "WP02", Lane.PLANNED, Lane.CLAIMED, 4, timestamp=base_t + timedelta(seconds=3)),
        ]
        result = reduce_status_events(events)
        assert len(result.wp_states) == 2
        assert result.wp_states["WP01"].current_lane == Lane.CLAIMED
        assert result.wp_states["WP02"].current_lane == Lane.CLAIMED

    def test_empty_events(self) -> None:
        result = reduce_status_events([])
        assert result.wp_states == {}
        assert result.anomalies == []
        assert result.event_count == 0
        assert result.last_processed_event_id is None

    def test_non_status_events_skipped(self) -> None:
        """Events with wrong event_type are ignored."""
        event = Event(
            event_id="01HV0000000000000000000001",
            event_type="SomethingElse",
            aggregate_id="test/WP01",
            payload={},
            timestamp=datetime.now(timezone.utc),
            node_id="test",
            lamport_clock=1,
            project_uuid=_PROJECT_UUID,
        )
        result = reduce_status_events([event])
        assert result.wp_states == {}
        assert result.event_count == 0

    def test_invalid_transition_flagged(self) -> None:
        """Jump planned -> done without force/evidence -> anomaly."""
        base_t = datetime(2026, 1, 1, tzinfo=timezone.utc)
        # First set up WP01 at PLANNED
        e1 = _make_event("01HV0000000000000000000001", "WP01", None, Lane.PLANNED, 1, timestamp=base_t)
        # Try illegal jump: planned -> for_review (skipping claimed/in_progress)
        e2 = _make_event("01HV0000000000000000000002", "WP01", Lane.PLANNED, Lane.FOR_REVIEW, 2, timestamp=base_t + timedelta(seconds=1))
        result = reduce_status_events([e1, e2])
        assert len(result.anomalies) == 1
        assert result.anomalies[0].wp_id == "WP01"
        assert result.wp_states["WP01"].current_lane == Lane.PLANNED

    def test_from_lane_mismatch_flagged(self) -> None:
        """Event claims from_lane=claimed when WP is in planned -> anomaly."""
        base_t = datetime(2026, 1, 1, tzinfo=timezone.utc)
        e1 = _make_event("01HV0000000000000000000001", "WP01", None, Lane.PLANNED, 1, timestamp=base_t)
        # Claims from_lane=claimed but WP is actually in planned
        e2 = _make_event("01HV0000000000000000000002", "WP01", Lane.CLAIMED, Lane.IN_PROGRESS, 2, timestamp=base_t + timedelta(seconds=1))
        result = reduce_status_events([e1, e2])
        assert len(result.anomalies) == 1
        assert "mismatch" in result.anomalies[0].reason
        assert result.wp_states["WP01"].current_lane == Lane.PLANNED

    def test_rollback_precedence(self) -> None:
        """Two concurrent events (same lamport_clock) for same WP.

        One moves for_review -> done, other is rollback (for_review -> in_progress
        with review_ref). Final state should be in_progress because rollback
        is applied last.
        """
        base_t = datetime(2026, 1, 1, tzinfo=timezone.utc)
        evidence = DoneEvidence(
            repos=[RepoEvidence(repo="test", branch="main", commit="abc123")],
            verification=[],
            review=ReviewVerdict(reviewer="alice", verdict="approved"),
        )
        # Build up to FOR_REVIEW
        events = [
            _make_event("01HV0000000000000000000001", "WP01", None, Lane.PLANNED, 1, timestamp=base_t),
            _make_event("01HV0000000000000000000002", "WP01", Lane.PLANNED, Lane.CLAIMED, 2, timestamp=base_t + timedelta(seconds=1)),
            _make_event("01HV0000000000000000000003", "WP01", Lane.CLAIMED, Lane.IN_PROGRESS, 3, timestamp=base_t + timedelta(seconds=2)),
            _make_event("01HV0000000000000000000004", "WP01", Lane.IN_PROGRESS, Lane.FOR_REVIEW, 4, timestamp=base_t + timedelta(seconds=3)),
        ]
        # Two concurrent events at same lamport_clock=5
        e_done = _make_event(
            "01HV0000000000000000000005", "WP01", Lane.FOR_REVIEW, Lane.DONE, 5,
            timestamp=base_t + timedelta(seconds=4),
            evidence=evidence,
        )
        e_rollback = _make_event(
            "01HV0000000000000000000006", "WP01", Lane.FOR_REVIEW, Lane.IN_PROGRESS, 5,
            timestamp=base_t + timedelta(seconds=4),
            review_ref="PR#42",
        )
        events.extend([e_done, e_rollback])
        result = reduce_status_events(events)
        assert result.wp_states["WP01"].current_lane == Lane.IN_PROGRESS

    def test_event_count_correct(self) -> None:
        """Verify count matches unique status events."""
        base_t = datetime(2026, 1, 1, tzinfo=timezone.utc)
        events = [
            _make_event("01HV0000000000000000000001", "WP01", None, Lane.PLANNED, 1, timestamp=base_t),
            _make_event("01HV0000000000000000000002", "WP01", Lane.PLANNED, Lane.CLAIMED, 2, timestamp=base_t + timedelta(seconds=1)),
            # Duplicate of first event
            _make_event("01HV0000000000000000000001", "WP01", None, Lane.PLANNED, 1, timestamp=base_t),
        ]
        result = reduce_status_events(events)
        assert result.event_count == 2  # deduped

    def test_last_processed_event_id(self) -> None:
        """Verify it's the last event in sorted order."""
        base_t = datetime(2026, 1, 1, tzinfo=timezone.utc)
        events = [
            _make_event("01HV0000000000000000000001", "WP01", None, Lane.PLANNED, 1, timestamp=base_t),
            _make_event("01HV0000000000000000000002", "WP01", Lane.PLANNED, Lane.CLAIMED, 2, timestamp=base_t + timedelta(seconds=1)),
        ]
        result = reduce_status_events(events)
        assert result.last_processed_event_id == "01HV0000000000000000000002"
