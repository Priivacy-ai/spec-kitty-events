# Implementation Plan: Glossary Semantic Integrity Contracts

**Branch**: `007-glossary-semantic-integrity-contracts` (on `2.x`) | **Date**: 2026-02-16 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `kitty-specs/007-glossary-semantic-integrity-contracts/spec.md`

## Summary

Add 8 typed glossary semantic integrity event contracts, a standalone glossary reducer with strict/permissive dual-mode, and 3 conformance fixtures to `spec-kitty-events`. All work targets the `2.x` branch (cut from current `main` HEAD). The module (`glossary.py`) mirrors the `collaboration.py` structural pattern: same reducer pipeline shape (filter → sort → dedup → process → assemble frozen state), same anomaly-recording pattern, and same frozen Pydantic output models.

## Technical Context

**Language/Version**: Python 3.10+ (target), 3.11 for dev tooling (pip/pytest)
**Primary Dependencies**: pydantic>=2.0.0,<3.0.0, python-ulid>=1.1.0 (no new deps)
**Storage**: N/A — pure event contracts and reducer, no I/O
**Testing**: pytest + pytest-cov + hypothesis + mypy --strict
**Target Platform**: Library package (pip-installable), local-first with SaaS projection
**Project Type**: Single Python package (`src/spec_kitty_events/`)
**Performance Goals**: N/A — contract library, not a service
**Constraints**: mypy --strict, Python 3.10 minimum, frozen Pydantic models, 98%+ coverage target
**Scale/Scope**: 8 event types, ~8 payload models, ~5 supporting value models, 1 reducer, 1 reduced state model, 3 conformance fixture sets, ~20 new exports

## Constitution Check

*No constitution file exists at `.kittify/memory/constitution.md`. Skipped.*

## Project Structure

### Documentation (this feature)

```
kitty-specs/007-glossary-semantic-integrity-contracts/
├── plan.md              # This file
├── spec.md              # Feature specification
├── meta.json            # Feature metadata (target_branch: 2.x)
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   └── glossary-events.md
├── checklists/
│   └── requirements.md  # Spec quality checklist
└── tasks.md             # Phase 2 output (NOT created by /spec-kitty.plan)
```

### Source Code (repository root)

```
src/spec_kitty_events/
├── __init__.py                          # Add ~20 new glossary exports
├── glossary.py                          # NEW: Event types, payloads, reducer
├── conformance/
│   └── fixtures/
│       ├── manifest.json                # MODIFIED: Add glossary fixture entries
│       └── glossary/                    # NEW: Glossary conformance fixtures
│           ├── valid/
│           │   ├── glossary_scope_activated.json
│           │   ├── term_candidate_observed.json
│           │   ├── semantic_check_evaluated_warn.json
│           │   ├── semantic_check_evaluated_block.json
│           │   ├── generation_blocked.json
│           │   ├── glossary_clarification_requested.json
│           │   ├── glossary_clarification_resolved.json
│           │   ├── glossary_sense_updated.json
│           │   └── glossary_strictness_set.json
│           └── invalid/
│               ├── semantic_check_missing_step_id.json
│               ├── glossary_scope_invalid_type.json
│               └── clarification_missing_check_ref.json

tests/
├── test_glossary.py                     # NEW: Unit tests for glossary module
├── test_glossary_reducer.py             # NEW: Reducer tests (determinism, edge cases)
└── test_glossary_conformance.py         # NEW: Conformance fixture validation
```

**Structure Decision**: Single module (`glossary.py`) in the existing package, matching the established pattern where each domain has one module file (lifecycle.py, status.py, collaboration.py). Conformance fixtures in a namespaced `glossary/` subdirectory under existing `conformance/fixtures/`.

## Design Decisions

### D1: Single module vs. multi-file package

**Decision**: Single `glossary.py` file.
**Rationale**: `collaboration.py` is ~1070 lines and works well as a single file. Glossary will be simpler (~600-800 lines estimated) since it has no roster/presence/reverse-index machinery. One file keeps imports clean and matches the pattern.
**Alternative rejected**: `glossary/` package with `__init__.py`, `models.py`, `reducer.py` — unnecessary complexity for the expected size.

### D2: Reducer pipeline reuse

**Decision**: Import and reuse `status_event_sort_key` and `dedup_events` from `status.py` at function call time (late import), matching `collaboration.py`'s approach.
**Rationale**: These are well-tested utilities. Late import avoids circular dependency issues. The spec requires dedup-by-event_id semantics; `dedup_events()` implements exactly that.
**Note**: If `dedup_events` moves in a future refactor, the import path changes but the semantic stays the same — this is implementation reuse, not a contract coupling.

### D3: Enum vs. Literal for constrained fields

**Decision**: Use `Literal` types for fields with small fixed value sets (scope_type, strictness, severity, conflict_nature, recommended_action). Use `Enum` only if the set needs to be iterated or referenced programmatically.
**Rationale**: Matches the existing pattern in `collaboration.py` (e.g., `Literal["human", "llm_context"]` for participant_type). Keeps models simple and avoids enum serialization overhead.
**Exception**: `GlossaryStrictness` as an enum if needed for programmatic iteration in the reducer's strictness-tracking logic. Decision to be made during implementation.

### D4: Conflict entry as embedded value object

**Decision**: Define a `SemanticConflictEntry` frozen Pydantic model used as a list element within `SemanticCheckEvaluatedPayload.conflicts`.
**Rationale**: Conflict entries have 3+ fields (term, nature, severity) — a typed model is clearer than a nested dict and enables validation.

### D5: Clarification burst grouping

**Decision**: Group clarifications by `semantic_check_event_id` field on `GlossaryClarificationRequestedPayload`. The reducer counts active (unresolved) requests per group and caps at 3.
**Rationale**: This was the P2 review finding fix — gives every consumer the same deterministic grouping key.

### D6: Actor identity representation

**Decision**: Use `str` for actor fields in glossary payloads.
**Rationale**: Matches lifecycle (`MissionStartedPayload.actor: str`) and collaboration payload patterns where actor is a simple identifier. The full `ParticipantIdentity` model belongs to the collaboration domain and would be cross-domain coupling.

### D7: Branch `2.x` setup

**Decision**: Cut `2.x` from current `main` HEAD at branch-cut time (`f4692ea` at planning time). Tag the cut point as `2.x-baseline`.
**Rationale**: Includes spec artifacts (planning metadata, not runtime code). Avoids cherry-pick divergence. Downstream repos can align to the tagged commit.

## Complexity Tracking

No constitution violations to justify — no constitution exists.
