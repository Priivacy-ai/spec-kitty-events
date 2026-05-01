---
work_package_id: WP04
title: Payload Reconciliation
dependencies:
- WP01
- WP02
requirement_refs:
- C-004
- FR-003
- FR-004
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T012
- T013
- T014
- T015
- T016
agent: "claude:sonnet:reviewer-rachel:reviewer"
shell_pid: "34867"
history:
- event: created
  at: '2026-05-01T09:44:26Z'
  by: /spec-kitty.tasks
agent_profile: implementer-ivan
authoritative_surface: src/spec_kitty_events/lifecycle.py
execution_mode: code_change
owned_files:
- src/spec_kitty_events/lifecycle.py
- src/spec_kitty_events/schemas/mission_created_payload.schema.json
- src/spec_kitty_events/schemas/mission_closed_payload.schema.json
- src/spec_kitty_events/schemas/status_transition_payload.schema.json
- src/spec_kitty_events/schemas/generate.py
- tests/test_payload_reconciliation.py
- kitty-specs/teamspace-event-contract-foundation-01KQHDE4/contracts/payload-reconciliation.md
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load implementer-ivan
```

---

## Objective

Reconcile the payload contracts for `MissionCreated`, `WPStatusChanged` (a.k.a. `StatusTransitionPayload`), and `MissionClosed` so that the events package is the **single source of truth** for these payloads. CLI and SaaS producers conform to the canonical models; the CLI canonicalizer is the transformation layer for legacy shapes.

This WP closes the spec-cited drift between CLI emission and `MissionClosedPayload` (and brings the other two payloads into the same source-of-truth discipline).

---

## Context

- Spec: FR-003, FR-004, C-002, C-004, SC-004.
- Contract: [contracts/payload-reconciliation.md](../contracts/payload-reconciliation.md) — note the **Reconciliation log** section that this WP appends to.
- Research: [research.md R-02](../research.md#r-02--reconciliation-direction-for-missioncreated-wpstatuschanged-missionclosed).
- Existing models live in `src/spec_kitty_events/lifecycle.py`. The `StatusTransitionPayload` lives in `src/spec_kitty_events/status.py` and is owned by **WP01**. This WP **does not** modify `status.py` directly; instead, the audit step covers it and the model change for it lives inside WP01 if needed (coordinate via the audit log).
- `src/spec_kitty_events/schemas/generate.py` is the regenerator script.

---

## Subtasks

### T012 — Audit CLI emission sites

**Purpose**: Produce a precise, evidenced list of what the CLI currently emits for each of the three event types.

**Steps**:
1. Search the workspace for CLI emission sites:
   - `../spec-kitty/src/` for any place that constructs a `MissionCreated`, `WPStatusChanged`, or `MissionClosed` event.
   - `../spec-kitty-saas/src/` for any place that consumes/produces them.
   - Look for direct dict literals as well as use of typed builders.
2. For each event type, build a table:

   | Event | CLI fields emitted (today) | Library payload fields (today) | Discrepancy |
   |---|---|---|---|
   | `MissionCreated` | ... | ... | ... |
   | `WPStatusChanged` | ... | ... | ... |
   | `MissionClosed` | ... | ... | ... |

3. For each field in a discrepancy: classify as **canonical-keeper**, **canonical-rejecter** (drop from CLI), or **canonicalizer-normalizes** (the dry-run translator drops/maps it).

4. Save the audit table to a temporary working file (e.g., as a section appended to the reconciliation log in T013) — do not commit a separate audit file outside of `contracts/payload-reconciliation.md`.

**Files**:
- (no files modified yet; this subtask informs T013/T014)

**Validation**:
- [ ] Every field surfaced by the audit has a classification.
- [ ] No field is left as "?".

---

### T013 — Append reconciliation log to `contracts/payload-reconciliation.md`

**Purpose**: Record the field-by-field decisions made by T012 so they are visible to Codex review and to downstream tranches.

**Steps**:
1. Open `kitty-specs/teamspace-event-contract-foundation-01KQHDE4/contracts/payload-reconciliation.md`. Append a new section using the template the contract reserves:

   ```markdown
   ### Reconciliation log — 2026-05-01

   #### MissionCreated
   - Field `<name>`: **retained** in canonical / **dropped** from canonical / **normalized by canonicalizer**.
     Rationale: <one or two lines>.
     Affected callers: <CLI file path / SaaS file path>.

   #### WPStatusChanged
   - ...

   #### MissionClosed
   - ...
   ```

2. The log must be specific: name each field by its actual identifier; cite the file path and (when discoverable) the line range of the emission site for affected callers.

3. Where a field is "canonical-rejecter" (dropped), state that the corresponding CLI emission code must change in `spec-kitty` Tranche A (audit) or Tranche B (canonicalizer). The reconciliation log is the cross-tranche handshake.

**Files**:
- `kitty-specs/teamspace-event-contract-foundation-01KQHDE4/contracts/payload-reconciliation.md` (modified, append-only — preserve existing content)

**Validation**:
- [ ] Section appears below existing content.
- [ ] Every event type from T012 has a populated subsection.
- [ ] Cross-tranche callers are named.

---

### T014 — Update payload models with reconciled fields and `extra='forbid'`

**Purpose**: Land the payload-model changes that match the audit's canonical-keeper / canonical-rejecter decisions.

**Steps**:
1. Open `src/spec_kitty_events/lifecycle.py`. Locate `class MissionCreatedPayload(BaseModel):` and `class MissionClosedPayload(BaseModel):` (around lines 100 and 122).
2. For each model:
   - Add `model_config = ConfigDict(extra="forbid")` if not already present.
   - Apply the field changes recorded in the reconciliation log: add fields the audit marked canonical-keeper (with appropriate types and Optional-ness), remove fields the audit marked canonical-rejecter, leave canonicalizer-normalized fields out of the canonical payload.
3. Use the canonical lane vocabulary from WP01 wherever lane references appear (import from `spec_kitty_events.status` rather than restating string lane values).
4. **For `StatusTransitionPayload`** (in `status.py`, owned by WP01): if the audit reveals required model changes, do **not** edit `status.py` from this WP. Instead, document the required change in the reconciliation log and coordinate with WP01 via a tasks.md note. (If WP01 already merged with stable model, propose changes via a follow-up WP.)
5. Keep the existing public symbol exports working; do not rename classes.

**Files**:
- `src/spec_kitty_events/lifecycle.py` (modified, ~50–100 lines of changes depending on audit results)

**Validation**:
- [ ] `mypy --strict` clean.
- [ ] Existing imports of `MissionCreatedPayload` and `MissionClosedPayload` continue to work.
- [ ] Pydantic `extra='forbid'` rejects unknown fields.
- [ ] Lane references point to `Lane` enum members (no string literals).

---

### T015 — Regenerate JSON Schemas

**Purpose**: Keep the committed JSON Schemas in sync with the updated Pydantic models so the schema-drift CI gate stays green.

**Steps**:
1. Read `src/spec_kitty_events/schemas/generate.py` to understand the regeneration entry point. The plan referenced this script at line 23 and 159 with mappings for the payload models.
2. Run the regenerator (the typical invocation, but confirm by reading the script):

   ```bash
   python -m spec_kitty_events.schemas.generate
   ```

   Or whatever invocation the script supports.
3. Confirm the diff to `mission_created_payload.schema.json`, `mission_closed_payload.schema.json`, and `status_transition_payload.schema.json` matches the model changes.
4. If the schema-drift CI gate exists in `tests/`, run it locally to confirm green.

**Files**:
- `src/spec_kitty_events/schemas/mission_created_payload.schema.json` (regenerated)
- `src/spec_kitty_events/schemas/mission_closed_payload.schema.json` (regenerated)
- `src/spec_kitty_events/schemas/status_transition_payload.schema.json` (regenerated)
- `src/spec_kitty_events/schemas/generate.py` (touched only if a model change requires a generator update)

**Validation**:
- [ ] Schema files are byte-deterministic (rerun the generator twice; diff is zero).
- [ ] Schema-drift CI gate is green.

---

### T016 — Author `tests/test_payload_reconciliation.py`

**Purpose**: Lock the reconciled payload contracts.

**Steps**:
1. Create `tests/test_payload_reconciliation.py` (new file).
2. Add tests that exercise:

   - **Each canonical-keeper field**: a valid payload includes it; the model accepts it.
   - **Each canonical-rejecter field**: a payload that includes it (mimicking historical CLI emission) is rejected by the canonical model with a `ValidationErrorCode.PAYLOAD_SCHEMA_FAIL` (after the canonicalizer would have normalized — but the model itself rejects).
   - **Lane references in `WPStatusChanged`**: a payload with `to_lane=Lane.IN_REVIEW.value` is accepted (handshake to WP01).
   - **`MissionClosed` cross-shape**: build a sample of the historical CLI emission and assert the canonical model's response (accept or reject as the reconciliation log dictates).
   - **Schema-drift parity**: a tiny test that loads the regenerated schema JSON and asserts a known canonical instance validates against it (using `jsonschema`).

3. Each test name should reference the FR it's covering (e.g., `def test_FR_003_mission_closed_canonical_rejects_extra_fields():`).

**Files**:
- `tests/test_payload_reconciliation.py` (new, ~200 lines)

**Validation**:
- [ ] Every reconciled field has at least one test.
- [ ] Tests pass.
- [ ] `mypy --strict` clean.

---

## Branch Strategy

- Planning/base branch: `main` · Merge target: `main` · Worktree allocated by `finalize-tasks`.

---

## Definition of Done

- [ ] Audit table built (T012).
- [ ] Reconciliation log appended (T013) and committed.
- [ ] Payload models reconciled with `extra='forbid'` (T014).
- [ ] Three JSON Schemas regenerated; schema-drift CI green (T015).
- [ ] `tests/test_payload_reconciliation.py` passes (T016).
- [ ] `mypy --strict` clean for `lifecycle.py`.
- [ ] Existing pytest suite still green.
- [ ] Cross-tranche caller list in the reconciliation log is complete.

---

## Risks

- **R-1**: The audit reveals more drift than the seeded change set (e.g., `legacy_aggregate_id` in `MissionClosed` per epic survey). Mitigation: the reconciliation log is the canonical record; if drift is large, surface it to Codex review.
- **R-2**: Updating the canonical model breaks an existing test that was testing the *old* shape. Mitigation: those tests must be updated to reflect the new contract; if a test is no longer meaningful, delete it with a comment in the commit.
- **R-3**: Schema regeneration is non-deterministic across Python versions. Mitigation: the existing `generate.py` is the source of truth; run it locally with the same Python version as CI.

---

## Reviewer Guidance

Codex reviewer will check:

1. The reconciliation log is field-precise, not vague.
2. Every canonical-rejecter field is named in a cross-tranche caller list so downstream tranches know where to change emission code.
3. `extra='forbid'` is set on all three reconciled models.
4. Lane references use `Lane` enum members, not string literals.
5. Schema regeneration is reproducible.
6. The `MissionClosed` cross-shape test specifically covers the disagreement the spec called out.

## Activity Log

- 2026-05-01T10:44:46Z – claude:sonnet:implementer-ivan:implementer – shell_pid=33657 – Started implementation via action command
- 2026-05-01T10:50:01Z – claude:sonnet:implementer-ivan:implementer – shell_pid=33657 – Ready for review: payload reconciliation + schemas + tests + log
- 2026-05-01T10:50:23Z – claude:sonnet:reviewer-rachel:reviewer – shell_pid=34867 – Started review via action command
- 2026-05-01T10:53:32Z – claude:sonnet:reviewer-rachel:reviewer – shell_pid=34867 – Review passed: 16 tests pass, schemas in lockstep (generate --check up to date), mypy --strict clean on lifecycle.py, all three payloads pin extra='forbid', reconciliation log on main lists canonical fields per event type and explicitly drops legacy_aggregate_id/closed_at/closed_by from MissionClosed canonical, WP04 diff strictly within owned files.
