# Additive Event Contracts for Charter Phase 4/5/6

**Mission ID**: `01KP343JBG2V7WSWSDJ0HD76BR`
**Mission Type**: software-dev
**Target Branch**: main
**Charter Epic**: #461
**Date**: 2026-04-13
**Schema Baseline**: spec-kitty-events 3.0.0

---

## Overview

This specification defines the smallest additive event-contract tranche needed to support charter epic #461 Phase 4/5/6 work. It adds two new domain modules to `spec-kitty-events` and explicitly evaluates two candidate contract surfaces that do not yet have concrete consumers.

The tranche is strictly additive: no existing event types, payloads, or envelope fields are modified. All new events use the existing `schema_version="3.0.0"` envelope and follow established domain module conventions (frozen Pydantic payloads, FrozenSet type registries, conformance fixtures, dual-layer validation).

### Contract Surfaces

| Surface | Decision | Rationale |
|---------|----------|-----------|
| Profile Invocation | **Add** | Concrete consumer: SaaS runtime dashboard needs to show which profile governed each execution step |
| Retrospective | **Add** | Concrete consumer: post-merge closeout flow needs durable record of retro completion or skip |
| Glossary Summary Drift | **Defer** | No concrete Phase 4/5/6 consumer identified; current 8 glossary events cover interaction-level needs |
| Provenance Query/Summary | **No new event** | `ProvenanceRef` value object already serves this need; query is a read-path concern, not an event |

---

## Actors

- **Runtime Orchestrator**: The spec-kitty runtime (`spec-kitty next --agent <name>`) that resolves profiles, issues steps, and drives the mission execution loop.
- **Human Operator**: A person who triggers, skips, or reviews retrospectives and other post-merge steps.
- **SaaS Consumer**: Downstream projection services that subscribe to event streams for dashboards, audit trails, and analytics.
- **Conformance CI**: Automated test infrastructure that validates every event against its contract.

---

## User Scenarios & Testing

### Scenario 1: Profile Invocation Tracking

A runtime orchestrator resolves agent profile `architect-v2` for WP03 implementation. Before dispatching the step, it emits a `ProfileInvocationStarted` event carrying the resolved profile identity, the bound action, and the runtime context. The SaaS dashboard projects this event to show "WP03 executing under architect-v2 profile."

**Acceptance**: Given a valid `ProfileInvocationStarted` event, when a SaaS consumer receives it, then the consumer can extract the profile slug, action scope, mission context, and actor identity without replaying prior events.

### Scenario 2: Retrospective Completed

After a mission merges successfully, the runtime/operator runs the retrospective step. It produces an artifact (e.g., a retro summary). The runtime emits `RetrospectiveCompleted` with a reference to the artifact. The SaaS audit trail records this as a durable closeout signal.

**Acceptance**: Given a `RetrospectiveCompleted` event, when a SaaS consumer projects it, then the consumer can determine that the mission's retrospective ran, who triggered it, and optionally locate the retro artifact.

### Scenario 3: Retrospective Skipped

An operator decides not to run the retrospective for a trivial mission. The runtime emits `RetrospectiveSkipped` with the operator's reason. The SaaS audit trail records the explicit skip rather than inferring it from absence.

**Acceptance**: Given a `RetrospectiveSkipped` event, when a SaaS consumer projects it, then the consumer can distinguish an intentional skip (with reason) from a retrospective that simply hasn't happened yet.

### Scenario 4: Unknown Event Type Forward Compatibility

A consumer running an older version of `spec-kitty-events` receives a `ProfileInvocationStarted` event it doesn't recognize. The event passes envelope validation but the consumer logs an unknown-type warning and skips payload validation. No crash, no data loss.

**Acceptance**: Given an event with an unrecognized `event_type`, when the envelope is valid, then the consumer can store the event and skip payload validation without error.

---

## Functional Requirements

