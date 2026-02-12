# Feature Specification: Event Contract Conformance Suite

**Feature Branch**: `005-event-contract-conformance-suite`
**Created**: 2026-02-12
**Status**: Draft
**Input**: User description: "Finalize and enforce the event contract needed by CLI and SaaS for a complete 2.x target state."

## User Scenarios & Testing

### User Story 1 — Schema Consumers Import Locked Contracts (Priority: P1)

A developer working on `spec-kitty` (CLI) or `spec-kitty-saas` needs to emit status-change events that conform to the canonical event contract. They `pip install spec-kitty-events>=2.0.0,<3.0.0` and import the `SyncLaneV1` enum and `canonical_to_sync_v1()` mapping function. They construct payloads using the published models and the mapping function, confident that the 7-lane canonical model is correctly collapsed to the 4-lane sync model their system expects.

**Why this priority**: Without a first-class, importable lane mapping contract, each consumer hardcodes its own mapping — the primary source of contract drift today.

**Independent Test**: Can be tested by importing `SyncLaneV1`, `canonical_to_sync_v1`, and `CANONICAL_TO_SYNC_V1` from `spec_kitty_events` and verifying each of the 7 canonical lanes maps to the expected sync lane.

**Acceptance Scenarios**:

1. **Given** a consumer imports `spec_kitty_events`, **When** they call `canonical_to_sync_v1(Lane.BLOCKED)`, **Then** the return value is `SyncLaneV1.DOING`.
2. **Given** a consumer imports `CANONICAL_TO_SYNC_V1`, **When** they inspect the mapping dict, **Then** all 7 canonical lanes are present as keys and all values are one of the 4 sync lanes.
3. **Given** a consumer constructs a `StatusTransitionPayload` with `to_lane=Lane.CANCELED`, **When** they apply `canonical_to_sync_v1()`, **Then** the sync-lane value is `SyncLaneV1.PLANNED`.

---

### User Story 2 — CI Conformance Checks Prevent Contract Drift (Priority: P1)

A CI pipeline in `spec-kitty` or `spec-kitty-saas` runs `pytest --pyargs spec_kitty_events.conformance` as a required check. The conformance suite validates that the consumer's pinned version of `spec-kitty-events` includes all expected schemas, fixtures, and mappings. If a contract-breaking change is introduced upstream without a major version bump, the conformance tests fail and block the merge.

**Why this priority**: Cross-repo contract drift is the confirmed gap. CI-enforced conformance is the mechanism that closes it.

**Independent Test**: Can be tested by running the conformance pytest suite and verifying it passes against the published fixtures and schemas.

**Acceptance Scenarios**:

1. **Given** a consumer CI pipeline pins `spec-kitty-events>=2.0.0,<3.0.0`, **When** `pytest --pyargs spec_kitty_events.conformance` runs, **Then** all conformance tests pass.
2. **Given** a hypothetical breaking change to the lane mapping (e.g., `BLOCKED→PLANNED` instead of `BLOCKED→DOING`), **When** conformance tests run against the altered mapping, **Then** the tests fail with a clear violation message.
3. **Given** a `2.1.0` release adds a new optional event field, **When** conformance tests run in a consumer pinned to `>=2.0.0`, **Then** all tests still pass (additive changes are non-breaking).

---

### User Story 3 — Consumer Validates Own Emitted Payloads (Priority: P2)

A developer in `spec-kitty` or `spec-kitty-saas` wants to validate that their locally emitted event payloads conform to the canonical schema. They import the callable validator API from `spec_kitty_events.conformance` and pass their payload dicts to it. The validator returns a structured result indicating pass/fail with specific violation details.

**Why this priority**: Turnkey CI catches upstream drift, but consumers also need to validate their own output against the contract — especially during migration to 2.x.

**Independent Test**: Can be tested by constructing a valid payload dict, calling the validator, and confirming it passes; then mutating one field and confirming it fails with the expected violation.

**Acceptance Scenarios**:

1. **Given** a consumer constructs a valid `WPStatusChanged` payload dict, **When** they call the validator, **Then** the result indicates the payload conforms.
2. **Given** a consumer constructs a payload with an invalid lane value (e.g., `"in_review"` instead of `"for_review"`), **When** they call the validator, **Then** the result indicates failure with the specific field and violation.
3. **Given** a consumer constructs a payload missing a required field (`correlation_id`), **When** they call the validator, **Then** the result indicates failure naming the missing field.

---

### User Story 4 — JSON Schema Files Enable Non-Python Consumers (Priority: P2)

A developer or tool working outside Python needs to validate events against the canonical schema. The `spec-kitty-events` package ships JSON Schema files in `src/spec_kitty_events/schemas/` that are generated from the Pydantic v2 models. These files are the machine-readable contract and can be consumed by any JSON Schema validator in any language.

**Why this priority**: JSON Schema files are the language-agnostic foundation. They also serve as documentation and as the source for conformance fixture validation.

