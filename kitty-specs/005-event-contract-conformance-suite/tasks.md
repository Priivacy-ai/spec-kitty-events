# Tasks: Event Contract Conformance Suite

**Feature**: 005-event-contract-conformance-suite
**Date**: 2026-02-12
**Total Subtasks**: 44
**Work Packages**: 7

---

## Phase 1: Foundation

### WP01 — Lane Mapping Contract (Priority: P1)

**Goal**: Implement `SyncLaneV1` enum, `CANONICAL_TO_SYNC_V1` mapping, and `canonical_to_sync_v1()` function in `status.py`. Export from `__init__.py`. Full test coverage including property tests.

**Prompt**: `tasks/WP01-lane-mapping-contract.md`
**Dependencies**: None
**Estimated size**: ~350 lines

**Subtasks**:
- [x] T001: Add `SyncLaneV1` enum to `status.py` [P]
- [x] T002: Add `CANONICAL_TO_SYNC_V1` mapping constant using `MappingProxyType` [P]
- [x] T003: Add `canonical_to_sync_v1()` function [P]
- [x] T004: Export new symbols from `__init__.py` and update `__all__`
- [x] T005: Unit tests for `SyncLaneV1`, mapping completeness, and function correctness
- [x] T006: Property tests for mapping determinism and totality

---

### WP02 — Schema Subpackage and Generation Script (Priority: P1)

**Goal**: Create `src/spec_kitty_events/schemas/` subpackage with `__init__.py` (loader API), `generate.py` (build-time script with `--check` mode), and generate all 11 JSON Schema files from existing Pydantic models.

**Prompt**: `tasks/WP02-schema-generation.md`
**Dependencies**: WP01 (needs `SyncLaneV1` for `sync_lane_v1.schema.json`)
**Estimated size**: ~500 lines

**Subtasks**:
- [x] T007: Create `schemas/__init__.py` with `load_schema()`, `schema_path()`, `list_schemas()`
- [x] T008: Create `schemas/generate.py` with model registry and generation logic
- [x] T009: Implement `--check` mode for CI drift detection
- [x] T010: Generate all 11 `.schema.json` files (event, payloads, enums)
- [x] T011: Update `pyproject.toml`: package-data for `schemas/*.json`, `[conformance]` optional extra
- [x] T012: Unit tests for schema loader API and generation script
- [x] T013: Integration test for schema drift detection (`--check` mode)

---

## Phase 2: Conformance Infrastructure

### WP03 — Conformance Validator API (Priority: P1)

**Goal**: Create `src/spec_kitty_events/conformance/` subpackage with dual-layer validator: Pydantic-first (primary) + JSON Schema (secondary). Implement `ConformanceResult`, `ModelViolation`, `SchemaViolation`, and `validate_event()`.

**Prompt**: `tasks/WP03-conformance-validator.md`
**Dependencies**: WP02 (needs schema loader for secondary validation layer)
**Estimated size**: ~450 lines

**Subtasks**:
- [x] T014: Create `conformance/__init__.py` with public API surface
- [x] T015: Create `conformance/validators.py` with `ConformanceResult`, `ModelViolation`, `SchemaViolation`
- [x] T016: Implement event-type-to-model resolver (maps event_type strings to Pydantic model classes)
- [x] T017: Implement Pydantic validation layer (Layer 1) with `ModelViolation` extraction
- [ ] T018: Implement JSON Schema validation layer (Layer 2) with graceful degradation (`schema_check_skipped`)
- [ ] T019: Implement `validate_event()` function with `strict` parameter
- [ ] T020: Unit tests for validator (valid payloads, invalid payloads, missing jsonschema, strict mode)

---

### WP04 — Canonical Fixtures and Manifest (Priority: P2)

**Goal**: Create the fixture directory structure with valid/invalid JSON fixtures for all event types, lane mappings, and edge cases. Create `manifest.json` with expectations. Implement `load_fixtures()` and `FixtureCase`.

**Prompt**: `tasks/WP04-fixtures-and-manifest.md`
**Dependencies**: WP03 (needs validator to verify fixtures work)
**Estimated size**: ~500 lines

