---
work_package_id: WP02
title: Transition Validation
lane: planned
dependencies: []
base_branch: main
subtasks:
- T008
- T009
- T010
- T011
- T012
phase: Phase 1 - Foundation
assignee: ''
agent: ''
shell_pid: ''
review_status: ''
reviewed_by: ''
history:
- timestamp: '2026-02-08T00:00:00Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP02 – Transition Validation

## Implementation Command

```bash
spec-kitty implement WP02 --base WP01
```

## Objectives & Success Criteria

Implement the transition matrix, `TransitionValidationResult`, and `validate_transition()` function in `status.py`. The validator encodes the full PRD transition matrix with guard conditions and force-override semantics. Write comprehensive unit tests covering every legal transition, every illegal combination, and all guard conditions.

**Success criteria**:
- Transition matrix is data-driven (frozenset + programmatic rules)
- `validate_transition()` returns `TransitionValidationResult` (never raises for business rules)
- All 9 legal default transitions accepted
- All illegal (from, to) combinations rejected
- All guard conditions enforced (actor, evidence, review_ref, reason)
- Force override correctly unlocks terminal lanes and non-standard transitions
- `__init__.py` updated with 2 new exports (TransitionValidationResult, validate_transition)
- mypy --strict clean
- All tests pass

## Context & Constraints

**Reference documents**:
- `kitty-specs/003-status-state-model-contracts/data-model.md` — Transition Matrix section
- `kitty-specs/003-status-state-model-contracts/contracts/status-api.md` — validate_transition() signature
- `kitty-specs/003-status-state-model-contracts/research.md` — R2 (validation return type)
- `kitty-specs/003-status-state-model-contracts/plan.md` — D3 (data-driven matrix), D4 (results not exceptions)

**WP01 provides**: Lane, ExecutionMode, StatusTransitionPayload, TERMINAL_LANES, normalize_lane(), TransitionError, all evidence models.

**Key design decision**: `validate_transition()` returns a result object. It does NOT raise exceptions for business rule violations. This is per research decision R2.

## Subtasks & Detailed Guidance

### Subtask T008 – Implement transition matrix data structure

**Purpose**: Define the allowed transitions as a data structure, not branching logic. This makes the matrix testable, extensible, and easy to reason about.

**Steps**:

1. Add section marker in `status.py`:
   ```python
   # === Section 4: Validation ===
   ```

2. Define the explicit allowed transitions:
   ```python
   _ALLOWED_TRANSITIONS: FrozenSet[Tuple[Optional[Lane], Lane]] = frozenset({
       # Initial
       (None, Lane.PLANNED),
       # Happy path
       (Lane.PLANNED, Lane.CLAIMED),
       (Lane.CLAIMED, Lane.IN_PROGRESS),
       (Lane.IN_PROGRESS, Lane.FOR_REVIEW),
       (Lane.FOR_REVIEW, Lane.DONE),
       # Review rollback
       (Lane.FOR_REVIEW, Lane.IN_PROGRESS),
       # Abandon/reassign
       (Lane.IN_PROGRESS, Lane.PLANNED),
       # Unblock
       (Lane.BLOCKED, Lane.IN_PROGRESS),
   })
   ```

3. The `→ blocked` and `→ canceled` rules are programmatic (any non-terminal lane can transition to blocked or canceled). These are checked in the validator logic, not in the frozenset.

**Files**: `src/spec_kitty_events/status.py` (append to Section 4)
**Parallel?**: Independent of T009.
**Notes**: The frozenset has 8 explicit entries. The 9th legal transition type (`any_non_terminal -> blocked` and `any_non_terminal -> canceled`) is handled programmatically.

### Subtask T009 – Implement TransitionValidationResult

