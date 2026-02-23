"""Tests for glossary payload models (WP07)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from spec_kitty_events import (
    SemanticConflictEntry,
    GlossaryScopeActivatedPayload,
    TermCandidateObservedPayload,
    GlossarySenseUpdatedPayload,
    GlossaryStrictnessSetPayload,
    SemanticCheckEvaluatedPayload,
    GlossaryClarificationRequestedPayload,
    GlossaryClarificationResolvedPayload,
    GenerationBlockedBySemanticConflictPayload,
)


# ── T031: Scope and Strictness Payloads ──────────────────────────────────────


class TestGlossaryScopeActivatedPayload:
    """Tests for GlossaryScopeActivatedPayload."""

    @pytest.mark.parametrize("scope_type", [
        "spec_kitty_core", "team_domain", "audience_domain", "mission_local",
    ])
    def test_valid_scope_types(self, scope_type: str) -> None:
        p = GlossaryScopeActivatedPayload(
            mission_id="m1", scope_id="s1",
            scope_type=scope_type, glossary_version_id="v1",
        )
        assert p.scope_type == scope_type

    def test_round_trip(self) -> None:
        p = GlossaryScopeActivatedPayload(
            mission_id="m1", scope_id="s1",
            scope_type="team_domain", glossary_version_id="v1",
        )
        reconstructed = GlossaryScopeActivatedPayload(**p.model_dump())
        assert reconstructed == p

    def test_invalid_scope_type(self) -> None:
        with pytest.raises(ValidationError):
            GlossaryScopeActivatedPayload(
                mission_id="m1", scope_id="s1",
                scope_type="invalid_scope", glossary_version_id="v1",
            )

    @pytest.mark.parametrize("field", ["scope_id", "mission_id", "glossary_version_id"])
    def test_empty_string_rejected(self, field: str) -> None:
        data = {
            "mission_id": "m1", "scope_id": "s1",
            "scope_type": "team_domain", "glossary_version_id": "v1",
        }
        data[field] = ""
        with pytest.raises(ValidationError):
            GlossaryScopeActivatedPayload(**data)


class TestGlossaryStrictnessSetPayload:
    """Tests for GlossaryStrictnessSetPayload."""

    @pytest.mark.parametrize("strictness", ["off", "medium", "max"])
    def test_valid_strictness(self, strictness: str) -> None:
        p = GlossaryStrictnessSetPayload(
            mission_id="m1", new_strictness=strictness, actor="admin",
        )
        assert p.new_strictness == strictness

    def test_previous_strictness_none(self) -> None:
        p = GlossaryStrictnessSetPayload(
            mission_id="m1", new_strictness="max", actor="admin",
        )
        assert p.previous_strictness is None

    def test_previous_strictness_set(self) -> None:
        p = GlossaryStrictnessSetPayload(
            mission_id="m1", new_strictness="max",
            previous_strictness="medium", actor="admin",
        )
        assert p.previous_strictness == "medium"

    def test_invalid_strictness(self) -> None:
        with pytest.raises(ValidationError):
            GlossaryStrictnessSetPayload(
                mission_id="m1", new_strictness="extreme", actor="admin",
            )

    def test_round_trip(self) -> None:
        p = GlossaryStrictnessSetPayload(
            mission_id="m1", new_strictness="max",
            previous_strictness="medium", actor="admin",
        )
        assert GlossaryStrictnessSetPayload(**p.model_dump()) == p


# ── T032: Term Candidate Payload ─────────────────────────────────────────────


class TestTermCandidateObservedPayload:
    """Tests for TermCandidateObservedPayload."""

    def test_valid_construction(self) -> None:
        p = TermCandidateObservedPayload(
            mission_id="m1", scope_id="s1", step_id="st1",
            term_surface="api", confidence=0.7, actor="a1",
        )
        assert p.confidence == 0.7

    def test_confidence_zero(self) -> None:
        p = TermCandidateObservedPayload(
            mission_id="m1", scope_id="s1", step_id="st1",
            term_surface="api", confidence=0.0, actor="a1",
        )
        assert p.confidence == 0.0

    def test_confidence_one(self) -> None:
        p = TermCandidateObservedPayload(
            mission_id="m1", scope_id="s1", step_id="st1",
            term_surface="api", confidence=1.0, actor="a1",
        )
        assert p.confidence == 1.0

    def test_confidence_too_low(self) -> None:
        with pytest.raises(ValidationError):
            TermCandidateObservedPayload(
                mission_id="m1", scope_id="s1", step_id="st1",
                term_surface="api", confidence=-0.1, actor="a1",
            )

    def test_confidence_too_high(self) -> None:
        with pytest.raises(ValidationError):
            TermCandidateObservedPayload(
                mission_id="m1", scope_id="s1", step_id="st1",
                term_surface="api", confidence=1.1, actor="a1",
            )

    def test_empty_term_surface_rejected(self) -> None:
        with pytest.raises(ValidationError):
            TermCandidateObservedPayload(
                mission_id="m1", scope_id="s1", step_id="st1",
                term_surface="", confidence=0.5, actor="a1",
            )

    def test_step_metadata_default(self) -> None:
        p = TermCandidateObservedPayload(
            mission_id="m1", scope_id="s1", step_id="st1",
            term_surface="api", confidence=0.5, actor="a1",
        )
        assert p.step_metadata == {}

    def test_step_metadata_with_values(self) -> None:
        p = TermCandidateObservedPayload(
            mission_id="m1", scope_id="s1", step_id="st1",
            term_surface="api", confidence=0.5, actor="a1",
            step_metadata={"primitive": "specify"},
        )
        assert p.step_metadata == {"primitive": "specify"}

    def test_round_trip(self) -> None:
        p = TermCandidateObservedPayload(
            mission_id="m1", scope_id="s1", step_id="st1",
            term_surface="api", confidence=0.85, actor="a1",
            step_metadata={"k": "v"},
        )
        assert TermCandidateObservedPayload(**p.model_dump()) == p


# ── T033: Semantic Check and Conflict Entry ──────────────────────────────────


class TestSemanticConflictEntry:
    """Tests for SemanticConflictEntry value object."""

    @pytest.mark.parametrize("nature", ["overloaded", "drift", "ambiguous"])
    def test_valid_natures(self, nature: str) -> None:
        e = SemanticConflictEntry(
            term="api", nature=nature, severity="high", description="desc",
        )
        assert e.nature == nature

    def test_invalid_nature(self) -> None:
        with pytest.raises(ValidationError):
            SemanticConflictEntry(
                term="api", nature="unknown", severity="high", description="desc",
            )

    @pytest.mark.parametrize("severity", ["low", "medium", "high"])
    def test_valid_severities(self, severity: str) -> None:
        e = SemanticConflictEntry(
            term="api", nature="drift", severity=severity, description="desc",
        )
        assert e.severity == severity

    def test_invalid_severity(self) -> None:
        with pytest.raises(ValidationError):
            SemanticConflictEntry(
                term="api", nature="drift", severity="critical", description="desc",
            )

    def test_empty_term_rejected(self) -> None:
        with pytest.raises(ValidationError):
            SemanticConflictEntry(
                term="", nature="drift", severity="high", description="desc",
            )

    def test_round_trip(self) -> None:
        e = SemanticConflictEntry(
            term="api", nature="overloaded", severity="high", description="desc",
        )
        assert SemanticConflictEntry(**e.model_dump()) == e


class TestSemanticCheckEvaluatedPayload:
    """Tests for SemanticCheckEvaluatedPayload."""

    def test_valid_with_conflicts(self) -> None:
        conflict = SemanticConflictEntry(
            term="api", nature="overloaded", severity="high", description="ambig",
        )
        p = SemanticCheckEvaluatedPayload(
            mission_id="m1", scope_id="s1", step_id="st1",
            conflicts=(conflict,), severity="high", confidence=0.9,
            recommended_action="block", effective_strictness="max",
        )
        assert len(p.conflicts) == 1

    def test_empty_conflicts_valid(self) -> None:
        p = SemanticCheckEvaluatedPayload(
            mission_id="m1", scope_id="s1", step_id="st1",
            conflicts=(), severity="low", confidence=0.1,
            recommended_action="pass", effective_strictness="medium",
        )
        assert len(p.conflicts) == 0

    @pytest.mark.parametrize("action", ["block", "warn", "pass"])
    def test_recommended_actions(self, action: str) -> None:
        p = SemanticCheckEvaluatedPayload(
            mission_id="m1", scope_id="s1", step_id="st1",
            conflicts=(), severity="low", confidence=0.5,
            recommended_action=action, effective_strictness="medium",
        )
        assert p.recommended_action == action

    @pytest.mark.parametrize("strictness", ["off", "medium", "max"])
    def test_effective_strictness(self, strictness: str) -> None:
        p = SemanticCheckEvaluatedPayload(
            mission_id="m1", scope_id="s1", step_id="st1",
            conflicts=(), severity="low", confidence=0.5,
            recommended_action="pass", effective_strictness=strictness,
        )
        assert p.effective_strictness == strictness

    def test_confidence_bounds(self) -> None:
        for val in [0.0, 1.0]:
            p = SemanticCheckEvaluatedPayload(
                mission_id="m1", scope_id="s1", step_id="st1",
                conflicts=(), severity="low", confidence=val,
                recommended_action="pass", effective_strictness="off",
            )
            assert p.confidence == val

    def test_confidence_out_of_bounds(self) -> None:
        with pytest.raises(ValidationError):
            SemanticCheckEvaluatedPayload(
                mission_id="m1", scope_id="s1", step_id="st1",
                conflicts=(), severity="low", confidence=1.1,
                recommended_action="pass", effective_strictness="off",
            )

    def test_round_trip_with_nested_conflicts(self) -> None:
        conflict = SemanticConflictEntry(
            term="api", nature="overloaded", severity="high", description="ambig",
        )
        p = SemanticCheckEvaluatedPayload(
            mission_id="m1", scope_id="s1", step_id="st1",
            conflicts=(conflict,), severity="high", confidence=0.9,
            recommended_action="block", effective_strictness="max",
        )
        assert SemanticCheckEvaluatedPayload(**p.model_dump()) == p


# ── T034: Clarification Payloads ─────────────────────────────────────────────


class TestGlossaryClarificationRequestedPayload:
    """Tests for GlossaryClarificationRequestedPayload."""

    def test_valid_construction(self) -> None:
        p = GlossaryClarificationRequestedPayload(
            mission_id="m1", scope_id="s1", step_id="st1",
            semantic_check_event_id="evt1", term="api",
            question="Which meaning?", options=("REST", "Generic"),
            urgency="high", actor="a1",
        )
        assert p.semantic_check_event_id == "evt1"

    def test_semantic_check_event_id_required(self) -> None:
        with pytest.raises(ValidationError):
            GlossaryClarificationRequestedPayload(
                mission_id="m1", scope_id="s1", step_id="st1",
                term="api", question="Which?", options=("A",),
                urgency="low", actor="a1",
            )

    @pytest.mark.parametrize("urgency", ["low", "medium", "high"])
    def test_urgency_values(self, urgency: str) -> None:
        p = GlossaryClarificationRequestedPayload(
            mission_id="m1", scope_id="s1", step_id="st1",
            semantic_check_event_id="evt1", term="api",
            question="Which?", options=("A",), urgency=urgency, actor="a1",
        )
        assert p.urgency == urgency

    def test_options_multiple(self) -> None:
        p = GlossaryClarificationRequestedPayload(
            mission_id="m1", scope_id="s1", step_id="st1",
            semantic_check_event_id="evt1", term="api",
            question="Which?", options=("A", "B", "C"), urgency="low", actor="a1",
        )
        assert len(p.options) == 3

    def test_round_trip(self) -> None:
        p = GlossaryClarificationRequestedPayload(
            mission_id="m1", scope_id="s1", step_id="st1",
            semantic_check_event_id="evt1", term="api",
            question="Which?", options=("REST", "Generic"),
            urgency="high", actor="a1",
        )
        assert GlossaryClarificationRequestedPayload(**p.model_dump()) == p


class TestGlossaryClarificationResolvedPayload:
    """Tests for GlossaryClarificationResolvedPayload."""

    def test_valid_construction(self) -> None:
        p = GlossaryClarificationResolvedPayload(
            mission_id="m1", clarification_event_id="evt1",
            selected_meaning="REST interface", actor="a1",
        )
        assert p.selected_meaning == "REST interface"

    def test_clarification_event_id_required(self) -> None:
        with pytest.raises(ValidationError):
            GlossaryClarificationResolvedPayload(
                mission_id="m1", selected_meaning="REST", actor="a1",
            )

    def test_empty_selected_meaning_rejected(self) -> None:
        with pytest.raises(ValidationError):
            GlossaryClarificationResolvedPayload(
                mission_id="m1", clarification_event_id="evt1",
                selected_meaning="", actor="a1",
            )

    def test_round_trip(self) -> None:
        p = GlossaryClarificationResolvedPayload(
            mission_id="m1", clarification_event_id="evt1",
            selected_meaning="REST interface", actor="a1",
        )
        assert GlossaryClarificationResolvedPayload(**p.model_dump()) == p


# ── T035: Generation Block Payload ───────────────────────────────────────────


class TestGenerationBlockedBySemanticConflictPayload:
    """Tests for GenerationBlockedBySemanticConflictPayload."""

    def test_valid_medium(self) -> None:
        p = GenerationBlockedBySemanticConflictPayload(
            mission_id="m1", step_id="st1",
            conflict_event_ids=("e1",), blocking_strictness="medium",
        )
        assert p.blocking_strictness == "medium"

    def test_valid_max(self) -> None:
        p = GenerationBlockedBySemanticConflictPayload(
            mission_id="m1", step_id="st1",
            conflict_event_ids=("e1",), blocking_strictness="max",
        )
        assert p.blocking_strictness == "max"

    def test_off_rejected(self) -> None:
        with pytest.raises(ValidationError):
            GenerationBlockedBySemanticConflictPayload(
                mission_id="m1", step_id="st1",
                conflict_event_ids=("e1",), blocking_strictness="off",
            )

    def test_empty_conflict_event_ids_rejected(self) -> None:
        with pytest.raises(ValidationError):
            GenerationBlockedBySemanticConflictPayload(
                mission_id="m1", step_id="st1",
                conflict_event_ids=(), blocking_strictness="max",
            )

    def test_step_metadata_default(self) -> None:
        p = GenerationBlockedBySemanticConflictPayload(
            mission_id="m1", step_id="st1",
            conflict_event_ids=("e1",), blocking_strictness="max",
        )
        assert p.step_metadata == {}

    def test_step_metadata_with_values(self) -> None:
        p = GenerationBlockedBySemanticConflictPayload(
            mission_id="m1", step_id="st1",
            conflict_event_ids=("e1",), blocking_strictness="max",
            step_metadata={"primitive": "generate"},
        )
        assert p.step_metadata == {"primitive": "generate"}

    def test_round_trip(self) -> None:
        p = GenerationBlockedBySemanticConflictPayload(
            mission_id="m1", step_id="st1",
            conflict_event_ids=("e1", "e2"), blocking_strictness="max",
            step_metadata={"k": "v"},
        )
        assert GenerationBlockedBySemanticConflictPayload(**p.model_dump()) == p


# ── T036: Sense Updated Payload ──────────────────────────────────────────────


class TestGlossarySenseUpdatedPayload:
    """Tests for GlossarySenseUpdatedPayload."""

    def test_initial_definition(self) -> None:
        p = GlossarySenseUpdatedPayload(
            mission_id="m1", scope_id="s1", term_surface="api",
            before_sense=None, after_sense="REST interface",
            reason="initial definition", actor="a1",
        )
        assert p.before_sense is None

    def test_update_existing(self) -> None:
        p = GlossarySenseUpdatedPayload(
            mission_id="m1", scope_id="s1", term_surface="api",
            before_sense="old meaning", after_sense="new meaning",
            reason="refinement", actor="a1",
        )
        assert p.before_sense == "old meaning"

    def test_empty_term_surface_rejected(self) -> None:
        with pytest.raises(ValidationError):
            GlossarySenseUpdatedPayload(
                mission_id="m1", scope_id="s1", term_surface="",
                after_sense="meaning", reason="initial", actor="a1",
            )

    def test_empty_after_sense_rejected(self) -> None:
        with pytest.raises(ValidationError):
            GlossarySenseUpdatedPayload(
                mission_id="m1", scope_id="s1", term_surface="api",
                after_sense="", reason="initial", actor="a1",
            )

    def test_round_trip_none_before(self) -> None:
        p = GlossarySenseUpdatedPayload(
            mission_id="m1", scope_id="s1", term_surface="api",
            before_sense=None, after_sense="REST interface",
            reason="initial", actor="a1",
        )
        assert GlossarySenseUpdatedPayload(**p.model_dump()) == p

    def test_round_trip_with_before(self) -> None:
        p = GlossarySenseUpdatedPayload(
            mission_id="m1", scope_id="s1", term_surface="api",
            before_sense="old", after_sense="new",
            reason="update", actor="a1",
        )
        assert GlossarySenseUpdatedPayload(**p.model_dump()) == p
