# Research: Glossary Semantic Integrity Contracts

**Feature**: 007-glossary-semantic-integrity-contracts
**Date**: 2026-02-16

## R1: Reducer Pipeline Pattern (collaboration.py as template)

**Decision**: Mirror `collaboration.py`'s 5-stage pipeline.

**Rationale**: The collaboration reducer (`reduce_collaboration_events()`) at `src/spec_kitty_events/collaboration.py:539` establishes the canonical pattern:
1. Filter events to glossary types via `GLOSSARY_EVENT_TYPES` frozenset
2. Sort using `status_event_sort_key` (lamport_clock, timestamp, event_id)
3. Dedup using `dedup_events()` from `status.py`
4. Process each event, mutating intermediate state dicts
5. Assemble frozen `ReducedGlossaryState` from mutable intermediates

**Key implementation details observed from collaboration.py**:
- Late imports of `dedup_events` and `status_event_sort_key` from `status.py` (line 575)
- Empty-input short-circuit returns empty state (lines 577-584)
- Mutable intermediate dicts (`Dict`, `Set`, `List`) during processing, frozen on assembly
- `mode: Literal["strict", "permissive"]` parameter with default `"strict"`
- Anomaly recording in permissive mode via mutable list, converted to tuple on assembly

**Alternatives considered**:
- Standalone sort/dedup utilities — rejected because existing ones are battle-tested (427 tests, 98% coverage)
- Process events via match/case — viable but explicit if/elif chain matches existing style

## R2: Conformance Fixture Structure

**Decision**: Place glossary fixtures at `src/spec_kitty_events/conformance/fixtures/glossary/valid/` and `glossary/invalid/`.

**Rationale**: Existing fixture structure uses domain-namespaced subdirectories:
- `events/valid/`, `events/invalid/` — core Event model
- `lane_mapping/valid/`, `lane_mapping/invalid/` — lane mappings
- `edge_cases/valid/`, `edge_cases/invalid/` — edge cases
- `collaboration/valid/`, `collaboration/invalid/` — collaboration events

Adding `glossary/valid/` and `glossary/invalid/` follows the exact same pattern.

**Manifest registration**: Each fixture gets an entry in `manifest.json` with fields:
- `id`: e.g., `"glossary-scope-activated-valid"`
- `path`: e.g., `"glossary/valid/glossary_scope_activated.json"`
- `expected_result`: `"valid"` or `"invalid"`
- `event_type`: e.g., `"GlossaryScopeActivated"`
- `min_version`: `"2.0.0"` (matching schema version)

**Package data**: Must add `"conformance/fixtures/glossary/valid/*.json"` and `"conformance/fixtures/glossary/invalid/*.json"` to `pyproject.toml` `[tool.setuptools.package-data]`.

## R3: Reduced State Design

**Decision**: `ReducedGlossaryState` tracks 8 state facets.

**Rationale**: Derived from FR-018 (reducer must reconstruct) and the spec's Key Entities:

| State facet | Type | Source events |
|---|---|---|
| `active_scopes` | `Dict[str, GlossaryScopeInfo]` | `GlossaryScopeActivated` |
| `current_strictness` | `str` (Literal `off`/`medium`/`max`) | `GlossaryStrictnessSet` |
| `strictness_history` | `Tuple[StrictnessTransition, ...]` | `GlossaryStrictnessSet` |
| `term_candidates` | `Dict[str, TermCandidateInfo]` | `TermCandidateObserved` |
| `term_senses` | `Dict[str, TermSenseInfo]` | `GlossarySenseUpdated` |
| `clarifications` | `Tuple[ClarificationInfo, ...]` | `GlossaryClarificationRequested/Resolved` |
| `semantic_checks` | `Tuple[SemanticCheckInfo, ...]` | `SemanticCheckEvaluated` |
| `generation_blocks` | `Tuple[GenerationBlockInfo, ...]` | `GenerationBlockedBySemanticConflict` |

Plus standard reducer bookkeeping: `mission_id`, `anomalies`, `event_count`, `last_processed_event_id`.

**Burst cap enforcement**: The reducer counts unresolved clarifications grouped by `semantic_check_event_id`. When >3 exist for a group, the reducer records an anomaly for each excess request (permissive) or raises (strict).

## R4: Schema Version Alignment

**Decision**: Use `SCHEMA_VERSION = "2.0.0"` (reuse from lifecycle module).

**Rationale**: Glossary events are additive contracts within the 2.x generation. They don't change existing schemas. Using the same version string signals contract-generation alignment, not feature-level versioning (which is tracked in `__version__`).

**Implementation**: Import `SCHEMA_VERSION` from `lifecycle.py` rather than redefining it, to ensure single source of truth.

## R5: Branch Setup Sequence

**Decision**: First work package cuts `2.x` from `main` HEAD and tags it.

**Sequence**:
1. `BASE_SHA=$(git rev-parse HEAD)` — capture current `main` HEAD at branch-cut time
2. `git branch 2.x "$BASE_SHA"` — create branch from captured baseline
3. `git tag 2.x-baseline "$BASE_SHA"` — tag for downstream alignment
3. `git checkout 2.x` — switch to new branch
4. All feature work happens on `2.x`
5. `main` stays maintenance-only

**Risk**: No `2.x` branch exists on remote. Push must be coordinated.

## R6: Export Count Impact

**Current state**: 65 exports in `__init__.py` (from `__all__`), 279 lines.

**New exports** (~20):
- 8 event type constants: `GLOSSARY_SCOPE_ACTIVATED`, `TERM_CANDIDATE_OBSERVED`, `SEMANTIC_CHECK_EVALUATED`, `GLOSSARY_CLARIFICATION_REQUESTED`, `GLOSSARY_CLARIFICATION_RESOLVED`, `GLOSSARY_SENSE_UPDATED`, `GENERATION_BLOCKED_BY_SEMANTIC_CONFLICT`, `GLOSSARY_STRICTNESS_SET`
- 1 event type frozenset: `GLOSSARY_EVENT_TYPES`
- 8 payload models: `GlossaryScopeActivatedPayload`, `TermCandidateObservedPayload`, `SemanticCheckEvaluatedPayload`, `GlossaryClarificationRequestedPayload`, `GlossaryClarificationResolvedPayload`, `GlossarySenseUpdatedPayload`, `GenerationBlockedBySemanticConflictPayload`, `GlossaryStrictnessSetPayload`
- 1 conflict value model: `SemanticConflictEntry`
- 1 reduced state model: `ReducedGlossaryState`
- 1 anomaly model: `GlossaryAnomaly`
- 1 reducer function: `reduce_glossary_events`

**Total**: ~21 new exports → ~86 total exports.
