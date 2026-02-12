---
work_package_id: WP01
title: Lane Mapping Contract
lane: "for_review"
dependencies: []
base_branch: main
base_commit: 1c16bd2a704cc44184e768fda496a645fe9356b1
created_at: '2026-02-12T10:21:10.782442+00:00'
subtasks: [T001, T002, T003, T004, T005, T006]
shell_pid: "54078"
agent: "claude-opus"
history:
- date: '2026-02-12'
  action: created
  by: spec-kitty.tasks
---

# WP01 — Lane Mapping Contract

## Implementation Command

```bash
spec-kitty implement WP01
```

## Objective

Implement the first-class lane mapping contract: `SyncLaneV1` enum, `CANONICAL_TO_SYNC_V1` immutable mapping, and `canonical_to_sync_v1()` function. These are the foundational exports that close the 7-lane vs 4-lane gap between canonical and consumer models.

## Context

The canonical status model uses 7 lanes (`Lane` enum in `src/spec_kitty_events/status.py`):
- `planned`, `claimed`, `in_progress`, `for_review`, `done`, `blocked`, `canceled`

Downstream consumers (CLI and SaaS) currently use a 4-lane sync model:
- `planned`, `doing`, `for_review`, `done`

The mapping is currently hardcoded in each consumer. This WP formalizes it as a locked, importable contract.

**Key files to modify**:
- `src/spec_kitty_events/status.py` — add new types and function
- `src/spec_kitty_events/__init__.py` — export new symbols
- `tests/unit/test_sync_lane.py` — new test file
- `tests/property/test_lane_mapping_determinism.py` — new test file

## Subtask Guidance

### T001: Add `SyncLaneV1` enum to `status.py`

**Purpose**: Define the 4-value sync lane enum that consumers will import.

**Steps**:
1. Add `SyncLaneV1` class after the existing `Lane` enum (around line 23) in `src/spec_kitty_events/status.py`.
2. Must be `(str, Enum)` to match the existing pattern used by `Lane`.
3. Exactly 4 values: `PLANNED = "planned"`, `DOING = "doing"`, `FOR_REVIEW = "for_review"`, `DONE = "done"`.
4. Add a docstring: `"""V1 compatibility sync lanes for downstream consumers."""`

**Validation**:
- [ ] `SyncLaneV1` has exactly 4 members
- [ ] Each value is a lowercase string matching the wire format
- [ ] `SyncLaneV1("doing")` works (string enum lookup)

### T002: Add `CANONICAL_TO_SYNC_V1` mapping constant

**Purpose**: Create an immutable mapping from all 7 `Lane` values to `SyncLaneV1` values.

**Steps**:
1. Import `MappingProxyType` from `types` at the top of `status.py`.
2. Define the mapping after `SyncLaneV1`:
   ```python
   CANONICAL_TO_SYNC_V1: MappingProxyType[Lane, SyncLaneV1] = MappingProxyType({
       Lane.PLANNED: SyncLaneV1.PLANNED,
       Lane.CLAIMED: SyncLaneV1.PLANNED,
       Lane.IN_PROGRESS: SyncLaneV1.DOING,
       Lane.FOR_REVIEW: SyncLaneV1.FOR_REVIEW,
       Lane.DONE: SyncLaneV1.DONE,
       Lane.BLOCKED: SyncLaneV1.DOING,
       Lane.CANCELED: SyncLaneV1.PLANNED,
   })
   ```
3. The type annotation must satisfy `mypy --strict`.

**Validation**:
- [ ] All 7 `Lane` members are present as keys
- [ ] All values are `SyncLaneV1` members
- [ ] `CANONICAL_TO_SYNC_V1[Lane.BLOCKED]` returns `SyncLaneV1.DOING`
- [ ] Attempting to mutate raises `TypeError` (MappingProxyType is immutable)

### T003: Add `canonical_to_sync_v1()` function

**Purpose**: Provide a typed function wrapper for the mapping.

**Steps**:
1. Define after the mapping constant:
   ```python
   def canonical_to_sync_v1(lane: Lane) -> SyncLaneV1:
       """Apply the V1 canonical-to-sync lane mapping.

       Args:
           lane: A canonical Lane enum value.

       Returns:
           The corresponding SyncLaneV1 value.

       Raises:
           KeyError: If lane is not in the V1 mapping.
       """
       return CANONICAL_TO_SYNC_V1[lane]
   ```
2. The function is intentionally simple — it exists for type safety and discoverability.

**Validation**:
- [ ] `canonical_to_sync_v1(Lane.IN_PROGRESS)` returns `SyncLaneV1.DOING`
- [ ] `canonical_to_sync_v1(Lane.CANCELED)` returns `SyncLaneV1.PLANNED`
- [ ] Function has correct type signature for mypy

### T004: Export new symbols from `__init__.py`

**Purpose**: Make the lane mapping contract importable from the top-level package.

