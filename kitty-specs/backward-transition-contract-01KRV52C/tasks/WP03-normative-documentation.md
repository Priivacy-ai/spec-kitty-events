---
work_package_id: WP03
title: Normative Documentation
dependencies: []
requirement_refs:
- FR-001
- FR-002
- FR-003
- FR-010
- FR-011
- FR-013
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this mission were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-backward-transition-contract-01KRV52C
base_commit: 6458eb518cb08390e28e6bebd9d28b097d12f93a
created_at: '2026-05-17T14:45:28.186817+00:00'
subtasks:
- T007
- T008
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "8837"
history:
- timestamp: '2026-05-17T14:30:00Z'
  actor: planner
  action: created
  note: Initial WP03 prompt drafted by /spec-kitty.tasks
agent_profile: curator-carla
authoritative_surface: src/spec_kitty_events/status.py
execution_mode: code_change
mission_slug: backward-transition-contract-01KRV52C
owned_files:
- src/spec_kitty_events/status.py
- docs/consumer-contract-dossier-v2.4.0.md
priority: P1
role: curator
tags: []
---

# WP03 — Normative Documentation

## ⚡ Do This First: Load Agent Profile

**STOP. Before reading anything else, load your assigned profile.**

```
/ad-hoc-profile-load curator-carla
```

This profile identifies you as the documentation curator — owning catalog, classification, and knowledge-base consistency across docstring and external docs. Confirm the initialization declaration before proceeding.

## Objective

Add the normative "Review-Rejection Transition Family" section to **two anchor locations** with mutual cross-links and references to the new fixtures:

1. The top-of-file module docstring of `src/spec_kitty_events/status.py`.
2. A new section in `docs/consumer-contract-dossier-v2.4.0.md`.

No behavior change to any function or class. This WP is pure documentation — but the documentation IS the public contract surface.

## Context

The mission spec (`kitty-specs/backward-transition-contract-01KRV52C/spec.md`) explicitly requires both anchors with cross-links (FR-001, FR-013, NFR-005). The source-of-truth draft text is `kitty-specs/backward-transition-contract-01KRV52C/contracts/backward-transition-family.md` (Sections 1–7). Implement by adapting that draft into both target locations with minor formatting tweaks to fit each medium.

Read first:

- Source-of-truth draft: `kitty-specs/backward-transition-contract-01KRV52C/contracts/backward-transition-family.md`
- Existing module docstring: `src/spec_kitty_events/status.py` (lines 1-50 — the existing top-of-file docstring shape)
- Existing dossier: `docs/consumer-contract-dossier-v2.4.0.md`
- WP01 fixture filenames (so cross-links are correct): see WP01 prompt's "Files" sections

## Branch Strategy

- Planning/base branch: `main`
- Merge target: `main`
- Lane: assigned by `finalize-tasks`. Independent of WP01 and WP02 (different files).

## Subtasks

### T007 — Add normative section to `src/spec_kitty_events/status.py` module docstring

**Purpose**: The primary anchor. Python `help(spec_kitty_events.status)` and IDE introspection surface this content. The section must be inside the module docstring (the first statement in the file) and use markdown headings that render acceptably in both raw `__doc__` and rich IDE renderers.

**Steps**:

1. Open `src/spec_kitty_events/status.py` and identify the current top-of-file docstring. Confirm its triple-quote location (line 1 onward).
2. If the file does not yet have a module docstring, add one. If it does, extend it.
3. Place a new section titled `## Review-Rejection Transition Family` after any existing summary line(s) and before any imports. The full section content adapts Sections 1–7 of `kitty-specs/backward-transition-contract-01KRV52C/contracts/backward-transition-family.md`:

