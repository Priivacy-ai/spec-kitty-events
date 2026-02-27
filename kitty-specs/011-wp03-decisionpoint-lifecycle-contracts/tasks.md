# Work Packages: DecisionPoint Lifecycle Contracts (011)

**Inputs**: `spec.md`, `plan.md`
**Prerequisites**: WP03 scope locked to DecisionPoint lifecycle contracts only
**Sequence**: `WP01 -> WP02`

## Work Package WP01: DecisionPoint Constants, Payload Models, Reducer Transitions (Priority: P0)

**Goal**: Implement canonical DecisionPoint event constants, frozen payload models with mandatory audit fields, and deterministic reducer transitions with authority-policy checks.

**Independent Test**: DecisionPoint module imports cleanly, strict typing passes, and reducer transition tests confirm canonical state progression and policy enforcement.

**Prompt**: `tasks/WP01-decisionpoint-contracts-and-reducer.md`

### Included Subtasks

- [x] T001 Create DecisionPoint event constants and state/role enums.
- [x] T002 Implement frozen payload models with required audit-trail fields.
- [x] T003 Implement deterministic reducer and transition validation with anomaly handling.
- [x] T004 Add unit and reducer tests for transition and authority rules.

## Work Package WP02: Conformance Fixtures, Replay, Versioning, Downstream Notes (Priority: P1)

**Goal**: Add conformance coverage (valid/invalid/replay), replay determinism checks, schema/validator registrations, public export/versioning updates, and downstream impact notes.

**Independent Test**: DecisionPoint conformance fixtures validate correctly, replay outputs match committed goldens, and package exports/version notes are complete for consumer adoption.

**Prompt**: `tasks/WP02-conformance-replay-versioning-notes.md`

### Included Subtasks

- [ ] T005 Register DecisionPoint models/schemas in conformance validator and loader.
- [ ] T006 Add DecisionPoint valid, invalid, replay, and reducer-output fixtures with manifest entries.
- [ ] T007 Add conformance and property tests for replay determinism and dedup idempotence.
- [ ] T008 Add schema generation entries, public exports, and versioning/downstream impact notes.

## Requirement Mapping

- WP01 -> FR-001, FR-002, FR-003
- WP02 -> FR-004, FR-005, FR-006

<!-- status-model:start -->
## Canonical Status (Generated)
- WP01: done
<!-- status-model:end -->
