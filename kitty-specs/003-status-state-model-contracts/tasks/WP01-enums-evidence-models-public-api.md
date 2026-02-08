---
work_package_id: WP01
title: Enums, Evidence Models, and Public API
lane: "for_review"
dependencies: []
base_branch: main
base_commit: 6d27fb7938b32b7b9f004ccb5bf29c82f80030d0
created_at: '2026-02-08T14:15:18.525188+00:00'
subtasks:
- T001
- T002
- T003
- T004
- T005
- T006
- T007
phase: Phase 1 - Foundation
assignee: ''
agent: "claude-opus"
shell_pid: "39467"
review_status: ''
reviewed_by: ''
history:
- timestamp: '2026-02-08T00:00:00Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP01 – Enums, Evidence Models, and Public API

## Implementation Command

```bash
spec-kitty implement WP01
```

## Objectives & Success Criteria

Create the `src/spec_kitty_events/status.py` module with all foundational data types: Lane enum, ExecutionMode enum, constants, `normalize_lane()`, evidence models (RepoEvidence, VerificationEntry, ReviewVerdict, DoneEvidence), ForceMetadata, StatusTransitionPayload with cross-field validators, and TransitionError exception. Wire up all 21 new exports in `__init__.py`. Write comprehensive unit tests. Verify mypy --strict clean.

**Success criteria**:
- `status.py` exists with sections 1-3 implemented (enums, evidence models, transition models)
- All 8 Pydantic models + 2 enums + 1 exception + 1 function + 3 constants defined
- `__init__.py` exports all 21 new symbols; `__all__` updated
- Unit tests pass for all models, validators, and normalize_lane()
- `mypy --strict` reports zero errors on `status.py`
- All existing tests still pass (no regressions)

## Context & Constraints

**Reference documents** (read these before starting):
- `kitty-specs/003-status-state-model-contracts/data-model.md` — entity definitions with field types
- `kitty-specs/003-status-state-model-contracts/contracts/status-api.md` — public API surface
- `kitty-specs/003-status-state-model-contracts/research.md` — design decisions R1, R2, R7, R8
- `kitty-specs/003-status-state-model-contracts/plan.md` — D1, D2 decisions

**Existing patterns to follow**:
- `src/spec_kitty_events/gates.py` — frozen Pydantic models, `ConfigDict(frozen=True)`, field validators, `SpecKittyEventsError` subclass
- `src/spec_kitty_events/models.py` — `Event` model, `ValidationError`, `Field(min_length=...)` pattern
- `src/spec_kitty_events/__init__.py` — import block + `__all__` grouping pattern

**Constraints**:
- Python 3.10 target: use `class Lane(str, Enum)` NOT `StrEnum` (3.11+)
- Pydantic v2: `ConfigDict(frozen=True)`, `@field_validator`, `@model_validator`
- No new dependencies
- All models frozen (immutable)
- Import `SpecKittyEventsError` and `ValidationError` from `spec_kitty_events.models`

## Subtasks & Detailed Guidance

### Subtask T001 – Create status.py with Lane, ExecutionMode, constants, normalize_lane()

**Purpose**: Establish the module file with enums and the lane normalization function that everything else depends on.

**Steps**:

1. Create `src/spec_kitty_events/status.py` with module docstring:
   ```python
   """Status state model contracts for feature/WP lifecycle events."""
   ```

2. Add section marker comments matching plan.md D1:
   ```python
   # === Section 1: Enums (Lane, ExecutionMode) ===
   ```

3. Implement `Lane(str, Enum)` with exactly 7 values:
   ```python
   class Lane(str, Enum):
       PLANNED = "planned"
       CLAIMED = "claimed"
       IN_PROGRESS = "in_progress"
       FOR_REVIEW = "for_review"
       DONE = "done"
       BLOCKED = "blocked"
       CANCELED = "canceled"
   ```

4. Implement `ExecutionMode(str, Enum)`:
   ```python
   class ExecutionMode(str, Enum):
       WORKTREE = "worktree"
       DIRECT_REPO = "direct_repo"
   ```

5. Define constants:
   ```python
   TERMINAL_LANES: FrozenSet[Lane] = frozenset({Lane.DONE, Lane.CANCELED})
   LANE_ALIASES: Dict[str, Lane] = {"doing": Lane.IN_PROGRESS}
   WP_STATUS_CHANGED: str = "WPStatusChanged"
   ```

