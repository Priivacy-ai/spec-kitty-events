---
work_package_id: WP02
title: Family Tests + Quality Gates
dependencies:
- WP01
requirement_refs:
- FR-007
- FR-008
- FR-012
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this mission were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T005
- T006
- T009
- T010
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "98387"
history:
- timestamp: '2026-05-17T14:30:00Z'
  actor: planner
  action: created
  note: Initial WP02 prompt drafted by /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: tests/unit/
execution_mode: code_change
mission_slug: backward-transition-contract-01KRV52C
owned_files:
- tests/unit/test_status.py
- tests/unit/test_fixtures.py
priority: P1
role: implementer
tags: []
---

# WP02 — Family Tests + Quality Gates

## ⚡ Do This First: Load Agent Profile

**STOP. Before reading anything else, load your assigned profile.**

```
/ad-hoc-profile-load python-pedro
```

This profile identifies you as a Python implementer with pytest + Pydantic expertise. Confirm the initialization declaration before proceeding.

## Objective

Register the three new conformance fixtures (landed by WP01) in `tests/unit/test_fixtures.py` parametrize lists, add a parametrized `TestReviewRejectionFamily` class in `tests/unit/test_status.py` that enumerates the four family members, then verify the three charter quality gates (full unit suite, mypy --strict, schema-diff zero).

## Context

WP01 landed three fixtures under `src/spec_kitty_events/conformance/fixtures/edge_cases/`. This WP makes the contract assertions that codify the review-rejection family as a tested property of the canonical `WPStatusChanged` validator. Sibling missions in `spec-kitty` (CLI emit path) and `spec-kitty-saas` (materializer + drain) cite these tests as the conformance behavior they must mirror.

Read first:

- WP01 prompt: `kitty-specs/backward-transition-contract-01KRV52C/tasks/WP01-conformance-fixtures.md` (what fixtures look like)
- Mission spec: `kitty-specs/backward-transition-contract-01KRV52C/spec.md` (FR-007, FR-008, FR-012)
- Contract draft: `kitty-specs/backward-transition-contract-01KRV52C/contracts/backward-transition-family.md`
- Existing test file structure: `tests/unit/test_fixtures.py` (parametrize list pattern: `VALID_EVENT_FILES = [(path, event_type), ...]`)
- Existing tests for `StatusTransitionPayload` validation: `tests/unit/test_status.py` (TestForceMetadata, force_must_be_true, force_requires_reason, force_with_reason_valid, force_with_empty_reason_rejected, forced_done_still_requires_evidence, forced_done_with_evidence_valid)

## Branch Strategy

- Planning/base branch: `main`
- Merge target: `main`
- Lane: assigned by `finalize-tasks`; depends on WP01 approval.

## Subtasks

### T005 — Register edge_cases fixtures in `tests/unit/test_fixtures.py`

**Purpose**: Make the three new fixtures part of the standing parametrized test suite so the loader contract is enforced and the negative case is asserted to fail validation.

**Steps**:

1. Read the existing `test_fixtures.py` to confirm the parametrize-list patterns (search `VALID_EVENT_FILES`, `INVALID_*`, or whichever lists enumerate fixtures).
2. Append to the `VALID_EVENT_FILES` list (defined at `tests/unit/test_fixtures.py:~84` and consumed by `TestValidEventFixtures.test_valid_fixture_is_valid_json`, `..._passes_model`, and `..._passes_conformance`):
   - `("edge_cases/valid/wp_status_changed_approved_rewind.json", "WPStatusChanged")`
3. Append to the `INVALID_EVENT_FILES` list (defined at `tests/unit/test_fixtures.py:121` and consumed by `test_invalid_fixture_fails_model` and `test_invalid_fixture_fails_conformance`):
   - `("edge_cases/invalid/wp_status_changed_unforced_in_review_to_planned.json", "WPStatusChanged")`
4. Add a new test class `TestReviewRejectionCycle` that calls `load_replay_stream("wp-review-rejection-cycle-replay")` and:
   - Asserts the stream has exactly 11 events.
   - For each event, validates the payload via `_EVENT_TYPE_TO_MODEL["WPStatusChanged"]`.
   - Asserts Lamport clocks are strictly increasing 1..11.
   - Asserts event with `lamport_clock == 6` has `payload["force"] is True` and `payload["reason"].startswith("backward rewind: in_review -> planned")`.
   - Asserts all other events have `payload["force"] is False`.

**Files**:

- `tests/unit/test_fixtures.py` (MODIFY — additive list entries + new test class)