| ID | Requirement | Status |
|----|-------------|--------|
| FR-001 | The library SHALL define a `ProfileInvocationStarted` event type with a typed Pydantic payload model in a new `profile_invocation.py` domain module. | Proposed |
| FR-002 | The `ProfileInvocationStartedPayload` SHALL include fields: `mission_id` (str, required), `run_id` (str, required), `step_id` (str, required), `action` (str, required), `profile_slug` (str, required), `profile_version` (Optional[str]), `actor` (RuntimeActorIdentity, required), and `governance_scope` (Optional[str]). | Proposed |
| FR-003 | The library SHALL define a `RetrospectiveCompleted` event type with a typed Pydantic payload model in a new `retrospective.py` domain module. | Proposed |
| FR-004 | The `RetrospectiveCompletedPayload` SHALL include fields: `mission_id` (str, required), `actor` (str, required), `trigger_source` (Literal["runtime", "operator", "policy"], required), `artifact_ref` (Optional[ProvenanceRef]), and `completed_at` (str, ISO 8601, required). | Proposed |
| FR-005 | The library SHALL define a `RetrospectiveSkipped` event type with a typed Pydantic payload model in the `retrospective.py` domain module. | Proposed |
| FR-006 | The `RetrospectiveSkippedPayload` SHALL include fields: `mission_id` (str, required), `actor` (str, required), `trigger_source` (Literal["runtime", "operator", "policy"], required), `skip_reason` (str, required, min_length=1), and `skipped_at` (str, ISO 8601, required). | Proposed |
| FR-007 | Each new domain module SHALL export a `FrozenSet[str]` constant (`PROFILE_INVOCATION_EVENT_TYPES`, `RETROSPECTIVE_EVENT_TYPES`) enumerating its event type strings. | Proposed |
| FR-008 | Each new domain module SHALL define a domain schema version constant (`PROFILE_INVOCATION_SCHEMA_VERSION`, `RETROSPECTIVE_SCHEMA_VERSION`) set to `"3.1.0"`. | Proposed |
| FR-009 | All new payload models SHALL be registered in `conformance/validators.py` in both `_EVENT_TYPE_TO_MODEL` and `_EVENT_TYPE_TO_SCHEMA` dispatch maps. | Proposed |
| FR-010 | All new payload models and constants SHALL be re-exported from `__init__.py` and listed in `__all__`. | Proposed |
| FR-011 | JSON schemas SHALL be auto-generated for all new payload models via `python -m spec_kitty_events.schemas.generate` and committed to `src/spec_kitty_events/schemas/`. | Proposed |
| FR-012 | Conformance test fixtures (valid and invalid) SHALL be created for each new event type and registered in `conformance/fixtures/manifest.json`. | Proposed |
| FR-013 | All new payload models SHALL use `ConfigDict(frozen=True, extra="forbid")` to enforce immutability and reject unknown fields. | Proposed |
| FR-014 | The `ProfileInvocationStartedPayload` SHALL reuse the existing `RuntimeActorIdentity` value object from `mission_next.py` for the `actor` field. | Proposed |
| FR-015 | The `RetrospectiveCompletedPayload` SHALL reuse the existing `ProvenanceRef` value object from `dossier.py` for the optional `artifact_ref` field. | Proposed |

---

## Non-Functional Requirements

| ID | Requirement | Threshold | Status |
|----|-------------|-----------|--------|
| NFR-001 | All new payload models SHALL pass Pydantic validation in under 1ms per event on a standard developer machine. | < 1ms per validation | Proposed |
| NFR-002 | JSON schema generation SHALL complete for all new models without drift when run via `--check` mode. | Zero drift on CI | Proposed |
| NFR-003 | All new code SHALL pass `mypy --strict` type checking with zero errors. | 0 mypy errors | Proposed |
| NFR-004 | Conformance test suite SHALL achieve 100% coverage of new payload field validation paths (valid + invalid). | 100% field coverage | Proposed |
| NFR-005 | New domain modules SHALL not increase import time of the `spec_kitty_events` package by more than 5%. | < 5% import time increase | Proposed |

---

## Constraints