6. Implement `normalize_lane(value: str) -> Lane`:
   - Check if value is already a Lane member value → return it
   - Check LANE_ALIASES → return mapped Lane
   - Otherwise raise `ValidationError(f"Unknown lane: {value!r}. ...")`
   - Import `ValidationError` from `spec_kitty_events.models`

**Files**: `src/spec_kitty_events/status.py` (new)
**Parallel?**: Independent — first subtask.

### Subtask T002 – Implement evidence models

**Purpose**: Define the typed evidence structures required for `done` transitions.

**Steps**:

1. Add section marker:
   ```python
   # === Section 2: Evidence Models ===
   ```

2. Implement `RepoEvidence(BaseModel)`:
   - `model_config = ConfigDict(frozen=True)`
   - Fields: `repo: str = Field(..., min_length=1)`, `branch: str`, `commit: str`, `files_touched: Optional[List[str]] = None`

3. Implement `VerificationEntry(BaseModel)`:
   - Frozen. Fields: `command: str`, `result: str`, `summary: Optional[str] = None`

4. Implement `ReviewVerdict(BaseModel)`:
   - Frozen. Fields: `reviewer: str`, `verdict: str`, `reference: Optional[str] = None`

5. Implement `DoneEvidence(BaseModel)`:
   - Frozen. Fields: `repos: List[RepoEvidence] = Field(..., min_length=1)`, `verification: List[VerificationEntry] = Field(default_factory=list)`, `review: ReviewVerdict`
   - The `repos` field requires at least 1 entry (`min_length=1` on the Field)

**Files**: `src/spec_kitty_events/status.py` (append)
**Parallel?**: Can be written alongside T001 (different section).

### Subtask T003 – Implement ForceMetadata and StatusTransitionPayload

**Purpose**: Define the core transition payload model with Pydantic cross-field validators for business rules.

**Steps**:

1. Add section marker:
   ```python
   # === Section 3: Transition Models ===
   ```

2. Implement `ForceMetadata(BaseModel)`:
   - Frozen. Fields: `force: bool = True`, `actor: str = Field(..., min_length=1)`, `reason: str = Field(..., min_length=1)`

3. Implement `StatusTransitionPayload(BaseModel)`:
   - Frozen. All fields per data-model.md:
     - `feature_slug: str = Field(..., min_length=1)`
     - `wp_id: str = Field(..., min_length=1)`
     - `from_lane: Optional[Lane] = None`
     - `to_lane: Lane`
     - `actor: str = Field(..., min_length=1)`
     - `force: bool = False`
     - `reason: Optional[str] = None`
     - `execution_mode: ExecutionMode`
     - `review_ref: Optional[str] = None`
     - `evidence: Optional[DoneEvidence] = None`

4. Add `@field_validator("from_lane", "to_lane", mode="before")` to normalize lane aliases:
   ```python
   @field_validator("from_lane", "to_lane", mode="before")
   @classmethod
   def _normalize_lane(cls, v: Any) -> Any:
       if v is None:
           return v
       if isinstance(v, str) and v not in Lane.__members__.values():
           # Check alias map
           ...
       return v
   ```
   - If the string matches a LANE_ALIASES key, return the mapped Lane value
   - If the string is a valid Lane value, pass through
   - If unknown, let Pydantic's enum validation raise its own error

5. Add `@model_validator(mode="after")` for cross-field rules:
   - When `force is True`: `reason` must not be None and must be non-empty
   - When `to_lane == Lane.DONE` and `force is False`: `evidence` must not be None
   - Raise `ValueError` for violations (Pydantic converts to `pydantic.ValidationError`)

**Important**: The `@model_validator` validates *structural* integrity (is the payload self-consistent?). Transition *legality* (is this transition allowed by the state machine?) is handled by `validate_transition()` in WP02.

**Files**: `src/spec_kitty_events/status.py` (append)
**Parallel?**: Depends on T001 (needs Lane, ExecutionMode) and T002 (needs DoneEvidence).

### Subtask T004 – Add TransitionError exception

**Purpose**: Provide a typed exception for consumers who want to raise on invalid transitions.

**Steps**:

