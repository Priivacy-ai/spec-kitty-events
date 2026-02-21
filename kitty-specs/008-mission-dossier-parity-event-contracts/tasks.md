# Work Packages: Mission Dossier Parity Event Contracts

**Inputs**: Design documents from `kitty-specs/008-mission-dossier-parity-event-contracts/`
**Prerequisites**: spec.md ✓, plan.md ✓, data-model.md ✓, contracts/dossier_types.py ✓

**Tests**: Tests are explicitly required per spec FR 12/16 and plan WP05.

**Organisation**: 30 subtasks (T001–T030) rolled into 5 work packages. Each WP is independently deliverable; the dependency graph is linear except WP02 and WP03 which both unblock from WP01 in parallel.

---

## Work Package WP01: Core Domain Module (Priority: P0) 🎯 MVP

**Goal**: Implement `src/spec_kitty_events/dossier.py` — the single flat domain module containing all constants, the exception, provenance sub-types, event payload models, reducer output models, and the `reduce_mission_dossier()` reducer.
**Independent Test**: `python3.11 -m pytest tests/test_dossier_reducer.py -x` passes; `mypy --strict src/spec_kitty_events/dossier.py` exits 0.
**Prompt**: `tasks/WP01-core-domain-module.md`
**Estimated prompt size**: ~450 lines

### Included Subtasks
- [x] T001 Add event type constants and `DOSSIER_EVENT_TYPES` frozenset to `dossier.py`
- [x] T002 Define `NamespaceMixedStreamError(ValueError)` with message carrying both namespace tuples
- [x] T003 [P] Define value objects: `LocalNamespaceTuple`, `ArtifactIdentity`, `ContentHashRef`, `ProvenanceRef`
- [x] T004 [P] Define 4 event payload models: `MissionDossierArtifactIndexedPayload`, `MissionDossierArtifactMissingPayload`, `MissionDossierSnapshotComputedPayload`, `MissionDossierParityDriftDetectedPayload`
- [x] T005 Define reducer output models: `ArtifactEntry`, `AnomalyEntry`, `SnapshotSummary`, `DriftRecord`, `MissionDossierState`
- [x] T006 Implement `reduce_mission_dossier(events)` using the filter → sort → dedup → namespace-check → fold pipeline

### Implementation Notes
- Follow the exact section structure from `mission_next.py` (constants, exception, value objects, payload models, reducer output models, reducer).
- All models use `ConfigDict(frozen=True)`.
- Use `from __future__ import annotations` at top; use distinct variable names per type branch (per memory: mypy strictness).
- `artifact_class` is defined ONLY in `ArtifactIdentity` — NOT at any event top level.
- `manifest_version` is defined ONLY in `LocalNamespaceTuple` — NOT in event payloads.
- Reducer imports `status_event_sort_key` and `dedup_events` from `status.py` (same import pattern as `mission_next.py` line 260).
- Sort key: `(lamport_clock, timestamp, event_id)` — three-field, via existing `status_event_sort_key`.
- `NamespaceMixedStreamError` must carry both namespaces in its message string.

### Parallel Opportunities
- T003 and T004 can be written in parallel once T001/T002 are done (different model groups).

### Dependencies
- None (starting work package).

### Risks & Mitigations
- `from __future__ import annotations` + forward references: use distinct intermediate variable names per type branch to satisfy mypy strict.
- `Optional[Dict[str, str]]` for `context_diagnostics`: use `Optional[Dict[str, str]] = Field(default=None)`.

---

## Work Package WP02: Schemas & Conformance Wiring (Priority: P0)

**Goal**: Register the 8 new JSON schemas (generate + commit), wire the `dossier` fixture category into the loader, register 4 event types in the validator, add ~10 exports to `__init__.py`, and add 3 package-data globs to `pyproject.toml`.
**Independent Test**: `python -m spec_kitty_events.schemas.generate --check` exits 0; `load_fixtures("dossier")` does not raise; all new exports importable.
**Prompt**: `tasks/WP02-schemas-and-conformance-wiring.md`
**Estimated prompt size**: ~380 lines

