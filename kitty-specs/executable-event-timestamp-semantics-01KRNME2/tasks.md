---
description: "Work packages for executable-event-timestamp-semantics-01KRNME2"
---

# Work Packages: Executable Event Timestamp Semantics

**Inputs**: Design documents from `kitty-specs/executable-event-timestamp-semantics-01KRNME2/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: Required — this mission adds executable contract enforcement. Tests are the deliverable.

**Organization**: Two work packages keep this contract-strengthening mission within the 3–7 subtask sweet spot per WP and isolate "contract surface" from "conformance helper + tests" so the two surfaces can be reviewed independently.

## Subtask Index

| ID | Description | WP | Parallel |
|----|-------------|----|----------|
| T001 | Strengthen `Event.timestamp` Pydantic docstring/description text | WP01 | |
| T002 | Regenerate committed JSON Schemas so the timestamp description matches the new text | WP01 | |
| T003 | Update canonical contract document `kitty-specs/teamspace-event-contract-foundation-01KQHDE4/data-model.md` with Rule R-T-01/R-T-02/R-T-03 and the `received_at` consumer convention | WP01 | [P] |
| T004 | Add CHANGELOG entry covering the strengthened semantics, helper, and migration note | WP01 | [P] |
| T005 | Add `src/spec_kitty_events/conformance/timestamp_semantics.py` (helper + typed `TimestampSubstitutionError`) | WP02 | |
| T006 | Re-export new helper and error from `src/spec_kitty_events/conformance/__init__.py` | WP02 | |
| T007 | Add three committed fixtures under `src/spec_kitty_events/conformance/fixtures/timestamp_semantics/` | WP02 | [P] |
| T008 | Add `src/spec_kitty_events/conformance/tests/test_timestamp_semantics.py` covering good-consumer, equality-edge, and bad-consumer paths | WP02 | |
| T009 | Run charter quality gates (pytest, schema drift, mypy --strict) on the resulting tree | WP02 | |

---

## Work Package WP01: Contract Surface Strengthening (Priority: P0)

**Goal**: Make the canonical producer-occurrence semantics for `Event.timestamp` executable at the contract-surface level — Pydantic model docstring, regenerated JSON Schemas, canonical contract document, and CHANGELOG.
**Independent Test**: After this WP, reading only `src/spec_kitty_events/models.py`, the regenerated JSON Schemas, and `kitty-specs/teamspace-event-contract-foundation-01KQHDE4/data-model.md` correctly tells a new contributor "`timestamp` is producer occurrence time; receipt time MUST be stored under a different name." The schema drift check passes.
**Prompt**: `tasks/WP01-contract-surface-strengthening.md`

### Included Subtasks
- [x] T001 Strengthen `Event.timestamp` Pydantic docstring/description text (WP01)
- [x] T002 Regenerate committed JSON Schemas so the timestamp description matches the new text (WP01)
- [x] T003 Update canonical contract document with Rule R-T-01/R-T-02/R-T-03 and `received_at` convention (WP01)
- [x] T004 Add CHANGELOG entry (WP01)

### Implementation Notes

- `Event.timestamp` lives in `src/spec_kitty_events/models.py` at line ~86. The new `description=` value must state producer occurrence time and explicitly warn consumers not to reuse the field name for receipt time.
- The existing schema generation script (look under `scripts/` or invoke the documented schema regen entrypoint; if not found, regenerate via the same procedure the charter "committed schema generation check" expects) MUST be run after the description change.
- The canonical contract document already has a timestamp row at line ~22. Append a new "Timestamp Semantics (Rules R-T-01..R-T-03)" subsection inside the data-model document and update the existing row's "Description" cell to point to it.
- CHANGELOG entry: follow the file's existing style. Mark this as a non-breaking strengthening; do not bump the package version.

### Parallel Opportunities

- T003 and T004 can proceed in parallel with T001/T002 once a draft of the new docstring text exists.

### Dependencies

- None (starting package).

### Risks & Mitigations

- Schema regeneration drift: regenerate via the existing tooling, never edit committed schema JSON by hand.
- Wording divergence across model docstring and contract doc: copy the canonical sentence verbatim into both.

---

## Work Package WP02: Conformance Helper, Fixtures, and Tests (Priority: P0)

**Goal**: Ship the executable conformance helper, fixtures, and pytest cases that downstream consumers can re-use to prove they preserved producer occurrence time.
**Independent Test**: `pytest --pyargs spec_kitty_events.conformance` plus the new `tests/test_timestamp_semantics.py` pass. A deliberately-broken fake consumer that overwrites `timestamp` with receipt time fails with `TimestampSubstitutionError`.
**Prompt**: `tasks/WP02-conformance-helper-fixtures-and-tests.md`

### Included Subtasks
- [x] T005 Add `src/spec_kitty_events/conformance/timestamp_semantics.py` (helper + typed `TimestampSubstitutionError`) (WP02)
- [x] T006 Re-export helper and error from `src/spec_kitty_events/conformance/__init__.py` (WP02)
- [x] T007 Add three committed fixtures under `src/spec_kitty_events/conformance/fixtures/timestamp_semantics/` (WP02)
- [x] T008 Add `src/spec_kitty_events/conformance/tests/test_timestamp_semantics.py` covering good-consumer, equality-edge, and bad-consumer paths (WP02)
- [x] T009 Run charter quality gates (pytest, schema drift, mypy --strict) (WP02)

### Implementation Notes

- The helper takes the canonical envelope dict and a consumer-supplied `persisted_occurrence_time: datetime`. It MUST normalise both to UTC `datetime` for comparison so timezone-naïve vs aware values do not cause spurious failures, BUT it MUST still raise `TimestampSubstitutionError` whenever the canonical instant differs.
- Fixtures: producer `timestamp` = `2026-01-01T00:00:00+00:00`, receipt-time annotation in fixture metadata at least 30 days later (use `2026-05-15T10:00:00+00:00`). The invalid fixture's `persisted_occurrence_time` equals receipt time.
- `TimestampSubstitutionError` carries three attributes: `field_name: str`, `expected: datetime`, `actual: datetime`, and produces a useful `__str__`.
- `tests/test_timestamp_semantics.py` MUST cover all three fixture cases plus a unit test that constructs the error directly and asserts its attributes.

### Parallel Opportunities

- T005, T006, T007 can be drafted in parallel once the helper signature is locked. T008 depends on T005–T007. T009 is final-gate.

### Dependencies

- Depends on WP01.

### Risks & Mitigations

- Timezone-naïve fixture values causing comparison anomalies: helper canonicalises to UTC `datetime`.
- Conformance fixture not discovered by the existing loader: the new fixture kind (`timestamp_semantics`) MUST be registered in the existing `manifest.json` if the loader expects a manifest entry; verify by tracing `loader.load_fixtures`.
- Schema drift check failing because new schema JSON not regenerated: WP01 already addresses this; WP02 just re-runs the gate.