1. Add after the models section:
   ```python
   class TransitionError(SpecKittyEventsError):
       """Raised when a status transition violates the state machine rules.

       Not raised by the library internally (reducer records anomalies).
       Available for consumers: if not result.valid: raise TransitionError(result.violations)
       """
       def __init__(self, violations: Tuple[str, ...]) -> None:
           self.violations = violations
           super().__init__(f"Invalid transition: {'; '.join(violations)}")
   ```

**Files**: `src/spec_kitty_events/status.py` (append)
**Parallel?**: Independent — small addition.

### Subtask T005 – Update __init__.py with new exports

**Purpose**: Wire up all 21 new public symbols so consumers can import from `spec_kitty_events` directly.

**Steps**:

1. Add a new import block in `__init__.py` after the gate observability block:
   ```python
   # Status state model contracts
   from spec_kitty_events.status import (
       Lane,
       ExecutionMode,
       RepoEvidence,
       VerificationEntry,
       ReviewVerdict,
       DoneEvidence,
       ForceMetadata,
       StatusTransitionPayload,
       TransitionError,
       TransitionValidationResult,
       normalize_lane,
       validate_transition,
       status_event_sort_key,
       dedup_events,
       reduce_status_events,
       WPState,
       TransitionAnomaly,
       ReducedStatus,
       TERMINAL_LANES,
       LANE_ALIASES,
       WP_STATUS_CHANGED,
   )
   ```

   **Note**: Some of these symbols (TransitionValidationResult, validate_transition, status_event_sort_key, dedup_events, reduce_status_events, WPState, TransitionAnomaly, ReducedStatus) won't exist yet — they'll be added in WP02 and WP03. **For WP01, only import the symbols that exist.** The remaining imports will be added by WP02 and WP03 as they implement their symbols.

   For WP01, import:
   ```python
   # Status state model contracts
   from spec_kitty_events.status import (
       Lane,
       ExecutionMode,
       RepoEvidence,
       VerificationEntry,
       ReviewVerdict,
       DoneEvidence,
       ForceMetadata,
       StatusTransitionPayload,
       TransitionError,
       normalize_lane,
       TERMINAL_LANES,
       LANE_ALIASES,
       WP_STATUS_CHANGED,
   )
   ```

2. Extend `__all__` with the WP01 symbols (13 new exports this WP):
   ```python
   # Status state model contracts
   "Lane",
   "ExecutionMode",
   "RepoEvidence",
   "VerificationEntry",
   "ReviewVerdict",
   "DoneEvidence",
   "ForceMetadata",
   "StatusTransitionPayload",
   "TransitionError",
   "normalize_lane",
   "TERMINAL_LANES",
   "LANE_ALIASES",
   "WP_STATUS_CHANGED",
   ```

