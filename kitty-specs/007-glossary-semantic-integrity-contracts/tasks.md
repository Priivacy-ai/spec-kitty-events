# Work Packages: Glossary Semantic Integrity Contracts

**Inputs**: Design documents from `kitty-specs/007-glossary-semantic-integrity-contracts/`
**Prerequisites**: plan.md, spec.md, data-model.md, contracts/glossary-events.md, research.md, quickstart.md
**Target Branch**: `2.x` (cut from `main` HEAD at branch-cut time; `f4692ea` at planning time)

**Organization**: 54 subtasks (`Txxx`) across 10 work packages (`WPxx`). Each work package is independently deliverable.

---

## Work Package WP01: Branch Setup & Module Scaffold (Priority: P0)

**Goal**: Establish the `2.x` branch and create the `glossary.py` module skeleton with event type constants.
**Independent Test**: Module imports successfully, all 8 event type constants are defined, `GLOSSARY_EVENT_TYPES` frozenset is accessible.
**Prompt**: `tasks/WP01-branch-setup-and-scaffold.md`
**Estimated Size**: ~300 lines

### Included Subtasks
- [x] T001 Cut `2.x` branch from `main` HEAD (`f4692ea` at planning time), tag as `2.x-baseline`
- [x] T002 Create `src/spec_kitty_events/glossary.py` scaffold (docstring, `from __future__ import annotations`, imports)
- [x] T003 Define 8 event type constants and `GLOSSARY_EVENT_TYPES` frozenset
- [x] T004 Add `pyproject.toml` package-data entries for `conformance/fixtures/glossary/valid/*.json` and `conformance/fixtures/glossary/invalid/*.json`

### Implementation Notes
- Branch cut is the very first step — all subsequent WPs work on `2.x`.
- Module scaffold follows `collaboration.py` section structure: Constants → Value Objects → Payload Models → Reducer Output Models → Reducer.
- Event type string values match PascalCase event names (e.g., `GLOSSARY_SCOPE_ACTIVATED = "GlossaryScopeActivated"`).

### Parallel Opportunities
- T002/T003 and T004 touch different files and can proceed in parallel.

### Dependencies
- None (starting package).

### Risks & Mitigations
- No `2.x` branch on remote — coordinate push timing with team.

---

## Work Package WP02: Core Payload Models — Scope, Term, Sense, Strictness (Priority: P1)

**Goal**: Define the 5 payload models for scope activation, term observation, sense update, strictness configuration, and the SemanticConflictEntry value object.
**Independent Test**: All 5 models construct with valid data, reject invalid data, and round-trip through `.model_dump()` / model reconstruction.
**Prompt**: `tasks/WP02-core-payload-models.md`
**Estimated Size**: ~450 lines

### Included Subtasks
- [x] T005 [P] Define `SemanticConflictEntry` value object (term, nature, severity, description)
- [x] T006 [P] Define `GlossaryScopeActivatedPayload` (mission_id, scope_id, scope_type, glossary_version_id)
- [x] T007 [P] Define `TermCandidateObservedPayload` (mission_id, scope_id, step_id, term_surface, confidence, actor, step_metadata)
- [x] T008 [P] Define `GlossarySenseUpdatedPayload` (mission_id, scope_id, term_surface, before_sense, after_sense, reason, actor)
- [x] T009 [P] Define `GlossaryStrictnessSetPayload` (mission_id, new_strictness, previous_strictness, actor)

### Implementation Notes
- All models: `ConfigDict(frozen=True)`, `from __future__ import annotations`.
- `scope_type` uses `Literal["spec_kitty_core", "team_domain", "audience_domain", "mission_local"]`.
- `confidence` field: `Field(..., ge=0.0, le=1.0)`.
- `term_surface`: `Field(..., min_length=1)`.
- `step_metadata`: `Dict[str, str]` with `default_factory=dict`.

### Parallel Opportunities
- All 5 models are independent and can be written in parallel.

### Dependencies
- Depends on WP01 (module scaffold must exist).

### Risks & Mitigations
- Pydantic v2 `Literal` type serialization — verify round-trip in tests (WP06).

---

