---
work_package_id: WP10
title: Conformance Fixtures & Integration Verification
lane: "for_review"
dependencies:
- WP06
base_branch: 007-glossary-semantic-integrity-contracts-WP06
base_commit: 36b0cdc3f4066d989ad8ab413208b3854c24a655
created_at: '2026-02-16T13:32:08.193177+00:00'
subtasks:
- T049
- T050
- T051
- T052
- T053
- T054
phase: Phase 4 - Conformance & Polish
assignee: ''
agent: "claude-opus"
shell_pid: "29932"
review_status: ''
reviewed_by: ''
history:
- timestamp: '2026-02-16T12:00:00Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP10 – Conformance Fixtures & Integration Verification

## ⚠️ IMPORTANT: Review Feedback Status

- **Has review feedback?**: Check the `review_status` field above.
- **You must address all feedback** before your work is complete.

---

## Review Feedback

*[This section is empty initially.]*

---

## Objectives & Success Criteria

- Create 12 glossary conformance fixture JSON files (9 valid, 3 invalid).
- Register all fixtures in the existing `conformance/fixtures/manifest.json`.
- Write 3 conformance tests proving the required gate behaviors.
- Run full integration verification: mypy, test suite, coverage, export check.

**Success**: All conformance fixtures load and validate correctly. All 3 scenario tests pass. `mypy --strict` clean. Coverage ≥98%. All ~22 glossary exports importable from top-level.

## Context & Constraints

- **Reference**: `src/spec_kitty_events/conformance/fixtures/manifest.json` — existing fixture manifest structure.
- **Reference**: `src/spec_kitty_events/conformance/fixtures/collaboration/` — existing fixture directory pattern.
- **Reference**: `kitty-specs/007-glossary-semantic-integrity-contracts/contracts/glossary-events.md` — 3 conformance fixture specifications.
- **Fixture path**: `src/spec_kitty_events/conformance/fixtures/glossary/valid/` and `glossary/invalid/`.
- **Test file**: `tests/test_glossary_conformance.py` (new file).

**Implementation command**: `spec-kitty implement WP10 --base WP09` (or `--base WP08` if WP09 is not yet merged — use whichever is latest)

## Subtasks & Detailed Guidance

### Subtask T049 – Create valid glossary fixture JSON files

- **Purpose**: 9 valid fixture files, one per event type plus a `semantic_check_evaluated_warn` variant.
- **Steps**:
  1. Create directory: `src/spec_kitty_events/conformance/fixtures/glossary/valid/`
  2. Create 9 JSON files, each being a complete `Event` JSON object:

     **glossary_scope_activated.json**:
     ```json
     {
       "event_id": "01HTEST000000SCOPEACTIVAT",
       "event_type": "GlossaryScopeActivated",
       "aggregate_id": "mission-fixture-001",
       "payload": {
         "mission_id": "mission-fixture-001",
         "scope_id": "scope-team-domain",
         "scope_type": "team_domain",
         "glossary_version_id": "v1"
       },
       "timestamp": "2026-02-16T10:00:00Z",
       "node_id": "fixture-node",
       "lamport_clock": 1,
       "correlation_id": "01HTESTCORRELATION000001",
       "schema_version": "2.0.0"
     }
     ```

     Create similar files for:
     - `term_candidate_observed.json` (clock=2, confidence=0.7)
     - `semantic_check_evaluated_block.json` (clock=3, severity=high, recommended_action=block, effective_strictness=max)
     - `semantic_check_evaluated_warn.json` (clock=3, severity=medium, recommended_action=warn, effective_strictness=medium)
     - `generation_blocked.json` (clock=4, blocking_strictness=max)
     - `glossary_clarification_requested.json` (clock=5, with semantic_check_event_id)
     - `glossary_clarification_resolved.json` (clock=6, with clarification_event_id)
     - `glossary_sense_updated.json` (clock=7, with before/after sense)
     - `glossary_strictness_set.json` (clock=8, new_strictness=max)

  3. Ensure all `event_id` values are valid 26-character ULID format strings.
  4. All fields must match the Pydantic model schemas exactly.
- **Files**: `src/spec_kitty_events/conformance/fixtures/glossary/valid/` (9 new files).
- **Parallel?**: Yes — fixture creation is independent.
- **Notes**: Reference existing fixtures (e.g., `collaboration/valid/participant_joined_valid.json`) for the exact JSON structure of `Event`.

### Subtask T050 – Create invalid glossary fixture JSON files

- **Purpose**: 3 invalid fixture files that should fail validation.
- **Steps**:
  1. Create directory: `src/spec_kitty_events/conformance/fixtures/glossary/invalid/`
  2. Create 3 JSON files:

     **semantic_check_missing_step_id.json**: `SemanticCheckEvaluated` event with `step_id` removed from payload.

     **glossary_scope_invalid_type.json**: `GlossaryScopeActivated` event with `scope_type: "invalid_scope"`.

     **clarification_missing_check_ref.json**: `GlossaryClarificationRequested` event with `semantic_check_event_id` removed.

- **Files**: `src/spec_kitty_events/conformance/fixtures/glossary/invalid/` (3 new files).
- **Parallel?**: Yes.

### Subtask T051 – Register fixtures in manifest.json

