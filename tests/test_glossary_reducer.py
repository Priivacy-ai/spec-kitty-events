"""Tests for glossary reducer — happy path, determinism, and edge cases (WP08/WP09)."""

from __future__ import annotations

import json
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
        assert ("s1", "dashboard") in state.term_candidates
        assert len(state.term_candidates[("s1", "dashboard")]) == 1
        assert ("s1", "dashboard") in state.term_senses
        assert state.term_senses[("s1", "dashboard")].after_sense == "UI panel"
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


# ── T043: Strict Mode — Unactivated Scope ────────────────────────────────────


class TestStrictModeUnactivatedScope:
    """Test strict mode raises on unactivated scope reference."""

    def test_term_in_unactivated_scope_raises(self) -> None:
        event = make_glossary_event("TermCandidateObserved", {
            "mission_id": "m1", "scope_id": "nonexistent", "step_id": "st1",
            "term_surface": "api", "confidence": 0.5, "actor": "a1",
        }, lamport_clock=1)
        with pytest.raises(SpecKittyEventsError, match="unactivated scope"):
            reduce_glossary_events([event], mode="strict")


# ── T044: Strict Mode — Unobserved Term ──────────────────────────────────────


class TestStrictModeUnobservedTerm:
    """Test strict mode raises on sense update for unobserved term."""

    def test_sense_update_unobserved_term_raises(self) -> None:
        events = [
            make_glossary_event("GlossaryScopeActivated", {
                "mission_id": "m1", "scope_id": "s1",
                "scope_type": "team_domain", "glossary_version_id": "v1",
            }, lamport_clock=1),
            make_glossary_event("GlossarySenseUpdated", {
                "mission_id": "m1", "scope_id": "s1",
                "term_surface": "unknown_term", "after_sense": "meaning",
                "reason": "initial", "actor": "a1",
            }, lamport_clock=2),
        ]
        with pytest.raises(SpecKittyEventsError, match="unobserved term"):
            reduce_glossary_events(events, mode="strict")


# ── T045: Permissive Mode — Scope Anomaly ────────────────────────────────────


class TestPermissiveModeScope:
    """Test permissive mode records anomaly and continues on scope errors."""

    def test_unactivated_scope_records_anomaly_and_continues(self) -> None:
        events = [
            make_glossary_event("TermCandidateObserved", {
                "mission_id": "m1", "scope_id": "bad_scope", "step_id": "st1",
                "term_surface": "early_term", "confidence": 0.5, "actor": "a1",
            }, lamport_clock=1),
            make_glossary_event("GlossaryScopeActivated", {
                "mission_id": "m1", "scope_id": "s1",
                "scope_type": "team_domain", "glossary_version_id": "v1",
            }, lamport_clock=2),
            make_glossary_event("TermCandidateObserved", {
                "mission_id": "m1", "scope_id": "s1", "step_id": "st2",
                "term_surface": "valid_term", "confidence": 0.8, "actor": "a1",
            }, lamport_clock=3),
        ]
        state = reduce_glossary_events(events, mode="permissive")
        assert len(state.anomalies) == 1
        assert "unactivated scope" in state.anomalies[0].reason
        assert ("s1", "valid_term") in state.term_candidates
        assert state.event_count == 3


# ── T046: Permissive Mode — Unobserved Term Anomaly ──────────────────────────


class TestPermissiveModeUnobservedTerm:
    """Test permissive mode records anomaly for unobserved term and continues."""

    def test_sense_update_unobserved_term_records_anomaly(self) -> None:
        events = [
            make_glossary_event("GlossaryScopeActivated", {
                "mission_id": "m1", "scope_id": "s1",
                "scope_type": "team_domain", "glossary_version_id": "v1",
            }, lamport_clock=1),
            make_glossary_event("GlossarySenseUpdated", {
                "mission_id": "m1", "scope_id": "s1",
                "term_surface": "unknown_term", "after_sense": "meaning",
                "reason": "initial", "actor": "a1",
            }, lamport_clock=2),
            make_glossary_event("TermCandidateObserved", {
                "mission_id": "m1", "scope_id": "s1", "step_id": "st1",
                "term_surface": "known_term", "confidence": 0.7, "actor": "a1",
            }, lamport_clock=3),
        ]
        state = reduce_glossary_events(events, mode="permissive")
        assert len(state.anomalies) == 1
        assert "unobserved term" in state.anomalies[0].reason
        assert ("s1", "unknown_term") in state.term_senses
        assert ("s1", "known_term") in state.term_candidates