## Work Package WP03: Gate & Clarification Payload Models (Priority: P1)

**Goal**: Define the 3 remaining payload models for semantic check evaluation, clarification request/resolution, and generation block.
**Independent Test**: All 3 models construct with valid data, reject invalid data, and enforce business rules (blocking_strictness ≠ "off", conflict_event_ids non-empty).
**Prompt**: `tasks/WP03-gate-clarification-models.md`
**Estimated Size**: ~400 lines

### Included Subtasks
- [x] T010 Define `SemanticCheckEvaluatedPayload` (mission_id, scope_id, step_id, conflicts, severity, confidence, recommended_action, effective_strictness, step_metadata)
- [x] T011 [P] Define `GlossaryClarificationRequestedPayload` (mission_id, scope_id, step_id, semantic_check_event_id, term, question, options, urgency, actor)
- [x] T012 [P] Define `GlossaryClarificationResolvedPayload` (mission_id, clarification_event_id, selected_meaning, actor)
- [x] T013 Define `GenerationBlockedBySemanticConflictPayload` (mission_id, step_id, conflict_event_ids, blocking_strictness, step_metadata)

### Implementation Notes
- `SemanticCheckEvaluatedPayload.conflicts` is `Tuple[SemanticConflictEntry, ...]` — uses the value object from WP02.
- `GenerationBlockedBySemanticConflictPayload.blocking_strictness` uses `Literal["medium", "max"]` — intentionally excludes `"off"`.
- `conflict_event_ids`: use `Field(..., min_length=1)` on the tuple to enforce non-empty.
- `semantic_check_event_id` on clarification request is the burst-window grouping key.

### Parallel Opportunities
- T011 and T012 are independent of T010 and T013.

### Dependencies
- Depends on WP02 (`SemanticConflictEntry` must exist).

### Risks & Mitigations
- Pydantic `min_length` on `Tuple` — verify behavior with `Tuple[str, ...]` (Pydantic v2 supports this).

---

## Work Package WP04: Reducer Output Models & Exports (Priority: P1)

**Goal**: Define the reducer output models (`GlossaryAnomaly`, `ClarificationRecord`, `ReducedGlossaryState`) and add all glossary exports to `__init__.py`.
**Independent Test**: All output models construct correctly, `ReducedGlossaryState` defaults are valid, all ~21 new symbols are importable from package top-level.
**Prompt**: `tasks/WP04-reducer-models-and-exports.md`
**Estimated Size**: ~400 lines

### Included Subtasks
- [x] T014 Define `GlossaryAnomaly` model (event_id, event_type, reason)
- [x] T015 Define `ClarificationRecord` model (request_event_id, semantic_check_event_id, term, resolved, resolution_event_id)
- [x] T016 Define `ReducedGlossaryState` model (all ~12 fields with defaults)
- [x] T017 Add all glossary imports and `__all__` entries to `__init__.py` (~21 new exports)
- [x] T018 Run `mypy --strict` on `glossary.py` to catch type issues early

### Implementation Notes
- `ReducedGlossaryState` follows `ReducedCollaborationState` pattern: frozen Pydantic model with Field defaults.
- `current_strictness` defaults to `"medium"` (spec: medium is default).
- Dict fields use `default_factory=dict`, tuple fields use `default_factory=tuple`.
- Export block in `__init__.py` follows the existing section pattern (comment header + imports + `__all__` entries).

### Parallel Opportunities
- T014/T015/T016 are models (parallel), T017 is the export wiring.

### Dependencies
- Depends on WP03 (all payload models must exist before exports can reference them).

### Risks & Mitigations
- Large `__init__.py` (~86 exports after) — maintain alphabetical order within section.

---

## Work Package WP05: Reducer — Scope, Strictness & Term Processing (Priority: P1)

**Goal**: Implement the reducer pipeline skeleton and processing for scope activation, strictness changes, term observation, and sense updates.
**Independent Test**: Reducing a sequence of scope/strictness/term events produces correct `ReducedGlossaryState` with active_scopes, current_strictness, term_candidates, and term_senses populated.
**Prompt**: `tasks/WP05-reducer-scope-term-processing.md`
**Estimated Size**: ~500 lines

