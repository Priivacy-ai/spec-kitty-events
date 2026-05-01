---
work_package_id: WP01
title: Lane Vocabulary Canonicalization
dependencies: []
requirement_refs:
- C-002
- FR-001
- FR-002
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-teamspace-event-contract-foundation-01KQHDE4
base_commit: b7ae7279397452a13380a891073e76b50054060a
created_at: '2026-05-01T09:58:40.631429+00:00'
subtasks:
- T001
- T002
- T003
- T004
agent: "codex:gpt-5:reviewer-rachel:reviewer"
shell_pid: "3544"
history:
- event: created
  at: '2026-05-01T09:44:26Z'
  by: /spec-kitty.tasks
agent_profile: implementer-ivan
authoritative_surface: src/spec_kitty_events/status.py
execution_mode: code_change
owned_files:
- src/spec_kitty_events/status.py
- tests/test_lane_vocabulary.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your agent profile:

```
/ad-hoc-profile-load implementer-ivan
```

That profile sets the implementation identity, governance scope, boundaries, and initialization declaration for this work package.

---

## Objective

Make `in_review` a canonical work-package lane in `spec-kitty-events`. Today the package treats `in_review` as **invalid**; this WP flips it to canonical so envelopes referencing the lane validate. Establish a single-source-of-truth test that asserts the canonical lane vocabulary cannot drift, and clean up legacy fixtures and tests that asserted `in_review` was invalid.

This is the foundation WP. Every other WP depends on this directly or transitively.

---

## Context

- Spec: [spec.md](../spec.md) — FR-001, FR-002, C-002, C-004, SC-003.
- Contract: [contracts/lane-vocabulary.md](../contracts/lane-vocabulary.md).
- Decision: `in_review` stays canonical (recorded in [spec.md](../spec.md) Assumptions).
- Existing state: `src/spec_kitty_events/status.py` defines a `Lane` enum (line ~17). Conformance fixtures explicitly mark `in_review` as INVALID:
  - `src/spec_kitty_events/conformance/fixtures/lane_mapping/invalid/unknown_lanes.json` includes `"canonical": "in_review"`
  - `src/spec_kitty_events/conformance/fixtures/events/invalid/wp_status_changed_invalid_lane.json` has `"to_lane": "in_review"`
  - `src/spec_kitty_events/conformance/fixtures/manifest.json` has a fixture entry with note `"StatusTransitionPayload with invalid to_lane value 'in_review'"`

These artifacts must move; the lane is now canonical.

---

## Subtasks

### T001 — Add `IN_REVIEW` to the `Lane` enum

**Purpose**: Make `in_review` a member of the canonical `Lane` enum so payload validation accepts it.

**Steps**:
1. Read `src/spec_kitty_events/status.py` and locate `class Lane(str, Enum):` (around line 17).
2. Add `IN_REVIEW = "in_review"` as a new enum member. Place it in the natural ordering position relative to the existing lanes (typically between `IN_PROGRESS` and `REVIEW` if those exist, or wherever the existing convention dictates).
3. If there is a transition map or allowed-transition list elsewhere in `status.py` or in `src/spec_kitty_events/lifecycle.py`, add the natural transitions involving `IN_REVIEW`:
   - `IN_PROGRESS → IN_REVIEW`
   - `IN_REVIEW → REVIEW` (if `REVIEW` exists as a separate terminal-pending lane)
   - `IN_REVIEW → IN_PROGRESS` (rejection path)
   - `IN_REVIEW → DONE` (if direct close-after-review is supported)
4. Verify the new enum member is exported via `src/spec_kitty_events/__init__.py` if `Lane` itself is exported.

**Files**:
- `src/spec_kitty_events/status.py` (modified, ~5–10 lines added)

**Validation**:
- [ ] `Lane.IN_REVIEW` is importable from `spec_kitty_events`.
- [ ] `Lane.IN_REVIEW.value == "in_review"`.
- [ ] Existing tests do not regress.

---

### T002 — Move `in_review` out of "invalid lane" fixtures

**Purpose**: Stop misclassifying `in_review` as an invalid lane.

**Steps**:
1. Edit `src/spec_kitty_events/conformance/fixtures/lane_mapping/invalid/unknown_lanes.json`:
   - Remove the entry that has `"canonical": "in_review"` (or the equivalent entry treating `in_review` as unknown).
   - If the file becomes empty after removal, leave the JSON structure as `{}` or `[]` consistent with the file's existing top-level shape; do not delete the file in this WP — fixture content elsewhere will be reorganized in WP05.
2. Delete or move `src/spec_kitty_events/conformance/fixtures/events/invalid/wp_status_changed_invalid_lane.json`:
   - The cleanest path is to delete it here (the fixture is no longer truthful).
   - If the file is referenced by `manifest.json`, update the manifest entry: either remove the entry or change it to reference a different invalid case (e.g., a truly unknown lane like `"to_lane": "blocked"` — author the replacement file in `events/invalid/` if needed; this is acceptable inline work for this WP).
3. Update `src/spec_kitty_events/conformance/fixtures/manifest.json` accordingly:
   - Remove or rewrite the entry whose `notes` field says `"StatusTransitionPayload with invalid to_lane value 'in_review'"`.
   - Keep the manifest valid JSON.

