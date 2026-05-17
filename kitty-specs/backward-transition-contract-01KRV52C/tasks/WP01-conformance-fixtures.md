---
work_package_id: WP01
title: Conformance Fixtures + Manifest
dependencies: []
requirement_refs:
- FR-004
- FR-005
- FR-006
- FR-009
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this mission were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
- T004
agent: claude
history:
- timestamp: '2026-05-17T14:30:00Z'
  actor: planner
  action: created
  note: Initial WP01 prompt drafted by /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/spec_kitty_events/conformance/fixtures/
execution_mode: code_change
mission_slug: backward-transition-contract-01KRV52C
owned_files:
- src/spec_kitty_events/conformance/fixtures/edge_cases/replay/wp_review_rejection_cycle.jsonl
- src/spec_kitty_events/conformance/fixtures/edge_cases/valid/wp_status_changed_approved_rewind.json
- src/spec_kitty_events/conformance/fixtures/edge_cases/invalid/wp_status_changed_unforced_in_review_to_planned.json
- src/spec_kitty_events/conformance/fixtures/manifest.json
priority: P1
role: implementer
tags: []
---

# WP01 — Conformance Fixtures + Manifest

## ⚡ Do This First: Load Agent Profile

**STOP. Before reading anything else, load your assigned profile.**

```
/ad-hoc-profile-load python-pedro
```

This profile identifies you as a Python implementer with focus on Pydantic models, JSON shape correctness, and conformance fixture authoring. Confirm the initialization declaration before proceeding.

## Objective

Land three new synthetic conformance fixtures under `src/spec_kitty_events/conformance/fixtures/edge_cases/` and register them in `manifest.json`. The fixtures exemplify the **review-rejection transition family** in the canonical `WPStatusChanged` event — one full lifecycle replay stream (JSONL), one positive single-event JSON, and one negative single-event JSON.

This WP is the foundation. WP02 (Family Tests) loads these fixtures; WP03 (Docs) references them by filename.

## Context — Why this WP exists

Cross-repo planning issue `Priivacy-ai/spec-kitty-planning#16` surfaced that CLI, SaaS materializer, and durable drain disagree about how a review-rejection (e.g. `in_review → planned` or `approved → planned`) appears on the wire. The contract layer already supports `force=True + reason` semantics in `StatusTransitionPayload`, but lacks canonical fixtures showing what a *correct* review-rejection event looks like vs an *unforced backward-transition bug* event.

Read these references before writing fixtures:

- Mission spec: `kitty-specs/backward-transition-contract-01KRV52C/spec.md`
- Plan: `kitty-specs/backward-transition-contract-01KRV52C/plan.md`
- Research (loader behavior, replay-stream precedent): `kitty-specs/backward-transition-contract-01KRV52C/research.md`
- Contract draft (Sections 1–7): `kitty-specs/backward-transition-contract-01KRV52C/contracts/backward-transition-family.md`
- Data model recap: `kitty-specs/backward-transition-contract-01KRV52C/data-model.md`
- Existing model: `src/spec_kitty_events/status.py` (search for `class StatusTransitionPayload`)
- Existing happy-path fixture (shape to mirror): `src/spec_kitty_events/conformance/fixtures/events/valid/wp_status_changed.json`
- Existing canonical event envelope shape: `src/spec_kitty_events/conformance/fixtures/events/valid/event.json`
- Replay-stream precedents:
  - `src/spec_kitty_events/conformance/fixtures/dossier/replay/dossier_happy_path.jsonl`
  - `src/spec_kitty_events/conformance/fixtures/sync/replay/sync-ingest-lifecycle.jsonl`
- Manifest: `src/spec_kitty_events/conformance/fixtures/manifest.json`

## Branch Strategy

- Planning/base branch: `main`
- Merge target: `main`
- This WP runs in a per-lane worktree created by `spec-kitty agent action implement WP01`. Do not create the worktree manually. The lane is computed by `finalize-tasks` and recorded in `kitty-specs/backward-transition-contract-01KRV52C/lanes.json`.

## Subtasks

### T001 — Author `edge_cases/replay/wp_review_rejection_cycle.jsonl`