| ID | Constraint | Status |
|----|------------|--------|
| C-001 | All new events SHALL use the existing `schema_version="3.0.0"` envelope. The envelope model MUST NOT be modified. | Active |
| C-002 | All new events are additive only. No existing event type, payload field, or constant SHALL be modified or removed. | Active |
| C-003 | No new events SHALL be added for glossary summary drift in this tranche. This is deferred until a concrete consumer is identified. | Active |
| C-004 | No new event type SHALL be created for provenance query or summary. The existing `ProvenanceRef` value object is sufficient. | Active |
| C-005 | The package version SHALL be bumped from `3.0.0` to `3.1.0` to reflect the additive contract surface. The bump is minor (additive, backward-compatible). | Active |
| C-006 | New domain modules SHALL follow the established module structure: Section 1 (Constants), Section 2 (Value Objects if needed), Section 3 (Enums if needed), Section 4 (Payload Models), Section 5 (Reducer Output Models if needed), Section 6 (Reducer if needed). | Active |
| C-007 | `ProfileInvocationCompleted` and `ProfileInvocationFailed` event types SHALL NOT be added in this tranche. They are reserved for a future tranche when a concrete closure consumer exists. | Active |
| C-008 | The retrospective domain SHALL NOT include a reducer in this tranche. The two events are terminal signals, not a state machine requiring projection. | Active |
| C-009 | All new events belong in `spec-kitty-events` (the shared library), not as local-only repo artifacts, because SaaS consumers need to validate and project them. | Active |
| C-010 | New events SHALL use `data_tier=0` (local) by default, consistent with existing domain events. The emitter controls elevation to higher tiers. | Active |

---

## What Should NOT Become an Event

The following are explicitly out of scope as event contracts. They are either internal runtime details, read-path concerns, or lack a concrete consumer.

| Candidate | Reason NOT to eventify |
|-----------|----------------------|
| Per-consultation governance lookups | Internal to the runtime profile executor. High-frequency, low-signal. Would create observation spam with no consumer. Profile invocation start is the useful boundary signal. |
| Internal prompt/context reads | These are implementation details of how the runtime assembles context. No downstream consumer needs this granularity. |
| Profile resolution logic | The resolution algorithm (which profile wins, fallback chains) is an internal concern. Only the *result* (which profile was bound) matters to consumers. |
| Glossary summary/drift surfacing | Deferred. The existing 8 glossary events cover interaction-level mutations. Mission-level summaries need a concrete consumer and payload shape before contracting. |
| Provenance query results | Provenance is a read-path concern. `ProvenanceRef` is a value object embedded in existing payloads, not an event stream. Adding a provenance-query event would conflate commands with events. |
| Speculative Phase 7+ events | This tranche serves Phase 4/5/6 only. Do not contract events for phases that don't exist yet. |
| Retrospective content/body | The retro artifact itself is a file, not event payload. The event records that the retro happened and optionally points to the artifact via `ProvenanceRef`. |

---

## Payload Inventory

### Domain: Profile Invocation (`profile_invocation.py`)

**Domain schema version**: `3.1.0`

#### `ProfileInvocationStarted`

Emitted when the runtime begins executing a step under a resolved agent profile.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `mission_id` | `str` | Yes | Mission identifier (ULID or slug) |
| `run_id` | `str` | Yes | Run identifier from `MissionRunStarted` |
| `step_id` | `str` | Yes | Step being executed (e.g., "implement", "review") |
| `action` | `str` | Yes | Bound action name (e.g., "implement WP03") |
| `profile_slug` | `str` | Yes | Resolved agent profile slug (e.g., "architect-v2") |
| `profile_version` | `Optional[str]` | No | Profile version if versioned profiles are in use |
| `actor` | `RuntimeActorIdentity` | Yes | Runtime actor identity (reused from `mission_next.py`) |
| `governance_scope` | `Optional[str]` | No | Governance scope string if the profile specifies one |

**Aggregate ID convention**: `mission_id` (the mission being executed)

**Correlation**: Links to the `MissionRunStarted` event via `correlation_id`. The `run_id` field provides direct run-level correlation.

#### Reserved (NOT in this tranche)

- `ProfileInvocationCompleted` -- Reserved constant, payload deferred (same pattern as `NextStepPlanned`)
- `ProfileInvocationFailed` -- Reserved constant, payload deferred

---

### Domain: Retrospective (`retrospective.py`)

**Domain schema version**: `3.1.0`

#### `RetrospectiveCompleted`

Emitted when a retrospective step runs and produces a durable outcome.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `mission_id` | `str` | Yes | Mission identifier |
| `actor` | `str` | Yes | Actor who triggered/completed the retrospective |
| `trigger_source` | `Literal["runtime", "operator", "policy"]` | Yes | What initiated the retrospective |
| `artifact_ref` | `Optional[ProvenanceRef]` | No | Reference to the retro artifact if one was produced (reused from `dossier.py`) |
| `completed_at` | `str` | Yes | ISO 8601 timestamp of completion |

