# Work Packages: GitHub Gate Observability Contracts

**Inputs**: Design documents from `kitty-specs/002-github-gate-observability-contracts/`
**Prerequisites**: plan.md (required), spec.md (user stories), research.md, data-model.md, contracts/gates-api.md, quickstart.md

**Tests**: Explicitly required by FR-011, FR-012. Unit tests and property tests included.

**Organization**: 13 fine-grained subtasks (`T001`–`T013`) rolled into 3 work packages (`WP01`–`WP03`). Each work package is independently deliverable and testable.

**Prompt Files**: Each work package references a matching prompt file in `kitty-specs/002-github-gate-observability-contracts/tasks/`.

## Subtask Format: `[Txxx] [P?] Description`
- **[P]** indicates the subtask can proceed in parallel (different files/components).
- Paths are relative to repository root.

---

## Work Package WP01: Gate Payload Models & Public API (Priority: P1)

**Goal**: Create the `gates.py` module with typed Pydantic payload models (`GatePayloadBase`, `GatePassedPayload`, `GateFailedPayload`), the `UnknownConclusionError` exception, and wire everything into the package's public API.
**Independent Test**: Import `GatePassedPayload` from `spec_kitty_events`, construct one with valid data, and verify it's frozen. Run `mypy --strict` on the new module.
**Prompt**: `kitty-specs/002-github-gate-observability-contracts/tasks/WP01-gate-payload-models.md`
**Estimated prompt size**: ~350 lines

### Included Subtasks
- [x] T001 Create `GatePayloadBase` model with all fields and Pydantic constraints in `src/spec_kitty_events/gates.py`
- [x] T002 Create `GatePassedPayload` and `GateFailedPayload` subclasses in `src/spec_kitty_events/gates.py`
- [x] T003 Create `UnknownConclusionError(SpecKittyEventsError)` exception in `src/spec_kitty_events/gates.py`
- [x] T004 Update `src/spec_kitty_events/__init__.py` with new public API exports and `__all__` entries
- [x] T005 Verify `mypy --strict` passes for the new `gates.py` module

### Implementation Notes
- Start by creating `src/spec_kitty_events/gates.py` with all imports from `pydantic` and the existing exception base from `models.py`.
- `GatePayloadBase` holds all 8 fields (7 required, 1 optional). Use `ConfigDict(frozen=True)`.
- Subclasses are trivial — `pass` body with docstrings. They exist for type discrimination.
- `UnknownConclusionError` stores the unrecognized `conclusion` string as an attribute.
- `__init__.py` adds 5 new exports: `GatePayloadBase`, `GatePassedPayload`, `GateFailedPayload`, `UnknownConclusionError`, `map_check_run_conclusion`.
- `map_check_run_conclusion` import is added here but the function itself is implemented in WP02.

### Parallel Opportunities
- T001, T002, T003 are all in the same file (`gates.py`) so must be sequential.
- T004 (`__init__.py`) can be drafted in parallel but depends on T001–T003 for import correctness.

### Dependencies
- None (starting package).

### Risks & Mitigations
- **Pydantic `AnyHttpUrl` serialization**: In Pydantic v2, `AnyHttpUrl` serializes as a `Url` object by default. Ensure `model_dump(mode="python")` returns a plain string or add a serializer. Test this in WP02.
- **mypy strict compliance**: `Literal` types and `Optional` require correct `from __future__ import annotations` or explicit `Union` syntax for Python 3.10. Verify with `mypy --strict`.

---

## Work Package WP02: Conclusion Mapping & Tests (Priority: P1)

**Goal**: Implement the `map_check_run_conclusion()` function with stdlib logging and optional callback, then write comprehensive unit tests and Hypothesis property tests covering all payload models and the mapping function.
**Independent Test**: Run `pytest tests/unit/test_gates.py tests/property/test_gates_determinism.py -v` — all pass. Run `pytest --cov=src/spec_kitty_events/gates` — 100% coverage on `gates.py`.
**Prompt**: `kitty-specs/002-github-gate-observability-contracts/tasks/WP02-conclusion-mapping-and-tests.md`
**Estimated prompt size**: ~450 lines

### Included Subtasks
- [x] T006 Implement `map_check_run_conclusion()` function with logging and callback in `src/spec_kitty_events/gates.py`
- [x] T007 [P] Write unit tests for payload model validation and serialization in `tests/unit/test_gates.py`
- [x] T008 [P] Write unit tests for conclusion mapping (all 8 conclusions + unknown + edge cases) in `tests/unit/test_gates.py`
- [x] T009 [P] Write Hypothesis property tests for mapping determinism in `tests/property/test_gates_determinism.py`
- [x] T010 Run full test suite and verify coverage targets met