### Included Subtasks
- [x] T019 Implement `reduce_glossary_events()` skeleton (filter → sort → dedup → empty-input short-circuit, mode parameter)
- [x] T020 Implement `GlossaryScopeActivated` processing (add to active_scopes mutable dict)
- [x] T021 Implement `GlossaryStrictnessSet` processing (update current_strictness, append to strictness_history)
- [x] T022 Implement `TermCandidateObserved` processing (append to term_candidates by term_surface)
- [x] T023 Implement `GlossarySenseUpdated` processing (update term_senses, integrity check for unobserved term)
- [x] T024 Extract `mission_id` from first processed event's payload

### Implementation Notes
- Late import of `dedup_events` and `status_event_sort_key` from `status.py` (inside function body, matching collaboration.py line 575).
- Scope validation: if event references scope_id not in active_scopes, strict mode raises, permissive mode records anomaly.
- Sense update integrity: if term_surface not in term_candidates for the same scope_id, strict mode raises, permissive mode records anomaly.
- Use mutable `Dict` and `List` intermediates during processing.

### Parallel Opportunities
- None — sequential pipeline implementation.

### Dependencies
- Depends on WP04 (output models and exports must exist).

### Risks & Mitigations
- Late import pattern — test that import works correctly at runtime.

---

## Work Package WP06: Reducer — Checks, Clarifications, Blocks & Assembly (Priority: P1)

**Goal**: Complete the reducer with semantic check processing, clarification lifecycle (including burst cap), generation block processing, and final frozen state assembly.
**Independent Test**: Full event sequence reduces to correct `ReducedGlossaryState` with all facets populated, burst cap enforced, and state frozen.
**Prompt**: `tasks/WP06-reducer-checks-clarifications-assembly.md`
**Estimated Size**: ~500 lines

### Included Subtasks
- [x] T025 Implement `SemanticCheckEvaluated` processing (append to semantic_checks list)
- [x] T026 Implement `GlossaryClarificationRequested` processing (create `ClarificationRecord`, enforce burst cap per `semantic_check_event_id`)
- [x] T027 Implement `GlossaryClarificationResolved` processing (mark record resolved, handle concurrent resolution with last-write-wins)
- [x] T028 Implement `GenerationBlockedBySemanticConflict` processing (append to generation_blocks)
- [x] T029 Implement final state assembly — freeze all mutable intermediates into `ReducedGlossaryState`
- [x] T030 Run `mypy --strict` on completed `glossary.py`

### Implementation Notes
- Burst cap enforcement: count unresolved `ClarificationRecord` entries grouped by `semantic_check_event_id`. If count >3, strict mode raises, permissive mode records anomaly and caps at 3.
- Concurrent resolution: if two `GlossaryClarificationResolved` reference the same `clarification_event_id`, the one processed last (by sort order) wins.
- Final assembly converts all mutable dicts/lists to frozen types (tuple, frozenset) matching `ReducedGlossaryState` field types.
- Event processing uses if/elif chain on `event.event_type` matching `collaboration.py` style.

### Parallel Opportunities
- None — sequential implementation within the reducer body.

### Dependencies
- Depends on WP05 (pipeline skeleton and scope/term processing must be complete).

### Risks & Mitigations
- Burst cap off-by-one — test with exactly 3, 4, and 5 requests in WP08.

---

## Work Package WP07: Payload Model Tests (Priority: P1)

**Goal**: Comprehensive unit tests for all 8 payload models and `SemanticConflictEntry`, covering valid construction, round-trip serialization, invalid data rejection, and business rule validation.
**Independent Test**: All tests pass, covering valid/invalid construction for every model, confidence bounds, and constraint enforcement.
**Prompt**: `tasks/WP07-payload-model-tests.md`
**Estimated Size**: ~450 lines

