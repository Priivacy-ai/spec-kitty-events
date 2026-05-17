# Tasks: Backward-Transition Contract

**Mission**: backward-transition-contract-01KRV52C
**Mid8**: 01KRV52C
**Target branch**: main
**Plan**: [plan.md](./plan.md) — Spec: [spec.md](./spec.md) — Research: [research.md](./research.md) — Data model: [data-model.md](./data-model.md) — Contracts: [contracts/backward-transition-family.md](./contracts/backward-transition-family.md) — Quickstart: [quickstart.md](./quickstart.md)

This mission lands the contract source of truth for the review-rejection transition family. Work is small and tightly scoped: three new JSON/JSONL conformance fixtures + manifest update, family tests, and matching normative documentation in two anchor locations.

## Subtask Index

| ID | Description | WP | Parallel |
|---|---|---|---|
| T001 | Author `edge_cases/replay/wp_review_rejection_cycle.jsonl` (review-rejection cycle replay stream) | WP01 | [P] |
| T002 | Author `edge_cases/valid/wp_status_changed_approved_rewind.json` (positive single — approved rewind) | WP01 | [P] |
| T003 | Author `edge_cases/invalid/wp_status_changed_unforced_in_review_to_planned.json` (negative single — unforced backward) | WP01 | [P] |
| T004 | Register all three fixtures in `src/spec_kitty_events/conformance/fixtures/manifest.json` | WP01 |  |
| T005 | Register new edge_cases fixtures in `tests/unit/test_fixtures.py` parametrize lists (positive + negative) | WP02 |  |
| T006 | Add review-rejection family tests in `tests/unit/test_status.py` (parametrized over 4 family members) | WP02 |  |
| T007 | Add normative "Review-Rejection Transition Family" section to `src/spec_kitty_events/status.py` module docstring | WP03 | [P] |
| T008 | Add normative section "Backward Transitions: The Review-Rejection Family" to `docs/consumer-contract-dossier-v2.4.0.md` | WP03 |  |
| T009 | Run schema generation, confirm zero diff against committed `*.schema.json` files | WP02 |  |
| T010 | Run `uv run pytest tests/unit/ -q` and `uv run mypy --strict src/spec_kitty_events/` — verify both pass | WP02 |  |

The `[P]` marker in the Parallel column indicates the subtask can be authored in parallel with sibling subtasks within the same WP (different files). It is not a tracking signal.

## Work Packages

### WP01 — Conformance Fixtures + Manifest

**Goal**: Land three synthetic JSON/JSONL conformance fixtures that exemplify the review-rejection transition family (one cycle replay stream, one positive single-event, one negative single-event) and register them in the conformance manifest.

**Priority**: P1 (foundation — WP02 depends on these fixtures).

**Independent test**: After this WP, the following commands all return non-empty results:
- `python -c "from spec_kitty_events.conformance.loader import load_replay_stream; print(len(load_replay_stream('wp-review-rejection-cycle-replay')))"`
- `python -c "from spec_kitty_events.conformance import load_fixtures; ids = {fc.id for fc in load_fixtures('edge_cases')}; print(set(['wp-status-changed-approved-rewind-valid','wp-status-changed-unforced-in-review-to-planned-invalid']).issubset(ids))"`

**Included subtasks**:
- [x] T001 Author `edge_cases/replay/wp_review_rejection_cycle.jsonl` — full canonical Event-envelope JSONL with monotonic Lamport clocks, synthetic event ids, one full review-rejection round-trip
- [x] T002 Author `edge_cases/valid/wp_status_changed_approved_rewind.json` — single `WPStatusChanged` payload mirroring the planning#16 evidence shape but synthetic, with `force=True + reason` per FR-010 shape
- [x] T003 Author `edge_cases/invalid/wp_status_changed_unforced_in_review_to_planned.json` — single `WPStatusChanged` payload with `from_lane=in_review, to_lane=planned, force=False` (validator MUST reject)
- [x] T004 Register all three in `src/spec_kitty_events/conformance/fixtures/manifest.json` with stable `id` values