**Files**:
- `src/spec_kitty_events/conformance/fixtures/lane_mapping/invalid/unknown_lanes.json` (modified)
- `src/spec_kitty_events/conformance/fixtures/events/invalid/wp_status_changed_invalid_lane.json` (deleted or rewritten)
- `src/spec_kitty_events/conformance/fixtures/manifest.json` (modified)

**Validation**:
- [ ] Manifest is valid JSON.
- [ ] No fixture remains that asserts `in_review` is invalid.
- [ ] Conformance test runner does not error on the moved/deleted entries (run any existing conformance test pre-WP05).

---

### T003 — Author `tests/test_lane_vocabulary.py`

**Purpose**: Pin the canonical lane vocabulary as a single source of truth and assert `Lane.IN_REVIEW` is canonical.

**Steps**:
1. Create `tests/test_lane_vocabulary.py` (new file).
2. Add three tests:

   ```python
   from spec_kitty_events import Lane

   EXPECTED_CANONICAL_LANES = frozenset({
       # the full set of Lane enum values, including IN_REVIEW
       # (read the actual enum and pin them here)
   })

   def test_in_review_is_canonical():
       assert Lane.IN_REVIEW.value == "in_review"
       assert Lane.IN_REVIEW in Lane

   def test_canonical_lane_set_is_pinned():
       """Asserts the canonical lane set has not silently drifted."""
       actual = frozenset(member.value for member in Lane)
       assert actual == EXPECTED_CANONICAL_LANES, (
           f"Lane vocabulary drifted. New: {actual - EXPECTED_CANONICAL_LANES}, "
           f"Removed: {EXPECTED_CANONICAL_LANES - actual}"
       )

   def test_lane_vocabulary_is_single_source_of_truth():
       """No duplicate lane definition exists elsewhere in the package."""
       # Static check: scan src/spec_kitty_events for other str-Enum subclasses
       # whose values overlap with Lane values, or for hand-rolled lane lists.
       # Implementation: walk the package's Python files, parse, and assert.
       # If a lighter implementation is preferred, scan for the literal "in_review"
       # in source files outside status.py and assert occurrences are documented.
       ...
   ```

3. Implement the third test using a simple AST or text scan; the goal is that a future contributor cannot quietly add a parallel lane list.

**Files**:
- `tests/test_lane_vocabulary.py` (new, ~80–120 lines including imports and helpers)

**Validation**:
- [ ] All three tests pass.
- [ ] The pinned set explicitly includes `"in_review"`.
- [ ] The single-source-of-truth test fails if someone later adds a duplicate lane constant (manually verify by introducing a test mutation locally and confirming a failure, then remove the mutation).

---

### T004 — Update existing tests that asserted `in_review` was invalid

**Purpose**: Catch the long tail of tests that were written under the old assumption.

**Steps**:
1. Grep the repository for `"in_review"` and `"in-review"` in `tests/`, `src/spec_kitty_events/`, and `kitty-specs/`:
   ```
   grep -rn '"in_review"' tests/ src/ kitty-specs/
   ```
2. For each match, decide:
   - If the test or fixture treats `in_review` as **invalid** → update so it treats `in_review` as **canonical** (move it from a rejection assertion to an acceptance assertion). Adjust the surrounding assertion accordingly.
   - If the test references `in_review` as part of an existing valid scenario → no change needed.
3. Run the existing pytest suite locally and confirm no regressions remain.

**Files**:
- Various test files identified by grep (modified as needed).
- Some fixture files may need touching if they were not covered by T002.

**Validation**:
- [ ] `pytest` is green.
- [ ] No `assert ... not in ... in_review` or equivalent rejection pattern remains.

---

## Branch Strategy

- Planning/base branch: `main`
- Merge target: `main`
- This WP runs in a worktree allocated by `finalize-tasks` (lane assignment computed from `lanes.json`). Do not branch manually.

---

## Definition of Done

- [ ] `Lane.IN_REVIEW` is a member of the canonical `Lane` enum and `Lane.IN_REVIEW.value == "in_review"`.
- [ ] Every fixture and test that previously asserted `in_review` was invalid now asserts canonical-or-removed.
- [ ] `tests/test_lane_vocabulary.py` exists with the three tests above and is green.
- [ ] Full `pytest` is green.
- [ ] `mypy --strict` is green for `src/spec_kitty_events/status.py`.
- [ ] No file outside `owned_files` was modified.

---

## Risks

- **R-1**: A test elsewhere assumes `in_review` is rejected and now silently passes for the wrong reason. Mitigation: T004's grep-and-fix pass is exhaustive; review failures in CI carefully if they come up.
- **R-2**: Adding a new enum member changes the enum's hash/order in subtle ways for code that switches on `member` identity. Mitigation: the package documents that consumers should compare to `Lane.X` constants, not iterate by index.

---

## Reviewer Guidance

The Codex reviewer will check:

1. The enum addition is in the natural ordering position.
2. Transition rules involving `IN_REVIEW` are coherent with the existing transition graph.
3. No fixture remains that asserts `in_review` is invalid.
4. The single-source-of-truth test is non-trivial (it would catch a real drift, not just a typo).
5. Imports of `Lane` from `spec_kitty_events` (not from internal submodules) are preserved at the public API boundary.

## Activity Log

- 2026-05-01T10:06:46Z – claude – shell_pid=77568 – Ready for review: Lane.IN_REVIEW added; lane vocabulary tests authored
- 2026-05-01T10:07:15Z – codex:gpt-5:reviewer-rachel:reviewer – shell_pid=3544 – Started review via action command