### Included Subtasks
- [x] T007 [P] Add 8 dossier model imports to `generate.py` `PYDANTIC_MODELS` list and run generator to emit 8 `.schema.json` files
- [x] T008 Run `python -m spec_kitty_events.schemas.generate --check` and verify zero drift; commit schema files
- [x] T009 [P] Add `"dossier"` to `_VALID_CATEGORIES` frozenset in `loader.py`
- [x] T010 [P] Add 4 event types to `_EVENT_TYPE_TO_MODEL` and `_EVENT_TYPE_TO_SCHEMA` dicts in `validators.py`
- [x] T011 Add ~10 new exports to `src/spec_kitty_events/__init__.py`
- [x] T012 [P] Add 3 package-data globs to `pyproject.toml`
- [x] T013 Smoke-test: `python -c "from spec_kitty_events import MissionDossierArtifactIndexedPayload, reduce_mission_dossier, NamespaceMixedStreamError"` succeeds

### Implementation Notes
- Schema file names follow snake_case convention: `artifact_identity.schema.json`, `content_hash_ref.schema.json`, `provenance_ref.schema.json`, `local_namespace_tuple.schema.json`, plus the 4 payload schemas.
- `generate.py` import block: add a `# Dossier event contract models` section at the end of imports, before `PYDANTIC_MODELS`.
- `validators.py` import: add `from spec_kitty_events.dossier import ...` alongside other domain imports.
- `pyproject.toml` new globs: `"conformance/fixtures/dossier/valid/*.json"`, `"conformance/fixtures/dossier/invalid/*.json"`, `"conformance/fixtures/dossier/replay/*.jsonl"`.

### Parallel Opportunities
- T007, T009, T010, T012 are all independent file edits and can be done in parallel.

### Dependencies
- Depends on WP01 (models must exist before importing in generate.py and validators.py).

### Risks & Mitigations
- Running `generate.py` writes to `src/spec_kitty_events/schemas/`. Commit the 8 new files before running `--check` or CI will flag them as missing.

---

## Work Package WP03: Dossier Fixtures (Priority: P0)

**Goal**: Create the `dossier/` fixture category directory with 10 valid JSON fixtures, 3 invalid JSON fixtures, and 2 JSONL replay streams; update `manifest.json` with all 15 entries.
**Independent Test**: `load_fixtures("dossier")` returns exactly 13 `FixtureCase` objects; `load_replay_stream("dossier-replay-happy-path")` and `load_replay_stream("dossier-replay-drift-scenario")` each return non-empty lists of event dicts.
**Prompt**: `tasks/WP03-dossier-fixtures.md`
**Estimated prompt size**: ~480 lines

### Included Subtasks
- [x] T014 Create directory structure: `conformance/fixtures/dossier/valid/`, `.../invalid/`, `.../replay/`
- [x] T015 [P] Write 10 valid fixture JSON files in `dossier/valid/`
- [x] T016 [P] Write 3 invalid fixture JSON files in `dossier/invalid/`
- [x] T017 [P] Write 2 JSONL replay streams in `dossier/replay/`
- [x] T018 Add 13 fixture case entries + 2 replay stream entries to `manifest.json`
- [x] T019 Verify: `load_fixtures("dossier")` returns 13 cases; both replay streams load without error

### Implementation Notes
- Fixture JSON files follow existing naming: `dossier_artifact_indexed_valid.json`, etc. (snake_case, mirrors manifest id with hyphens → underscores).
- All valid fixtures must include the complete `namespace` (LocalNamespaceTuple with all 5 required fields), full `artifact_id` (ArtifactIdentity with path + artifact_class + mission_key), and required event-specific fields.
- `artifact_class` lives in `artifact_id` for indexed events, in `expected_identity` for missing events — NOT at top level.
- Replay streams are standard spec-kitty-events Event envelopes (JSONL, one per line). Use sequential lamport clocks (1, 2, 3, ...) and a shared `correlation_id`. Use `project_uuid`, `node_id`, `aggregate_id` consistent within each stream.
- `manifest.json` entries: `min_version: "2.4.0"` for all dossier fixtures.

### Parallel Opportunities
- T015, T016, T017 can all be written in parallel once T014 directory structure exists.

### Dependencies
- Depends on WP01 (event type strings and field names must be stable).
- Can proceed in parallel with WP02 (no code dependency on wiring; only requires WP01 type knowledge).