**Implementation sketch**:
1. Match existing `wp_status_changed.json` field shape exactly for T002 and T003 (consistent wire shape).
2. Use deterministic event ids of the form `01KCYCLE000000000000000NNN`. Use a synthetic mission slug `mission-backward-transition-demo`. Synthetic WP id `WP01`. Synthetic team `synthetic-team`.
3. JSONL ordering for T001: `planned → claimed → in_progress → for_review → in_review → planned (force=True) → claimed → in_progress → for_review → in_review → approved` (11 events). Lamport clocks 1..11.
4. Manifest entries follow the `id`/`path`/`expected_result`/`event_type`/`notes`/`min_version` (`fixture_type` for the replay stream) shape of existing entries. Use `min_version: "3.0.0"` to mark new fixtures introduced in this release line.

**Parallel opportunities**: T001/T002/T003 all touch different new files — fully parallel. T004 is the only sequential subtask (touches existing manifest.json).

**Dependencies**: None (independent foundation).

**Risks**:
- Lamport clock ordering subtlety — the cycle must have strictly increasing Lamport clocks across all events (matches existing replay stream convention).
- Manifest JSON formatting — preserve existing indentation, trailing-comma rules, and final-newline behavior or schema-drift tooling may complain.

**Estimated prompt size**: ~350 lines.

**Owned files**:
- `src/spec_kitty_events/conformance/fixtures/edge_cases/replay/wp_review_rejection_cycle.jsonl` (new)
- `src/spec_kitty_events/conformance/fixtures/edge_cases/valid/wp_status_changed_approved_rewind.json` (new)
- `src/spec_kitty_events/conformance/fixtures/edge_cases/invalid/wp_status_changed_unforced_in_review_to_planned.json` (new)
- `src/spec_kitty_events/conformance/fixtures/manifest.json` (modify — additive entries only)

### WP02 — Family Tests + Quality Gates

**Goal**: Register the new fixtures in test parametrize lists, add review-rejection family tests over the four family members in `test_status.py`, and verify charter quality gates (schema diff, full unit suite, mypy --strict).