# ── T047: Concurrent Clarification Resolution ────────────────────────────────


class TestConcurrentClarificationResolution:
    """Test last-write-wins for concurrent resolutions."""

    def test_last_resolution_wins(self) -> None:
        req_eid = "01HX0000000000000000000203"
        check_eid = "01HX0000000000000000000202"
        events = [
            make_glossary_event("GlossaryScopeActivated", {
                "mission_id": "m1", "scope_id": "s1",
                "scope_type": "team_domain", "glossary_version_id": "v1",
            }, event_id="01HX0000000000000000000201", lamport_clock=201),
            make_glossary_event("SemanticCheckEvaluated", {
                "mission_id": "m1", "scope_id": "s1", "step_id": "st1",
                "conflicts": [], "severity": "low", "confidence": 0.5,
                "recommended_action": "pass", "effective_strictness": "medium",
            }, event_id=check_eid, lamport_clock=202),
            make_glossary_event("GlossaryClarificationRequested", {
                "mission_id": "m1", "scope_id": "s1", "step_id": "st1",
                "semantic_check_event_id": check_eid,
                "term": "api", "question": "Which?",
                "options": ["A", "B"], "urgency": "low", "actor": "a1",
            }, event_id=req_eid, lamport_clock=203),
            make_glossary_event("GlossaryClarificationResolved", {
                "mission_id": "m1", "clarification_event_id": req_eid,
                "selected_meaning": "A", "actor": "actor-A",
            }, event_id="01HX0000000000000000000204", lamport_clock=204),
            make_glossary_event("GlossaryClarificationResolved", {
                "mission_id": "m1", "clarification_event_id": req_eid,
                "selected_meaning": "B", "actor": "actor-B",
            }, event_id="01HX0000000000000000000205", lamport_clock=205),
        ]
        state = reduce_glossary_events(events)
        assert len(state.clarifications) == 1
        record = state.clarifications[0]
        assert record.resolved is True
        assert record.resolution_event_id == "01HX0000000000000000000205"


# ── T048: Mid-Mission Strictness Change ──────────────────────────────────────


class TestMidMissionStrictnessChange:
    """Test that block events are preserved when strictness changes."""

    def test_blocks_preserved_after_strictness_off(self) -> None:
        events = [
            make_glossary_event("GlossaryScopeActivated", {
                "mission_id": "m1", "scope_id": "s1",
                "scope_type": "team_domain", "glossary_version_id": "v1",
            }, lamport_clock=1),
            make_glossary_event("GlossaryStrictnessSet", {
                "mission_id": "m1", "new_strictness": "max", "actor": "admin",
            }, lamport_clock=2),
            make_glossary_event("SemanticCheckEvaluated", {
                "mission_id": "m1", "scope_id": "s1", "step_id": "st1",
                "conflicts": [{"term": "api", "nature": "overloaded",
                               "severity": "high", "description": "ambig"}],
                "severity": "high", "confidence": 0.9,
                "recommended_action": "block", "effective_strictness": "max",
            }, lamport_clock=3),
            make_glossary_event("GenerationBlockedBySemanticConflict", {
                "mission_id": "m1", "step_id": "st1",
                "conflict_event_ids": ["e3"], "blocking_strictness": "max",
            }, lamport_clock=4),
            make_glossary_event("GlossaryStrictnessSet", {
                "mission_id": "m1", "new_strictness": "off",
                "previous_strictness": "max", "actor": "admin",
            }, lamport_clock=5),
        ]
        state = reduce_glossary_events(events)
        assert state.current_strictness == "off"
        assert len(state.generation_blocks) == 1
        assert len(state.strictness_history) == 2
        assert state.generation_blocks[0].blocking_strictness == "max"


# ── T049+: Cross-Scope Same Term ─────────────────────────────────────────────


