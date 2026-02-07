---
work_package_id: "WP01"
subtasks:
  - "T001"
  - "T002"
  - "T003"
  - "T004"
  - "T005"
title: "Gate Payload Models & Public API"
phase: "Phase 1 - Foundation"
lane: "planned"
assignee: ""
agent: ""
shell_pid: ""
review_status: ""
reviewed_by: ""
dependencies: []
history:
  - timestamp: "2026-02-07T00:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP01 – Gate Payload Models & Public API

## Review Feedback

> **Populated by `/spec-kitty.review`** – Reviewers add detailed feedback here when work needs changes.

*[This section is empty initially.]*

---

## Markdown Formatting
Wrap HTML/XML tags in backticks: `<div>`, `<script>`
Use language identifiers in code blocks: `python`, `bash`

---

## Objectives & Success Criteria

Create the `src/spec_kitty_events/gates.py` module containing:
- `GatePayloadBase` — shared Pydantic base model with all gate payload fields
- `GatePassedPayload` — subclass for successful gate conclusions
- `GateFailedPayload` — subclass for failed gate conclusions
- `UnknownConclusionError` — custom exception for unrecognized conclusions

Wire all new types into the package's public API via `__init__.py`.

**Success criteria**:
- `from spec_kitty_events import GatePassedPayload, GateFailedPayload, GatePayloadBase, UnknownConclusionError` works
- Constructing a `GatePassedPayload` with all required fields succeeds
- Constructing one with a missing required field raises `pydantic.ValidationError`
- Payload models are frozen (immutable)
- `mypy --strict src/spec_kitty_events/gates.py` passes with zero errors

## Context & Constraints

**Reference documents** (read these before implementing):
- **Spec**: `kitty-specs/002-github-gate-observability-contracts/spec.md` — FR-001 through FR-004, FR-010
- **Plan**: `kitty-specs/002-github-gate-observability-contracts/plan.md` — Design decisions D1–D5
- **Data model**: `kitty-specs/002-github-gate-observability-contracts/data-model.md` — field table with types and constraints
- **API contract**: `kitty-specs/002-github-gate-observability-contracts/contracts/gates-api.md` — exact class signatures

**Existing code to study**:
- `src/spec_kitty_events/models.py` — follow the same `ConfigDict(frozen=True)` pattern used by `Event`
- `src/spec_kitty_events/__init__.py` — follow the existing import/export pattern

**Architectural constraints**:
- Do NOT modify `models.py` — keep gate concerns in `gates.py`
- Do NOT add new dependencies — use only `pydantic` (already a dependency)
- Must pass `mypy --strict` (Python 3.10 target)
- All models must use `ConfigDict(frozen=True)`

**Implementation command**: `spec-kitty implement WP01`

## Subtasks & Detailed Guidance

### Subtask T001 – Create GatePayloadBase model

**Purpose**: Define the shared base Pydantic model that holds all gate payload fields. This base is not meant to be instantiated directly by consumers but provides the validated schema for both pass and fail payloads.

**Steps**:
1. Create `src/spec_kitty_events/gates.py` with the following imports:
   ```python
   import logging
   from typing import Literal, Optional, Callable

   from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field

   from spec_kitty_events.models import SpecKittyEventsError
   ```

2. Define `GatePayloadBase`:
   ```python
   class GatePayloadBase(BaseModel):
       """Base payload for CI gate outcome events."""

       model_config = ConfigDict(frozen=True)

       gate_name: str = Field(
           ..., min_length=1,
           description="Name of the CI gate (e.g., 'ci/build', 'ci/lint')"
       )
       gate_type: Literal["ci"] = Field(
           ..., description="Type of gate. Currently only 'ci' is supported."
       )
       conclusion: str = Field(
           ..., min_length=1,
           description="Raw conclusion string from the external provider"
       )
       external_provider: Literal["github"] = Field(
           ..., description="External CI provider. Currently only 'github' is supported."
       )
       check_run_id: int = Field(
           ..., gt=0,
           description="GitHub check run ID"
       )
       check_run_url: AnyHttpUrl = Field(
           ..., description="URL of the GitHub check run"
       )
       delivery_id: str = Field(
           ..., min_length=1,
           description="Webhook delivery ID used as idempotency key"
       )
       pr_number: Optional[int] = Field(
           None, gt=0,
           description="Pull request number, if the gate is associated with a PR"
       )
   ```

3. **Field constraints to verify**:
   - `gate_name`: `min_length=1` — rejects empty string
   - `gate_type`: `Literal["ci"]` — rejects any other string
   - `conclusion`: `min_length=1` — rejects empty string
   - `external_provider`: `Literal["github"]` — rejects any other string
   - `check_run_id`: `gt=0` — rejects zero and negative
   - `check_run_url`: `AnyHttpUrl` — rejects non-URL strings
   - `delivery_id`: `min_length=1` — rejects empty string
   - `pr_number`: `Optional[int]`, `gt=0` when present — rejects zero and negative

**Files**: `src/spec_kitty_events/gates.py` (new file)
**Parallel?**: No — must be created before T002, T003.

**Notes**:
- `AnyHttpUrl` in Pydantic v2 returns a `Url` object, not a plain string. When calling `model_dump()`, the URL will serialize. Verify this doesn't break downstream `Event.payload` usage (which expects `Dict[str, Any]`). If needed, add a model serializer — but test first in WP02 before adding complexity.