```python
"""<existing summary>

## Review-Rejection Transition Family

The **review-rejection transition family** is the named set of legitimate
forced backward lane transitions in WPStatusChanged events:

  | from_lane    | to_lane |
  |--------------|---------|
  | in_progress  | planned |
  | for_review   | planned |
  | in_review    | planned |
  | approved     | planned |

These transitions arise from user-deliberate rewinds in the work-package
lifecycle — most commonly a review rejection that returns a WP to `planned`
for re-implementation. They are not infrastructure events and they are not
graph errors.

### Wire requirements

For every event in the family, the emitting agent MUST set:

  1. `force = True`
  2. `reason` — a non-empty string. Enforced by the existing
     StatusTransitionPayload model validator ("force=True requires a
     non-empty reason").

Recommended canonical `reason` shape:

    backward rewind: <from_lane> -> <to_lane>[: <feedback-ref>]

where `<feedback-ref>` is optional. When present, the recommended URI shape
is `feedback://<mission-slug>/<wp-id>/<timestamp>-<hash>.md`.

### Unforced backward transitions are contract-invalid

A WPStatusChanged event with a `from_lane → to_lane` pair drawn from the
family table but `force = False` is contract-invalid. The existing
`validate_transition()` rejects such events via the lane matrix
check. Consumers MAY reject them as graph violations and SHOULD classify
them as business-rule rejections, not transient infrastructure failures.

### Relationship to ReviewRollback

ReviewRollback (declared in src/spec_kitty_events/lifecycle.py) is a
mission-level event recording the higher-level intent of a review rejection.
It is NOT a substitute for the per-WP WPStatusChanged events in the family —
the two are complementary records (mission-level intent + per-WP lane move).

### Distinction from bootstrap-planned events

A forced `* → planned` transition with `from_lane = None` is a
bootstrap-planned event, not a review-rejection. See
`is_bootstrap_planned_event()` for the discriminator.

### Forward-transition guards unaffected

Forward-transition guard semantics are unchanged by this contract section.
`force = True` is reserved for documented backward families and terminal-lane
exits. It MUST NOT be used to bypass forward guards or evidence
requirements.

### Conformance fixtures

The conformance fixture set under `src/spec_kitty_events/conformance/fixtures/`
includes (registered in `manifest.json`):

  - id `wp-review-rejection-cycle-replay` —
    full 11-event lifecycle including one review-rejection round-trip
    (path: edge_cases/replay/wp_review_rejection_cycle.jsonl)
  - id `wp-status-changed-approved-rewind-valid` —
    positive single-event approved→planned with force=True + reason
    (path: edge_cases/valid/wp_status_changed_approved_rewind.json)
  - id `wp-status-changed-unforced-in-review-to-planned-invalid` —
    negative single-event in_review→planned with force=False
    (path: edge_cases/invalid/wp_status_changed_unforced_in_review_to_planned.json)