### Included Subtasks
- [x] T031 [P] Tests for `GlossaryScopeActivatedPayload` and `GlossaryStrictnessSetPayload` — valid construction, round-trip, invalid scope_type/strictness rejection
- [x] T032 [P] Tests for `TermCandidateObservedPayload` — valid, confidence bounds (reject <0.0, >1.0), empty term_surface rejection
- [x] T033 [P] Tests for `SemanticCheckEvaluatedPayload` + `SemanticConflictEntry` — valid with conflict list, recommended_action values, confidence bounds
- [x] T034 [P] Tests for `GlossaryClarificationRequestedPayload` and `GlossaryClarificationResolvedPayload` — valid, semantic_check_event_id presence
- [x] T035 [P] Tests for `GenerationBlockedBySemanticConflictPayload` — blocking_strictness cannot be "off", conflict_event_ids must be non-empty
- [x] T036 [P] Tests for `GlossarySenseUpdatedPayload` — valid, optional before_sense=None for initial definition

### Implementation Notes
- Test file: `tests/test_glossary.py` (payload models only).
- Follow existing test patterns from `tests/test_collaboration.py` (parametrized pytest tests).
- Each test function covers: valid construction, `.model_dump()` round-trip, and rejection of invalid inputs.
- Use `pytest.raises(ValidationError)` for rejection tests.

### Parallel Opportunities
- All 6 subtasks test independent models — fully parallelizable.

### Dependencies
- Depends on WP04 (all models defined, exports wired).

### Risks & Mitigations
- Pydantic v2 validation error message format may differ from v1 — check `ValidationError.errors()` structure.

---

## Work Package WP08: Reducer Tests — Happy Path & Determinism (Priority: P1)

**Goal**: Tests for the reducer's happy path, strictness tracking, dedup, and determinism invariant (including Hypothesis property test).
**Independent Test**: All tests pass, including 200-example Hypothesis property test proving permutation invariance.
**Prompt**: `tasks/WP08-reducer-tests-happy-path.md`
**Estimated Size**: ~500 lines

### Included Subtasks
- [x] T037 Test reducer with empty input — returns empty `ReducedGlossaryState` with defaults
- [x] T038 Test full happy path — scope activation → term observation → sense update → semantic check → generation block
- [x] T039 Test strictness tracking — initial default (`medium`), transitions, history preservation
- [x] T040 Test dedup — duplicate `event_id` entries discarded, same result as unique set
- [x] T041 Test determinism — Hypothesis property test with `@given(st.permutations(...))`, 200 examples
- [x] T042 Test clarification lifecycle — request/resolve pairs, burst cap at exactly 3

### Implementation Notes
- Test file: `tests/test_glossary_reducer.py`.
- Hypothesis test strategy: generate a fixed set of glossary events, then test that `reduce_glossary_events(permutation)` always equals `reduce_glossary_events(sorted_events)`.
- Use `@settings(max_examples=200)` matching existing property test pattern.
- Helper factory functions for creating test `Event` instances with glossary payloads.

### Parallel Opportunities
- All subtasks test independent aspects — parallelizable.

### Dependencies
- Depends on WP06 (reducer must be fully implemented).

### Risks & Mitigations
- Hypothesis may find unexpected orderings — ensure sort key is truly deterministic.

---

## Work Package WP09: Reducer Tests — Edge Cases & Dual-Mode (Priority: P1)

**Goal**: Tests for strict/permissive dual-mode behavior, edge cases (unobserved term, unactivated scope, concurrent resolution, mid-mission strictness change).
**Independent Test**: All edge case tests pass in both strict and permissive modes.
**Prompt**: `tasks/WP09-reducer-tests-edge-cases.md`
**Estimated Size**: ~450 lines

### Included Subtasks
- [x] T043 Test strict mode — raises on event for unactivated scope
- [x] T044 Test strict mode — raises on `GlossarySenseUpdated` for unobserved term
- [x] T045 Test permissive mode — records anomaly for unactivated scope, continues processing remaining events
- [x] T046 Test permissive mode — records anomaly for unobserved term sense update, continues
- [x] T047 Test concurrent clarification resolution — last-write-wins by causal ordering
- [x] T048 Test strictness change from `max` to `off` mid-mission — existing block events remain in state