**Purpose**: A full canonical Event-envelope replay stream that walks one work package through `planned → claimed → in_progress → for_review → in_review → planned (force=True, rewind) → claimed → in_progress → for_review → in_review → approved`. Eleven events, strictly monotonic Lamport clocks, deterministic event ids.

**Steps**:

1. Create directory if it does not exist: `src/spec_kitty_events/conformance/fixtures/edge_cases/replay/`.
2. Open `src/spec_kitty_events/conformance/fixtures/events/valid/event.json` and `src/spec_kitty_events/conformance/fixtures/events/valid/wp_status_changed.json` to confirm the canonical Event envelope shape and the `StatusTransitionPayload` keys.
3. Write 11 JSON-on-one-line records to `wp_review_rejection_cycle.jsonl`, in this order:

   | Lamport | Event id (synthetic) | from_lane | to_lane | force | reason | actor |
   |---|---|---|---|---|---|---|
   | 1 | `01KCYCLE0000000000000001A` | (null / omitted) | `planned` | false | null | `synthetic-agent` |
   | 2 | `01KCYCLE0000000000000002B` | `planned` | `claimed` | false | null | `synthetic-agent` |
   | 3 | `01KCYCLE0000000000000003C` | `claimed` | `in_progress` | false | null | `synthetic-agent` |
   | 4 | `01KCYCLE0000000000000004D` | `in_progress` | `for_review` | false | null | `synthetic-agent` |
   | 5 | `01KCYCLE0000000000000005E` | `for_review` | `in_review` | false | null | `reviewer-renata` |
   | 6 | `01KCYCLE0000000000000006F` | `in_review` | `planned` | **true** | `"backward rewind: in_review -> planned: feedback://mission-backward-transition-demo/WP01/20260517T140000Z-aaaa.md"` | `reviewer-renata` |
   | 7 | `01KCYCLE0000000000000007G` | `planned` | `claimed` | false | null | `synthetic-agent` |
   | 8 | `01KCYCLE0000000000000008H` | `claimed` | `in_progress` | false | null | `synthetic-agent` |
   | 9 | `01KCYCLE0000000000000009J` | `in_progress` | `for_review` | false | null | `synthetic-agent` |
   | 10 | `01KCYCLE0000000000000010K` | `for_review` | `in_review` | false | null | `reviewer-renata` |
   | 11 | `01KCYCLE0000000000000011L` | `in_review` | `approved` | false | null | `reviewer-renata` |

4. Each record is a canonical Event envelope. Shared envelope fields:
   - `event_type`: `"WPStatusChanged"`
   - `aggregate_id`: `"WP01"`
   - `team_slug`: `"synthetic-team"`
   - `project_uuid`: `"00000000-0000-0000-0000-00000000c001"` (synthetic, deterministic)
   - `build_id`: `"backward-transition-contract-demo-20260517"`
   - `lamport_clock`: as in the table
   - `event_id`: as in the table
   - `timestamp`: monotonically increasing ISO-8601 UTC timestamps starting `2026-05-17T14:00:00.000000+00:00` (+1 second per event)
   - `origin`: `null`
   - `payload`: a `StatusTransitionPayload` dict with fields from the table plus:
     - `execution_mode`: `"worktree"`
     - `wp_id`: `"WP01"`
     - `mission_slug`: `"mission-backward-transition-demo"`
     - `evidence`: `null`
     - `review_ref`: for event 6, the same URI as the reason's feedback-ref segment; null otherwise.

5. Each line MUST be a single JSON document with no leading/trailing whitespace. Final newline required at EOF.

**Files**:

- `src/spec_kitty_events/conformance/fixtures/edge_cases/replay/wp_review_rejection_cycle.jsonl` (NEW, ~11 lines × ~400 bytes ≈ 4.5 KB)

**Validation**:

