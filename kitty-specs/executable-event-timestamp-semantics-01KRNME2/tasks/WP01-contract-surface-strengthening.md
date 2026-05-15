---
work_package_id: WP01
title: Contract Surface Strengthening
dependencies: []
requirement_refs:
- FR-001
- FR-002
- FR-003
- FR-004
- FR-009
- FR-011
- NFR-004
- C-001
- C-002
- C-003
- C-004
- C-005
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this mission were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
- T004
phase: Phase 1 - Contract
assignee: ''
agent: claude
history:
- timestamp: '2026-05-15T11:00:00Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
agent_profile: implementer-ivan
authoritative_surface: src/spec_kitty_events/
execution_mode: code_change
lane: planned
owned_files:
- src/spec_kitty_events/models.py
- src/spec_kitty_events/schemas/**
- kitty-specs/teamspace-event-contract-foundation-01KQHDE4/data-model.md
- CHANGELOG.md
review_status: ''
reviewed_by: ''
role: implementer
tags: []
---

# Work Package Prompt: WP01 – Contract Surface Strengthening

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your assigned agent profile so you operate with the right governance scope and identity:

```text
/ad-hoc-profile-load implementer-ivan
```

If your environment does not support that slash command, run:

```bash
spec-kitty profiles show implementer-ivan
```

and adopt the identity, governance scope, and boundaries it declares.

---

## ⚠️ IMPORTANT: Review Feedback Status

Read this first if you are implementing this task. If `review_status` above says `has_feedback`, scroll to **Review Feedback** below and treat each item as a must-do. Update `review_status: acknowledged` when you start.

---

## Review Feedback

*(empty)*

---

## Objectives & Success Criteria

Make the canonical event-envelope `Event.timestamp` field's semantic meaning (producer-assigned wall-clock occurrence time) executable at the contract-surface level. The wire format does NOT change.

Done means:

- The Pydantic `Event.timestamp` field's `description=` (and surrounding docstring/comment) explicitly states "producer-assigned wall-clock occurrence time" and explicitly warns consumers MUST NOT reuse the field name for receipt/import/server time. The text matches the canonical sentence in the contract document.
- The committed JSON Schemas under `src/spec_kitty_events/schemas/` have been regenerated so the `timestamp` field description in any per-payload schema (and any top-level envelope schema, if present) carries the new text. No hand-edited schema JSON.
- `kitty-specs/teamspace-event-contract-foundation-01KQHDE4/data-model.md` documents Rule R-T-01 (producer wins), Rule R-T-02 (no name collision), and Rule R-T-03 (ordering invariance), and names `received_at` as the recommended consumer-owned receipt-time slot. The existing `timestamp` row in that document points to the new section.
- `CHANGELOG.md` has a new entry under the current/next unreleased section noting:
  - Strengthened producer-occurrence semantics on `Event.timestamp` (docs/schemas only, wire unchanged).
  - The forthcoming `assert_producer_occurrence_preserved` helper (delivered in WP02).
  - A one-paragraph migration note for consumers that may have been substituting receipt time.
- The charter-required schema drift check passes after regeneration (`pytest` schema drift suite green, or whatever the project's regeneration entrypoint validates).

Mission requirements covered: FR-001, FR-002, FR-003, FR-004, FR-009, FR-011, C-002, NFR-004.

## Context & Constraints

- Charter (`.kittify/charter/charter.md`): Python 3.10+, Pydantic event models, committed JSON Schemas, conformance fixtures as public contract. Quality gates: pytest, schema generation check, mypy --strict.
- Mission spec: `kitty-specs/executable-event-timestamp-semantics-01KRNME2/spec.md` — FR-001..FR-011, NFR-001..NFR-004, C-001..C-005.
- Plan: `kitty-specs/executable-event-timestamp-semantics-01KRNME2/plan.md`.
- Research: `kitty-specs/executable-event-timestamp-semantics-01KRNME2/research.md` (notably R-01 receipt-time naming, R-03 drift detection, R-04 fixture determinism).
- Data model view: `kitty-specs/executable-event-timestamp-semantics-01KRNME2/data-model.md` (cross-references the canonical contract doc).
- Contract: `kitty-specs/executable-event-timestamp-semantics-01KRNME2/contracts/timestamp-semantics.md` (producer/consumer obligations + failure mode).
- Constraints to honour:
  - C-001: import paths stable.
  - C-002: wire identifier stays `timestamp`.
  - C-003: no new runtime deps on consumer repos.
  - C-004: reducer ordering unchanged.
  - C-005: no provenance/inference flag on the envelope.

## Subtasks & Detailed Guidance

### Subtask T001 – Strengthen `Event.timestamp` description text

- **Purpose**: Make the producer-occurrence semantics impossible to miss when reading the model.
- **Steps**:
  1. Open `src/spec_kitty_events/models.py`. Locate the `Event` class and the `timestamp` field (current `description=` reads `"Wall-clock timestamp (human-readable, not used for ordering)"`).
  2. Replace the `description=` with text along the lines of: "Producer-assigned wall-clock occurrence time (ISO-8601 UTC). Records when the modelled event actually happened on the producing system. Consumers MUST preserve this value through ingestion, persistence, projection, reduction, and serialization. Consumers MUST NOT substitute receipt/import/server time for this field; store consumer receipt time separately (e.g. `received_at`)."
  3. If the surrounding class docstring also discusses timestamps, add a short paragraph noting the producer-vs-receipt distinction and pointing to `kitty-specs/teamspace-event-contract-foundation-01KQHDE4/data-model.md`.
  4. Preserve the existing `Field(... description=...)` signature shape; do NOT change the field's type, validators, or required/optional status.
- **Files**: `src/spec_kitty_events/models.py`
- **Parallel?**: no — gates T002.
- **Notes**: Use exactly the same wording in the canonical contract doc (T003). Copy-pasting reduces drift.

### Subtask T002 – Regenerate committed JSON Schemas

- **Purpose**: Mirror the strengthened semantics into the machine-readable artifact.
- **Steps**:
  1. Identify the existing schema generation entrypoint. Look in `scripts/`, `pyproject.toml`, and `Makefile`. Common names: `scripts/generate_schemas.py`, `python -m spec_kitty_events.schemas.regenerate`, or a `make schemas` target.
  2. If no entrypoint is documented, grep for usages of `model_json_schema` and `.schemas/` writes. Use whichever path the schema drift check expects.
  3. Run the regeneration command. Commit any modified files under `src/spec_kitty_events/schemas/`.
  4. Run the existing schema drift check (`pytest` may run it automatically; if not, locate it under `tests/` or `src/spec_kitty_events/conformance/`). It must pass.
- **Files**: `src/spec_kitty_events/schemas/**` (regenerated, not hand-edited).
- **Parallel?**: no — depends on T001.
- **Notes**: If the regeneration is purely model-driven and the existing schemas already inherit field descriptions from the Pydantic model, the diff may be small; that is expected. The point is that nothing is hand-edited.

### Subtask T003 – Update canonical contract doc

- **Purpose**: Make the producer-vs-receipt distinction part of the audit-of-record contract.
- **Steps**:
  1. Open `kitty-specs/teamspace-event-contract-foundation-01KQHDE4/data-model.md`.
  2. Update the existing `timestamp` row in the canonical field table (line ~22) so its "Description" text matches the strengthened model description from T001 (use a single short sentence; point to the new rules section for detail).
  3. Add a new subsection inside that document titled "Timestamp Semantics" containing Rules R-T-01 / R-T-02 / R-T-03 verbatim as written in `kitty-specs/executable-event-timestamp-semantics-01KRNME2/data-model.md`.
  4. Document `received_at` as the recommended (consumer-owned) name for receipt/import time, and state explicitly that it is NOT part of the canonical envelope.
  5. Do not modify any other contract surface in that document.
- **Files**: `kitty-specs/teamspace-event-contract-foundation-01KQHDE4/data-model.md`
- **Parallel?**: yes (with T004) once T001 sentence is drafted.
- **Notes**: Keep prose style consistent with the rest of the document.

### Subtask T004 – CHANGELOG entry

- **Purpose**: Mark the contract strengthening so consumers know to align.
- **Steps**:
  1. Open `CHANGELOG.md`. Find the current unreleased / topmost in-progress section.
  2. Append a new bullet group (e.g. under "Changed" or whatever heading style the file uses) noting:
     - Strengthened `Event.timestamp` producer-occurrence semantics in model docstring and committed JSON Schemas (wire unchanged).
     - Coming in this release: `spec_kitty_events.conformance.assert_producer_occurrence_preserved` helper and `timestamp_semantics` fixture class (delivered in WP02).
     - Migration note: consumers that previously stored receipt/import time under a column or field named `timestamp` should add a separate `received_at` slot and run the new helper in their test suite. The producer `timestamp` value MUST be preserved end-to-end.
  3. Do NOT bump the project version unless the file's prior practice is to bump in the same commit; the change is additive and constraint C-001 forbids breakage.
- **Files**: `CHANGELOG.md`
- **Parallel?**: yes (with T003).
- **Notes**: Keep the entry concise; the contract doc is the long-form reference.

## Test Strategy

- After T002, the committed schema drift check MUST pass (`pytest` covers this in the existing suite — look for `test_schema*` or similar).
- `pytest` overall: green.
- `mypy --strict`: green for any models.py changes.

Run:

```bash
pytest
mypy --strict src/spec_kitty_events
```

If schema regeneration is a separate command, run it before pytest.

## Risks & Mitigations

- **Risk**: Modifying `Event.timestamp` field signature inadvertently changes wire format. **Mitigation**: only change `description=` text and surrounding docstring/comment. Do not touch type, required, validator.
- **Risk**: Forgetting to regenerate schemas leaves drift between model and committed schema files. **Mitigation**: run regeneration tooling explicitly in T002; pytest schema drift suite is the safety net.
- **Risk**: Diverging wording between model docstring and canonical contract doc. **Mitigation**: copy-paste one canonical sentence in both locations.
- **Risk**: CHANGELOG style drift. **Mitigation**: read the file before editing and match the existing format.

## Review Guidance

Reviewer checks:

- [ ] `Event.timestamp` description text explicitly states "producer-assigned wall-clock occurrence time" and forbids substituting receipt time under the same name.
- [ ] No type/validator/requirement-status change on the `Event.timestamp` field.
- [ ] Schema regeneration was run (committed JSON under `src/spec_kitty_events/schemas/` matches model); the schema drift check is green.
- [ ] `kitty-specs/teamspace-event-contract-foundation-01KQHDE4/data-model.md` contains Rules R-T-01/02/03 and documents `received_at`.
- [ ] `CHANGELOG.md` entry mentions strengthened semantics, forthcoming helper, and migration note.
- [ ] `mypy --strict` and `pytest` both green.

## Activity Log

- 2026-05-15T11:00:00Z – system – lane=planned – Prompt created