### Risks & Mitigations
- Replay streams must use valid Event envelopes (all required envelope fields: event_id, event_type, aggregate_id, timestamp, node_id, lamport_clock, project_uuid, correlation_id, payload). Validate each stream manually against the Event schema before committing.
- Namespace collision fixture (`dossier_namespace_collision_coverage.json`): must contain two distinct namespace objects with at least one differing field (e.g., `feature_slug`) to assert key tuple uniqueness.

---

## Work Package WP04: Tests (Priority: P1)

**Goal**: Write `tests/test_dossier_conformance.py` (dual-layer validation, fixture loading, category wiring) and `tests/test_dossier_reducer.py` (unit tests + Hypothesis property tests). All tests must pass; coverage ≥98% for `dossier.py`.
**Independent Test**: `python3.11 -m pytest tests/test_dossier_conformance.py tests/test_dossier_reducer.py -v` exits 0.
**Prompt**: `tasks/WP04-tests.md`
**Estimated prompt size**: ~480 lines

### Included Subtasks
- [x] T020 Create `tests/test_dossier_conformance.py`: valid fixtures pass dual-layer, invalid fixtures produce violations
- [x] T021 [P] Add category coverage test: `load_fixtures("dossier")` returns 13 cases; both replay streams loadable
- [x] T022 [P] Add round-trip schema conformance test: all valid fixtures pass both layers; all invalid produce ≥1 violation
- [x] T023 Create `tests/test_dossier_reducer.py`: unit tests (empty stream, happy-path, drift scenario, dedup, unknown event skip, supersedes)
- [x] T024 Add `NamespaceMixedStreamError` test: reducer raises on multi-namespace input; message contains both namespace values
- [x] T025 Add Hypothesis property test: `reduce_mission_dossier` output is identical across all causal-order-preserving permutations of the happy-path replay stream (200 examples)

### Implementation Notes
- Follow `test_mission_next_conformance.py` and `test_mission_next_reducer.py` as structural models.
- Use `pytest.mark.parametrize` with `load_fixtures("dossier")` for fixture-driven validation tests.
- For T024: build a two-event stream where both events have all required dossier payload fields but carry different `namespace` tuples. Assert `NamespaceMixedStreamError` is raised and `str(exc)` contains a substring from both namespace values.
- For T025 (Hypothesis): `from hypothesis import given, settings, strategies as st`. Strategy: `st.permutations(events_list)`. `@settings(max_examples=200)`.
- Coverage: `python3.11 -m pytest --cov=src/spec_kitty_events/dossier --cov-report=term-missing tests/test_dossier_*.py` and verify ≥98%.

### Parallel Opportunities
- T020 and T023 are separate files and can be written in parallel.
- T021, T022 can be added to T020 file in parallel with T023 file.

### Dependencies
- Depends on WP02 (loader wired) and WP03 (fixtures on disk) — both must complete before this WP.

### Risks & Mitigations
- Hypothesis: must `from hypothesis import given, settings, strategies as st` — check that `hypothesis` is in dev dependencies (`pyproject.toml [project.optional-dependencies] dev`). It should already be present from existing property tests.
- mypy strict: test files need type annotations on fixtures and parameterize args if strict is enforced on test files.

---

## Work Package WP05: Final Verification & Changelog (Priority: P1)

**Goal**: Write the CHANGELOG.md v2.4.0 section with consumer migration notes, run the full test suite, verify ≥98% coverage, confirm `mypy --strict` and schema drift check pass, and verify export count.
**Independent Test**: `python3.11 -m pytest` (full suite) exits 0; `python -m spec_kitty_events.schemas.generate --check` exits 0; `mypy --strict src/` exits 0; CHANGELOG contains v2.4.0 section.
**Prompt**: `tasks/WP05-final-verification-and-changelog.md`
**Estimated prompt size**: ~280 lines

### Included Subtasks
- [ ] T026 Prepend v2.4.0 section to `CHANGELOG.md` with migration notes for `spec-kitty` and `spec-kitty-saas`
- [ ] T027 Run `python3.11 -m pytest` (full suite) and confirm all pass; run `--cov` to verify ≥98% coverage on `dossier.py`
- [ ] T028 Run `mypy --strict src/spec_kitty_events/` and fix any remaining errors
- [ ] T029 Run `python -m spec_kitty_events.schemas.generate --check` and verify exits 0 (no drift)
- [ ] T030 Count exports in `__init__.py` and verify ~10 new dossier symbols are present; update version to 2.4.0 in `pyproject.toml`