**Independent Test**: Can be tested by loading a JSON Schema file and validating a sample event payload against it using any JSON Schema library.

**Acceptance Scenarios**:

1. **Given** the package is installed, **When** a developer locates `schemas/event.schema.json`, **Then** the file is a valid JSON Schema document that describes the canonical `Event` model.
2. **Given** a valid event payload, **When** validated against `event.schema.json`, **Then** validation passes.
3. **Given** the Pydantic models are updated with a new optional field, **When** schemas are regenerated, **Then** the JSON Schema files reflect the addition without breaking existing valid payloads.

---

### User Story 5 — Version Graduation and Release (Priority: P3)

The package maintainer graduates `spec-kitty-events` from `0.4.0-alpha` to `2.0.0-rc1`. Both CLI and SaaS CI pass conformance against the RC. The maintainer then promotes to `2.0.0`. From this point, the SemVer policy is strictly enforced: `2.x.y` for fixes, `2.(x+1).0` for additive changes, `3.0.0` for breaking changes.

**Why this priority**: The release process is the culmination — it only matters once the contracts and conformance suite are built.

**Independent Test**: Can be tested by verifying the package version, changelog, and compatibility table are present and accurate.

**Acceptance Scenarios**:

1. **Given** all conformance tests pass in both CLI and SaaS CI against `2.0.0-rc1`, **When** the maintainer promotes to `2.0.0`, **Then** the published package version is `2.0.0` with no alpha/rc suffix.
2. **Given** the `2.0.0` package is published, **When** a consumer inspects the changelog, **Then** they find migration notes from `0.4.x` to `2.0.0` including the lane mapping compatibility table.
3. **Given** the `2.0.0` package is published, **When** the compatibility table is inspected, **Then** it documents all 7 canonical lanes, all 4 sync lanes, and the complete mapping.

---

### Edge Cases

- What happens when a consumer sends an event with a `schema_version` higher than the installed package supports? The validator rejects it with a clear "unsupported schema version" error.
- What happens when a consumer uses the `doing` alias instead of `in_progress` in a canonical-lane context? The existing alias normalization in `StatusTransitionPayload` handles it; conformance tests verify this.
- What happens when a new canonical lane is added in a future `2.x` release (e.g., `PAUSED`)? The `SyncLaneV1` mapping must be extended to map it to one of the 4 sync lanes. Conformance tests verify all canonical lanes are covered by the active mapping.
- What happens during mixed-version deployments where one consumer is on `2.0.0` and another on `2.1.0`? Both versions share the same `SyncLaneV1` mapping. The `2.1.0` consumer may emit events with new optional fields that `2.0.0` consumers ignore safely.

## Requirements

### Functional Requirements

#### Lane Mapping Contract

- **FR-001**: Package MUST export a `SyncLaneV1` enum with exactly 4 values: `PLANNED`, `DOING`, `FOR_REVIEW`, `DONE`.
- **FR-002**: Package MUST export a `CANONICAL_TO_SYNC_V1` immutable mapping from all 7 `Lane` values to `SyncLaneV1` values, implementing: `PLANNED→PLANNED`, `CLAIMED→PLANNED`, `IN_PROGRESS→DOING`, `FOR_REVIEW→FOR_REVIEW`, `DONE→DONE`, `BLOCKED→DOING`, `CANCELED→PLANNED`.
- **FR-003**: Package MUST export a `canonical_to_sync_v1(lane: Lane) -> SyncLaneV1` function that applies the V1 mapping.
- **FR-004**: The V1 mapping MUST be treated as a locked contract — any behavioral change to the mapping for a given input constitutes a breaking change requiring a major version bump.
- **FR-005**: Future mapping versions (V2, V3) MUST be additive exports that coexist with V1 unchanged.

#### JSON Schema Artifacts

- **FR-006**: Package MUST ship JSON Schema files in `src/spec_kitty_events/schemas/` generated from the canonical Pydantic v2 models.
- **FR-007**: JSON Schema files MUST cover: `Event` model, all payload models (`StatusTransitionPayload`, `GatePassedPayload`, `GateFailedPayload`, lifecycle payloads), `Lane` enum, `SyncLaneV1` enum.
- **FR-008**: JSON Schema files MUST be regenerable from Pydantic models and MUST match the current model state (drift between models and schemas is a conformance failure).
- **FR-009**: JSON Schema files MUST be bundled as package data and discoverable at a well-known path after installation.

#### Conformance Fixtures

- **FR-010**: Package MUST ship canonical JSON fixture files covering: valid events for all event types, valid payloads for each payload model, lane mapping test cases (all 7 canonical lanes with expected sync output), edge cases (missing optional fields, alias normalization).
- **FR-011**: Fixture files MUST be versioned alongside the package and MUST be loadable via a public API (e.g., `load_fixtures("status_transitions")`).