**Purpose**: The return type for `validate_transition()`. A frozen dataclass (not Pydantic model — it's a simple result container).

**Steps**:

1. Define as a frozen dataclass:
   ```python
   from dataclasses import dataclass

   @dataclass(frozen=True)
   class TransitionValidationResult:
       """Result of validating a proposed status transition."""
       valid: bool
       violations: Tuple[str, ...] = ()
   ```

2. This is intentionally a dataclass, not a Pydantic model:
   - It's a result container, not a domain entity
   - Matches `ConflictResolution` pattern in `models.py` (which is also a dataclass)
   - Simpler, no serialization needed

**Files**: `src/spec_kitty_events/status.py` (append to Section 4)
**Parallel?**: Independent of T008.

### Subtask T010 – Implement validate_transition()

**Purpose**: The core validation function. Takes a `StatusTransitionPayload` and checks it against the transition matrix + guard conditions.

**Steps**:

1. Implement the function:
   ```python
   def validate_transition(
       payload: StatusTransitionPayload,
   ) -> TransitionValidationResult:
   ```

2. Collect violations in a list. Check in this order:

   a. **Terminal lane check**: If `from_lane` is in `TERMINAL_LANES` and `force` is False:
      - Add violation: `"{from_lane} is terminal; requires force=True to exit"`

   b. **Force metadata check**: If `force` is True:
      - Check `reason` is not None and not empty (should already be caught by model validator, but defense in depth)
      - If force is True and from_lane is terminal, allow any transition (skip matrix check)
      - If force is True and from_lane is not terminal, allow any transition (skip matrix check)

   c. **Matrix check** (only when force is False):
      - Check if `(from_lane, to_lane)` is in `_ALLOWED_TRANSITIONS`
      - OR if `to_lane` is `Lane.BLOCKED` and `from_lane` is not in `TERMINAL_LANES`
      - OR if `to_lane` is `Lane.CANCELED` and `from_lane` is not in `TERMINAL_LANES`
      - If none match: add violation `"Transition {from_lane} -> {to_lane} is not allowed"`

   d. **Guard conditions** (checked regardless of force):
      - `planned -> claimed`: actor must be non-empty (already required by model, but validate context)
      - `for_review -> done`: evidence must be present (already enforced by model_validator, but validate)
      - `for_review -> in_progress`: `review_ref` must be present
        - Add violation: `"for_review -> in_progress requires review_ref"`
      - `in_progress -> planned`: `reason` must be present (abandon requires explanation)
        - Add violation: `"in_progress -> planned requires reason"`

3. Return `TransitionValidationResult(valid=len(violations) == 0, violations=tuple(violations))`

**Important edge cases**:
- `None -> planned` with force=False: legal (initial event)
- `None -> claimed` with force=False: illegal (must go through planned first)
- `None -> anything` with force=True: legal (force overrides)
- `done -> done` with force=True: technically allowed by force, but semantically odd — don't special-case it, just let force override work normally

**Files**: `src/spec_kitty_events/status.py` (append to Section 4)
**Parallel?**: Depends on T008 (matrix) and T009 (result type).

### Subtask T011 – Write unit tests for full matrix coverage

**Purpose**: Exhaustively test every legal and illegal transition combination.

**Steps**:

1. Add test class `TestTransitionMatrix` in `tests/unit/test_status.py`:

2. **test_all_legal_default_transitions**: Parametrize over all 9 legal transitions (including blocked/canceled):
   ```python
   @pytest.mark.parametrize("from_lane,to_lane", [
       (None, Lane.PLANNED),
       (Lane.PLANNED, Lane.CLAIMED),
       (Lane.CLAIMED, Lane.IN_PROGRESS),
       (Lane.IN_PROGRESS, Lane.FOR_REVIEW),
       (Lane.FOR_REVIEW, Lane.DONE),       # needs evidence
       (Lane.FOR_REVIEW, Lane.IN_PROGRESS), # needs review_ref
       (Lane.IN_PROGRESS, Lane.PLANNED),    # needs reason
       (Lane.BLOCKED, Lane.IN_PROGRESS),
       (Lane.PLANNED, Lane.BLOCKED),        # any non-terminal -> blocked
       (Lane.IN_PROGRESS, Lane.CANCELED),   # any non-terminal -> canceled
   ])
   def test_legal_transition(self, from_lane, to_lane):
       # Build payload with all required guards satisfied
       ...
       result = validate_transition(payload)
       assert result.valid, f"Expected valid: {result.violations}"
   ```

   For each parametrized case, construct the payload with the required guards:
   - `for_review -> done`: include evidence
   - `for_review -> in_progress`: include review_ref
   - `in_progress -> planned`: include reason

3. **test_all_illegal_transitions**: Generate all possible (from, to) pairs that are NOT in the legal set, and verify they are rejected:
   ```python
   def test_illegal_transitions(self):
       legal = {(None, Lane.PLANNED), (Lane.PLANNED, Lane.CLAIMED), ...}
       # Add dynamic legal transitions (non-terminal -> blocked, non-terminal -> canceled)
       all_lanes = [None] + list(Lane)
       for from_l in all_lanes:
           for to_l in Lane:
               if (from_l, to_l) not in legal:
                   payload = build_payload(from_l, to_l, force=False)
                   result = validate_transition(payload)
                   assert not result.valid, f"Expected invalid: {from_l} -> {to_l}"
   ```

4. **test_terminal_to_any_with_force**: `done -> planned` with force=True is valid.

5. **test_self_transition_rejected**: `planned -> planned` without force is invalid.

**Files**: `tests/unit/test_status.py` (append)
**Parallel?**: Can be written alongside T012.

### Subtask T012 – Write unit tests for guard conditions and force override

**Purpose**: Test specific guard condition enforcement and force override behavior.

**Steps**:

1. Add test class `TestGuardConditions`:

2. **test_for_review_to_in_progress_without_review_ref**:
   - Payload with `from_lane=FOR_REVIEW, to_lane=IN_PROGRESS, review_ref=None`
   - Assert `result.valid is False` and "review_ref" in violations

3. **test_for_review_to_in_progress_with_review_ref**:
   - Same but with `review_ref="PR #42 comment"`
   - Assert `result.valid is True`

4. **test_in_progress_to_planned_without_reason**:
   - Payload with `from_lane=IN_PROGRESS, to_lane=PLANNED, reason=None`
   - Assert `result.valid is False`

5. **test_in_progress_to_planned_with_reason**:
   - Same but with `reason="Reassigning to different agent"`
   - Assert `result.valid is True`

6. **test_force_exit_from_done**:
   - `from_lane=DONE, to_lane=IN_PROGRESS, force=True, reason="Reopening"`
   - Assert valid

7. **test_force_exit_from_canceled**:
   - `from_lane=CANCELED, to_lane=PLANNED, force=True, reason="Un-canceling"`
   - Assert valid

8. **test_no_force_exit_from_done**:
   - `from_lane=DONE, to_lane=IN_PROGRESS, force=False`
   - Assert invalid with "terminal" in violation

9. **test_force_allows_nonstandard_transition**:
   - `from_lane=PLANNED, to_lane=FOR_REVIEW, force=True, reason="Skipping ahead"`
   - Assert valid (force overrides matrix)

10. **test_multiple_violations_collected**:
    - Construct a payload that violates multiple rules simultaneously
    - Assert `len(result.violations) > 1`

11. Update `__init__.py` to export `TransitionValidationResult` and `validate_transition` (add to import block and `__all__`).

12. Run mypy --strict and full test suite.

**Files**: `tests/unit/test_status.py` (append), `src/spec_kitty_events/__init__.py` (edit)
**Parallel?**: Can be written alongside T011.

## Test Strategy

Use a helper function to reduce boilerplate:
```python
def _make_payload(
    from_lane: Optional[Lane] = Lane.PLANNED,
    to_lane: Lane = Lane.CLAIMED,
    force: bool = False,
    reason: Optional[str] = None,
    review_ref: Optional[str] = None,
    evidence: Optional[DoneEvidence] = None,
) -> StatusTransitionPayload:
    return StatusTransitionPayload(
        feature_slug="test-feature",
        wp_id="WP01",
        from_lane=from_lane,
        to_lane=to_lane,
        actor="test-actor",
        force=force,
        reason=reason,
        execution_mode=ExecutionMode.WORKTREE,
        review_ref=review_ref,
        evidence=evidence,
    )
```

And a helper to build valid DoneEvidence for tests that need it:
```python
def _make_evidence() -> DoneEvidence:
    return DoneEvidence(
        repos=[RepoEvidence(repo="test", branch="main", commit="abc123")],
        verification=[],
        review=ReviewVerdict(reviewer="alice", verdict="approved"),
    )
```

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Matrix misses a legal transition from PRD | Exhaustive test in T011 that iterates ALL Lane x Lane combos |
| Guard conditions overlap with model validators | Clearly document: model validators = structural, validate_transition = business rules |
| Force override too permissive | Test that force still requires reason+actor (structural check by model validator) |

## Review Guidance

- Compare transition matrix against PRD Section 7.2 — all 9 rules must be present
- Verify `blocked -> in_progress` is the ONLY exit from blocked (without force)
- Verify `any_non_terminal -> blocked` and `any_non_terminal -> canceled` are both handled
- Verify `done` and `canceled` are both treated as terminal
- Verify `validate_transition` never raises — always returns result
- Verify `__init__.py` now exports `TransitionValidationResult` and `validate_transition`

## Activity Log

- 2026-02-08T00:00:00Z – system – lane=planned – Prompt created.