- [ ] File exists and is exactly 11 lines.
- [ ] `python -c "import json,pathlib; [json.loads(l) for l in pathlib.Path('src/spec_kitty_events/conformance/fixtures/edge_cases/replay/wp_review_rejection_cycle.jsonl').read_text().splitlines()]"` exits 0.
- [ ] Lamport clocks are strictly increasing 1..11.
- [ ] Event 6 has `payload.force == True`, `payload.reason` starting with `"backward rewind: in_review -> planned"`, and `payload.review_ref` non-null.
- [ ] All other events have `payload.force == False`.

### T002 — Author `edge_cases/valid/wp_status_changed_approved_rewind.json`

**Purpose**: A single `WPStatusChanged` payload mirroring the planning#16 evidence-pack shape (`from_lane=approved, to_lane=planned`) but synthetic and conformant (`force=True + reason`). This is the positive contract case the evidence pack should have looked like.

**Steps**:

1. Inspect `src/spec_kitty_events/conformance/fixtures/events/valid/wp_status_changed.json` for the exact key set.
2. Write the new fixture with:
   - `wp_id`: `"WP07"`
   - `from_lane`: `"approved"`
   - `to_lane`: `"planned"`
   - `actor`: `"user"`
   - `force`: `true`
   - `reason`: `"backward rewind: approved -> planned: feedback://mission-backward-transition-demo/WP07/20260517T141000Z-bbbb.md"`
   - `execution_mode`: `"worktree"`
   - `review_ref`: `"feedback://mission-backward-transition-demo/WP07/20260517T141000Z-bbbb.md"`
   - `evidence`: `null`
   - `mission_slug`: `"mission-backward-transition-demo"`

**Files**:

- `src/spec_kitty_events/conformance/fixtures/edge_cases/valid/wp_status_changed_approved_rewind.json` (NEW)

**Validation**:

- [ ] Loads via `StatusTransitionPayload.model_validate(json.load(open(<path>)))` without error.
- [ ] `validate_transition(...)` (or whichever validator the test invokes) classifies it as VALID.
- [ ] Field set is exactly the keys present in `wp_status_changed.json` (no surplus, no missing).

### T003 — Author `edge_cases/invalid/wp_status_changed_unforced_in_review_to_planned.json`

**Purpose**: A single `WPStatusChanged` payload with `from_lane=in_review, to_lane=planned, force=False`. This is the wire shape of the planning#16 bug. The validator MUST reject it.

**Steps**:

1. Mirror the field set of `wp_status_changed.json` but with:
   - `wp_id`: `"WP09"`
   - `from_lane`: `"in_review"`
   - `to_lane`: `"planned"`
   - `actor`: `"user"`
   - `force`: `false`
   - `reason`: `null`
   - `execution_mode`: `"worktree"`
   - `review_ref`: `null`
   - `evidence`: `null`
   - `mission_slug`: `"mission-backward-transition-demo"`

**Files**:

- `src/spec_kitty_events/conformance/fixtures/edge_cases/invalid/wp_status_changed_unforced_in_review_to_planned.json` (NEW)

**Validation**:

- [ ] `StatusTransitionPayload.model_validate(...)` may or may not parse (the model itself allows force=False); but `validate_transition(...)` MUST return invalid for this payload.
- [ ] The fixture is loaded by `load_fixtures("edge_cases")` and the resulting `FixtureCase.expected_valid == False`.

### T004 — Register all three fixtures in `manifest.json`

**Purpose**: Make the three new fixtures discoverable by the conformance loader.

**Steps**:

1. Open `src/spec_kitty_events/conformance/fixtures/manifest.json` and locate the existing `edge_cases/...` entries near other valid/invalid edge-case fixtures.
2. Append three new entries (preserve existing indentation and trailing-comma rules):