3. Update `__version__` — **do NOT bump yet** (that's WP04). Leave as `"0.2.0-alpha"`.

**Files**: `src/spec_kitty_events/__init__.py` (edit)
**Parallel?**: Depends on T001-T004 (needs all symbols to exist).

### Subtask T006 – Write unit tests

**Purpose**: Comprehensive test coverage for all models, enums, and normalize_lane.

**Steps**:

1. Create `tests/unit/test_status.py` with test classes:

2. **TestLane**:
   - `test_lane_values`: All 7 Lane members have correct string values
   - `test_lane_string_equality`: `Lane.PLANNED == "planned"` etc.
   - `test_lane_iteration`: Can iterate all 7 members
   - `test_lane_from_value`: `Lane("planned") == Lane.PLANNED`
   - `test_lane_invalid_value`: `Lane("bogus")` raises ValueError

3. **TestExecutionMode**:
   - `test_execution_mode_values`: Both members have correct string values
   - `test_execution_mode_from_value`: Construction from string

4. **TestNormalizeLane**:
   - `test_normalize_canonical`: All 7 canonical values return correct Lane
   - `test_normalize_alias_doing`: `normalize_lane("doing")` returns `Lane.IN_PROGRESS`
   - `test_normalize_unknown_raises`: `normalize_lane("bogus")` raises `ValidationError`
   - `test_normalize_unknown_is_library_error`: Raised error is `SpecKittyEventsError` subclass

5. **TestRepoEvidence**:
   - `test_construction`: Valid construction
   - `test_frozen`: Assignment raises `ValidationError`
   - `test_files_touched_optional`: None by default
   - `test_empty_repo_rejected`: `repo=""` raises validation error
   - `test_round_trip`: `model_dump()` → `model_validate()` round-trip

6. **TestVerificationEntry**, **TestReviewVerdict**: Same pattern (construction, frozen, optional fields, round-trip)

7. **TestDoneEvidence**:
   - `test_construction`: Valid construction with repos, verification, review
   - `test_repos_required_nonempty`: Empty repos list raises validation error
   - `test_verification_defaults_empty`: Default is empty list
   - `test_round_trip`: Nested model round-trip

8. **TestForceMetadata**:
   - `test_construction`: Valid construction
   - `test_actor_required_nonempty`: Empty actor rejected
   - `test_reason_required_nonempty`: Empty reason rejected

9. **TestStatusTransitionPayload**:
   - `test_basic_construction`: Simple planned→claimed payload
   - `test_alias_normalization_from_lane`: `from_lane="doing"` normalized to `Lane.IN_PROGRESS`
   - `test_alias_normalization_to_lane`: `to_lane="doing"` normalized to `Lane.IN_PROGRESS`
   - `test_force_requires_reason`: `force=True, reason=None` raises
   - `test_force_with_reason_valid`: `force=True, reason="..."` succeeds
   - `test_done_requires_evidence`: `to_lane=Lane.DONE, evidence=None, force=False` raises
   - `test_done_with_evidence_valid`: With evidence succeeds
   - `test_forced_done_without_evidence_valid`: `force=True, to_lane=done, evidence=None` should succeed (force overrides evidence requirement? — Check: per data-model.md validator rule 2 is "When to_lane=done: evidence must not be None". But the spec edge case says "Force + done requires both force metadata AND done evidence." So forced done still needs evidence. The model_validator should enforce: `to_lane == done → evidence required` regardless of force.)
   - `test_round_trip`: Full payload round-trip via model_dump/model_validate
   - `test_frozen`: Assignment raises

10. **TestTransitionError**:
    - `test_construction`: Takes violations tuple, stores it, formats message
    - `test_is_spec_kitty_error`: isinstance check

**Files**: `tests/unit/test_status.py` (new)
**Parallel?**: Can start once T001-T004 are done.
**Notes**: Use existing `tests/unit/test_gates.py` as a pattern reference for test structure.

### Subtask T007 – Run mypy --strict

**Purpose**: Verify all new code passes strict type checking.

**Steps**:

1. Run: `python3.11 -m mypy --strict src/spec_kitty_events/status.py`
2. Fix any type errors (common issues: missing return types, untyped `cls` in validators)
3. Run: `python3.11 -m mypy --strict src/spec_kitty_events/__init__.py`
4. Run full test suite: `python3.11 -m pytest tests/`
5. Verify zero failures in both existing and new tests

**Files**: Various (fix any type issues found)
**Parallel?**: Depends on all previous subtasks.

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| `Lane(str, Enum)` doesn't serialize cleanly through Pydantic v2 | Test round-trip in T006 early; if needed, add `@field_serializer` like gates.py's URL serializer |
| `@field_validator` for lane alias normalization interferes with Pydantic's own enum validation | Use `mode="before"` so our normalizer runs before Pydantic's type coercion |
| `@model_validator` cross-field checks conflict with frozen model | Use `mode="after"` — validation runs after construction, before freeze |
| Done + force evidence requirement ambiguity | Spec edge case is explicit: "Force + done requires both." Enforce `to_lane=done → evidence required` always. |

## Review Guidance

- Verify all 7 Lane values match PRD section 7.1 exactly
- Verify `normalize_lane("doing")` returns `Lane.IN_PROGRESS` (not raises)
- Verify StatusTransitionPayload cross-validators: force+reason, done+evidence
- Verify `__init__.py` has the correct 13 new exports (not 21 yet — 8 more come in WP02/WP03)
- Verify zero mypy errors
- Verify existing tests still pass

## Activity Log

- 2026-02-08T00:00:00Z – system – lane=planned – Prompt created.
- 2026-02-08T14:15:23Z – claude-opus – shell_pid=39467 – lane=doing – Assigned agent via workflow command
- 2026-02-08T14:19:31Z – claude-opus – shell_pid=39467 – lane=for_review – Ready for review: status.py with enums, evidence models, transition payload, 282 tests pass, mypy clean, 100% coverage