**Validation**:

- [ ] `uv run pytest tests/unit/test_fixtures.py -q` passes including the new entries.
- [ ] `uv run pytest tests/unit/test_fixtures.py::TestReviewRejectionCycle -q` passes.
- [ ] The negative-fixture entry causes the appropriate parametrized invalid-fixture test to assert "this fixture is correctly classified as invalid".

### T006 — Add `TestReviewRejectionFamily` class in `tests/unit/test_status.py`

**Purpose**: Codify the review-rejection family (`{in_progress, for_review, in_review, approved} → planned`) as parametrized contract behavior of `validate_transition()` and `StatusTransitionPayload`.

**Steps**:

1. Read `tests/unit/test_status.py` to confirm imports and `VALID_TRANSITION_DATA` (or equivalent) base dict structure.
2. Add a new class `TestReviewRejectionFamily` with these parametrized tests (use `@pytest.mark.parametrize("from_lane", ["in_progress", "for_review", "in_review", "approved"])`). The validator returns a frozen `TransitionValidationResult` dataclass with two fields: `valid: bool` and `violations: tuple[str, ...]` (defined at `src/spec_kitty_events/status.py:372`). The assertion shape is:

   - `test_forced_backward_with_reason_accepted(from_lane)` — build a `StatusTransitionPayload` with `from_lane → planned`, `force=True`, `reason="backward rewind: <from> -> planned"`. Call `result = validate_transition(payload)`. Assert `result.valid is True` and `result.violations == ()`.
   - `test_unforced_backward_rejected(from_lane)` — same payload shape but `force=False, reason=None`. Call `result = validate_transition(payload)`. Assert `result.valid is False` and `len(result.violations) >= 1`. (Diagnostic strings can include the lane pair or the word "force"; do not over-specify the exact wording in the assertion — match a substring like `assert any("force" in v or from_lane in v for v in result.violations)`.)
   - `test_forced_backward_without_reason_rejected(from_lane)` — Pydantic `ValidationError` expected at model construction time because the `StatusTransitionPayload` model validator enforces `force=True requires a non-empty reason`. Use `pytest.raises(pydantic.ValidationError, match="force=True requires")` (matches existing test at line 438-440 of `test_status.py`).
   - `test_forced_backward_with_empty_reason_rejected(from_lane)` — same as above but with `reason=""`.

3. Cross-link the contract anchor in a class docstring:

```python
class TestReviewRejectionFamily:
    """Contract behavior for the review-rejection transition family.

    See: src/spec_kitty_events/status.py module docstring
         docs/consumer-contract-dossier-v2.4.0.md § "Backward Transitions: The Review-Rejection Family"
         kitty-specs/backward-transition-contract-01KRV52C/contracts/backward-transition-family.md
    """
```

**Files**:

- `tests/unit/test_status.py` (MODIFY — additive test class)

**Validation**:

- [ ] `uv run pytest tests/unit/test_status.py::TestReviewRejectionFamily -q` passes.
- [ ] The test class produces 16 test points (4 from_lanes × 4 test methods).
- [ ] No existing test in `tests/unit/test_status.py` regresses.

### T009 — Schema generation: zero diff

**Purpose**: Confirm that adding conformance fixtures does not regenerate or change any committed JSON schema (NFR-004, NFR-005, SC-005).

**Steps**:

1. Run the schema generator in CI/check mode (the generator at `src/spec_kitty_events/schemas/generate.py` accepts a `--check` flag that detects drift without writing files):

```bash
uv run python src/spec_kitty_events/schemas/generate.py --check
```

   Expected exit code: 0. A non-zero exit indicates schema drift.

2. As a redundant verification, run without `--check` and confirm zero working-tree changes:

```bash
uv run python src/spec_kitty_events/schemas/generate.py
git diff --stat src/spec_kitty_events/schemas/
```

   Expected output of `git diff --stat`: **empty** (zero lines, no files changed).

3. If `--check` exits non-zero or `git diff --stat` is non-empty: the change reveals a previously hidden coupling. Investigate by examining the diff — most likely a Pydantic model picked up an indirect change. Surface this in the activity log and resolve with WP01 author before continuing.

**Files**:

- None modified. This is a verification step.

**Validation**:

- [ ] `git diff --stat src/spec_kitty_events/schemas/` is empty after running schema generation.
- [ ] If the project uses a `make schemas` or similar target instead of direct module execution, the equivalent target was run and produced zero diff.

### T010 — Full unit suite + mypy --strict