**Steps**:
1. In `src/spec_kitty_events/__init__.py`, add to the status imports block:
   ```python
   from spec_kitty_events.status import (
       ...  # existing imports
       SyncLaneV1,
       CANONICAL_TO_SYNC_V1,
       canonical_to_sync_v1,
   )
   ```
2. Add all three to the `__all__` list under the `# Status state model` section.

**Validation**:
- [ ] `from spec_kitty_events import SyncLaneV1` works
- [ ] `from spec_kitty_events import CANONICAL_TO_SYNC_V1` works
- [ ] `from spec_kitty_events import canonical_to_sync_v1` works

### T005: Unit tests for SyncLaneV1 and mapping

**Purpose**: Comprehensive unit tests proving the mapping contract is correct.

**Steps**:
1. Create `tests/unit/test_sync_lane.py`.
2. Test cases:
   - `test_sync_lane_v1_has_exactly_four_members`: Assert `len(SyncLaneV1) == 4`.
   - `test_sync_lane_v1_values`: Assert each member's string value.
   - `test_canonical_to_sync_v1_mapping_completeness`: Assert all 7 `Lane` members are in `CANONICAL_TO_SYNC_V1`.
   - `test_canonical_to_sync_v1_specific_mappings`: Test each of the 7 mappings explicitly.
   - `test_canonical_to_sync_v1_function`: Test the function returns the same as the dict lookup.
   - `test_canonical_to_sync_v1_immutable`: Assert `CANONICAL_TO_SYNC_V1` cannot be mutated.
   - `test_canonical_to_sync_v1_output_values_are_sync_lane`: Assert all output values are `SyncLaneV1` instances.

**Validation**:
- [ ] All tests pass with `python3.11 -m pytest tests/unit/test_sync_lane.py -v`
- [ ] No mypy errors

### T006: Property tests for mapping determinism

**Purpose**: Use Hypothesis to prove the mapping is deterministic and total.

**Steps**:
1. Create `tests/property/test_lane_mapping_determinism.py`.
2. Property tests:
   - `test_canonical_to_sync_v1_is_total`: For any `Lane` member, `canonical_to_sync_v1` returns a `SyncLaneV1`.
   - `test_canonical_to_sync_v1_is_deterministic`: Same input always returns same output (test across multiple calls).
   - `test_all_sync_lane_values_reachable`: At least one canonical lane maps to each `SyncLaneV1` member.
3. Use `hypothesis.strategies.sampled_from(list(Lane))` for lane generation.
4. Use `@settings(max_examples=200)` to match existing property test convention.

**Validation**:
- [ ] All property tests pass with `python3.11 -m pytest tests/property/test_lane_mapping_determinism.py -v`
- [ ] No mypy errors

## Definition of Done

- [ ] `SyncLaneV1` enum with 4 values exists in `status.py`
- [ ] `CANONICAL_TO_SYNC_V1` is an immutable `MappingProxyType` with all 7 lanes mapped
- [ ] `canonical_to_sync_v1()` function works and passes mypy
- [ ] All three symbols are exported from `__init__.py` and in `__all__`
- [ ] Unit tests pass: `python3.11 -m pytest tests/unit/test_sync_lane.py -v`
- [ ] Property tests pass: `python3.11 -m pytest tests/property/test_lane_mapping_determinism.py -v`
- [ ] `mypy --strict src/spec_kitty_events/status.py src/spec_kitty_events/__init__.py` passes
- [ ] Full test suite still passes: `python3.11 -m pytest`

## Risks

- **MappingProxyType and mypy**: Ensure the type annotation `MappingProxyType[Lane, SyncLaneV1]` satisfies `mypy --strict`. If mypy complains, use `Mapping[Lane, SyncLaneV1]` for the annotation and `MappingProxyType(...)` for the value.
- **Import ordering**: `SyncLaneV1` must be defined after `Lane` in `status.py` since it doesn't depend on it, but logically they're related.

## Reviewer Guidance

- Verify the exact mapping table matches the contract: `PLANNED→PLANNED`, `CLAIMED→PLANNED`, `IN_PROGRESS→DOING`, `FOR_REVIEW→FOR_REVIEW`, `DONE→DONE`, `BLOCKED→DOING`, `CANCELED→PLANNED`.
- Verify immutability: `CANONICAL_TO_SYNC_V1` should be a `MappingProxyType`, not a regular dict.
- Verify completeness: All 7 `Lane` members must be in the mapping — no missing keys.

## Activity Log

- 2026-02-12T10:21:10Z – claude-opus – shell_pid=54078 – lane=doing – Assigned agent via workflow command
- 2026-02-12T10:22:09Z – claude-opus – shell_pid=54078 – lane=for_review – Ready for review: SyncLaneV1 enum, CANONICAL_TO_SYNC_V1 mapping, canonical_to_sync_v1() function, unit + property tests. All 13 tests pass, mypy clean.