### Implementation Notes
- Test file: `tests/test_glossary_reducer.py` (same file as WP08, or separate class).
- Strict mode tests use `pytest.raises(SpecKittyEventsError)`.
- Permissive mode tests assert `state.anomalies` contains expected entries with correct `reason` and `event_id`.
- Concurrent resolution test: create two `GlossaryClarificationResolved` events with same `clarification_event_id` but different actors, verify the one with higher sort key wins.

### Parallel Opportunities
- All subtasks test independent scenarios — parallelizable.

### Dependencies
- Depends on WP06 (reducer must be fully implemented).

### Risks & Mitigations
- Permissive mode must not lose events after an anomaly — test that subsequent valid events are still processed.

---

## Work Package WP10: Conformance Fixtures & Integration Verification (Priority: P2)

**Goal**: Create glossary conformance fixture JSON files, register them in the manifest, write conformance tests for the 3 required scenarios, and verify full integration (mypy, coverage, exports).
**Independent Test**: All conformance fixtures load and validate, all 3 scenario tests pass, mypy strict passes, coverage ≥98%.
**Prompt**: `tasks/WP10-conformance-and-integration.md`
**Estimated Size**: ~500 lines

### Included Subtasks
- [ ] T049 Create valid glossary fixture JSON files (9 files: one per event type + semantic_check_evaluated_warn variant)
- [ ] T050 Create invalid glossary fixture JSON files (3 files: missing step_id, invalid scope_type, missing semantic_check_event_id)
- [ ] T051 Register all 12 fixtures in `conformance/fixtures/manifest.json`
- [ ] T052 Write conformance test — high-severity block scenario (fixture sequence → reduce → assert block)
- [ ] T053 Write conformance test — medium-severity warn scenario + clarification burst cap scenario
- [ ] T054 Run full integration verification: `mypy --strict`, full test suite, coverage check, export verification

### Implementation Notes
- Fixture JSONs follow existing structure (see `conformance/fixtures/collaboration/valid/` for reference).
- Each valid fixture is a complete `Event` JSON with `event_type` and `payload` matching the glossary models.
- Manifest entries: `"id"`, `"path"`, `"expected_result"`, `"event_type"`, `"notes"`, `"min_version": "2.0.0"`.
- Conformance tests go in `tests/test_glossary_conformance.py`.
- Integration verification: `python3.11 -m pytest` with coverage, `mypy --strict src/spec_kitty_events/glossary.py`.

### Parallel Opportunities
- T049/T050/T051 (fixture creation) can proceed alongside T052/T053 (test writing).

### Dependencies
- Depends on WP06 (reducer), WP07 (payload tests validate models), WP08/WP09 (reducer tests validate behavior).

### Risks & Mitigations
- Fixture JSON format must exactly match `Event.model_validate()` expectations — validate against existing fixtures.

---

## Dependency & Execution Summary

```
WP01 (branch+scaffold)
  ↓
WP02 (core payload models)
  ↓
WP03 (gate+clarification models)
  ↓
WP04 (reducer output models + exports)
  ↓           ↘
WP05 (reducer: scope/term)    WP07 (payload model tests) ← can start after WP04
  ↓
WP06 (reducer: checks/clarifications/assembly)
  ↓           ↘           ↘
WP08 (reducer happy path)  WP09 (edge cases)  [WP07 may still be running]
  ↓           ↓              ↓
WP10 (conformance + integration) ← waits for WP07, WP08, WP09
```

- **Sequence**: WP01 → WP02 → WP03 → WP04 → WP05 → WP06 → WP10
- **Parallelization**: WP07 can start after WP04 (parallel with WP05/WP06). WP08 + WP09 run in parallel after WP06.
- **MVP Scope**: WP01–WP06 (typed events + working reducer). Tests and conformance (WP07–WP10) complete the feature.

---

## Subtask Index (Reference)