### Implementation Notes
- CHANGELOG format: follow existing v2.x.y section headings. v2.4.0 section must include: Added (list all 10 new exports), Migration for spec-kitty, Migration for spec-kitty-saas (with explicit `>=2.4.0,<3.0.0` pins).
- Version bump: update `version = "2.4.0"` in `pyproject.toml [project]` block.
- If `mypy` reports errors in new code, fix before marking done.

### Parallel Opportunities
- T026 (CHANGELOG) can be written in parallel with T027/T028/T029 (all are read-only checks or doc edits on different files).

### Dependencies
- Depends on WP04 (tests must pass before final verification is meaningful).

### Risks & Mitigations
- If coverage drops below 98%: identify uncovered lines in `dossier.py` (usually the `NamespaceMixedStreamError` path or edge cases in reducer); add targeted test to `test_dossier_reducer.py`.

---

## Dependency & Execution Summary

```
WP01 (dossier.py)
  ├─→ WP02 (schemas + wiring)    ← parallel with WP03 after WP01
  └─→ WP03 (fixtures)            ← parallel with WP02 after WP01
        └─→ WP04 (tests) ← depends on both WP02 + WP03
              └─→ WP05 (final verification + changelog)
```

**Parallelization**: After WP01 completes, WP02 and WP03 can run simultaneously on separate branches/worktrees.
**MVP Scope**: WP01 + WP02 + WP03 + WP04 (all required for a shippable 2.4.0; WP05 is the release gate).

---

## Subtask Index (Reference)

| Subtask ID | Summary | Work Package | Priority | Parallel? |
|---|---|---|---|---|
| T001 | Event type constants + DOSSIER_EVENT_TYPES | WP01 | P0 | No |
| T002 | NamespaceMixedStreamError(ValueError) | WP01 | P0 | No |
| T003 | Value objects (4 provenance sub-types) | WP01 | P0 | Yes |
| T004 | 4 event payload models | WP01 | P0 | Yes |
| T005 | 5 reducer output models + MissionDossierState | WP01 | P0 | No |
| T006 | reduce_mission_dossier() reducer | WP01 | P0 | No |
| T007 | Add dossier imports to generate.py + run generator | WP02 | P0 | Yes |
| T008 | Verify --check exits 0 + commit schemas | WP02 | P0 | No |
| T009 | Add "dossier" to loader.py _VALID_CATEGORIES | WP02 | P0 | Yes |
| T010 | Add 4 event types to validators.py dicts | WP02 | P0 | Yes |
| T011 | Add ~10 exports to __init__.py | WP02 | P0 | No |
| T012 | Add 3 package-data globs to pyproject.toml | WP02 | P0 | Yes |
| T013 | Smoke-test all new exports importable | WP02 | P0 | No |
| T014 | Create dossier/valid/, invalid/, replay/ dirs | WP03 | P0 | No |
| T015 | Write 10 valid fixture JSON files | WP03 | P0 | Yes |
| T016 | Write 3 invalid fixture JSON files | WP03 | P0 | Yes |
| T017 | Write 2 JSONL replay streams | WP03 | P0 | Yes |
| T018 | Add 15 entries to manifest.json | WP03 | P0 | No |
| T019 | Verify load_fixtures("dossier") + replay streams | WP03 | P0 | No |
| T020 | test_dossier_conformance.py (valid/invalid validation) | WP04 | P1 | Yes |
| T021 | Category coverage: 13 cases + 2 replay streams | WP04 | P1 | Yes |
| T022 | Round-trip schema conformance assertions | WP04 | P1 | Yes |
| T023 | test_dossier_reducer.py (unit tests) | WP04 | P1 | Yes |
| T024 | NamespaceMixedStreamError test | WP04 | P1 | No |
| T025 | Hypothesis property test (200 examples) | WP04 | P1 | No |
| T026 | CHANGELOG.md v2.4.0 section | WP05 | P1 | Yes |
| T027 | Full test suite + coverage ≥98% | WP05 | P1 | No |
| T028 | mypy --strict src/ (zero errors) | WP05 | P1 | No |
| T029 | Schema drift check exits 0 | WP05 | P1 | No |
| T030 | Export count + version bump to 2.4.0 | WP05 | P1 | No |
