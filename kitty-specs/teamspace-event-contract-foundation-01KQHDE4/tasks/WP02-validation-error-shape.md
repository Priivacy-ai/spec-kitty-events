---
work_package_id: WP02
title: Validation Error Shape
dependencies:
- WP01
requirement_refs:
- NFR-006
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T005
- T006
- T007
agent: "claude:sonnet:implementer-ivan:implementer"
shell_pid: "94874"
history:
- event: created
  at: '2026-05-01T09:44:26Z'
  by: /spec-kitty.tasks
agent_profile: implementer-ivan
authoritative_surface: src/spec_kitty_events/validation_errors.py
execution_mode: code_change
owned_files:
- src/spec_kitty_events/validation_errors.py
- tests/test_validation_error.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load implementer-ivan
```

---

## Objective

Introduce a structured `ValidationError` Pydantic model with a closed `ValidationErrorCode` string enum, and add a non-breaking adapter (`as_validation_error()`) on existing typed exceptions so consumers can read structured rejection details uniformly. This is the rejection vocabulary every other WP will use.

---

## Context

- Spec: NFR-006.
- Contract: [contracts/validation-error-shape.md](../contracts/validation-error-shape.md).
- Research: [research.md R-04](../research.md#r-04--structured-error-format-on-rejection).
- Existing taxonomy: `src/spec_kitty_events/status.py` already has `class TransitionError(SpecKittyEventsError):` (around line 300) and `class TransitionValidationResult` (around line 336). Other typed exceptions exist in `lifecycle.py`. We **layer** on top, we do not replace.

---

## Subtasks

### T005 — Create `src/spec_kitty_events/validation_errors.py`

**Purpose**: Provide the `ValidationError` model + closed `ValidationErrorCode` enum.

**Steps**:
1. Create `src/spec_kitty_events/validation_errors.py` (new file).
2. Define the closed enum:

   ```python
   from enum import Enum

   class ValidationErrorCode(str, Enum):
       FORBIDDEN_KEY = "FORBIDDEN_KEY"
       UNKNOWN_LANE = "UNKNOWN_LANE"
       PAYLOAD_SCHEMA_FAIL = "PAYLOAD_SCHEMA_FAIL"
       ENVELOPE_SHAPE_INVALID = "ENVELOPE_SHAPE_INVALID"
       RAW_HISTORICAL_ROW = "RAW_HISTORICAL_ROW"
   ```

3. Define the `ValidationError` Pydantic model:

   ```python
   from typing import Any
   from pydantic import BaseModel, ConfigDict

   class ValidationError(BaseModel):
       model_config = ConfigDict(extra="forbid", frozen=True)

       code: ValidationErrorCode
       message: str
       path: list[str | int] = []
       details: dict[str, Any] = {}
   ```

   - `frozen=True` makes instances hashable and prevents accidental mutation, supporting determinism (NFR-001).
   - `extra='forbid'` matches the closed-set discipline.

4. Export both from `src/spec_kitty_events/__init__.py`:

   ```python
   from spec_kitty_events.validation_errors import ValidationError, ValidationErrorCode
   __all__ = [..., "ValidationError", "ValidationErrorCode"]
   ```

**Files**:
- `src/spec_kitty_events/validation_errors.py` (new, ~40 lines)
- `src/spec_kitty_events/__init__.py` (modified to export — note: this file is NOT in owned_files; if export is required, this WP authors `validation_errors.py` and a follow-up WP can add the public re-export. If the implementer determines the public re-export must land in this WP for downstream WPs to depend on, ADD `src/spec_kitty_events/__init__.py` to `owned_files` in the frontmatter and re-run `finalize-tasks --validate-only` to confirm no overlap. Otherwise, leave `__init__.py` untouched and have downstream WPs import from the submodule directly.)

> **Implementer note on `__init__.py`**: this WP's `owned_files` does **not** list `__init__.py` to avoid ownership conflicts with WP03 (also touches it for the forbidden-key validator). If you need to extend `__init__.py`, coordinate by adding it explicitly to `owned_files` and re-validating. The safe default is to import via the full module path: `from spec_kitty_events.validation_errors import ValidationError, ValidationErrorCode`.

**Validation**:
- [ ] `from spec_kitty_events.validation_errors import ValidationError, ValidationErrorCode` works.
- [ ] `ValidationError(code=ValidationErrorCode.FORBIDDEN_KEY, message="x")` succeeds.
- [ ] `ValidationError(code="not_a_code", ...)` raises a Pydantic validation error.
- [ ] `ValidationError(extra_field=1, ...)` raises a Pydantic validation error.

---

### T006 — Add `as_validation_error()` adapters on existing typed exceptions

**Purpose**: Existing typed exceptions in `status.py` and `lifecycle.py` must be convertible to the structured shape so consumers can choose either form.

**Steps**:
1. In `src/spec_kitty_events/status.py`, locate `class TransitionError(SpecKittyEventsError):` and add a method:

   ```python
   def as_validation_error(self) -> ValidationError:
       return ValidationError(
           code=ValidationErrorCode.<map-from-self>,
           message=str(self),
           path=getattr(self, "path", []),
           details=getattr(self, "details", {}),
       )
   ```

   The mapping from a `TransitionError` to a `ValidationErrorCode` depends on the error's existing semantic — many transition errors map to `UNKNOWN_LANE`. If a `TransitionError` does not cleanly map, raise that explicitly in the method (do NOT use a generic fallback code; the closed enum is the contract).

2. **Note on cross-file modifications**: this subtask edits `src/spec_kitty_events/status.py` and `src/spec_kitty_events/lifecycle.py`, which are owned by **WP01** and **WP04** respectively. To avoid ownership conflict, this WP **does not** modify those files. Instead, this WP provides:
   - The `ValidationError` and `ValidationErrorCode` definitions (T005).
   - A small **conversion-helper module section** inside `validation_errors.py` containing free functions:

     ```python
     def transition_error_to_validation_error(err: "TransitionError") -> ValidationError: ...
     def lifecycle_error_to_validation_error(err: Exception) -> ValidationError: ...
     ```

   These helpers are imported by WP01 (after WP01 lands) and WP04 to expose `as_validation_error()` on the actual exception classes.

3. Document this design choice at the top of `validation_errors.py` so the next WP knows where to find the helpers.

**Files**:
- `src/spec_kitty_events/validation_errors.py` (modified — add helpers, ~30 more lines)

**Validation**:
- [ ] Helper functions exist and are typed (`mypy --strict` clean).
- [ ] A unit test in T007 calls each helper with a constructed exception and asserts the returned `ValidationError` is well-formed.

---

### T007 — Author `tests/test_validation_error.py`

**Purpose**: Lock the shape, the closed enum, the determinism property, and the helper-function correctness.

**Steps**:
1. Create `tests/test_validation_error.py` (new file) with the following tests:

   ```python
   import pytest
   from spec_kitty_events.validation_errors import (
       ValidationError,
       ValidationErrorCode,
       transition_error_to_validation_error,
       lifecycle_error_to_validation_error,
   )

   def test_validation_error_minimum_fields():
       err = ValidationError(code=ValidationErrorCode.UNKNOWN_LANE, message="x")
       assert err.code == ValidationErrorCode.UNKNOWN_LANE
       assert err.message == "x"
       assert err.path == []
       assert err.details == {}

   def test_validation_error_full_fields():
       err = ValidationError(
           code=ValidationErrorCode.FORBIDDEN_KEY,
           message="forbidden key found",
           path=["payload", "tags", 2, "feature_slug"],
           details={"key": "feature_slug"},
       )
       assert err.path == ["payload", "tags", 2, "feature_slug"]

   def test_validation_error_rejects_extra_fields():
       with pytest.raises(Exception):
           ValidationError(code=ValidationErrorCode.UNKNOWN_LANE, message="x", extra=1)

   def test_validation_error_rejects_unknown_code():
       with pytest.raises(Exception):
           ValidationError(code="NOT_A_CODE", message="x")

   def test_validation_error_is_frozen():
       err = ValidationError(code=ValidationErrorCode.UNKNOWN_LANE, message="x")
       with pytest.raises(Exception):
           err.message = "y"

   def test_validation_error_codes_are_closed_set():
       expected = {
           "FORBIDDEN_KEY",
           "UNKNOWN_LANE",
           "PAYLOAD_SCHEMA_FAIL",
           "ENVELOPE_SHAPE_INVALID",
           "RAW_HISTORICAL_ROW",
       }
       actual = {member.value for member in ValidationErrorCode}
       assert actual == expected

   def test_determinism():
       a = ValidationError(code=ValidationErrorCode.UNKNOWN_LANE, message="x", details={"a": 1, "b": 2})
       b = ValidationError(code=ValidationErrorCode.UNKNOWN_LANE, message="x", details={"a": 1, "b": 2})
       assert a == b
       assert a.model_dump_json() == b.model_dump_json()
   ```

2. Add helper-function tests:

   ```python
   def test_transition_error_to_validation_error_has_required_fields():
       # Construct a TransitionError-shaped exception (use a stub if direct
       # construction is awkward) and assert the returned ValidationError is
       # well-formed and has a closed-enum code.
       ...
   ```

**Files**:
- `tests/test_validation_error.py` (new, ~120–150 lines)

**Validation**:
- [ ] All tests pass.
- [ ] Determinism test produces byte-identical JSON.
- [ ] Closed-enum test catches accidental enum drift.

---

## Branch Strategy

- Planning/base branch: `main` · Merge target: `main`.
- Worktree allocated by `finalize-tasks`.

---

## Definition of Done

- [ ] `ValidationError` and `ValidationErrorCode` exist in `src/spec_kitty_events/validation_errors.py` with the exact shape from the contract.
- [ ] Conversion helpers exist for the existing typed exceptions.
- [ ] `tests/test_validation_error.py` passes.
- [ ] `mypy --strict` is green for `validation_errors.py` and the new tests.
- [ ] No file outside `owned_files` is modified.

---

## Risks

- **R-1**: Existing exception consumers may want `as_validation_error()` on the exception class itself. Mitigation: WP01 and WP04, which own those files, will add the method by calling the helper exposed here.
- **R-2**: Pydantic `frozen=True` may break a downstream consumer that mutated an error instance. Mitigation: prior code raised exceptions, not models — there is no existing mutation pattern to break.

---

## Reviewer Guidance

Codex reviewer will check:

1. The closed enum is exactly the five codes from the contract; no additions, no aliases.
2. `extra='forbid'` and `frozen=True` are both set on the model.
3. Conversion helpers do not invent new codes; if a typed exception cannot be mapped, the helper raises rather than using a fallback.
4. The determinism test uses `model_dump_json()` (or equivalent canonical serialization) to assert byte equality, not just `==`.

## Activity Log

- 2026-05-01T10:32:56Z – claude:sonnet:implementer-ivan:implementer – shell_pid=94874 – Started implementation via action command