**Aggregate ID convention**: `mission_id`

#### `RetrospectiveSkipped`

Emitted when a retrospective step is explicitly skipped.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `mission_id` | `str` | Yes | Mission identifier |
| `actor` | `str` | Yes | Actor who decided to skip |
| `trigger_source` | `Literal["runtime", "operator", "policy"]` | Yes | What would have initiated the retrospective |
| `skip_reason` | `str` | Yes | Why the retrospective was skipped (min_length=1) |
| `skipped_at` | `str` | Yes | ISO 8601 timestamp of the skip decision |

**Aggregate ID convention**: `mission_id`

---

## Versioning Strategy

### Package Version

- **Current**: `3.0.0`
- **After this tranche**: `3.1.0`
- **Rationale**: Minor version bump. Additive-only changes. No breaking changes. SaaS consumers running `>=3.0.0` continue to work; consumers that want the new event types upgrade to `>=3.1.0`.

### Envelope Schema Version

- **Unchanged**: `schema_version="3.0.0"` on the wire.
- **Rationale**: The envelope format is not changing. New events use the same envelope. The `schema_version` field signals envelope compatibility, not domain availability.

### Domain Schema Versions

- **New constant**: `PROFILE_INVOCATION_SCHEMA_VERSION = "3.1.0"` in `profile_invocation.py`
- **New constant**: `RETROSPECTIVE_SCHEMA_VERSION = "3.1.0"` in `retrospective.py`
- **Rationale**: Follows the existing pattern where each domain module declares its own schema version (e.g., `AUDIT_SCHEMA_VERSION = "2.5.0"`, `CONNECTOR_SCHEMA_VERSION = "2.8.0"`). The `3.1.0` value aligns with the package version bump.

### Backward Compatibility

| Consumer version | Behavior with new events |
|-----------------|-------------------------|
| `3.0.x` consumer | Envelope validates. Unknown `event_type` logged as warning. Payload validation skipped. No crash. |
| `3.1.x` consumer | Full dual-layer validation of new event types. |
| SaaS projections | Ignore unknown event types until projection code is deployed for the new types. |

### Reserved Event Types

`ProfileInvocationCompleted` and `ProfileInvocationFailed` are defined as string constants but their payload contracts are deferred (same pattern as `NextStepPlanned` in `mission_next.py`). The conformance suite SHALL NOT include fixtures for reserved types until their payloads are specified.

---

## Migration / Compatibility Strategy

1. **No migration required**: This tranche is purely additive. No schema migration, no data migration, no cutover signal change.

2. **Deployment order**: The `spec-kitty-events` package must be released at `3.1.0` before any runtime emitter references the new event types. SaaS consumers can deploy projection support at their own pace.

3. **Forward compatibility**: Existing consumers already handle unknown event types gracefully (envelope validates, unknown type is logged, no crash). This is tested by the conformance suite.

4. **Value object reuse**: `RuntimeActorIdentity` (from `mission_next.py`) and `ProvenanceRef` (from `dossier.py`) are reused in the new payloads. No duplication, no new value objects.

5. **Import path stability**: New domain modules (`profile_invocation.py`, `retrospective.py`) are added alongside existing modules. No import paths change.

---

## Conformance Test Plan

### Fixture Requirements

For each new event type, create:

| Fixture Category | Files | Purpose |
|-----------------|-------|---------|
| `profile_invocation/valid/` | `profile_invocation_started_minimal.json`, `profile_invocation_started_full.json` | Validate minimal required fields and full payload with all optional fields |
| `profile_invocation/invalid/` | `profile_invocation_started_missing_profile_slug.json`, `profile_invocation_started_empty_action.json` | Validate rejection of missing/invalid required fields |
| `retrospective/valid/` | `retrospective_completed_minimal.json`, `retrospective_completed_with_artifact.json`, `retrospective_skipped.json` | Validate both event types with minimal and full payloads |
| `retrospective/invalid/` | `retrospective_completed_missing_actor.json`, `retrospective_skipped_empty_reason.json` | Validate rejection of missing/invalid required fields |

### Test Files