Cross-reference: see also the equivalent normative section in
`docs/consumer-contract-dossier-v2.4.0.md` ("Backward Transitions: The
Review-Rejection Family"). Planning issue: Priivacy-ai/spec-kitty-planning#16.
"""
```

4. If existing module docstring content covers something else, preserve it. Place the new section appropriately.
5. Confirm Python still imports cleanly: `python -c "import spec_kitty_events.status; print(spec_kitty_events.status.__doc__[:200])"`.
6. Confirm `help(spec_kitty_events.status)` (or `python -c "import pydoc, spec_kitty_events.status as s; print(pydoc.text.document(s)[:2000])"`) renders the new section.

**Files**:

- `src/spec_kitty_events/status.py` (MODIFY — docstring only)

**Validation**:

- [ ] Module imports without error.
- [ ] `__doc__` contains the literal string `"Review-Rejection Transition Family"`.
- [ ] `__doc__` contains all four family members listed explicitly.
- [ ] `__doc__` contains the recommended `reason` shape including the literal `backward rewind:` prefix.
- [ ] Cross-link to `docs/consumer-contract-dossier-v2.4.0.md` is present.
- [ ] No behavior change — every existing test still passes.

### T008 — Add normative section to `docs/consumer-contract-dossier-v2.4.0.md`

**Purpose**: The secondary anchor — non-Python consumers (reviewers reading the repo on GitHub, sibling-mission implementers who haven't pip-installed the package locally) read this. The dossier filename includes the version (`v2.4.0`) so the URL is stable across releases.

**Steps**:

1. Open `docs/consumer-contract-dossier-v2.4.0.md` and find an appropriate insertion point — likely after any existing "Status / Lane Transitions" section. If no such section exists, append at the end.
2. Add a new top-level section:

```markdown
## Backward Transitions: The Review-Rejection Family

The **review-rejection transition family** is the named set of legitimate
forced backward lane transitions in `WPStatusChanged` events:

| `from_lane`   | `to_lane` |
|---------------|-----------|
| `in_progress` | `planned` |
| `for_review`  | `planned` |
| `in_review`   | `planned` |
| `approved`    | `planned` |

### Wire requirements

For every event in the family:

1. `force = True` — explicit acknowledgement that the transition is a
   user-deliberate rewind, not a forward step.
2. `reason` — non-empty. Enforced by the `StatusTransitionPayload` model
   validator.

Recommended canonical `reason` shape:

    backward rewind: <from_lane> -> <to_lane>[: <feedback-ref>]

`<feedback-ref>` is optional. URI shape `feedback://<mission-slug>/<wp-id>/<timestamp>-<hash>.md`.

### Unforced backward transitions are contract-invalid

`force = False` for any family-member transition is contract-invalid. The
existing `validate_transition()` rejects such events via the lane
matrix check. Consumers (materializers, projection engines, durable drain
workers) MAY reject these events as graph violations and SHOULD classify
them as business-rule rejections, not transient infrastructure failures.

### Relationship to `ReviewRollback`

`ReviewRollback` (declared in `src/spec_kitty_events/lifecycle.py`) is a
mission-level event. `WPStatusChanged(force=True, ...)` per affected WP is
the per-WP lane move. The two are complementary records, not substitutes.

### Distinction from bootstrap-planned events

A forced `* → planned` event with `from_lane = None` is a bootstrap-planned
event. See `is_bootstrap_planned_event()` for the discriminator.

### Forward-transition guards unaffected

Forward-transition guard semantics are unchanged. `force = True` is reserved
for documented backward families and terminal-lane exits. It MUST NOT be
used to bypass forward guards.

### Conformance fixtures

| Manifest id | Path | Purpose |
|---|---|---|
| `wp-review-rejection-cycle-replay` | `src/spec_kitty_events/conformance/fixtures/edge_cases/replay/wp_review_rejection_cycle.jsonl` | Full 11-event lifecycle replay including one review-rejection round-trip. |
| `wp-status-changed-approved-rewind-valid` | `src/spec_kitty_events/conformance/fixtures/edge_cases/valid/wp_status_changed_approved_rewind.json` | Positive single-event approved→planned with `force=True` + reason. |
| `wp-status-changed-unforced-in-review-to-planned-invalid` | `src/spec_kitty_events/conformance/fixtures/edge_cases/invalid/wp_status_changed_unforced_in_review_to_planned.json` | Negative single-event in_review→planned with `force=False`. Validator MUST reject. |

### Cross-references

- Module docstring: `src/spec_kitty_events/status.py` (mirror of this section).
- Pydantic model: `StatusTransitionPayload`.
- Validator: `validate_transition()`.
- Bootstrap discriminator: `is_bootstrap_planned_event()`.
- Mission-level intent event: `ReviewRollbackPayload` (`src/spec_kitty_events/lifecycle.py`).
- Planning issue: `Priivacy-ai/spec-kitty-planning#16`.
```

3. Maintain the existing docs file conventions (line wrap, heading levels). The new section uses `##` (top-level for the doc). Adjust to `###` if the doc uses a single `#` title pattern.
4. Confirm the markdown renders: paste through any local markdown previewer or just visually scan for table alignment and code-block syntax.

**Files**:

- `docs/consumer-contract-dossier-v2.4.0.md` (MODIFY — additive section only)

**Validation**:

- [ ] Section exists with heading exactly `## Backward Transitions: The Review-Rejection Family` (or `###` if the doc's heading hierarchy requires).
- [ ] All four family members listed in the table.
- [ ] Three fixture rows in the conformance-fixtures table with stable manifest ids matching WP01.
- [ ] Cross-link to `src/spec_kitty_events/status.py` is present.
- [ ] No existing dossier content is deleted or reworded — additive only.

## Integration Verification

After both subtasks land:

```bash
cd /Users/robert/spec-kitty-dev/spec-kitty-20260517-161351-nNtfEd/spec-kitty-events
python -c "import spec_kitty_events.status; assert 'Review-Rejection Transition Family' in spec_kitty_events.status.__doc__, 'docstring section missing'"
grep -q 'Backward Transitions: The Review-Rejection Family' docs/consumer-contract-dossier-v2.4.0.md && echo "docs anchor present"
```

Both checks pass.

The 2-minute readability test (FR-011, SC-001): a reviewer who reads only the new docstring section can answer "what does a legitimate review-rejection event look like on the wire?" without consulting other files. Verify by mental walkthrough.

## Definition of Done

- [ ] `status.py` module docstring contains the normative section per T007.
- [ ] `docs/consumer-contract-dossier-v2.4.0.md` contains the normative section per T008.
- [ ] Both sections cross-link to each other and reference all three fixture ids.
- [ ] `python -c "import spec_kitty_events.status"` succeeds — no syntax breakage.
- [ ] No existing test in `tests/unit/test_status.py` regresses (this WP should not change any test outcome).
- [ ] WP frontmatter `lane` advanced to `for_review` with note: `"Normative docs landed in both anchor locations"`.
- [ ] Git commit message: `docs(WP03): add review-rejection family normative section to status.py docstring + dossier`.

## Risks

| Risk | Mitigation |
|---|---|
| Triple-quote breakage on docstring edit | Use Edit tool carefully; preserve quote style of existing docstring. Run `python -c "import spec_kitty_events.status"` after each edit. |
| Cross-link drift | Relative paths in markdown render as-is in the dossier; in the docstring, treat as plain text references (no clickable links). |
| Section already exists in the dossier under a different heading | Search before adding. If a related section exists, place the new section adjacent and cross-link rather than replacing. |
| Heading level mismatch with existing dossier conventions | Inspect the doc and match its heading hierarchy. |
| Module import time grows due to longer docstring | Negligible — docstrings are not parsed for behavior; only `__doc__` length grows. |

## Reviewer Guidance

A reviewer should:

1. Mentally walk through the 2-minute readability test: read only the new docstring section and answer "what does a legitimate review-rejection event look like on the wire?"
2. Confirm all four family members are listed in both anchors.
3. Confirm the recommended `reason` shape appears verbatim in both anchors (`backward rewind: <from_lane> -> <to_lane>[: <feedback-ref>]`).
4. Confirm cross-links use stable paths (no NN-prefixed paths from kitty-specs, no version-pinned URLs other than the existing `v2.4.0` dossier filename).
5. Confirm no behavior change in `status.py` — only the docstring is modified.
6. Confirm no existing dossier content is deleted or paraphrased — additive only.

## Activity Log

- 2026-05-17T14:45:30Z – claude:opus:curator-carla:implementer – shell_pid=40431 – Assigned agent via action command
- 2026-05-17T14:49:35Z – claude:opus:curator-carla:implementer – shell_pid=40431 – Normative docs landed in both anchors; cross-links verified
- 2026-05-17T14:51:48Z – claude:opus:reviewer-renata:reviewer – shell_pid=8837 – Started review via action command
