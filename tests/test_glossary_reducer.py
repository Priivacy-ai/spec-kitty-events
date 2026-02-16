"""Tests for glossary reducer — happy path and determinism (WP08)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from spec_kitty_events import (
    Event,
    ReducedGlossaryState,
    SpecKittyEventsError,
    reduce_glossary_events,
)

UTC = timezone.utc

_clock_counter = 0


def make_glossary_event(
    event_type: str,
    payload: dict,  # type: ignore[type-arg]
    event_id: str | None = None,
    lamport_clock: int | None = None,
    aggregate_id: str = "mission-001",
) -> Event:
    """Factory for creating test Event instances with glossary payloads."""
    global _clock_counter
    if lamport_clock is None:
        _clock_counter += 1
        lamport_clock = _clock_counter
    # Generate 26-char ULID-like IDs
    if event_id is None:
        event_id = f"01HX{lamport_clock:022d}"
    corr_id = f"01CX{lamport_clock:022d}"
    return Event(
        event_id=event_id,
        event_type=event_type,
        aggregate_id=aggregate_id,
        payload=payload,
        timestamp=datetime(2024, 1, 1, 0, 0, lamport_clock % 60, tzinfo=UTC).isoformat(),
        node_id="test-node",
        lamport_clock=lamport_clock,
        correlation_id=corr_id,
        project_uuid=uuid.UUID("12345678-1234-5678-1234-567812345678"),
        schema_version="2.0.0",
    )


# ── T037: Empty Input ────────────────────────────────────────────────────────


class TestReducerEmptyInput:
    """Tests for reducer short-circuit paths."""

    def test_empty_list(self) -> None:
        state = reduce_glossary_events([])
        assert state == ReducedGlossaryState()
        assert state.current_strictness == "medium"
        assert state.mission_id == ""
        assert state.event_count == 0
        assert state.last_processed_event_id is None

    def test_non_glossary_events(self) -> None:
        event = make_glossary_event(
            "WPStatusChanged",
            {"wp_id": "WP01", "new_lane": "doing"},
            lamport_clock=1,
        )
        state = reduce_glossary_events([event])
        assert state == ReducedGlossaryState()


# ── T038: Full Happy Path ────────────────────────────────────────────────────


class TestReducerHappyPath:
    """End-to-end reducer test."""

    def test_full_lifecycle(self) -> None:
        events = [
            make_glossary_event("GlossaryScopeActivated", {
                "mission_id": "m1", "scope_id": "s1",
                "scope_type": "team_domain", "glossary_version_id": "v1",
            }, lamport_clock=1),
            make_glossary_event("GlossaryStrictnessSet", {
                "mission_id": "m1", "new_strictness": "max", "actor": "admin",
            }, lamport_clock=2),
            make_glossary_event("TermCandidateObserved", {
                "mission_id": "m1", "scope_id": "s1", "step_id": "st1",
                "term_surface": "dashboard", "confidence": 0.85, "actor": "a1",
            }, lamport_clock=3),
            make_glossary_event("GlossarySenseUpdated", {
                "mission_id": "m1", "scope_id": "s1",
                "term_surface": "dashboard", "after_sense": "UI panel",
                "reason": "initial", "actor": "a1",
            }, lamport_clock=4),
            make_glossary_event("SemanticCheckEvaluated", {
                "mission_id": "m1", "scope_id": "s1", "step_id": "st2",
                "conflicts": [{"term": "dashboard", "nature": "overloaded",
                               "severity": "high", "description": "ambig"}],
                "severity": "high", "confidence": 0.9,
                "recommended_action": "block", "effective_strictness": "max",
            }, lamport_clock=5),
            make_glossary_event("GenerationBlockedBySemanticConflict", {
                "mission_id": "m1", "step_id": "st2",
                "conflict_event_ids": ["e5"], "blocking_strictness": "max",
            }, lamport_clock=6),
        ]

        state = reduce_glossary_events(events)

        assert len(state.active_scopes) == 1
        assert state.current_strictness == "max"
        assert len(state.strictness_history) == 1
        assert "dashboard" in state.term_candidates
        assert len(state.term_candidates["dashboard"]) == 1
        assert "dashboard" in state.term_senses
        assert state.term_senses["dashboard"].after_sense == "UI panel"
        assert len(state.semantic_checks) == 1
        assert len(state.generation_blocks) == 1
        assert state.event_count == 6
        assert state.mission_id == "m1"
        assert len(state.anomalies) == 0


# ── T039: Strictness Tracking ────────────────────────────────────────────────


class TestReducerStrictnessTracking:
    """Tests for strictness state management."""

    def test_default_strictness(self) -> None:
        events = [
            make_glossary_event("GlossaryScopeActivated", {
                "mission_id": "m1", "scope_id": "s1",
                "scope_type": "team_domain", "glossary_version_id": "v1",
            }, lamport_clock=1),
        ]
        state = reduce_glossary_events(events)
        assert state.current_strictness == "medium"
        assert len(state.strictness_history) == 0

    def test_single_change(self) -> None:
        events = [
            make_glossary_event("GlossaryScopeActivated", {
                "mission_id": "m1", "scope_id": "s1",
                "scope_type": "team_domain", "glossary_version_id": "v1",
            }, lamport_clock=1),
            make_glossary_event("GlossaryStrictnessSet", {
                "mission_id": "m1", "new_strictness": "max",
                "previous_strictness": "medium", "actor": "admin",
            }, lamport_clock=2),
        ]
        state = reduce_glossary_events(events)
        assert state.current_strictness == "max"
        assert len(state.strictness_history) == 1

    def test_multiple_changes(self) -> None:
        events = [
            make_glossary_event("GlossaryScopeActivated", {
                "mission_id": "m1", "scope_id": "s1",
                "scope_type": "team_domain", "glossary_version_id": "v1",
            }, lamport_clock=1),
            make_glossary_event("GlossaryStrictnessSet", {
                "mission_id": "m1", "new_strictness": "max",
                "previous_strictness": "medium", "actor": "admin",
            }, lamport_clock=2),
            make_glossary_event("GlossaryStrictnessSet", {
                "mission_id": "m1", "new_strictness": "off",
                "previous_strictness": "max", "actor": "admin",
            }, lamport_clock=3),
            make_glossary_event("GlossaryStrictnessSet", {
                "mission_id": "m1", "new_strictness": "medium",
                "previous_strictness": "off", "actor": "admin",
            }, lamport_clock=4),
        ]
        state = reduce_glossary_events(events)
        assert state.current_strictness == "medium"
        assert len(state.strictness_history) == 3
        assert state.strictness_history[0].new_strictness == "max"
        assert state.strictness_history[1].new_strictness == "off"
        assert state.strictness_history[2].new_strictness == "medium"


# ── T040: Dedup Behavior ─────────────────────────────────────────────────────


class TestReducerDedup:
    """Tests for event deduplication."""

    def test_duplicate_events_ignored(self) -> None:
        eid = "01HX0000000000000000000001"
        event = make_glossary_event("GlossaryScopeActivated", {
            "mission_id": "m1", "scope_id": "s1",
            "scope_type": "team_domain", "glossary_version_id": "v1",
        }, event_id=eid, lamport_clock=1)
        dup = make_glossary_event("GlossaryScopeActivated", {
            "mission_id": "m1", "scope_id": "s1",
            "scope_type": "team_domain", "glossary_version_id": "v1",
        }, event_id=eid, lamport_clock=2)

        state_with_dup = reduce_glossary_events([event, dup])
        state_without_dup = reduce_glossary_events([event])
        assert state_with_dup.event_count == 1
        assert state_with_dup.active_scopes == state_without_dup.active_scopes


# ── T041: Determinism Property Test ──────────────────────────────────────────


def _make_determinism_events() -> list[Event]:
    """Fixed set of glossary events for determinism testing."""
    return [
        make_glossary_event("GlossaryScopeActivated", {
            "mission_id": "m1", "scope_id": "s1",
            "scope_type": "team_domain", "glossary_version_id": "v1",
        }, event_id="01HX0000000000000000000101", lamport_clock=101),
        make_glossary_event("GlossaryStrictnessSet", {
            "mission_id": "m1", "new_strictness": "max", "actor": "admin",
        }, event_id="01HX0000000000000000000102", lamport_clock=102),
        make_glossary_event("TermCandidateObserved", {
            "mission_id": "m1", "scope_id": "s1", "step_id": "st1",
            "term_surface": "api", "confidence": 0.8, "actor": "a1",
        }, event_id="01HX0000000000000000000103", lamport_clock=103),
        make_glossary_event("TermCandidateObserved", {
            "mission_id": "m1", "scope_id": "s1", "step_id": "st2",
            "term_surface": "endpoint", "confidence": 0.7, "actor": "a1",
        }, event_id="01HX0000000000000000000104", lamport_clock=104),
        make_glossary_event("GlossarySenseUpdated", {
            "mission_id": "m1", "scope_id": "s1",
            "term_surface": "api", "after_sense": "REST interface",
            "reason": "initial", "actor": "a1",
        }, event_id="01HX0000000000000000000105", lamport_clock=105),
        make_glossary_event("SemanticCheckEvaluated", {
            "mission_id": "m1", "scope_id": "s1", "step_id": "st3",
            "conflicts": [{"term": "api", "nature": "overloaded",
                           "severity": "high", "description": "ambig"}],
            "severity": "high", "confidence": 0.9,
            "recommended_action": "warn", "effective_strictness": "max",
        }, event_id="01HX0000000000000000000106", lamport_clock=106),
        make_glossary_event("GlossaryClarificationRequested", {
            "mission_id": "m1", "scope_id": "s1", "step_id": "st3",
            "semantic_check_event_id": "01HX0000000000000000000106",
            "term": "api", "question": "Which meaning?",
            "options": ["REST", "Generic"], "urgency": "high", "actor": "a1",
        }, event_id="01HX0000000000000000000107", lamport_clock=107),
        make_glossary_event("GlossaryClarificationResolved", {
            "mission_id": "m1",
            "clarification_event_id": "01HX0000000000000000000107",
            "selected_meaning": "REST interface", "actor": "a2",
        }, event_id="01HX0000000000000000000108", lamport_clock=108),
        make_glossary_event("GenerationBlockedBySemanticConflict", {
            "mission_id": "m1", "step_id": "st4",
            "conflict_event_ids": ["01HX0000000000000000000106"],
            "blocking_strictness": "max",
        }, event_id="01HX0000000000000000000109", lamport_clock=109),
        make_glossary_event("GlossaryStrictnessSet", {
            "mission_id": "m1", "new_strictness": "medium",
            "previous_strictness": "max", "actor": "admin",
        }, event_id="01HX0000000000000000000110", lamport_clock=110),
    ]


@given(data=st.data())
@settings(max_examples=200)
def test_reducer_determinism(data: st.DataObject) -> None:
    """Any permutation of glossary events produces identical reduced state."""
    events = _make_determinism_events()
    shuffled = data.draw(st.permutations(events))
    state_original = reduce_glossary_events(events)
    state_shuffled = reduce_glossary_events(list(shuffled))
    assert state_original == state_shuffled


# ── T042: Clarification Lifecycle and Burst Cap ──────────────────────────────


class TestReducerClarificationLifecycle:
    """Tests for clarification request/resolve and burst cap."""

    def _scope_event(self, clock: int = 1) -> Event:
        return make_glossary_event("GlossaryScopeActivated", {
            "mission_id": "m1", "scope_id": "s1",
            "scope_type": "team_domain", "glossary_version_id": "v1",
        }, event_id=f"01HX{clock:022d}", lamport_clock=clock)

    def _check_event(self, clock: int = 2) -> Event:
        return make_glossary_event("SemanticCheckEvaluated", {
            "mission_id": "m1", "scope_id": "s1", "step_id": "st1",
            "conflicts": [], "severity": "low", "confidence": 0.5,
            "recommended_action": "pass", "effective_strictness": "medium",
        }, event_id=f"01HX{clock:022d}", lamport_clock=clock)

    def _clar_request(self, check_eid: str, term: str, clock: int) -> Event:
        return make_glossary_event("GlossaryClarificationRequested", {
            "mission_id": "m1", "scope_id": "s1", "step_id": "st1",
            "semantic_check_event_id": check_eid,
            "term": term, "question": "Which?",
            "options": ["A", "B"], "urgency": "low", "actor": "a1",
        }, event_id=f"01HX{clock:022d}", lamport_clock=clock)

    def _clar_resolve(self, clar_eid: str, clock: int) -> Event:
        return make_glossary_event("GlossaryClarificationResolved", {
            "mission_id": "m1",
            "clarification_event_id": clar_eid,
            "selected_meaning": "meaning-A", "actor": "a2",
        }, event_id=f"01HX{clock:022d}", lamport_clock=clock)

    def test_request_and_resolution(self) -> None:
        check_eid = f"01HX{2:022d}"
        clar_eid = f"01HX{3:022d}"
        events = [
            self._scope_event(1),
            self._check_event(2),
            self._clar_request(check_eid, "api", 3),
            self._clar_resolve(clar_eid, 4),
        ]
        state = reduce_glossary_events(events)
        assert len(state.clarifications) == 1
        assert state.clarifications[0].resolved is True
        assert state.clarifications[0].resolution_event_id == f"01HX{4:022d}"

    def test_burst_cap_strict(self) -> None:
        check_eid = f"01HX{2:022d}"
        events = [
            self._scope_event(1),
            self._check_event(2),
            self._clar_request(check_eid, "t1", 3),
            self._clar_request(check_eid, "t2", 4),
            self._clar_request(check_eid, "t3", 5),
            self._clar_request(check_eid, "t4", 6),  # 4th — exceeds cap
        ]
        with pytest.raises(SpecKittyEventsError, match="burst cap exceeded"):
            reduce_glossary_events(events, mode="strict")

    def test_burst_cap_permissive(self) -> None:
        check_eid = f"01HX{2:022d}"
        events = [
            self._scope_event(1),
            self._check_event(2),
            self._clar_request(check_eid, "t1", 3),
            self._clar_request(check_eid, "t2", 4),
            self._clar_request(check_eid, "t3", 5),
            self._clar_request(check_eid, "t4", 6),  # 4th — anomaly
        ]
        state = reduce_glossary_events(events, mode="permissive")
        assert len(state.clarifications) == 3
        assert len(state.anomalies) == 1
        assert "burst cap" in state.anomalies[0].reason.lower()

    def test_resolved_clarification_frees_cap(self) -> None:
        check_eid = f"01HX{2:022d}"
        clar1_eid = f"01HX{3:022d}"
        events = [
            self._scope_event(1),
            self._check_event(2),
            self._clar_request(check_eid, "t1", 3),
            self._clar_request(check_eid, "t2", 4),
            self._clar_request(check_eid, "t3", 5),
            self._clar_resolve(clar1_eid, 6),  # resolve 1st — frees cap
            self._clar_request(check_eid, "t4", 7),  # 4th request, only 2 active → OK
        ]
        state = reduce_glossary_events(events)
        assert len(state.clarifications) == 4
        assert len(state.anomalies) == 0

    def test_independent_check_ids(self) -> None:
        check_a = f"01HX{2:022d}"
        check_b = f"01HX{3:022d}"
        events = [
            self._scope_event(1),
            self._check_event(2),
            make_glossary_event("SemanticCheckEvaluated", {
                "mission_id": "m1", "scope_id": "s1", "step_id": "st2",
                "conflicts": [], "severity": "low", "confidence": 0.5,
                "recommended_action": "pass", "effective_strictness": "medium",
            }, event_id=f"01HX{3:022d}", lamport_clock=3),
            self._clar_request(check_a, "t1", 4),
            self._clar_request(check_a, "t2", 5),
            self._clar_request(check_a, "t3", 6),
            self._clar_request(check_b, "t4", 7),
            self._clar_request(check_b, "t5", 8),
            self._clar_request(check_b, "t6", 9),
        ]
        state = reduce_glossary_events(events)
        assert len(state.clarifications) == 6
        assert len(state.anomalies) == 0
