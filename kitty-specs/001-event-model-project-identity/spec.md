# Feature Specification: Event Model Project Identity

**Feature Branch**: `001-event-model-project-identity`
**Created**: 2026-02-07
**Status**: Draft
**Input**: Extend spec-kitty-events Event model with project identity fields for cross-team event synchronization

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Emit Identity-Aware Events (Priority: P1)

A CLI developer creates events that carry project identity so the SaaS platform can associate events with the correct project. When the CLI emits a `WPStatusChanged` or `FeatureCreated` event, the event envelope includes the originating project's UUID and human-readable slug.

**Why this priority**: Without project identity on events, the SaaS cannot materialize Projects, Features, or WorkPackages from incoming events. This is the foundational capability that unblocks both CLI sync and SaaS dashboards.

**Independent Test**: Create an Event with `project_uuid` and `project_slug`, serialize it, deserialize it, and verify both fields round-trip correctly.

**Acceptance Scenarios**:

1. **Given** a valid UUID and slug, **When** an Event is created with `project_uuid` and `project_slug`, **Then** both fields are stored and accessible on the Event instance.
2. **Given** a valid UUID and no slug, **When** an Event is created with only `project_uuid`, **Then** the Event is valid and `project_slug` is `None`.
3. **Given** no `project_uuid`, **When** an Event is created without `project_uuid`, **Then** a validation error is raised.

---

### User Story 2 - Serialize and Deserialize Events with Identity (Priority: P1)

Events are serialized to dictionaries for transmission over WebSocket and batch sync APIs. The serialization must include `project_uuid` and `project_slug` so downstream consumers (SaaS ingestion, storage adapters) receive the full envelope.

**Why this priority**: Serialization is the transport mechanism. If identity fields are lost during `to_dict()` / `from_dict()`, the SaaS cannot process them.

**Independent Test**: Call `to_dict()` on an Event with identity fields, then `from_dict()` on the result, and verify the round-trip preserves all fields including `project_uuid` and `project_slug`.

**Acceptance Scenarios**:

1. **Given** an Event with `project_uuid` and `project_slug`, **When** `to_dict()` is called, **Then** the resulting dictionary includes `project_uuid` as a string and `project_slug` as a string.
2. **Given** a dictionary with valid `project_uuid`, **When** `from_dict()` is called, **Then** the resulting Event has the correct `project_uuid` as a UUID type.
3. **Given** a dictionary with `project_slug` set to `null`, **When** `from_dict()` is called, **Then** the resulting Event has `project_slug` as `None`.

---

### User Story 3 - Validate Project Identity Fields (Priority: P2)

The library validates that `project_uuid` is a properly formatted UUID when present, preventing malformed identifiers from propagating through the event system.

**Why this priority**: Data integrity is critical for a distributed event system. Invalid UUIDs would cause failures at the SaaS ingestion layer, which is harder to debug than catching them at creation time.

**Independent Test**: Attempt to create Events with invalid UUID formats and verify validation rejects them.

**Acceptance Scenarios**:

1. **Given** a valid UUID4 string, **When** an Event is created with it as `project_uuid`, **Then** the Event is valid.
2. **Given** a malformed string (e.g., "not-a-uuid"), **When** an Event is created with it as `project_uuid`, **Then** a validation error is raised.
3. **Given** an empty string, **When** used as `project_uuid`, **Then** a validation error is raised.

---

### User Story 4 - Updated Documentation (Priority: P2)

A developer integrating spec-kitty-events reads the README quickstart and sees how to include `project_uuid` when creating events. The documentation reflects the current model so new adopters are not confused by outdated examples.

**Why this priority**: The README is the primary onboarding surface. Outdated examples cause integration friction for CLI and SaaS teams.

**Independent Test**: Follow the README quickstart examples verbatim and verify they execute without errors against the updated library.

**Acceptance Scenarios**:

1. **Given** the updated README, **When** a developer copies the quickstart code, **Then** it runs successfully and produces an Event with `project_uuid`.
2. **Given** the updated README, **When** a developer reads the API overview, **Then** `project_uuid` and `project_slug` are listed as Event fields.

---

### Edge Cases

- What happens when `project_uuid` is provided as a UUID object instead of a string? The model should accept both and normalize to UUID.
- What happens when `project_slug` contains special characters or spaces? Validation should accept any string (slug enforcement is the CLI's responsibility, not the library's).
- What happens when `project_uuid` is `None`? Validation must reject it since the field is required.
- How do existing storage adapters handle the new fields? `to_dict()` / `from_dict()` must include them so storage adapters automatically persist them.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The `Event` model MUST include a `project_uuid` field of type UUID that is required on every event.
- **FR-002**: The `Event` model MUST include a `project_slug` field of type optional string that defaults to `None`.
- **FR-003**: The `Event.to_dict()` method MUST include `project_uuid` (as string) and `project_slug` in the output dictionary.
- **FR-004**: The `Event.from_dict()` class method MUST parse `project_uuid` from string back to UUID and `project_slug` from string or null.
- **FR-005**: The `Event` model MUST validate that `project_uuid` is a well-formed UUID, rejecting malformed values with a validation error.
- **FR-006**: The library version MUST be bumped from `0.1.0-alpha` to `0.1.1-alpha` in `pyproject.toml`.
- **FR-007**: The README quickstart MUST demonstrate creating an Event with `project_uuid`.
- **FR-008**: All existing tests MUST be updated to supply `project_uuid` since it is now required.
- **FR-009**: New tests MUST verify `project_uuid` presence, validation, and serialization round-trip.
- **FR-010**: The `__init__.py` public API exports MUST remain unchanged (Event is already exported; no new exports needed for the new fields).

### Key Entities

- **Event**: The core immutable event envelope. Gains `project_uuid` (UUID, required) and `project_slug` (string, optional). Represents a single state-change in a project's lifecycle. Identified by `event_id` (ULID), scoped by `project_uuid`.
- **Project Identity**: The combination of `project_uuid` and `project_slug` that ties an event to a specific project. Generated by the CLI during `spec-kitty init`, consumed by the SaaS during event ingestion.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of events created by the library include a valid `project_uuid` field.
- **SC-002**: All existing tests pass after updating to supply the new required field, with zero regressions.
- **SC-003**: New test coverage for `project_uuid` validation covers valid UUIDs, malformed strings, empty strings, and missing values.
- **SC-004**: README quickstart examples execute successfully against the updated library when copied verbatim.
- **SC-005**: Serialization round-trip (`to_dict()` then `from_dict()`) preserves `project_uuid` and `project_slug` with 100% fidelity.

## Assumptions

- The CLI and SaaS teams are updating simultaneously, so no backward compatibility shim is needed for events without `project_uuid`.
- `project_slug` validation (format, uniqueness) is the responsibility of the CLI, not this library. The library stores whatever string is provided.
- UUID version is not enforced — any valid UUID format (v1, v4, etc.) is accepted.
- The `project_uuid` field follows the same immutability guarantees as all other Event fields (Pydantic frozen model).

## Dependencies

- **Downstream**: CLI team (`emitter.py`, `events.py`) must populate `project_uuid` in every emitted event.
- **Downstream**: SaaS team (`models.py`, `consumers.py`) must read `project_uuid` from ingested events.
- **Upstream**: None — this library has no external dependencies beyond Pydantic and python-ulid, which already support UUID types.
