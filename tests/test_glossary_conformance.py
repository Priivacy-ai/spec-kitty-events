"""Conformance tests for glossary semantic integrity contracts (WP10).

Tests fixture validation against payload models and end-to-end
reducer scenarios using conformance fixtures.
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any, Dict, List

import pytest
from pydantic import ValidationError as PydanticValidationError

from spec_kitty_events.conformance.loader import _FIXTURES_DIR, load_fixtures
from spec_kitty_events.conformance.validators import (
    _EVENT_TYPE_TO_MODEL,
    validate_event,
)
from spec_kitty_events.glossary import (
    ClarificationRecord,
    GlossaryAnomaly,
    GlossaryClarificationRequestedPayload,
    GlossaryScopeActivatedPayload,
    GlossaryStrictnessSetPayload,
    ReducedGlossaryState,
    SemanticCheckEvaluatedPayload,
    TermCandidateObservedPayload,
    reduce_glossary_events,
)
from spec_kitty_events.models import Event


# ── Helpers ──────────────────────────────────────────────────────────────────


def _load_fixture(rel_path: str) -> Dict[str, Any]:
    """Load a glossary fixture JSON file."""
    full = _FIXTURES_DIR / rel_path
    with open(full, encoding="utf-8") as f:
        return json.load(f)  # type: ignore[no-any-return]


def _make_event(
    event_type: str,
    payload: Dict[str, Any],
    *,
    lamport_clock: int,
    event_id: str | None = None,
    aggregate_id: str = "mission-fixture-001",
) -> Event:
    """Create an Event wrapping a glossary payload."""
    eid = event_id or f"01HX{lamport_clock:022d}"
    return Event(
        event_id=eid,
        event_type=event_type,
        aggregate_id=aggregate_id,
        payload=payload,
        timestamp="2026-02-16T10:00:00Z",
        node_id="fixture-node",
        lamport_clock=lamport_clock,
        project_uuid=uuid.UUID("12345678-1234-5678-1234-567812345678"),
        correlation_id="01HTESTC0RRE1AT10N00000001",
        schema_version="2.0.0",
    )


# ── T049/T050: Fixture validation ───────────────────────────────────────────


VALID_GLOSSARY_FILES = [
    ("glossary/valid/glossary_scope_activated.json", "GlossaryScopeActivated"),
    ("glossary/valid/term_candidate_observed.json", "TermCandidateObserved"),
    ("glossary/valid/semantic_check_evaluated_block.json", "SemanticCheckEvaluated"),
    ("glossary/valid/semantic_check_evaluated_warn.json", "SemanticCheckEvaluated"),
    ("glossary/valid/generation_blocked.json", "GenerationBlockedBySemanticConflict"),
    ("glossary/valid/glossary_clarification_requested.json", "GlossaryClarificationRequested"),
    ("glossary/valid/glossary_clarification_resolved.json", "GlossaryClarificationResolved"),
    ("glossary/valid/glossary_sense_updated.json", "GlossarySenseUpdated"),
    ("glossary/valid/glossary_strictness_set.json", "GlossaryStrictnessSet"),
]

INVALID_GLOSSARY_FILES = [
    ("glossary/invalid/semantic_check_missing_step_id.json", "SemanticCheckEvaluated"),
    ("glossary/invalid/glossary_scope_invalid_type.json", "GlossaryScopeActivated"),
    ("glossary/invalid/clarification_missing_check_ref.json", "GlossaryClarificationRequested"),
]


class TestValidGlossaryFixtures:
    """Verify each valid glossary fixture passes model validation."""

    @pytest.mark.parametrize("path,event_type", VALID_GLOSSARY_FILES)
    def test_valid_fixture_is_valid_json(self, path: str, event_type: str) -> None:
        full = _FIXTURES_DIR / path
        assert full.is_file(), f"Missing fixture: {full}"
        data = _load_fixture(path)
        assert isinstance(data, dict)

    @pytest.mark.parametrize("path,event_type", VALID_GLOSSARY_FILES)
    def test_valid_fixture_passes_model(self, path: str, event_type: str) -> None:
        data = _load_fixture(path)
        model_class = _EVENT_TYPE_TO_MODEL[event_type]
        instance = model_class.model_validate(data)
        assert instance is not None

    @pytest.mark.parametrize("path,event_type", VALID_GLOSSARY_FILES)
    def test_valid_fixture_passes_conformance(self, path: str, event_type: str) -> None:
        data = _load_fixture(path)
        result = validate_event(data, event_type)
        assert result.valid is True, (
            f"Conformance failure for {path}: {result.model_violations}"
        )

    def test_nine_valid_glossary_fixtures_exist(self) -> None:
        valid_dir = _FIXTURES_DIR / "glossary" / "valid"
        files = sorted(valid_dir.glob("*.json"))
        assert len(files) == 9, f"Expected 9 valid glossary fixtures, got {len(files)}"


class TestInvalidGlossaryFixtures:
    """Verify each invalid glossary fixture fails model validation."""

    @pytest.mark.parametrize("path,event_type", INVALID_GLOSSARY_FILES)
    def test_invalid_fixture_fails_model(self, path: str, event_type: str) -> None:
        data = _load_fixture(path)
        model_class = _EVENT_TYPE_TO_MODEL[event_type]
        with pytest.raises(PydanticValidationError):
            model_class.model_validate(data)

    @pytest.mark.parametrize("path,event_type", INVALID_GLOSSARY_FILES)
    def test_invalid_fixture_fails_conformance(self, path: str, event_type: str) -> None:
        data = _load_fixture(path)
        result = validate_event(data, event_type)
        assert result.valid is False, f"Expected invalid for {path}"
        assert len(result.model_violations) > 0

    def test_three_invalid_glossary_fixtures_exist(self) -> None:
        invalid_dir = _FIXTURES_DIR / "glossary" / "invalid"
        files = sorted(invalid_dir.glob("*.json"))
        assert len(files) == 3, f"Expected 3 invalid glossary fixtures, got {len(files)}"


class TestGlossaryFixtureLoader:
    """Verify load_fixtures() works for the glossary category."""

    def test_load_glossary_returns_cases(self) -> None:
        cases = load_fixtures("glossary")
        assert len(cases) == 12

    def test_glossary_valid_cases(self) -> None:
        cases = load_fixtures("glossary")
        valid_cases = [c for c in cases if c.expected_valid]
        assert len(valid_cases) == 9

    def test_glossary_invalid_cases(self) -> None:
        cases = load_fixtures("glossary")
        invalid_cases = [c for c in cases if not c.expected_valid]
        assert len(invalid_cases) == 3


# ── T052: High-severity block scenario (FR-022, FR-026) ─────────────────────


class TestHighSeverityBlockScenario:
    """Prove that an unresolved high-severity conflict produces a generation block.

    Uses conformance fixtures fed through the glossary reducer to verify
    the block gate behavior end-to-end.
    """

    def test_block_scenario_produces_generation_block(self) -> None:
        """Full sequence: scope → strictness → term → check(block) → blocked."""
        scope_data = _load_fixture("glossary/valid/glossary_scope_activated.json")
        strictness_data = _load_fixture("glossary/valid/glossary_strictness_set.json")
        term_data = _load_fixture("glossary/valid/term_candidate_observed.json")
        check_data = _load_fixture("glossary/valid/semantic_check_evaluated_block.json")
        blocked_data = _load_fixture("glossary/valid/generation_blocked.json")

        events = [
            _make_event("GlossaryScopeActivated", scope_data, lamport_clock=1),
            _make_event("GlossaryStrictnessSet", strictness_data, lamport_clock=2),
            _make_event("TermCandidateObserved", term_data, lamport_clock=3),
            _make_event("SemanticCheckEvaluated", check_data, lamport_clock=4),
            _make_event("GenerationBlockedBySemanticConflict", blocked_data, lamport_clock=5),
        ]

        state = reduce_glossary_events(events)

        # Block gate fired
        assert len(state.generation_blocks) == 1
        block = state.generation_blocks[0]
        assert block.blocking_strictness == "max"

        # Semantic check recorded
        assert len(state.semantic_checks) == 1
        assert state.semantic_checks[0].severity == "high"
        assert state.semantic_checks[0].recommended_action == "block"

        # Strictness was set to max
        assert state.current_strictness == "max"

    def test_block_references_correct_conflict(self) -> None:
        """Block event references the semantic check event via conflict_event_ids."""
        scope_data = _load_fixture("glossary/valid/glossary_scope_activated.json")
        strictness_data = _load_fixture("glossary/valid/glossary_strictness_set.json")
        term_data = _load_fixture("glossary/valid/term_candidate_observed.json")
        check_data = _load_fixture("glossary/valid/semantic_check_evaluated_block.json")
        blocked_data = _load_fixture("glossary/valid/generation_blocked.json")

        check_event_id = "01HTESTCHECK00000000000001"
        events = [
            _make_event("GlossaryScopeActivated", scope_data, lamport_clock=1),
            _make_event("GlossaryStrictnessSet", strictness_data, lamport_clock=2),
            _make_event("TermCandidateObserved", term_data, lamport_clock=3),
            _make_event("SemanticCheckEvaluated", check_data, lamport_clock=4,
                        event_id=check_event_id),
            _make_event("GenerationBlockedBySemanticConflict", blocked_data, lamport_clock=5),
        ]

        state = reduce_glossary_events(events)

        block = state.generation_blocks[0]
        assert check_event_id in block.conflict_event_ids


# ── T053: Warn scenario + burst cap (FR-023, FR-024) ────────────────────────


class TestWarnScenario:
    """Prove medium-severity warns without blocking."""

    def test_warn_does_not_block(self) -> None:
        """Warn-level check produces no generation block."""
        scope_data = _load_fixture("glossary/valid/glossary_scope_activated.json")
        term_data = _load_fixture("glossary/valid/term_candidate_observed.json")
        warn_data = _load_fixture("glossary/valid/semantic_check_evaluated_warn.json")

        events = [
            _make_event("GlossaryScopeActivated", scope_data, lamport_clock=1),
            _make_event("TermCandidateObserved", term_data, lamport_clock=2),
            _make_event("SemanticCheckEvaluated", warn_data, lamport_clock=3),
        ]

        state = reduce_glossary_events(events)

        # Warn recorded
        assert len(state.semantic_checks) == 1
        assert state.semantic_checks[0].severity == "medium"
        assert state.semantic_checks[0].recommended_action == "warn"

        # No block
        assert len(state.generation_blocks) == 0


class TestBurstCap:
    """Prove clarification burst cap limits to 3 per semantic check."""

    def test_burst_cap_limits_clarifications(self) -> None:
        """5 clarification requests with same check ID: 3 accepted, 2 anomalies."""
        scope_data = _load_fixture("glossary/valid/glossary_scope_activated.json")
        check_data = _load_fixture("glossary/valid/semantic_check_evaluated_block.json")

        shared_check_event_id = "01HTESTCHECK00000000000001"

        events: List[Event] = [
            _make_event("GlossaryScopeActivated", scope_data, lamport_clock=1),
            _make_event("SemanticCheckEvaluated", check_data, lamport_clock=2,
                        event_id=shared_check_event_id),
        ]

        # 5 clarification requests all referencing the same semantic check
        for i in range(5):
            clar_payload: Dict[str, Any] = {
                "mission_id": "mission-fixture-001",
                "scope_id": "scope-team-domain",
                "step_id": "step-002",
                "semantic_check_event_id": shared_check_event_id,
                "term": f"term-{i}",
                "question": f"What does term-{i} mean?",
                "options": ["Meaning A", "Meaning B"],
                "urgency": "high",
                "actor": "agent-001",
            }
            events.append(
                _make_event(
                    "GlossaryClarificationRequested",
                    clar_payload,
                    lamport_clock=3 + i,
                )
            )

        state = reduce_glossary_events(events, mode="permissive")

        # Burst cap: exactly 3 accepted
        assert len(state.clarifications) == 3

        # 2 excess requests generated anomalies
        burst_anomalies = [
            a for a in state.anomalies if "Burst cap exceeded" in a.reason
        ]
        assert len(burst_anomalies) == 2

    def test_burst_cap_strict_raises(self) -> None:
        """In strict mode, 4th clarification raises SpecKittyEventsError."""
        from spec_kitty_events.models import SpecKittyEventsError

        scope_data = _load_fixture("glossary/valid/glossary_scope_activated.json")
        check_data = _load_fixture("glossary/valid/semantic_check_evaluated_block.json")

        shared_check_event_id = "01HTESTCHECK00000000000001"

        events: List[Event] = [
            _make_event("GlossaryScopeActivated", scope_data, lamport_clock=1),
            _make_event("SemanticCheckEvaluated", check_data, lamport_clock=2,
                        event_id=shared_check_event_id),
        ]

        for i in range(4):
            clar_payload: Dict[str, Any] = {
                "mission_id": "mission-fixture-001",
                "scope_id": "scope-team-domain",
                "step_id": "step-002",
                "semantic_check_event_id": shared_check_event_id,
                "term": f"term-{i}",
                "question": f"What does term-{i} mean?",
                "options": ["Meaning A", "Meaning B"],
                "urgency": "high",
                "actor": "agent-001",
            }
            events.append(
                _make_event(
                    "GlossaryClarificationRequested",
                    clar_payload,
                    lamport_clock=3 + i,
                )
            )

        with pytest.raises(SpecKittyEventsError, match="Clarification burst cap exceeded"):
            reduce_glossary_events(events, mode="strict")


# ── Schema Validation: Dual-Layer Active ─────────────────────────────────────


class TestGlossarySchemaValidation:
    """Assert glossary event types have dual-layer validation (not single-layer)."""

    def test_scope_activated_schema_not_skipped(self) -> None:
        """validate_event for GlossaryScopeActivated returns schema_check_skipped=False."""
        data = _load_fixture("glossary/valid/glossary_scope_activated.json")
        result = validate_event(data, "GlossaryScopeActivated")
        assert result.valid is True
        assert result.schema_check_skipped is False

    def test_term_candidate_schema_not_skipped(self) -> None:
        data = _load_fixture("glossary/valid/term_candidate_observed.json")
        result = validate_event(data, "TermCandidateObserved")
        assert result.valid is True
        assert result.schema_check_skipped is False

    def test_semantic_check_schema_not_skipped(self) -> None:
        data = _load_fixture("glossary/valid/semantic_check_evaluated_block.json")
        result = validate_event(data, "SemanticCheckEvaluated")
        assert result.valid is True
        assert result.schema_check_skipped is False

    def test_clarification_requested_schema_not_skipped(self) -> None:
        data = _load_fixture("glossary/valid/glossary_clarification_requested.json")
        result = validate_event(data, "GlossaryClarificationRequested")
        assert result.valid is True
        assert result.schema_check_skipped is False

    def test_clarification_resolved_schema_not_skipped(self) -> None:
        data = _load_fixture("glossary/valid/glossary_clarification_resolved.json")
        result = validate_event(data, "GlossaryClarificationResolved")
        assert result.valid is True
        assert result.schema_check_skipped is False

    def test_sense_updated_schema_not_skipped(self) -> None:
        data = _load_fixture("glossary/valid/glossary_sense_updated.json")
        result = validate_event(data, "GlossarySenseUpdated")
        assert result.valid is True
        assert result.schema_check_skipped is False

    def test_generation_blocked_schema_not_skipped(self) -> None:
        data = _load_fixture("glossary/valid/generation_blocked.json")
        result = validate_event(data, "GenerationBlockedBySemanticConflict")
        assert result.valid is True
        assert result.schema_check_skipped is False

    def test_strictness_set_schema_not_skipped(self) -> None:
        data = _load_fixture("glossary/valid/glossary_strictness_set.json")
        result = validate_event(data, "GlossaryStrictnessSet")
        assert result.valid is True
        assert result.schema_check_skipped is False
