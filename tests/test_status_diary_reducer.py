"""Reducer unit tests for the status diary (:mod:`spec_kitty_events.diary`).

Ports the behavioural core of the CLI's ``tests/status/test_reducer.py``
(issue #41 moved the reducer here verbatim): empty stream, ordering,
deduplication, force_count, rollback-aware concurrency, runtime-slot
carry-forward, the ``planned -> claimed`` policy_metadata claim triple,
the ``review_result`` slot rules, annotation folding, the traversal-guarded
mission slug, the row-partition contract, plus the packaged golden replays.
"""

from __future__ import annotations

import json
from typing import Any

import pytest

import spec_kitty_events.status as status_module
from spec_kitty_events.conformance.loader import (
    load_reducer_output,
    load_replay_stream,
)
from spec_kitty_events.diary import (
    ANNOTATION_KIND,
    NON_DISPLAY_LANES,
    DiaryError,
    EventStream,
    InnerStateChanged,
    Lane,
    State,
    StatusEvent,
    parse_diary,
    reduce,
    reduce_parsed,
)

# ── Helpers ────────────────────────────────────────────────────────────────────


def _ulid(n: int) -> str:
    return "01JZZZZ" + "0" * 15 + f"{n:04d}"


def _row(
    event_id: str,
    wp_id: str = "WP01",
    from_lane: str | None = "planned",
    to_lane: str = "claimed",
    at: str = "2026-02-08T12:00:00+00:00",
    actor: Any = "claude-opus",
    *,
    mission_slug: str = "034-feature-name",
    force: bool = False,
    execution_mode: str = "worktree",
    reason: str | None = None,
    review_ref: str | None = None,
    evidence: dict[str, Any] | None = None,
    review_result: dict[str, Any] | None = None,
    policy_metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build one raw diary row with sensible defaults."""
    row: dict[str, Any] = {
        "event_id": event_id,
        "mission_slug": mission_slug,
        "wp_id": wp_id,
        "from_lane": from_lane,
        "to_lane": to_lane,
        "at": at,
        "actor": actor,
        "force": force,
        "execution_mode": execution_mode,
        "reason": reason,
        "review_ref": review_ref,
        "evidence": evidence,
    }
    if review_result is not None:
        row["review_result"] = review_result
    if policy_metadata is not None:
        row["policy_metadata"] = policy_metadata
    return row


def _annotation(
    event_id: str,
    wp_id: str = "WP01",
    at: str = "2026-02-08T12:00:00+00:00",
    actor: Any = "claude",
    delta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "event_id": event_id,
        "kind": ANNOTATION_KIND,
        "wp_id": wp_id,
        "at": at,
        "actor": actor,
        "delta": delta or {},
    }


_DONE_EVIDENCE = {
    "review": {
        "reviewer": "reviewer-1",
        "verdict": "approved",
        "reference": "feedback://034/WP01/approval",
    },
    "repos": [{"repo": "demo", "branch": "kitty/m-01", "commit": "abc1234567890"}],
    "verification": [{"command": "make test-fast", "result": "pass", "summary": "green"}],
}

_REVIEW_RESULT = {
    "reviewer": "reviewer-1",
    "verdict": "approved",
    "reference": "feedback://034/WP01/approved",
}


# ── Empty stream ───────────────────────────────────────────────────────────────


class TestReduceEmpty:
    def test_reduce_empty_events(self) -> None:
        state = reduce([])

        assert state.mission_slug == ""
        assert state.event_count == 0
        assert state.last_event_id is None
        assert state.work_packages == {}
        # NON_DISPLAY_LANES (genesis, uninitialized) are excluded from the summary
        assert state.summary == {lane.value: 0 for lane in Lane if lane not in NON_DISPLAY_LANES}

    def test_reduce_generator_input(self) -> None:
        rows = iter([_row(_ulid(1))])
        state = reduce(rows)
        assert state.event_count == 1


# ── Basic folds ────────────────────────────────────────────────────────────────


class TestReduceSingleEvent:
    def test_reduce_single_event(self) -> None:
        state = reduce([_row(_ulid(1), actor="claude-opus")])

        assert state.mission_slug == "034-feature-name"
        assert state.event_count == 1
        assert state.last_event_id == _ulid(1)
        wp = state.work_packages["WP01"]
        assert wp["lane"] == "claimed"
        assert wp["actor"] == "claude-opus"
        assert wp["last_transition_at"] == "2026-02-08T12:00:00+00:00"
        assert wp["last_event_id"] == _ulid(1)
        assert wp["force_count"] == 0
        assert state.summary["claimed"] == 1


class TestReduceOrderedEvents:
    def test_reduce_ordered_events(self) -> None:
        events = [
            _row(_ulid(1), to_lane="claimed", at="2026-02-08T12:00:00+00:00"),
            _row(
                _ulid(2),
                from_lane="claimed",
                to_lane="in_progress",
                at="2026-02-08T13:00:00+00:00",
            ),
            _row(
                _ulid(3),
                from_lane="in_progress",
                to_lane="for_review",
                at="2026-02-08T14:00:00+00:00",
            ),
        ]
        state = reduce(events)

        assert state.event_count == 3
        assert state.work_packages["WP01"]["lane"] == "for_review"
        assert state.summary["for_review"] == 1


class TestReduceOutOfOrder:
    def test_reduce_out_of_order_events(self) -> None:
        """Events are sorted by (at, event_id), so order in list doesn't matter."""
        events = [
            _row(
                _ulid(3),
                from_lane="in_progress",
                to_lane="for_review",
                at="2026-02-08T14:00:00+00:00",
            ),
            _row(_ulid(1), to_lane="claimed", at="2026-02-08T12:00:00+00:00"),
            _row(
                _ulid(2),
                from_lane="claimed",
                to_lane="in_progress",
                at="2026-02-08T13:00:00+00:00",
            ),
        ]
        state = reduce(events)

        assert state.work_packages["WP01"]["lane"] == "for_review"
        assert state.last_event_id == _ulid(3)


class TestReduceSameTimestampTiebreak:
    def test_distinct_same_at_events_are_order_independent(self) -> None:
        """Two distinct events for one WP sharing `at` still fold deterministically.

        The sort key is ``(at, event_id)``, not ``at`` alone: without the
        ``event_id`` tiebreak, a stable sort would apply same-``at`` events in
        *list* order, so the fold would depend on the order rows happen to
        appear in ``status.events.jsonl`` rather than on the events themselves.
        """
        claim = _row(_ulid(1), from_lane="planned", to_lane="claimed")
        start = _row(_ulid(2), from_lane="claimed", to_lane="in_progress")
        assert claim["at"] == start["at"]  # concurrent: the tiebreak is what matters

        forward = reduce([claim, start])
        reversed_order = reduce([start, claim])

        assert forward.to_dict() == reversed_order.to_dict()
        assert forward.work_packages["WP01"]["lane"] == "in_progress"
        assert forward.work_packages["WP01"]["last_event_id"] == _ulid(2)


class TestReduceDeduplication:
    def test_reduce_deduplication(self) -> None:
        """Duplicate event_ids are deduplicated; first occurrence kept."""
        event = _row(_ulid(1), actor="claude-opus")
        # Same event_id but different actor (simulating corruption)
        duplicate = _row(_ulid(1), actor="other-agent")
        state = reduce([event, duplicate])

        assert state.event_count == 1
        assert state.work_packages["WP01"]["actor"] == "claude-opus"


class TestReduceMultipleWPs:
    def test_reduce_multiple_wps(self) -> None:
        events = [
            _row(_ulid(1), wp_id="WP01", to_lane="claimed"),
            _row(_ulid(2), wp_id="WP02", to_lane="claimed"),
            _row(_ulid(3), wp_id="WP01", from_lane="claimed", to_lane="in_progress"),
        ]
        state = reduce(events)

        assert set(state.work_packages) == {"WP01", "WP02"}
        assert state.work_packages["WP01"]["lane"] == "in_progress"
        assert state.work_packages["WP02"]["lane"] == "claimed"
        assert state.summary["claimed"] == 1
        assert state.summary["in_progress"] == 1


class TestReduceForceCount:
    def test_force_count_increments_and_carries(self) -> None:
        events = [
            _row(_ulid(1), to_lane="claimed", force=False),
            _row(
                _ulid(2),
                from_lane="claimed",
                to_lane="planned",
                force=True,
                reason="rewind",
            ),
            _row(_ulid(3), to_lane="claimed", force=True, reason="reclaim"),
        ]
        state = reduce(events)
        wp = state.work_packages["WP01"]
        assert wp["force_count"] == 2
        assert wp["lane"] == "claimed"


# ── Rollback-aware concurrency ─────────────────────────────────────────────────


class TestReduceConcurrentRollbackPrecedence:
    def test_in_review_to_in_progress_rollback_beats_concurrent_approval(self) -> None:
        """Current reviewer rollback transition wins over same-timestamp approval."""
        at = "2026-02-08T15:00:00+00:00"
        events = [
            _row(
                _ulid(1),
                from_lane="in_review",
                to_lane="in_progress",
                at=at,
                actor="reviewer-a",
            ),
            _row(
                _ulid(2),
                from_lane="in_review",
                to_lane="approved",
                at=at,
                actor="reviewer-b",
                review_ref="review://WP01/approved",
            ),
        ]

        state = reduce(events)

        assert state.work_packages["WP01"]["lane"] == "in_progress"
        assert state.work_packages["WP01"]["last_event_id"] == _ulid(1)
        assert state.summary["in_progress"] == 1
        assert state.summary["approved"] == 0

    def test_legacy_for_review_rollback_still_beats_concurrent_forward(self) -> None:
        """Legacy reviewer rollback shape keeps rollback precedence."""
        at = "2026-02-08T15:00:00+00:00"
        events = [
            _row(
                _ulid(1),
                from_lane="for_review",
                to_lane="in_progress",
                at=at,
                actor="reviewer-a",
                review_ref="review://WP01/changes-requested",
            ),
            _row(
                _ulid(2),
                from_lane="for_review",
                to_lane="approved",
                at=at,
                actor="reviewer-b",
                review_ref="review://WP01/approved",
            ),
        ]

        state = reduce(events)

        assert state.work_packages["WP01"]["lane"] == "in_progress"
        assert state.work_packages["WP01"]["last_event_id"] == _ulid(1)


class TestSummaryCounts:
    def test_summary_counts_match_wp_states(self) -> None:
        events = [
            _row(_ulid(1), wp_id="WP01", to_lane="in_progress"),
            _row(_ulid(2), wp_id="WP02", to_lane="in_progress"),
            _row(_ulid(3), wp_id="WP03", from_lane="planned", to_lane="for_review"),
            _row(
                _ulid(4),
                wp_id="WP04",
                from_lane="for_review",
                to_lane="done",
                evidence=_DONE_EVIDENCE,
            ),
        ]
        state = reduce(events)

        lane_counts: dict[str, int] = {
            lane.value: 0 for lane in Lane if lane not in NON_DISPLAY_LANES
        }
        for wp_state in state.work_packages.values():
            lane_counts[wp_state["lane"]] += 1

        assert state.summary == lane_counts


# ── Runtime slots ──────────────────────────────────────────────────────────────


class TestRuntimeSlotCarryForward:
    def test_transition_preserves_runtime_slots(self) -> None:
        """A later transition never erases slots written by earlier ones."""
        events = [
            _row(
                _ulid(1),
                to_lane="claimed",
                policy_metadata={
                    "shell_pid": 7,
                    "shell_pid_created_at": "t1",
                    "agent": "claude",
                },
            ),
            _annotation(
                _ulid(2),
                delta={
                    "note": "working",
                    "subtasks": {"T1": "done"},
                    "tracker_refs": ["TCK-1"],
                },
            ),
            _row(_ulid(3), from_lane="claimed", to_lane="in_progress"),
        ]
        state = reduce(events)
        wp = state.work_packages["WP01"]
        assert wp["shell_pid"] == 7
        assert wp["agent"] == "claude"
        assert wp["notes"] == ["working"]
        assert wp["subtasks"] == {"T1": "done"}
        assert wp["tracker_refs"] == ["TCK-1"]
        assert wp["lane"] == "in_progress"

    def test_claim_triple_from_policy_metadata(self) -> None:
        events = [
            _row(
                _ulid(1),
                to_lane="claimed",
                policy_metadata={
                    "shell_pid": 99,
                    "shell_pid_created_at": "2026-02-08T12:00:01+00:00",
                    "agent": "codex",
                },
            )
        ]
        state = reduce(events)
        wp = state.work_packages["WP01"]
        assert wp["shell_pid"] == 99
        assert wp["shell_pid_created_at"] == "2026-02-08T12:00:01+00:00"
        assert wp["agent"] == "codex"

    def test_empty_agent_sidecar_is_a_no_op(self) -> None:
        """An empty agent sidecar never blanks an existing slot."""
        events = [
            _row(_ulid(1), to_lane="claimed", policy_metadata={"agent": "claude"}),
            _row(
                _ulid(2),
                from_lane="claimed",
                to_lane="planned",
                force=True,
                reason="rewind",
            ),
            _row(_ulid(3), to_lane="claimed", policy_metadata={"agent": ""}),
        ]
        state = reduce(events)
        assert state.work_packages["WP01"]["agent"] == "claude"


# ── review_result slot rules ───────────────────────────────────────────────────


class TestReviewResultSlot:
    def test_outbound_from_in_review_writes_explicit_none(self) -> None:
        """A forced exit from in_review with no verdict lands an explicit None."""
        events = [
            _row(
                _ulid(1),
                from_lane="planned",
                to_lane="in_review",
                force=True,
                reason="skip ahead",
            ),
            _row(
                _ulid(2),
                from_lane="in_review",
                to_lane="planned",
                force=True,
                reason="forced rewind",
            ),
        ]
        state = reduce(events)
        assert state.work_packages["WP01"]["review_result"] is None

    def test_populated_verdict_overrides_regardless_of_from_lane(self) -> None:
        """A single-hop transition carrying a verdict records it."""
        events = [
            _row(
                _ulid(1),
                from_lane="in_progress",
                to_lane="approved",
                evidence=_DONE_EVIDENCE,
                review_result=_REVIEW_RESULT,
            ),
        ]
        state = reduce(events)
        assert state.work_packages["WP01"]["review_result"] == _REVIEW_RESULT

    def test_slot_is_sticky_when_absent(self) -> None:
        """An unrelated later transition carries the verdict forward verbatim."""
        events = [
            _row(
                _ulid(1),
                from_lane="in_progress",
                to_lane="approved",
                evidence=_DONE_EVIDENCE,
                review_result=_REVIEW_RESULT,
            ),
            _row(
                _ulid(2),
                from_lane="approved",
                to_lane="done",
                force=True,
                reason="close",
            ),
        ]
        state = reduce(events)
        assert state.work_packages["WP01"]["review_result"] == _REVIEW_RESULT


# ── Annotation folding ─────────────────────────────────────────────────────────


class TestAnnotationFolding:
    def test_annotation_only_stream_materializes_uninitialized_wp(self) -> None:
        events = [_annotation(_ulid(1), delta={"note": "runtime only"})]
        state = reduce(events)

        wp = state.work_packages["WP01"]
        assert wp["lane"] == str(Lane.UNINITIALIZED)
        # Non-display lanes never reach the board summary.
        assert sum(state.summary.values()) == 0
        # Annotations do not move the snapshot markers.
        assert state.last_event_id is None
        assert state.materialized_at == ""

    def test_replace_slots_fold_latest_wins(self) -> None:
        events = [
            _annotation(_ulid(1), delta={"role": "implementer", "model": "m1"}),
            _annotation(_ulid(2), delta={"role": "reviewer"}),
        ]
        state = reduce(events)
        wp = state.work_packages["WP01"]
        assert wp["role"] == "reviewer"
        assert wp["model"] == "m1"

    def test_blank_scalar_delta_is_a_no_op(self) -> None:
        events = [
            _annotation(_ulid(1), delta={"assignee": "avery"}),
            _annotation(_ulid(2), delta={"assignee": ""}),
        ]
        state = reduce(events)
        assert state.work_packages["WP01"]["assignee"] == "avery"

    def test_notes_append_and_subtasks_merge(self) -> None:
        events = [
            _annotation(_ulid(1), delta={"note": "one", "subtasks": {"T1": "done"}}),
            _annotation(_ulid(2), delta={"note": "two", "subtasks": {"T2": "done"}}),
        ]
        state = reduce(events)
        wp = state.work_packages["WP01"]
        assert wp["notes"] == ["one", "two"]
        assert wp["subtasks"] == {"T1": "done", "T2": "done"}

    def test_tracker_refs_union_vs_replace(self) -> None:
        events = [
            _annotation(_ulid(1), delta={"tracker_refs": ["A", "B"]}),
            _annotation(_ulid(2), delta={"tracker_refs": ["B", "C"]}),
            _annotation(_ulid(3), delta={"tracker_refs_replace": ["X", "X", "Y"]}),
        ]
        state = reduce(events)
        assert state.work_packages["WP01"]["tracker_refs"] == ["X", "Y"]

    def test_review_release_sentinel_clears_override(self) -> None:
        """The all-empty override is a deliberate clear, not a persisted {}."""
        events = [
            _annotation(
                _ulid(1),
                delta={
                    "review": {
                        "at": "2026-02-08T12:00:00+00:00",
                        "actor": "arbiter",
                        "wp_id": "WP01",
                        "reason": "override",
                    }
                },
            ),
            _annotation(
                _ulid(2),
                delta={"review": {"at": "", "actor": "", "wp_id": "", "reason": ""}},
            ),
        ]
        state = reduce(events)
        assert state.work_packages["WP01"]["review"] is None

    def test_partial_review_override_is_persisted(self) -> None:
        events = [
            _annotation(
                _ulid(1),
                delta={
                    "review": {
                        "at": "2026-02-08T12:00:00+00:00",
                        "actor": "arbiter",
                        "wp_id": "WP01",
                        "reason": "",
                    }
                },
            ),
        ]
        state = reduce(events)
        override = state.work_packages["WP01"]["review"]
        assert override == {
            "at": "2026-02-08T12:00:00+00:00",
            "actor": "arbiter",
            "wp_id": "WP01",
            "reason": "",
        }

    def test_claim_release_clears_only_the_claim_triple(self) -> None:
        events = [
            _row(
                _ulid(1),
                to_lane="claimed",
                policy_metadata={"shell_pid": 5, "agent": "claude"},
            ),
            _annotation(_ulid(2), delta={"assignee": "avery", "release_runtime_claim": True}),
        ]
        state = reduce(events)
        wp = state.work_packages["WP01"]
        assert wp["agent"] is None
        assert wp["shell_pid"] is None
        assert wp["shell_pid_created_at"] is None
        # Not part of the claim triple.
        assert wp["assignee"] == "avery"

    def test_annotations_never_move_force_count(self) -> None:
        events = [
            _row(_ulid(1), to_lane="claimed", force=True, reason="claim"),
            _annotation(_ulid(2), delta={"note": "x"}),
        ]
        state = reduce(events)
        assert state.work_packages["WP01"]["force_count"] == 1


class TestAnnotationSameTimestampTiebreak:
    def test_distinct_same_at_annotations_are_order_independent(self) -> None:
        """Two distinct annotations for one WP sharing `at` still fold deterministically.

        The annotation-pass sort key is ``(at, event_id)``, not ``at`` alone:
        without the ``event_id`` tiebreak, a stable sort would apply same-``at``
        annotations in *list* order, so the fold would depend on the order rows
        happen to appear in ``status.events.jsonl`` rather than on the events
        themselves (#2684 determinism).
        """
        first = _annotation(_ulid(1), delta={"role": "implementer"})
        second = _annotation(_ulid(2), delta={"role": "reviewer"})
        assert first["at"] == second["at"]  # concurrent: the tiebreak is what matters

        forward = reduce([first, second])
        reversed_order = reduce([second, first])

        assert forward.to_dict() == reversed_order.to_dict()
        assert forward.work_packages["WP01"]["role"] == "reviewer"

    def test_later_at_annotation_wins_even_with_earlier_event_id(self) -> None:
        """The annotation-pass sort key's `at` component is pinned, not just `event_id`.

        The key is ``(at, event_id)``: `at` is the primary component. Pick an
        `event_id` order that *disagrees* with the `at` order -- the earlier
        ULID carries the later timestamp -- so that dropping `at` from the key
        (sorting by `event_id` alone) would flip the fold winner. Sorting by
        `at` correctly, the later-timestamp annotation applies last and wins,
        regardless of which order the rows are given in (#166).
        """
        earlier_ulid_later_at = _annotation(
            _ulid(1), at="2026-02-08T13:00:00+00:00", delta={"role": "LATER-at"}
        )
        later_ulid_earlier_at = _annotation(
            _ulid(2),
            at="2026-02-08T12:00:00+00:00",
            delta={"role": "earlier-at-but-later-ulid"},
        )

        forward = reduce([earlier_ulid_later_at, later_ulid_earlier_at])
        reversed_order = reduce([later_ulid_earlier_at, earlier_ulid_later_at])

        assert forward.to_dict() == reversed_order.to_dict()
        assert forward.work_packages["WP01"]["role"] == "LATER-at"


# ── Mission slug safety ────────────────────────────────────────────────────────


class TestMissionSlugSafety:
    def test_traversal_slug_is_downgraded_to_empty(self) -> None:
        events = [_row(_ulid(1), mission_slug="../../../../tmp/evil")]
        state = reduce(events)
        assert state.mission_slug == ""
        # ...and the serialized payload stays canonical.
        assert state.to_dict()["mission_slug"] == ""

    def test_structured_actor_projects_to_string_identity(self) -> None:
        events = [
            _row(
                _ulid(1),
                actor={
                    "role": "implementer",
                    "profile": "p",
                    "tool": "claude",
                    "model": "opus",
                },
            )
        ]
        state = reduce(events)
        assert state.work_packages["WP01"]["actor"] == "claude"


# ── Row partition contract ─────────────────────────────────────────────────────


class TestRowPartition:
    def test_unknown_kind_fails_loud(self) -> None:
        row = _row(_ulid(1))
        row["kind"] = "mystery"
        with pytest.raises(DiaryError, match="Unknown event kind"):
            reduce([row])

    def test_unknown_event_type_rows_are_ignored(self) -> None:
        """Non-status writers sharing the file are ignored, not fatal (#41)."""
        noise = [
            {
                "event_type": "DecisionPointOpened",
                "event_id": "dp-1",
                "payload": {"question": "ship?"},
            },
            {"event_type": "SomeFutureProtocolEventV99", "event_id": "fut-1"},
            {
                "event_name": "retrospective.requested",
                "at": "2026-02-08T12:00:00+00:00",
                "event_id": "retro-1",
                "payload": {},
            },
        ]
        state = reduce([*noise, _row(_ulid(1))])
        assert state.event_count == 1

    @pytest.mark.parametrize(
        "event_type",
        ["RetrospectiveCaptured", "RetrospectiveCaptureFailed", "RetrospectiveSkipped"],
    )
    def test_type_envelope_retrospective_lifecycle_rows_are_ignored(self, event_type: str) -> None:
        """The CLI's top-level `type` retrospective lifecycle rows are non-lane (#41/#42)."""
        lifecycle_row = {
            "type": event_type,
            "event_id": "01KS049J4V9CSWBKJHTY2FB014",
            "mission_slug": "demo",
            "wp_id": None,
            "at": "2026-05-01T10:25:00+00:00",
        }
        state = reduce([lifecycle_row, _row(_ulid(1))])
        assert state.event_count == 1

    def test_malformed_lane_row_fails_loud(self) -> None:
        with pytest.raises(DiaryError, match="Invalid lane-transition row"):
            reduce([{"wp_id": "WP01"}])  # missing every required key

    def test_non_object_row_fails_loud(self) -> None:
        with pytest.raises(DiaryError, match="expected JSON object"):
            reduce(["not a dict"])  # type: ignore[list-item]

    def test_parse_diary_partitions_by_kind(self) -> None:
        rows = [
            _row(_ulid(1)),
            _annotation(_ulid(2), delta={"note": "n"}),
            {"event_type": "DecisionPointResolved", "event_id": "dp-2"},
        ]
        stream = parse_diary(rows)
        assert isinstance(stream, EventStream)
        assert [e.event_id for e in stream.transitions] == [_ulid(1)]
        assert [a.event_id for a in stream.annotations] == [_ulid(2)]

    def test_annotation_requires_valid_ulid(self) -> None:
        row = _annotation("not-a-ulid")
        with pytest.raises(DiaryError, match="not a valid ULID"):
            parse_diary([row])


# ── Typed fold parity + serialization ──────────────────────────────────────────


class TestTypedFoldParity:
    def test_reduce_parsed_matches_reduce(self) -> None:
        rows = [_row(_ulid(1)), _annotation(_ulid(2), delta={"note": "n"})]
        via_dicts = reduce(rows)
        stream = parse_diary(rows)
        via_typed = reduce_parsed(stream.transitions, stream.annotations)
        assert via_dicts.to_dict() == via_typed.to_dict()

    def test_to_dict_round_trip(self) -> None:
        state = reduce(
            [
                _row(_ulid(1), mission_slug="041-reducer-unification"),
            ]
        )
        restored = State.from_dict(state.to_dict())
        assert restored.to_dict() == state.to_dict()

    def test_to_dict_is_byte_stable(self) -> None:
        rows = [_row(_ulid(1)), _annotation(_ulid(2), delta={"note": "n"})]
        a = reduce(list(rows))
        b = reduce(list(reversed(rows)))
        doc_a = json.dumps(a.to_dict(), sort_keys=True, indent=2, ensure_ascii=False) + "\n"
        doc_b = json.dumps(b.to_dict(), sort_keys=True, indent=2, ensure_ascii=False) + "\n"
        assert doc_a == doc_b


# ── Facade re-export ───────────────────────────────────────────────────────────


def test_status_facade_exposes_the_shared_entry_point() -> None:
    """``spec_kitty_events.status.reduce`` IS the diary reducer (issue #41 API)."""
    assert status_module.reduce is reduce
    assert status_module.State is State
    assert status_module.parse_diary is parse_diary
    assert status_module.DiaryError is DiaryError


# ── Packaged golden replays ────────────────────────────────────────────────────


_GOLDEN_REPLAYS = (
    "status-diary-replay-fresh-mission",
    "status-diary-replay-every-lane",
    "status-diary-replay-out-of-order-duplicates",
    "status-diary-replay-unknown-kinds",
)


@pytest.mark.parametrize("fixture_id", _GOLDEN_REPLAYS)
def test_golden_replay(fixture_id: str) -> None:
    """reduce() reproduces the pinned golden output for each packaged stream."""
    rows = load_replay_stream(fixture_id)
    expected = load_reducer_output(f"{fixture_id}-output")
    assert reduce(rows).to_dict() == expected


@pytest.mark.parametrize("fixture_id", _GOLDEN_REPLAYS)
def test_golden_replay_is_permutation_invariant(fixture_id: str) -> None:
    """Any permutation of the same rows reduces to the same state."""
    import random

    rows = load_replay_stream(fixture_id)
    baseline = reduce(list(rows)).to_dict()
    shuffled = list(rows)
    random.Random(41).shuffle(shuffled)
    assert reduce(shuffled).to_dict() == baseline


def test_every_golden_stream_has_a_registered_pair() -> None:
    """Each replay id has its reducer_output counterpart in the manifest."""
    for fixture_id in _GOLDEN_REPLAYS:
        rows = load_replay_stream(fixture_id)
        output = load_reducer_output(f"{fixture_id}-output")
        assert rows and output


def test_status_event_round_trips_through_the_row_shape() -> None:
    """StatusEvent.to_dict rows re-parse losslessly (wire-format stability)."""
    event = StatusEvent.from_dict(_row(_ulid(9), to_lane="done", evidence=_DONE_EVIDENCE))
    reparsed = StatusEvent.from_dict(event.to_dict())
    assert reparsed == event


def test_inner_state_changed_round_trips_through_the_row_shape() -> None:
    record = InnerStateChanged.from_dict(_annotation(_ulid(8), delta={"note": "n"}))
    reparsed = InnerStateChanged.from_dict(record.to_dict())
    assert reparsed == record