### Subtask T002 – Create GatePassedPayload and GateFailedPayload subclasses

**Purpose**: Provide concrete types for type discrimination. Consumers can use `isinstance()` checks or type narrowing to distinguish pass/fail payloads.

**Steps**:
1. Add both subclasses directly below `GatePayloadBase` in `gates.py`:

   ```python
   class GatePassedPayload(GatePayloadBase):
       """Payload for a CI gate that concluded successfully.

       Attached to a generic Event with event_type='GatePassed'.
       """
       pass


   class GateFailedPayload(GatePayloadBase):
       """Payload for a CI gate that concluded with a failure condition.

       Covers conclusions: failure, timed_out, cancelled, action_required.
       Attached to a generic Event with event_type='GateFailed'.
       """
       pass
   ```

2. Verify both subclasses inherit all fields and the `frozen=True` config from the base.

**Files**: `src/spec_kitty_events/gates.py`
**Parallel?**: No — depends on T001.

### Subtask T003 – Create UnknownConclusionError exception

**Purpose**: Provide a specific, catchable exception for unrecognized GitHub conclusions. Consumers can catch this separately from `ValidationError` or other library errors.

**Steps**:
1. Add the exception class in `gates.py`:

   ```python
   class UnknownConclusionError(SpecKittyEventsError):
       """Raised when a check_run conclusion is not in the known set."""

       def __init__(self, conclusion: str) -> None:
           self.conclusion = conclusion
           super().__init__(
               f"Unknown check_run conclusion: {conclusion!r}. "
               f"Known values: success, failure, timed_out, cancelled, "
               f"action_required, neutral, skipped, stale"
           )
   ```

2. The error message should list all 8 known values to help debugging.

**Files**: `src/spec_kitty_events/gates.py`
**Parallel?**: No — depends on T001 (same file, needs the import of `SpecKittyEventsError`).

### Subtask T004 – Update `__init__.py` with new public API exports

**Purpose**: Make the new types importable from the top-level package (`from spec_kitty_events import GatePassedPayload`). This satisfies FR-010.

**Steps**:
1. Open `src/spec_kitty_events/__init__.py`.
2. Add a new import block after the existing "Core data models" imports:

   ```python
   # Gate observability contracts
   from spec_kitty_events.gates import (
       GatePayloadBase,
       GatePassedPayload,
       GateFailedPayload,
       UnknownConclusionError,
       map_check_run_conclusion,
   )
   ```

   **Note**: `map_check_run_conclusion` won't exist yet (implemented in WP02). To avoid import errors, you have two options:
   - **(Preferred)** Add the function stub in `gates.py` now as a placeholder that raises `NotImplementedError` — this keeps imports clean.
   - **(Alternative)** Defer the `map_check_run_conclusion` import to WP02. If you choose this, leave a `# TODO: WP02 adds map_check_run_conclusion` comment.

   **Decision**: Use the preferred approach — add a placeholder function in T001:
   ```python
   def map_check_run_conclusion(
       conclusion: str,
       on_ignored: Optional[Callable[[str, str], None]] = None,
   ) -> Optional[str]:
       """Map a GitHub check_run conclusion to an event type string.

       Placeholder — full implementation in WP02.
       """
       raise NotImplementedError("Implemented in WP02")
   ```

3. Add all 5 new names to `__all__`:
   ```python
   # Gate observability
   "GatePayloadBase",
   "GatePassedPayload",
   "GateFailedPayload",
   "UnknownConclusionError",
   "map_check_run_conclusion",
   ```

**Files**: `src/spec_kitty_events/__init__.py`
**Parallel?**: Can be drafted in parallel with T001–T003 but finalize after them.

### Subtask T005 – Verify mypy --strict compliance

**Purpose**: The library enforces `mypy --strict`. New code must pass without errors.

**Steps**:
1. Run: `mypy --strict src/spec_kitty_events/gates.py`
2. Fix any type errors. Common issues:
   - `Optional` vs `Union[X, None]` syntax
   - `Callable` type hints need `from typing import Callable`
   - `AnyHttpUrl` may need a `# type: ignore` if mypy can't resolve Pydantic's URL types (check first — usually it resolves fine with Pydantic v2)
3. Run: `mypy --strict src/spec_kitty_events/__init__.py` to verify imports are clean.

**Files**: No file changes expected — just verification.
**Parallel?**: No — depends on T001–T004 being complete.

## Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| `AnyHttpUrl` serializes as object, not string | Medium | Medium | Test `model_dump()` output type in WP02. Add `@field_serializer` if needed. |
| mypy errors on `Literal` + `Optional` combo | Low | Low | Use explicit `Union[int, None]` syntax if needed for Python 3.10 compat. |
| `map_check_run_conclusion` placeholder causes confusion | Low | Low | Clear docstring + `NotImplementedError`. WP02 replaces it immediately. |

## Review Guidance

- Verify all 8 fields on `GatePayloadBase` match the data model spec exactly (types, constraints, defaults).
- Verify `frozen=True` is set via `ConfigDict`.
- Verify `UnknownConclusionError` inherits from `SpecKittyEventsError` (not `Exception` or `ValueError`).
- Verify `__init__.py` exports all 5 new names in `__all__`.
- Verify `mypy --strict` passes.

## Activity Log

- 2026-02-07T00:00:00Z – system – lane=planned – Prompt created.