| Subtask | Summary | WP | Priority | Parallel? |
|---------|---------|-----|----------|-----------|
| T001 | Cut `2.x` branch, tag `2.x-baseline` | WP01 | P0 | No |
| T002 | Create `glossary.py` module scaffold | WP01 | P0 | Yes |
| T003 | Define 8 event type constants + frozenset | WP01 | P0 | Yes |
| T004 | Update `pyproject.toml` package-data | WP01 | P0 | Yes |
| T005 | Define `SemanticConflictEntry` value object | WP02 | P1 | Yes |
| T006 | Define `GlossaryScopeActivatedPayload` | WP02 | P1 | Yes |
| T007 | Define `TermCandidateObservedPayload` | WP02 | P1 | Yes |
| T008 | Define `GlossarySenseUpdatedPayload` | WP02 | P1 | Yes |
| T009 | Define `GlossaryStrictnessSetPayload` | WP02 | P1 | Yes |
| T010 | Define `SemanticCheckEvaluatedPayload` | WP03 | P1 | No |
| T011 | Define `GlossaryClarificationRequestedPayload` | WP03 | P1 | Yes |
| T012 | Define `GlossaryClarificationResolvedPayload` | WP03 | P1 | Yes |
| T013 | Define `GenerationBlockedBySemanticConflictPayload` | WP03 | P1 | No |
| T014 | Define `GlossaryAnomaly` model | WP04 | P1 | Yes |
| T015 | Define `ClarificationRecord` model | WP04 | P1 | Yes |
| T016 | Define `ReducedGlossaryState` model | WP04 | P1 | No |
| T017 | Add glossary exports to `__init__.py` | WP04 | P1 | No |
| T018 | Run `mypy --strict` checkpoint | WP04 | P1 | No |
| T019 | Implement reducer skeleton (filter/sort/dedup) | WP05 | P1 | No |
| T020 | Implement scope activation processing | WP05 | P1 | No |
| T021 | Implement strictness set processing | WP05 | P1 | No |
| T022 | Implement term candidate observation processing | WP05 | P1 | No |
| T023 | Implement sense update processing | WP05 | P1 | No |
| T024 | Extract mission_id from first event | WP05 | P1 | No |
| T025 | Implement semantic check processing | WP06 | P1 | No |
| T026 | Implement clarification request processing + burst cap | WP06 | P1 | No |
| T027 | Implement clarification resolution processing | WP06 | P1 | No |
| T028 | Implement generation block processing | WP06 | P1 | No |
| T029 | Implement final state assembly | WP06 | P1 | No |
| T030 | Run `mypy --strict` on complete reducer | WP06 | P1 | No |
| T031 | Tests: scope + strictness payloads | WP07 | P1 | Yes |
| T032 | Tests: term candidate payload | WP07 | P1 | Yes |
| T033 | Tests: semantic check + conflict entry | WP07 | P1 | Yes |
| T034 | Tests: clarification payloads | WP07 | P1 | Yes |
| T035 | Tests: generation block payload | WP07 | P1 | Yes |
| T036 | Tests: sense updated payload | WP07 | P1 | Yes |
| T037 | Test: reducer empty input | WP08 | P1 | Yes |
| T038 | Test: full happy path | WP08 | P1 | No |
| T039 | Test: strictness tracking | WP08 | P1 | Yes |
| T040 | Test: dedup behavior | WP08 | P1 | Yes |
| T041 | Test: determinism (Hypothesis 200 examples) | WP08 | P1 | No |
| T042 | Test: clarification lifecycle + burst cap | WP08 | P1 | No |
| T043 | Test: strict mode — unactivated scope | WP09 | P1 | Yes |
| T044 | Test: strict mode — unobserved term | WP09 | P1 | Yes |
| T045 | Test: permissive mode — scope anomaly | WP09 | P1 | Yes |
| T046 | Test: permissive mode — term anomaly | WP09 | P1 | Yes |
| T047 | Test: concurrent clarification resolution | WP09 | P1 | Yes |
| T048 | Test: strictness max→off mid-mission | WP09 | P1 | Yes |
| T049 | Create valid fixture JSONs (9 files) | WP10 | P2 | Yes |
| T050 | Create invalid fixture JSONs (3 files) | WP10 | P2 | Yes |
| T051 | Register fixtures in manifest.json | WP10 | P2 | No |
| T052 | Conformance test: high-severity block | WP10 | P2 | Yes |
| T053 | Conformance test: warn + burst cap | WP10 | P2 | Yes |
| T054 | Integration verification (mypy, coverage, exports) | WP10 | P2 | No |