```json
{
  "id": "wp-status-changed-approved-rewind-valid",
  "path": "edge_cases/valid/wp_status_changed_approved_rewind.json",
  "expected_result": "valid",
  "event_type": "WPStatusChanged",
  "notes": "Valid forced backward transition approved->planned per the review-rejection family; synthetic mirror of planning#16 evidence-pack shape.",
  "min_version": "3.0.0"
},
{
  "id": "wp-status-changed-unforced-in-review-to-planned-invalid",
  "path": "edge_cases/invalid/wp_status_changed_unforced_in_review_to_planned.json",
  "expected_result": "invalid",
  "event_type": "WPStatusChanged",
  "notes": "Unforced backward transition in_review->planned; contract-invalid (matches planning#16 wire bug).",
  "min_version": "3.0.0"
},
{
  "id": "wp-review-rejection-cycle-replay",
  "path": "edge_cases/replay/wp_review_rejection_cycle.jsonl",
  "fixture_type": "replay_stream",
  "event_type": "mixed",
  "expected_result": "valid",
  "notes": "Full 11-event review-rejection lifecycle: planned -> claimed -> in_progress -> for_review -> in_review -> planned (force=True) -> claimed -> in_progress -> for_review -> in_review -> approved.",
  "min_version": "3.0.0"
}
```

3. Verify JSON is still valid: `python -c "import json; json.load(open('src/spec_kitty_events/conformance/fixtures/manifest.json'))"`.

**Files**:

- `src/spec_kitty_events/conformance/fixtures/manifest.json` (MODIFY — additive only)

**Validation**:

- [ ] Manifest is valid JSON after edit.
- [ ] `python -c "from spec_kitty_events.conformance import load_fixtures; print({fc.id for fc in load_fixtures('edge_cases')} & {'wp-status-changed-approved-rewind-valid','wp-status-changed-unforced-in-review-to-planned-invalid'})"` returns both ids.
- [ ] `python -c "from spec_kitty_events.conformance.loader import load_replay_stream; print(len(load_replay_stream('wp-review-rejection-cycle-replay')))"` prints `11`.

## Integration Verification

After all subtasks land, run:

```bash
cd /Users/robert/spec-kitty-dev/spec-kitty-20260517-161351-nNtfEd/spec-kitty-events
uv run pytest tests/unit/test_fixtures.py -q
```

The existing parametrized tests in `test_fixtures.py` enumerate fixtures by hard-coded path list (see `VALID_EVENT_FILES`); they will not pick up the new edge_cases entries until WP02 registers them. That is expected — this WP does not need the new tests to pass yet.

What MUST stay green: the existing `test_fixtures.py` suite continues to pass (no regressions in already-registered fixtures).

## Definition of Done

- [ ] Three new files exist with the contents described.
- [ ] `manifest.json` is valid JSON and contains the three new entries with stable ids.
- [ ] `python -c "from spec_kitty_events.conformance import load_fixtures; load_fixtures('edge_cases')"` does not raise.
- [ ] `load_replay_stream('wp-review-rejection-cycle-replay')` returns a list of 11 dicts.
- [ ] Existing `uv run pytest tests/unit/test_fixtures.py -q` continues to pass.
- [ ] WP frontmatter `lane` advanced from `in_progress` to `for_review` via `spec-kitty agent tasks move-task WP01 --to for_review --note "Fixtures + manifest landed"`.
- [ ] Git commit message: `feat(WP01): add review-rejection conformance fixtures + manifest entries`.

## Risks

| Risk | Mitigation |
|---|---|
| Lamport clock or timestamp drift | Hard-code values per the table; do not generate at runtime. |
| Manifest JSON formatting violations | Use `python -m json.tool` to round-trip and confirm before commit. |
| Field-set drift from `wp_status_changed.json` | Diff field keys before saving; mirror exactly. |
| Synthetic event ids collide with existing fixtures | Use the `01KCYCLE...` prefix which is unique to this mission. |

## Reviewer Guidance

A reviewer should:

1. Confirm each new fixture's field set matches `wp_status_changed.json` for single-event fixtures and `event.json` envelope shape for the replay stream.
2. Verify Lamport clocks 1..11 are strictly monotonic in the JSONL.
3. Verify event 6 of the JSONL has `force=True, reason` starting with `"backward rewind: in_review -> planned"`, `review_ref` non-null.
4. Verify the unforced-invalid fixture has `force=False, reason=null` (the planning#16 bug shape).
5. Verify manifest.json parses cleanly and ids are unique across the file.
6. Confirm no copy of any of the 22 dev evidence events from `~/spec-kitty-dev/terminal-failed-evidence-2026-05-17.json` (all identifiers must be synthetic).