**Purpose**: Confirm the two standing charter quality gates hold (SC-004).

**Steps**:

1. From repo root (or the lane worktree):

```bash
cd /Users/robert/spec-kitty-dev/spec-kitty-20260517-161351-nNtfEd/spec-kitty-events
uv run pytest tests/unit/ -q
```

   Expected: exit code 0.

2. Run:

```bash
uv run mypy --strict src/spec_kitty_events/
```

   Expected: exit code 0.

3. If mypy complains about the new test additions (parametrize tuple types, for instance), conform to the existing convention in `test_fixtures.py` — typed parametrize fixtures using `tuple[str, str]` shapes are common in this repo; check before introducing `# type: ignore`.

**Files**:

- None modified. This is a verification step.

**Validation**:

- [ ] `uv run pytest tests/unit/ -q` exit 0.
- [ ] `uv run mypy --strict src/spec_kitty_events/` exit 0.
- [ ] Wall-clock time for the targeted subset (`tests/unit/test_status.py tests/unit/test_fixtures.py`) is under 10 seconds (NFR-001).

## Integration Verification

After T005 + T006 land:

```bash
uv run pytest tests/unit/test_status.py tests/unit/test_fixtures.py -q
```

Both files green. The `TestReviewRejectionFamily` class adds 16 test points; the `TestReviewRejectionCycle` adds at least 11 (one per event). The negative-fixture entry surfaces in the invalid-fixture parametrize sweep.

After all four subtasks land, the full mission gates pass:

```bash
uv run pytest tests/unit/ -q                # SC-004
uv run mypy --strict src/spec_kitty_events/  # charter gate
git diff --stat src/spec_kitty_events/schemas/  # SC-005 — must be empty
```

## Definition of Done

- [ ] `test_fixtures.py` lists the two new single-event fixtures.
- [ ] `TestReviewRejectionCycle` added to `test_fixtures.py` and green.
- [ ] `TestReviewRejectionFamily` added to `test_status.py` and green.
- [ ] Schema diff is empty after running the generator (recorded in commit message or activity log).
- [ ] Full unit suite passes.
- [ ] mypy --strict passes.
- [ ] WP frontmatter `lane` advanced to `for_review` with note: `"Tests + gates landed; schema diff empty; mypy strict clean"`.
- [ ] Git commit message: `test(WP02): add review-rejection family tests + verify charter gates`.

## Risks

| Risk | Mitigation |
|---|---|
| Existing `test_fixtures.py` has multiple parametrize lists for different validation steps — picking the wrong one | Read carefully; the file currently has at least 3 parametrize lists per fixture (valid JSON, passes model, passes conformance). Append to each that enumerates fixtures by path. |
| `validate_transition()` signature differs from what the test assumes | Cross-check the existing tests at `test_status.py:438+` for the actual signature and assertion style; mirror that exactly. |
| Schema-diff non-empty reveals coupling | Loop back to WP01 author. Do not "fix" by committing the new schema diff — the change reveals a bug. |
| mypy --strict failure on parametrize tuple types | Existing `test_fixtures.py` uses simple `(str, str)` tuples without explicit annotation — mirror that. |
| Replay-stream loader returns the raw envelope dicts, not just payloads | Confirmed from research.md: `load_replay_stream` returns `List[Dict[str, Any]]` where each dict is the full envelope. Access `event["payload"]["force"]` etc. |

## Reviewer Guidance

A reviewer should:

1. Confirm the new parametrize list entries match the existing tuple shape exactly.
2. Confirm `TestReviewRejectionFamily` enumerates all 4 family members and all 4 test methods.
3. Spot-check that the unforced-backward fixture is asserted invalid by the conformance validator path (not just by a JSON-syntax check).
4. Confirm the schema-diff verification was actually run (commit message or activity log mentions empty diff).
5. Confirm no test was marked `xfail` or `skip` — the contract is binary.
6. Confirm `force=True + reason=None` and `force=True + reason=""` both reject with the existing error message regex `"force=True requires"`.

## Activity Log

- 2026-05-17T15:00:13Z – claude:opus:python-pedro:implementer – shell_pid=92569 – Started implementation via action command
- 2026-05-17T15:09:19Z – claude:opus:python-pedro:implementer – shell_pid=92569 – Family tests + cycle test land; schema diff empty; pytest + mypy clean; targeted run within NFR-001 budget
- 2026-05-17T15:10:17Z – claude:opus:reviewer-renata:reviewer – shell_pid=98387 – Started review via action command
