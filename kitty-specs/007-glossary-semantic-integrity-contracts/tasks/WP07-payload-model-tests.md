---
work_package_id: WP07
title: Payload Model Tests
lane: "doing"
dependencies: [WP04]
base_branch: 007-glossary-semantic-integrity-contracts-WP04
base_commit: 1cc294fbe6cea88e0fcd6f32bc53645a7db5cb4d
created_at: '2026-02-16T13:26:22.789008+00:00'
subtasks:
- T031
- T032
- T033
- T034
- T035
- T036
phase: Phase 3 - Testing
assignee: ''
agent: "claude-opus"
shell_pid: "25971"
review_status: ''
reviewed_by: ''
history:
- timestamp: '2026-02-16T12:00:00Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP07 – Payload Model Tests

## ⚠️ IMPORTANT: Review Feedback Status

- **Has review feedback?**: Check the `review_status` field above.
- **You must address all feedback** before your work is complete.

---

## Review Feedback

*[This section is empty initially.]*

---

## Objectives & Success Criteria

- Comprehensive unit tests for all 8 payload models + `SemanticConflictEntry`.
- Each model tested for: valid construction, `.model_dump()` round-trip, invalid data rejection.
- Business rule validation: confidence bounds, non-empty constraints, Literal value enforcement.

**Success**: All tests pass, achieving full branch coverage for model construction and validation logic.

## Context & Constraints

- **Test file**: `tests/test_glossary.py` (new file).
- **Pattern**: Follow `tests/test_collaboration.py` style — parametrized pytest tests, clear test names.
- **Imports**: Import from `spec_kitty_events` top-level (not directly from `glossary` module).
- **Run**: `python3.11 -m pytest tests/test_glossary.py -v`

**Implementation command**: `spec-kitty implement WP07 --base WP04`

## Subtasks & Detailed Guidance

### Subtask T031 – Tests for scope and strictness payloads

- **Purpose**: Verify `GlossaryScopeActivatedPayload` and `GlossaryStrictnessSetPayload`.
- **Steps**:
  1. Test valid `GlossaryScopeActivatedPayload` with all 4 scope_type values.
  2. Test `.model_dump()` round-trip: construct → dump → reconstruct → assert equal.
  3. Test rejection of invalid `scope_type` (e.g., `"invalid_scope"`).
  4. Test rejection of empty `scope_id`, `mission_id`, `glossary_version_id`.
  5. Test valid `GlossaryStrictnessSetPayload` with all 3 strictness modes.
  6. Test `previous_strictness=None` (initial setting) is valid.
  7. Test rejection of invalid `new_strictness` value.
- **Files**: `tests/test_glossary.py`.
- **Parallel?**: Yes — all subtasks test independent models.

### Subtask T032 – Tests for term candidate payload

- **Purpose**: Verify `TermCandidateObservedPayload` with focus on confidence bounds.
- **Steps**:
  1. Test valid construction with confidence=0.7.
  2. Test confidence boundary values: 0.0 (valid), 1.0 (valid).
  3. Test confidence rejection: -0.1 (invalid), 1.1 (invalid).
  4. Test empty `term_surface` rejection (min_length=1).
  5. Test `step_metadata` default (empty dict when omitted).
  6. Test `step_metadata` with values: `{"primitive": "specify"}`.
  7. Test `.model_dump()` round-trip.
- **Files**: `tests/test_glossary.py`.
- **Parallel?**: Yes.

### Subtask T033 – Tests for semantic check and conflict entry

- **Purpose**: Verify `SemanticCheckEvaluatedPayload` and `SemanticConflictEntry`.
- **Steps**:
  1. Test valid `SemanticConflictEntry` with each `nature` value (overloaded, drift, ambiguous).
  2. Test rejection of invalid `nature` or `severity` values.
  3. Test valid `SemanticCheckEvaluatedPayload` with conflicts list.
  4. Test with empty conflicts tuple (valid — represents a "pass" check).
  5. Test all `recommended_action` values: block, warn, pass.
  6. Test all `effective_strictness` values: off, medium, max.
  7. Test confidence bounds (same as T032).
  8. Test round-trip with nested `SemanticConflictEntry` objects.
- **Files**: `tests/test_glossary.py`.
- **Parallel?**: Yes.

### Subtask T034 – Tests for clarification payloads

- **Purpose**: Verify `GlossaryClarificationRequestedPayload` and `GlossaryClarificationResolvedPayload`.
- **Steps**:
  1. Test valid `GlossaryClarificationRequestedPayload` with all fields.
  2. Test `semantic_check_event_id` is required (not optional).
  3. Test `options` tuple with multiple values.
  4. Test all `urgency` values: low, medium, high.
  5. Test valid `GlossaryClarificationResolvedPayload`.
  6. Test `clarification_event_id` is required.
  7. Test round-trip for both models.
- **Files**: `tests/test_glossary.py`.
- **Parallel?**: Yes.

### Subtask T035 – Tests for generation block payload

- **Purpose**: Verify `GenerationBlockedBySemanticConflictPayload` business rules.
- **Steps**:
  1. Test valid construction with `blocking_strictness="medium"`.
  2. Test valid construction with `blocking_strictness="max"`.
  3. Test rejection of `blocking_strictness="off"` — must fail validation.
  4. Test `conflict_event_ids` must be non-empty — empty tuple should be rejected.
  5. Test valid `step_metadata` with and without values.
  6. Test round-trip.
- **Files**: `tests/test_glossary.py`.
- **Parallel?**: Yes.
- **Notes**: If Pydantic `min_length` doesn't work on `Tuple[str, ...]`, verify the WP03 implementation uses a `@field_validator` instead, and test accordingly.

### Subtask T036 – Tests for sense updated payload

- **Purpose**: Verify `GlossarySenseUpdatedPayload` with optional `before_sense`.
- **Steps**:
  1. Test valid construction with `before_sense=None` (initial definition).
  2. Test valid construction with `before_sense="old meaning"` (update).
  3. Test empty `term_surface` rejection.
  4. Test empty `after_sense` rejection.
  5. Test round-trip for both cases (None and non-None before_sense).
- **Files**: `tests/test_glossary.py`.
- **Parallel?**: Yes.

## Risks & Mitigations

- **Risk**: Pydantic v2 `min_length` on `Tuple` may not behave as expected. **Mitigation**: Test this explicitly in T035; if it fails, update the model in WP03 to use a validator.

## Review Guidance

- Every model must have at least: valid construction test, round-trip test, and invalid data rejection test.
- Boundary values (0.0, 1.0 for confidence) must be tested as valid.
- Out-of-bounds values (-0.1, 1.1) must be tested as invalid.
- `blocking_strictness="off"` must be rejected.
- Empty string fields with `min_length=1` must be rejected.

## Activity Log

- 2026-02-16T12:00:00Z – system – lane=planned – Prompt created.
- 2026-02-16T13:26:23Z – claude-opus – shell_pid=25971 – lane=doing – Assigned agent via workflow command
