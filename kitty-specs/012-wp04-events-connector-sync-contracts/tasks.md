# Work Packages: Connector and Sync Lifecycle Contracts (012)

**Inputs**: `spec.md`, `plan.md`
**Prerequisites**: WP04 scope locked to connector and sync lifecycle contracts only
**Sequence**: `WP01 -> WP02`

## Work Package WP01: Connector and Sync Models, Constants, Schemas, Validators, Reducers (Priority: P0)

**Goal**: Implement canonical connector lifecycle and sync lifecycle event constants, frozen payload models with mandatory fields and idempotent ingest markers, external reference linking model, deterministic reducers with transition/dedup rules, and schema/validator wiring.

**Independent Test**: Connector and sync modules import cleanly, strict typing passes, and reducer transition tests confirm canonical state progression, idempotent dedup, and anomaly recording.

**Prompt**: `tasks/WP01-connector-sync-models-reducers.md`

### Included Subtasks

- [x] T001 Create connector lifecycle event constants, ConnectorState enum, and CONNECTOR_EVENT_TYPES frozen set.
- [x] T002 Implement frozen connector payload models with required fields per FR-002.
- [x] T003 Create sync lifecycle event constants, SyncOutcome enum, and SYNC_EVENT_TYPES frozen set.
- [x] T004 Implement frozen sync payload models with idempotency fields per FR-004.
- [x] T005 Implement ExternalReferenceLinkedPayload with external/internal binding fields per FR-005.
- [x] T006 Implement connector lifecycle reducer with deterministic transitions and anomaly handling per FR-006.
- [x] T007 Implement sync lifecycle reducer with idempotent ingest dedup and outcome tracking per FR-007.
- [x] T008 Wire connector and sync models into schema generation and conformance validator mappings.
- [x] T009 Add unit and reducer tests for transitions, dedup, idempotency, and anomaly behavior.

## Work Package WP02: Conformance Fixtures, Replay Scenarios, Compatibility Notes, Tests (Priority: P1)

**Goal**: Add conformance coverage (valid/invalid/replay) for connector, sync, and external reference families, replay determinism checks, schema/validator registrations, public export/versioning updates, and downstream impact notes.

**Independent Test**: Connector and sync conformance fixtures validate correctly, replay outputs match committed goldens, and package exports/version notes are complete for consumer adoption.

**Prompt**: `tasks/WP02-conformance-replay-compatibility.md`

### Included Subtasks

- [x] T010 Register connector and sync fixture categories in conformance loader.
- [x] T011 Add connector valid (6), invalid (4), and replay (1) fixtures with manifest entries.
- [x] T012 Add sync valid (6), invalid (4), and replay (1) fixtures with manifest entries.
- [x] T013 Add external-reference-linked valid (2) fixtures with manifest entries.
- [x] T014 Add mixed connector+sync replay stream (1) with golden reducer outputs.
- [x] T015 Add conformance and property tests for replay determinism and dedup idempotence.
- [x] T016 Add schema generation entries, public exports, and versioning/downstream impact notes.
- [x] T017 Update package-data configuration for connector and sync fixture assets in distributions.

## Requirement Mapping

- WP01 -> FR-001, FR-002, FR-003, FR-004, FR-005, FR-006, FR-007
- WP02 -> FR-008, FR-009, FR-010

<!-- status-model:start -->
## Canonical Status (Generated)
- WP01: done
- WP02: planned
<!-- status-model:end -->