class TestCrossScopeSameTerm:
    """Same term_surface in different scopes produces separate entries."""

    def test_same_term_different_scopes(self) -> None:
        events = [
            make_glossary_event("GlossaryScopeActivated", {
                "mission_id": "m1", "scope_id": "scope-a",
                "scope_type": "team_domain", "glossary_version_id": "v1",
            }, lamport_clock=1),
            make_glossary_event("GlossaryScopeActivated", {
                "mission_id": "m1", "scope_id": "scope-b",
                "scope_type": "audience_domain", "glossary_version_id": "v1",
            }, lamport_clock=2),
            make_glossary_event("TermCandidateObserved", {
                "mission_id": "m1", "scope_id": "scope-a", "step_id": "st1",
                "term_surface": "node", "confidence": 0.9, "actor": "a1",
            }, lamport_clock=3),
            make_glossary_event("TermCandidateObserved", {
                "mission_id": "m1", "scope_id": "scope-b", "step_id": "st2",
                "term_surface": "node", "confidence": 0.8, "actor": "a1",
            }, lamport_clock=4),
            make_glossary_event("GlossarySenseUpdated", {
                "mission_id": "m1", "scope_id": "scope-a",
                "term_surface": "node", "after_sense": "server instance",
                "reason": "infra context", "actor": "a1",
            }, lamport_clock=5),
            make_glossary_event("GlossarySenseUpdated", {
                "mission_id": "m1", "scope_id": "scope-b",
                "term_surface": "node", "after_sense": "graph vertex",
                "reason": "data context", "actor": "a1",
            }, lamport_clock=6),
        ]
        state = reduce_glossary_events(events)

        # Both scopes have separate term_candidates entries
        assert ("scope-a", "node") in state.term_candidates
        assert ("scope-b", "node") in state.term_candidates
        assert len(state.term_candidates) == 2

        # Both scopes have separate term_senses entries
        assert ("scope-a", "node") in state.term_senses
        assert ("scope-b", "node") in state.term_senses
        assert state.term_senses[("scope-a", "node")].after_sense == "server instance"
        assert state.term_senses[("scope-b", "node")].after_sense == "graph vertex"

        assert len(state.anomalies) == 0


# ── Clarification Scope Check ────────────────────────────────────────────────


class TestClarificationScopeCheck:
    """GlossaryClarificationRequested with unactivated scope_id."""

    def test_strict_raises_on_unactivated_scope(self) -> None:
        check_eid = "01HX0000000000000000000502"
        events = [
            make_glossary_event("GlossaryScopeActivated", {
                "mission_id": "m1", "scope_id": "s1",
                "scope_type": "team_domain", "glossary_version_id": "v1",
            }, lamport_clock=501),
            make_glossary_event("SemanticCheckEvaluated", {
                "mission_id": "m1", "scope_id": "s1", "step_id": "st1",
                "conflicts": [], "severity": "low", "confidence": 0.5,
                "recommended_action": "pass", "effective_strictness": "medium",
            }, event_id=check_eid, lamport_clock=502),
            make_glossary_event("GlossaryClarificationRequested", {
                "mission_id": "m1", "scope_id": "nonexistent", "step_id": "st1",
                "semantic_check_event_id": check_eid,
                "term": "api", "question": "Which?",
                "options": ["A", "B"], "urgency": "low", "actor": "a1",
            }, lamport_clock=503),
        ]
        with pytest.raises(SpecKittyEventsError, match="unactivated scope"):
            reduce_glossary_events(events, mode="strict")

    def test_permissive_records_anomaly(self) -> None:
        check_eid = "01HX0000000000000000000602"
        events = [
            make_glossary_event("GlossaryScopeActivated", {
                "mission_id": "m1", "scope_id": "s1",
                "scope_type": "team_domain", "glossary_version_id": "v1",
            }, lamport_clock=601),
            make_glossary_event("SemanticCheckEvaluated", {
                "mission_id": "m1", "scope_id": "s1", "step_id": "st1",
                "conflicts": [], "severity": "low", "confidence": 0.5,
                "recommended_action": "pass", "effective_strictness": "medium",
            }, event_id=check_eid, lamport_clock=602),
            make_glossary_event("GlossaryClarificationRequested", {
                "mission_id": "m1", "scope_id": "bad_scope", "step_id": "st1",
                "semantic_check_event_id": check_eid,
                "term": "api", "question": "Which?",
                "options": ["A", "B"], "urgency": "low", "actor": "a1",
            }, lamport_clock=603),
        ]
        state = reduce_glossary_events(events, mode="permissive")
        scope_anomalies = [a for a in state.anomalies if "unactivated scope" in a.reason]
        assert len(scope_anomalies) == 1