- **Purpose**: Add all 12 glossary fixtures to the conformance manifest.
- **Steps**:
  1. Open `src/spec_kitty_events/conformance/fixtures/manifest.json`.
  2. Add 12 entries to the `"fixtures"` array:
     ```json
     {
       "id": "glossary-scope-activated-valid",
       "path": "glossary/valid/glossary_scope_activated.json",
       "expected_result": "valid",
       "event_type": "GlossaryScopeActivated",
       "notes": "Valid GlossaryScopeActivatedPayload with team_domain scope",
       "min_version": "2.0.0"
     }
     ```
  3. Follow the same pattern for all 9 valid and 3 invalid fixtures.
  4. Use descriptive `"notes"` for each fixture explaining what it tests.
- **Files**: `src/spec_kitty_events/conformance/fixtures/manifest.json`.
- **Parallel?**: No — depends on T049 and T050 filenames being finalized.

### Subtask T052 – Conformance test: high-severity block scenario

- **Purpose**: Prove that an unresolved high-severity conflict produces a generation block.
- **Steps**:
  1. Create `tests/test_glossary_conformance.py`.
  2. Load the fixture sequence:
     - `glossary_scope_activated.json`
     - `glossary_strictness_set.json` (strictness=max)
     - `term_candidate_observed.json`
     - `semantic_check_evaluated_block.json` (severity=high, action=block)
     - `generation_blocked.json`
  3. Reduce through `reduce_glossary_events()`.
  4. Assert:
     - `state.generation_blocks` is non-empty.
     - Block references the correct conflict event ID.
     - `state.semantic_checks` contains the high-severity check.
- **Files**: `tests/test_glossary_conformance.py`.
- **Parallel?**: Yes — independent of T053.
- **Notes**: This proves FR-022 and the hard invariant FR-026. Load fixtures from the installed package path using the existing conformance loader if available, or use `importlib.resources`.

### Subtask T053 – Conformance test: warn scenario + burst cap

- **Purpose**: Prove medium-severity warns without blocking, and burst cap limits to 3.
- **Steps**:
  1. **Warn scenario**:
     - Load: `glossary_scope_activated.json`, `term_candidate_observed.json`, `semantic_check_evaluated_warn.json`
     - Reduce and assert: `state.semantic_checks` has the warn event, `state.generation_blocks` is empty.

  2. **Burst cap scenario**:
     - Construct 5 `GlossaryClarificationRequested` events programmatically (all with same `semantic_check_event_id`), preceded by `GlossaryScopeActivated` and `SemanticCheckEvaluated`.
     - Reduce in permissive mode.
     - Assert: exactly 3 `ClarificationRecord` entries, 2 anomalies for the excess requests.
- **Files**: `tests/test_glossary_conformance.py`.
- **Parallel?**: Yes.
- **Notes**: The warn test proves FR-023. The burst cap test proves FR-024.

### Subtask T054 – Integration verification

- **Purpose**: Final verification that everything works together.
- **Steps**:
  1. Run `mypy --strict src/spec_kitty_events/glossary.py` — must pass with 0 errors.
  2. Run `python3.11 -m pytest` — full test suite must pass.
  3. Check coverage: `python3.11 -m pytest --cov=src/spec_kitty_events --cov-report=term-missing` — target ≥98%.
  4. Verify exports: In a Python session or test:
     ```python
     from spec_kitty_events import (
         GLOSSARY_SCOPE_ACTIVATED, TERM_CANDIDATE_OBSERVED,
         SEMANTIC_CHECK_EVALUATED, GLOSSARY_CLARIFICATION_REQUESTED,
         GLOSSARY_CLARIFICATION_RESOLVED, GLOSSARY_SENSE_UPDATED,
         GENERATION_BLOCKED_BY_SEMANTIC_CONFLICT, GLOSSARY_STRICTNESS_SET,
         GLOSSARY_EVENT_TYPES, SemanticConflictEntry,
         GlossaryScopeActivatedPayload, TermCandidateObservedPayload,
         SemanticCheckEvaluatedPayload, GlossaryClarificationRequestedPayload,
         GlossaryClarificationResolvedPayload, GlossarySenseUpdatedPayload,
         GenerationBlockedBySemanticConflictPayload, GlossaryStrictnessSetPayload,
         GlossaryAnomaly, ClarificationRecord, ReducedGlossaryState,
         reduce_glossary_events,
     )
     assert len(GLOSSARY_EVENT_TYPES) == 8
     ```
  5. If any check fails, fix and re-run.
- **Files**: None (verification only).
- **Parallel?**: No — final step.

## Risks & Mitigations

- **Risk**: Fixture JSON structure doesn't match `Event.model_validate()` expectations. **Mitigation**: Validate each fixture against `Event(**json.load(f))` during test setup.
- **Risk**: Coverage drops below 98% due to new code. **Mitigation**: Ensure tests cover all branches (strict + permissive for every integrity check).

## Review Guidance

- All 9 valid fixtures must load and validate against their payload models.
- All 3 invalid fixtures must fail validation.
- Manifest entries must have correct `"path"` values matching actual file locations.
- Conformance tests must reduce fixture sequences through the actual reducer (not just validate payloads).
- Integration check: `mypy --strict` must pass with 0 errors, not just 0 warnings.

## Activity Log

- 2026-02-16T12:00:00Z – system – lane=planned – Prompt created.
- 2026-02-16T13:32:08Z – claude-opus – shell_pid=29932 – lane=doing – Assigned agent via workflow command
- 2026-02-16T13:42:10Z – claude-opus – shell_pid=29932 – lane=for_review – Ready for review: 12 glossary fixtures, 43 conformance tests, 928 total tests pass