### Implementation Notes
- T006: Mapping dict is a module-level `_CONCLUSION_MAP: Dict[str, Optional[str]]`. The function looks up the dict, handles ignored conclusions (log + callback), and raises `UnknownConclusionError` for missing keys.
- T007: Test each required field individually (omit one → `ValidationError`). Test `pr_number` optional. Test `model_dump()` → `model_validate()` round-trip. Test `AnyHttpUrl` rejects non-URL strings. Test `Literal` constraints reject wrong values.
- T008: Parametrize over all 8 conclusions. Test `"SUCCESS"` (uppercase) → `UnknownConclusionError`. Test `on_ignored` callback invoked for `neutral`, `skipped`, `stale`. Verify logging output.
- T009: Hypothesis strategy generates random known conclusions, verifies idempotent mapping. Strategy generates random strings, verifies either valid result or `UnknownConclusionError`.
- T010: Run `pytest` from repo root with coverage. Verify `gates.py` has 100% branch coverage.

### Parallel Opportunities
- T007, T008, T009 write to different files or different test classes within the same file. They can be developed in parallel after T006 is complete.

### Dependencies
- Depends on WP01 (needs models and exception class to exist).

### Risks & Mitigations
- **`AnyHttpUrl` serialization in round-trip tests**: Pydantic v2 may serialize `AnyHttpUrl` as a `Url` object, not a plain string. Tests must verify `model_dump()` output can be fed back to `model_validate()` — if not, a custom serializer is needed in WP01.
- **Hypothesis deadline**: Existing property tests disable Hypothesis deadline. Follow the same pattern in `test_gates_determinism.py` with `@settings(deadline=None)`.

---

## Work Package WP03: Version Bump & Changelog (Priority: P3)

**Goal**: Bump the library version to `0.2.0-alpha`, update the changelog with a complete entry documenting all new public API additions, and validate that the quickstart.md examples work with the actual implementation.
**Independent Test**: `python -c "import spec_kitty_events; assert spec_kitty_events.__version__ == '0.2.0-alpha'"` succeeds. The changelog contains an entry for `0.2.0-alpha`.
**Prompt**: `kitty-specs/002-github-gate-observability-contracts/tasks/WP03-version-bump-and-changelog.md`
**Estimated prompt size**: ~250 lines

### Included Subtasks
- [ ] T011 Bump version to `0.2.0-alpha` in `pyproject.toml` and `src/spec_kitty_events/__init__.py`
- [ ] T012 Update `CHANGELOG.md` with new version entry documenting all additions
- [ ] T013 Validate quickstart.md code examples against actual implementation

### Implementation Notes
- T011: Two files to update — `pyproject.toml` line `version = "0.1.1-alpha"` → `"0.2.0-alpha"`, and `__init__.py` line `__version__ = "0.1.1-alpha"` → `"0.2.0-alpha"`.
- T012: Follow Keep a Changelog format. New entry under `## [0.2.0-alpha]` with Added section listing `GatePayloadBase`, `GatePassedPayload`, `GateFailedPayload`, `UnknownConclusionError`, `map_check_run_conclusion`. Update comparison links at bottom of file.
- T013: Run quickstart.md code snippets as a smoke test. Verify imports, construction, and mapping produce expected results. If any quickstart example is wrong, fix quickstart.md.

### Parallel Opportunities
- T011 and T012 touch different files and can proceed in parallel.
- T013 depends on WP01 and WP02 being functionally complete.

### Dependencies
- Depends on WP01 and WP02 (all production code and tests must be in place before release prep).

### Risks & Mitigations
- **Version string drift**: Ensure `pyproject.toml` and `__init__.py` have the same version string. A mismatch causes packaging issues.
- **Changelog link correctness**: The `[Unreleased]` comparison link must be updated to compare against `v0.2.0-alpha`.

---

## Dependency & Execution Summary

- **Sequence**: WP01 → WP02 → WP03
- **Parallelization**: WP01 and WP02 are sequential (WP02 depends on WP01). WP03 depends on both.
- **MVP Scope**: WP01 + WP02 constitute the functional MVP — payload models, mapping, and tests. WP03 is release prep.
- **Total subtasks**: 13
- **Estimated total prompt lines**: ~1050 across 3 WPs (350 + 450 + 250)

---

## Subtask Index (Reference)

| Subtask ID | Summary                                                    | Work Package | Priority | Parallel? |
|------------|-------------------------------------------------------------|-------------|----------|-----------|
| T001       | Create GatePayloadBase model                                | WP01        | P1       | No        |
| T002       | Create GatePassedPayload & GateFailedPayload subclasses     | WP01        | P1       | No        |
| T003       | Create UnknownConclusionError exception                     | WP01        | P1       | No        |
| T004       | Update __init__.py with new exports                         | WP01        | P1       | No        |
| T005       | Verify mypy --strict compliance                             | WP01        | P1       | No        |
| T006       | Implement map_check_run_conclusion function                 | WP02        | P1       | No        |
| T007       | Write unit tests for payload model validation               | WP02        | P1       | Yes       |
| T008       | Write unit tests for conclusion mapping                     | WP02        | P1       | Yes       |
| T009       | Write Hypothesis property tests for determinism             | WP02        | P1       | Yes       |
| T010       | Run full test suite and verify coverage                     | WP02        | P1       | No        |
| T011       | Bump version to 0.2.0-alpha                                 | WP03        | P3       | Yes       |
| T012       | Update CHANGELOG.md                                         | WP03        | P3       | Yes       |
| T013       | Validate quickstart.md examples                             | WP03        | P3       | No        |