# ── Clarification Unknown Check Reference ────────────────────────────────────


class TestClarificationUnknownCheckRef:
    """GlossaryClarificationRequested referencing non-existent semantic check."""

    def test_strict_raises_on_unknown_check_ref(self) -> None:
        events = [
            make_glossary_event("GlossaryScopeActivated", {
                "mission_id": "m1", "scope_id": "s1",
                "scope_type": "team_domain", "glossary_version_id": "v1",
            }, lamport_clock=701),
            make_glossary_event("GlossaryClarificationRequested", {
                "mission_id": "m1", "scope_id": "s1", "step_id": "st1",
                "semantic_check_event_id": "fabricated-check-id-00000001",
                "term": "api", "question": "Which?",
                "options": ["A", "B"], "urgency": "low", "actor": "a1",
            }, lamport_clock=702),
        ]
        with pytest.raises(SpecKittyEventsError, match="unknown semantic check"):
            reduce_glossary_events(events, mode="strict")

    def test_permissive_records_anomaly(self) -> None:
        events = [
            make_glossary_event("GlossaryScopeActivated", {
                "mission_id": "m1", "scope_id": "s1",
                "scope_type": "team_domain", "glossary_version_id": "v1",
            }, lamport_clock=801),
            make_glossary_event("GlossaryClarificationRequested", {
                "mission_id": "m1", "scope_id": "s1", "step_id": "st1",
                "semantic_check_event_id": "fabricated-check-id-00000002",
                "term": "api", "question": "Which?",
                "options": ["A", "B"], "urgency": "low", "actor": "a1",
            }, lamport_clock=802),
        ]
        state = reduce_glossary_events(events, mode="permissive")
        ref_anomalies = [a for a in state.anomalies if "unknown semantic check" in a.reason]
        assert len(ref_anomalies) == 1
        # Clarification should NOT be added when reference is invalid
        assert len(state.clarifications) == 0


# ── JSON Serialization Safety ─────────────────────────────────────────────────


class TestGlossaryJsonSerialization:
    """JSON output must preserve distinct composite keys without collisions."""

    def test_tuple_key_collision_is_prevented_in_json_output(self) -> None:
        events = [
            make_glossary_event("GlossaryScopeActivated", {
                "mission_id": "m1", "scope_id": "a,b",
                "scope_type": "team_domain", "glossary_version_id": "v1",
            }, lamport_clock=901),
            make_glossary_event("GlossaryScopeActivated", {
                "mission_id": "m1", "scope_id": "a",
                "scope_type": "team_domain", "glossary_version_id": "v1",
            }, lamport_clock=902),
            make_glossary_event("TermCandidateObserved", {
                "mission_id": "m1", "scope_id": "a,b", "step_id": "st1",
                "term_surface": "c", "confidence": 0.9, "actor": "a1",
            }, lamport_clock=903),
            make_glossary_event("TermCandidateObserved", {
                "mission_id": "m1", "scope_id": "a", "step_id": "st2",
                "term_surface": "b,c", "confidence": 0.8, "actor": "a1",
            }, lamport_clock=904),
            make_glossary_event("GlossarySenseUpdated", {
                "mission_id": "m1", "scope_id": "a,b",
                "term_surface": "c", "after_sense": "sense-1",
                "reason": "collision test", "actor": "a1",
            }, lamport_clock=905),
            make_glossary_event("GlossarySenseUpdated", {
                "mission_id": "m1", "scope_id": "a",
                "term_surface": "b,c", "after_sense": "sense-2",
                "reason": "collision test", "actor": "a1",
            }, lamport_clock=906),
        ]
        state = reduce_glossary_events(events)

        payload = json.loads(state.model_dump_json())

        term_candidates = payload["term_candidates"]
        assert set(term_candidates.keys()) == {"a,b", "a"}
        assert "c" in term_candidates["a,b"]
        assert "b,c" in term_candidates["a"]

        term_senses = payload["term_senses"]
        assert set(term_senses.keys()) == {"a,b", "a"}
        assert term_senses["a,b"]["c"]["after_sense"] == "sense-1"
        assert term_senses["a"]["b,c"]["after_sense"] == "sense-2"