#### Conformance Validator API

- **FR-012**: Package MUST provide a callable validator API in `spec_kitty_events.conformance` that accepts a payload dict and event type, and returns a structured validation result (pass/fail with specific violations).
- **FR-013**: The validator MUST validate against the canonical JSON Schema and the Pydantic model constraints (field types, required fields, enum values, business rules).
- **FR-014**: The validator MUST return machine-readable violation details (field path, expected value/type, actual value/type, violation description).

#### Pytest Conformance Suite

- **FR-015**: Package MUST provide a pytest-runnable conformance suite invocable via `pytest --pyargs spec_kitty_events.conformance`.
- **FR-016**: The conformance suite MUST test: schema validity, fixture validity, lane mapping correctness, round-trip serialization of all models, payload validation for all event types.
- **FR-017**: Conformance test failures MUST produce clear, actionable messages identifying the specific contract violation.

#### Versioning and Release

- **FR-018**: Package version MUST graduate from `0.4.0-alpha` to `2.0.0-rc1`, then to `2.0.0` after cross-repo conformance passes.
- **FR-019**: Package MUST include a compatibility table documenting: all 7 canonical lanes, all 4 sync lanes, the complete V1 mapping, required vs optional fields per event type.
- **FR-020**: Package MUST include a changelog with migration notes from `0.4.x` to `2.0.0`.
- **FR-021**: Package MUST include a `SCHEMA_VERSION` constant reflecting the locked schema version at `2.0.0`.

#### Package Structure

- **FR-022**: Conformance dependencies (if any beyond core) MUST be installable via `pip install spec-kitty-events[conformance]` optional extra.
- **FR-023**: All new public symbols (enums, functions, constants, validators) MUST be exported from `spec_kitty_events.__init__`.

### Key Entities

- **Lane**: 7-value enum representing canonical status lanes (PLANNED, CLAIMED, IN_PROGRESS, FOR_REVIEW, DONE, BLOCKED, CANCELED). Already exists.
- **SyncLaneV1**: 4-value enum representing the V1 compatibility sync lanes (PLANNED, DOING, FOR_REVIEW, DONE). New.
- **CANONICAL_TO_SYNC_V1**: Immutable mapping from Lane to SyncLaneV1. New.
- **ConformanceResult**: Structured validation result with pass/fail status and violation details. New.
- **JSON Schema files**: Machine-readable contract documents generated from Pydantic models. New.
- **Fixture files**: Canonical JSON test data for all event types and edge cases. New.

## Success Criteria

### Measurable Outcomes

- **SC-001**: Both `spec-kitty` (CLI) and `spec-kitty-saas` CI pipelines pass `pytest --pyargs spec_kitty_events.conformance` with zero failures against the published `2.0.0` package.
- **SC-002**: All 7 canonical lanes map deterministically to exactly one of 4 sync lanes via the published `canonical_to_sync_v1()` function, verified by conformance tests.
- **SC-003**: 100% of event payload models have corresponding JSON Schema files that pass round-trip validation (model → schema → validate → model).
- **SC-004**: Consumer developers can validate any event payload against the canonical contract in a single function call, receiving structured pass/fail results within 1 second.
- **SC-005**: Zero contract drift between `spec-kitty-events` schemas and consumer implementations, enforced by CI on every merge to main in both consumer repos.
- **SC-006**: Migration from `0.4.x` to `2.0.0` is documented with a compatibility table and changelog, enabling consumers to upgrade without ambiguity.

## Assumptions

- The existing 7-lane `Lane` enum and `StatusTransitionPayload` model in `status.py` are stable and will not change structurally for 2.0.0 (they were finalized in Feature 003).
- The `Event` model extensions from Feature 004 (`correlation_id`, `schema_version`, `data_tier`) are stable.
- CLI and SaaS repos will add `spec-kitty-events>=2.0.0,<3.0.0` as a dependency and integrate the conformance CI step.
- The `doing` alias for `in_progress` remains a consumer-facing convention handled by the sync mapping, not a change to the canonical enum.
- JSON Schema generation from Pydantic v2 models via `model_json_schema()` produces valid JSON Schema Draft 2020-12 output.

## Dependencies

- Pydantic v2 `model_json_schema()` for JSON Schema generation.
- `jsonschema` library (or equivalent) for schema validation in the conformance module — installed via `[conformance]` extra.
- Existing modules: `models.py`, `status.py`, `lifecycle.py`, `gates.py` — all stable from Features 001–004.

## Out of Scope

- Language-agnostic conformance runners (e.g., a standalone CLI tool for non-Python consumers) — deferred until non-Python consumers emerge.
- Splitting conformance into a separate `spec-kitty-conformance` package — single package for now.
- Automated schema migration tooling — consumers handle migration manually using the compatibility table and changelog.
- Changes to the canonical 7-lane model itself — this feature formalizes and locks it, not modifies it.