**Priority**: P1 (consumes WP01 outputs; runs the contract assertions that make the mission's value testable).

**Independent test**: `uv run pytest tests/unit/test_status.py tests/unit/test_fixtures.py -q` exit code is 0. The full unit suite `uv run pytest tests/unit/ -q` also exits 0. `uv run mypy --strict src/spec_kitty_events/` exits 0. Schema diff produces zero changes after `python -m spec_kitty_events.schemas.generate` (or equivalent).

**Included subtasks**:
- [x] T005 Register new edge_cases fixtures in `tests/unit/test_fixtures.py` (add entries to the parametrize lists for valid + invalid; add a replay-stream loader test for the cycle JSONL)
- [x] T006 Add review-rejection family tests in `tests/unit/test_status.py` — parametrized over `{(in_progress, planned), (for_review, planned), (in_review, planned), (approved, planned)}`, asserting accept with `force=True + reason`, reject with `force=False`, reject with `force=True + empty reason`
- [x] T009 Run schema generation, confirm zero diff against committed `*.schema.json` files (charter quality gate)
- [x] T010 Run `uv run pytest tests/unit/ -q` and `uv run mypy --strict src/spec_kitty_events/` — verify both pass (charter quality gates)

**Implementation sketch**:
1. Read existing `tests/unit/test_fixtures.py` parametrize lists (`VALID_EVENT_FILES` and the equivalent invalid list) and append new entries with the matching tuple shape.
2. For the cycle replay stream test, add a new test class or method `TestReviewRejectionCycle` that calls `load_replay_stream('wp-review-rejection-cycle-replay')` and validates each event payload via `_EVENT_TYPE_TO_MODEL["WPStatusChanged"]`.
3. For T006, add a parametrized test class `TestReviewRejectionFamily` in `tests/unit/test_status.py` enumerating the four family members. Use the existing test data style (`VALID_TRANSITION_DATA` extension or per-test dict).
4. For T009/T010, run the gates locally and report; if schema diff is non-empty, investigate (the plan/research assert it should be empty).

**Parallel opportunities**: T005 and T006 touch different files (`test_fixtures.py` vs `test_status.py`) — parallel. T009 and T010 are validation steps that run after T005/T006 land.

**Dependencies**: WP01 (loads the fixtures registered by WP01 manifest entries).

**Risks**:
- A schema-drift detection in T009 would indicate a genuine bug in WP01 (e.g., introducing a previously absent field shape). Resolve by re-checking the fixture JSON against the model.
- `mypy --strict` failures often come from missing `# type: ignore` on parametrize tuples — match the existing convention in `test_fixtures.py`.

**Estimated prompt size**: ~450 lines.

**Owned files**:
- `tests/unit/test_status.py` (modify — additive test classes)
- `tests/unit/test_fixtures.py` (modify — additive parametrize entries + new test class)

### WP03 — Normative Documentation

**Goal**: Land the normative review-rejection family documentation in the two stable anchor locations (`status.py` module docstring + `docs/consumer-contract-dossier-v2.4.0.md`) with mutual cross-links and references to the new fixtures.

**Priority**: P1 (without these anchors, sibling missions in `spec-kitty` and `spec-kitty-saas` have no stable URL/path to cite).

**Independent test**: A reviewer who has never read the planning#16 issue can read `src/spec_kitty_events/status.py`'s top-of-file docstring plus the new section in `docs/consumer-contract-dossier-v2.4.0.md` and answer the question "what does a legitimate review-rejection event look like on the wire?" in under two minutes (FR-011, SC-001).

**Included subtasks**:
- [x] T007 Add normative "Review-Rejection Transition Family" section to `src/spec_kitty_events/status.py` module docstring — section content drawn from `contracts/backward-transition-family.md` (Sections 1–7), cross-link to docs file and fixture filenames
- [x] T008 Add normative section "Backward Transitions: The Review-Rejection Family" to `docs/consumer-contract-dossier-v2.4.0.md` — same Sections 1–7 content as the docstring, cross-link back to `status.py` and fixture paths

**Implementation sketch**:
1. Use `contracts/backward-transition-family.md` as the source-of-truth draft for both anchors. The docstring version is markdown-with-`>>>`-style indentation if needed; the docs file gets the markdown verbatim.
2. In `status.py`: place the section at the top of the module docstring (after the existing one-line summary, before any imports). Use markdown heading `## Review-Rejection Transition Family` (Python tooling renders it fine).
3. In `docs/consumer-contract-dossier-v2.4.0.md`: append the section in the appropriate place (likely after existing "Status / Lane Transitions" content, or at the end if no such section exists — explorer choice during implementation).
4. Confirm cross-links use relative paths.

**Parallel opportunities**: T007 and T008 touch different files — parallel.

**Dependencies**: None.

**Note on fixture filename references**: T007/T008 reference fixture filenames by string. Those filenames are decided in this mission's plan (`plan.md` and `tasks/WP01-conformance-fixtures.md`) and do not require WP01 to land first — the documentation can be authored against the planned filenames.

**Risks**:
- Module docstring location — Python convention is the docstring is the first statement in the file. The new section must be inside the existing docstring or replace its content. Don't accidentally break import behavior by mis-placing triple-quotes.
- Cross-link drift — relative path from `status.py` to `docs/consumer-contract-dossier-v2.4.0.md` is `../../docs/consumer-contract-dossier-v2.4.0.md`. Confirm before committing.

**Estimated prompt size**: ~300 lines.

**Owned files**:
- `src/spec_kitty_events/status.py` (modify — docstring only; no behavior change to any function or class)
- `docs/consumer-contract-dossier-v2.4.0.md` (modify — additive section)

## Execution Order

```
WP01 (fixtures) ─┐
                 ├──→ WP02 (tests + gates) ──→ Mission Review / Merge
WP03 (docs) ─────┘
```

- WP01 and WP03 are independent — dispatch in parallel.
- WP02 depends on WP01 (loads fixtures registered by WP01 manifest).
- WP02 can also be dispatched immediately after WP01 even if WP03 is still in flight; the family tests do not depend on docstring content.

## MVP Scope Recommendation

WP01 + WP02 (fixtures + tests) is the minimum that delivers verifiable contract behavior. WP03 (docs) is required for sibling-mission consumption and is non-skippable — but it can ship in a follow-up commit if absolutely needed. The plan ships all three in one mission.

## Requirement Coverage (will be normalized by `map-requirements`)

| WP | Requirement refs |
|---|---|
| WP01 | FR-004, FR-005, FR-006, FR-009 |
| WP02 | FR-007, FR-008, FR-012 |
| WP03 | FR-001, FR-002, FR-003, FR-010, FR-011, FR-013 |

NFR-001 (test runtime), NFR-002 (fixture minimality), NFR-003 (test reliability), NFR-004 (schema compat), NFR-005 (cross-link), and C-001 through C-006 are enforced by the combined WP set.