**Subtasks**:
- [ ] T021: Create fixture directory structure (`events/valid/`, `events/invalid/`, `lane_mapping/valid/`, etc.)
- [ ] T022: Create valid event fixtures for all 9 conformance payload types
- [ ] T023: Create invalid event fixtures (missing fields, wrong types, invalid enums)
- [ ] T024: Create lane mapping fixtures (all 7 canonical→sync cases + invalid lane values)
- [ ] T025: Create edge case fixtures (alias normalization, optional field omission, schema version mismatch)
- [ ] T026: Create `manifest.json` with id, path, expected_result, event_type, notes, min_version
- [ ] T027: Implement `load_fixtures()` and `FixtureCase` in `conformance/__init__.py`
- [ ] T028: Update `pyproject.toml` package-data for `conformance/fixtures/**/*.json`

---

## Phase 3: Pytest Conformance Suite

### WP05 — Pytest Conformance Entry Point (Priority: P1)

**Goal**: Create `test_pyargs_entrypoint.py`, `conftest.py`, and `pytest_helpers.py` in the conformance subpackage. Tests are manifest-driven. Verify `pytest --pyargs spec_kitty_events.conformance` works end-to-end.

**Prompt**: `tasks/WP05-pytest-conformance-suite.md`
**Dependencies**: WP04 (needs fixtures and manifest)
**Estimated size**: ~400 lines

**Subtasks**:
- [ ] T029: Create `conformance/pytest_helpers.py` with reusable assertion helpers
- [ ] T030: Create `conformance/conftest.py` with shared pytest fixtures
- [ ] T031: Create `conformance/test_pyargs_entrypoint.py` with manifest-driven conformance tests
- [ ] T032: Add coverage omit for `conformance/` directory in `pyproject.toml`
- [ ] T033: Verify `pytest --pyargs spec_kitty_events.conformance` works after editable install

---

## Phase 4: Release Preparation

### WP06 — Version Graduation and Package Finalization (Priority: P3)

**Goal**: Graduate version to `2.0.0-rc1`. Update `SCHEMA_VERSION`. Add `[conformance]` extra. Ensure all new symbols are exported. Run full test suite and mypy.

**Prompt**: `tasks/WP06-version-graduation.md`
**Dependencies**: WP05 (all code and tests must be complete)
**Estimated size**: ~300 lines

**Subtasks**:
- [ ] T034: Update `pyproject.toml` version to `2.0.0-rc1`
- [ ] T035: Update `__version__` in `__init__.py` to `2.0.0-rc1`
- [ ] T036: Update `SCHEMA_VERSION` constant in `lifecycle.py` to `"2.0.0"`
- [ ] T037: Final audit of `__init__.py` exports and `__all__` list
- [ ] T038: Run full `python3.11 -m pytest` suite and verify 98%+ coverage
- [ ] T039: Run `mypy --strict` and fix any type errors

---

### WP07 — Compatibility Table, Changelog, and Migration Notes (Priority: P3)

**Goal**: Create `CHANGELOG.md` with migration notes from `0.4.x` to `2.0.0`. Create compatibility table. Create `COMPATIBILITY.md` documenting lane mapping, required/optional fields per event type, and versioning policy.

**Prompt**: `tasks/WP07-docs-and-changelog.md`
**Dependencies**: WP06 (needs final version and exports)
**Estimated size**: ~350 lines

**Subtasks**:
- [ ] T040: Create `CHANGELOG.md` with `2.0.0-rc1` section and migration notes
- [ ] T041: Create `COMPATIBILITY.md` with lane mapping table and field requirements per event type
- [ ] T042: Document versioning policy (SemVer rules for 2.x)
- [ ] T043: Document consumer CI integration steps
- [ ] T044: Final review: ensure all FR-001 through FR-023 are addressed

---

## Dependency Graph

```
WP01 (Lane Mapping)
  └─▶ WP02 (Schema Generation)
        └─▶ WP03 (Conformance Validator)
              └─▶ WP04 (Fixtures & Manifest)
                    └─▶ WP05 (Pytest Conformance)
                          └─▶ WP06 (Version Graduation)
                                └─▶ WP07 (Docs & Changelog)
```

**Parallelization note**: The dependency chain is mostly serial because each WP builds on the prior one's artifacts. However, WP07 (docs) could start in parallel with WP06 (version) since documentation doesn't depend on the version number being set — just on knowing the final exports.

## MVP Scope

**Minimum viable contract**: WP01 + WP02 + WP03 deliver the lane mapping, JSON schemas, and validator. This is sufficient for consumers to import and validate against the contract. WP04–WP07 add fixtures, pytest entry point, and release polish.