| Test File | Scope |
|-----------|-------|
| `tests/test_profile_invocation_conformance.py` | Pydantic + JSON Schema validation of profile invocation fixtures |
| `tests/test_retrospective_conformance.py` | Pydantic + JSON Schema validation of retrospective fixtures |
| `tests/unit/test_profile_invocation.py` | Unit tests for payload model construction, field validation, immutability |
| `tests/unit/test_retrospective.py` | Unit tests for payload model construction, field validation, immutability, ProvenanceRef embedding |

### CI Integration

- `python -m spec_kitty_events.schemas.generate --check` must pass with zero drift after adding new JSON schemas.
- `mypy --strict` must pass with zero errors on new modules.
- All new fixtures must be registered in `conformance/fixtures/manifest.json`.
- The conformance loader's `KNOWN_CATEGORIES` must be extended with `"profile_invocation"` and `"retrospective"`.

### Property Tests

- All new payload models should be tested with Hypothesis strategies to verify:
  - Roundtrip serialization (`model_dump()` -> `model_validate()`)
  - Frozen immutability (assignment raises `ValidationError`)
  - `extra="forbid"` rejects unknown fields

---

## Event Placement Decision

All events in this tranche belong in `spec-kitty-events` (the shared library), not as local-only artifacts.

**Reasoning**: Both profile invocation and retrospective events have identified SaaS consumers (dashboard projection, audit trail). Events that exist only for local observability (e.g., debug logs, internal runtime tracing) should NOT be promoted to the shared contract library. The test for inclusion is: "Does a consumer outside the emitting process need to validate and project this event?"

| Event | In `spec-kitty-events`? | Why |
|-------|------------------------|-----|
| `ProfileInvocationStarted` | Yes | SaaS dashboard projects profile-per-step data |
| `RetrospectiveCompleted` | Yes | SaaS audit trail records closeout signals |
| `RetrospectiveSkipped` | Yes | SaaS audit trail distinguishes skip from absence |
| Profile consultation traces | No | Internal runtime detail, no external consumer |
| Glossary summary drift | Not yet | No consumer identified; defer |

---

## Assumptions

1. The `RuntimeActorIdentity` value object from `mission_next.py` is stable and its import path will not change. If it moves, a re-export alias should be maintained.
2. `ProvenanceRef` from `dossier.py` is the canonical way to reference artifacts from event payloads. No alternative provenance mechanism is needed.
3. The reserved event type pattern (constant defined, payload deferred, no fixtures) established by `NextStepPlanned` is the accepted convention for forward-declaring event types.
4. `trigger_source` as a Literal field is preferred over a free-form string because the set of retrospective triggers is small and known.
5. The conformance fixture loader supports adding new categories without breaking existing test parametrization.

---

## Success Criteria

1. A SaaS consumer can determine which agent profile governed each execution step in a mission run by projecting `ProfileInvocationStarted` events, without replaying the full mission event stream.
2. A SaaS consumer can determine the retrospective status of any completed mission (completed with artifact, completed without artifact, explicitly skipped with reason, or not yet recorded) by projecting retrospective events.
3. All new event types pass dual-layer contract validation with zero violations on valid test fixtures and appropriate violations on invalid test fixtures.
4. The package upgrade from `3.0.0` to `3.1.0` requires zero changes to existing consumers that do not use the new event types.
5. Automated quality gates pass with zero schema drift, zero type-checking errors, and zero contract validation failures after the tranche lands.

---

## Key Entities

| Entity | Description | Fields |
|--------|-------------|--------|
| `ProfileInvocationStartedPayload` | Frozen Pydantic model for profile invocation start events | mission_id, run_id, step_id, action, profile_slug, profile_version, actor, governance_scope |
| `RetrospectiveCompletedPayload` | Frozen Pydantic model for retrospective completion events | mission_id, actor, trigger_source, artifact_ref, completed_at |
| `RetrospectiveSkippedPayload` | Frozen Pydantic model for retrospective skip events | mission_id, actor, trigger_source, skip_reason, skipped_at |
| `RuntimeActorIdentity` | Reused value object from mission_next.py | actor_id, actor_type, display_name, provider, model, tool |
| `ProvenanceRef` | Reused value object from dossier.py | source_event_ids, git_sha, git_ref, actor_id, actor_kind, revised_at |

---

## Dependencies

- `spec-kitty-events` 3.0.0 (current baseline)
- Pydantic v2 (existing dependency)
- `jsonschema` (existing optional conformance dependency)
- No new external dependencies required
