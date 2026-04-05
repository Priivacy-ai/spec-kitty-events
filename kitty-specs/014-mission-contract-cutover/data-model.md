# Data Model: Mission Contract Cutover

**Feature**: 014-mission-contract-cutover
**Date**: 2026-04-05

## Core Entities

### Event (modified canonical envelope)

Primary file: `/private/tmp/mission/spec-kitty-events/src/spec_kitty_events/models.py`

| Field | Type | Required | Change | Notes |
|-------|------|----------|--------|-------|
| event_id | str | yes | existing | Canonical event identifier |
| event_type | str | yes | existing | Event name |
| aggregate_id | str | yes | existing | Aggregate identity |
| payload | object | yes | existing | Typed by event type |
| timestamp | datetime | yes | existing | Human-readable timestamp |
| **build_id** | **str** | **yes** | **NEW** | Canonical checkout/worktree identity |
| node_id | str | yes | clarified | Causal emitter identity only; not build identity |
| lamport_clock | int | yes | existing | Ordering field |
| causation_id | Optional[str] | no | existing | Event causation |
| project_uuid | UUID | yes | existing | Project UUID |
| project_slug | Optional[str] | no | existing | Human-readable project label |
| correlation_id | str | yes | existing | Correlation scope |
| schema_version | str | yes | existing | Envelope schema version |
| data_tier | int | no | existing | Sharing tier |

Validation rules:

- `build_id` is required on canonical events in this release.
- `node_id` remains required and retains Lamport/tiebreak semantics.
- The canonical compatibility signal used by downstream repos must match the field name and location declared in the cutover artifact.
- Any contract path that treats `node_id` as checkout identity is invalid.

### Cutover Contract Artifact (new authoritative release artifact)

Planned location: authoritative machine-readable artifact under the released package surface, determined during implementation by extending an existing release-authority manifest or adding a dedicated artifact.

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| artifact_version | semver string | yes | Version of the artifact schema itself |
| release_version | semver string | yes | `spec-kitty-events` release carrying the cutover |
| signal_field_name | string | yes | Exact on-wire field name live consumers must read |
| signal_location | string enum | yes | Where the signal appears on wire, such as `event_envelope` |
| cutover_contract_version | string | yes | Exact required compatibility-gate value carried by the canonical signal |
| accepted_major | integer | yes | Major version all live consumers must accept for canonical payloads |
| forbidden_legacy_keys | array[string] | yes | Legacy public mission-domain keys that force rejection |
| forbidden_legacy_event_names | array[string] | yes | Legacy catalog/runtime event names forbidden for this release policy |
| forbidden_legacy_aggregate_names | array[string] | yes | Legacy aggregate names that force rejection on live paths |
| forbidden_legacy_contract_surfaces | array[string] | no | Optional extra forbidden surfaces if needed |
| notes | array[string] | no | Human-readable release notes aligned with the artifact |

Validation rules:

- The artifact must be machine-readable and packaged with the release.
- The artifact is the single source of truth for downstream compatibility gating.
- The artifact must bind downstream compatibility checks to one exact on-wire signal name and location.
- The artifact must define the accepted major-version policy explicitly rather than leaving consumers to infer it.
- The artifact must make legacy aggregate-name rejection first-class alongside legacy keys and event names.
- Downstream repos must not replace artifact semantics with hand-maintained constant lists.

### Mission Catalog Payloads (modified and new)

Primary files: `/private/tmp/mission/spec-kitty-events/src/spec_kitty_events/lifecycle.py`, `/private/tmp/mission/spec-kitty-events/src/spec_kitty_events/schemas/generate.py`

| Payload/Event | Change | Canonical fields |
|---------------|--------|------------------|
| MissionCreatedPayload | new or renamed catalog payload | `mission_slug`, `mission_number`, `mission_type`, plus existing mission metadata |
| MissionClosedPayload | new or renamed catalog payload | `mission_slug`, `mission_number`, `mission_type`, closure metadata |
| MissionCompletedPayload | retained lifecycle meaning only | No catalog terminal overloading |
| MissionRunCompletedPayload | retained runtime meaning only | No alias from `MissionCompleted` |

Validation rules:

- Catalog events use `MissionCreated` and `MissionClosed` only.
- `MissionCompleted` remains lifecycle-only.
- `MissionRunCompleted` remains runtime-only.

### Mission Projection Models (modified)

Primary files:

- `/private/tmp/mission/spec-kitty-events/src/spec_kitty_events/dossier.py`
- `/private/tmp/mission/spec-kitty-events/src/spec_kitty_events/decisionpoint.py`
- `/private/tmp/mission/spec-kitty-events/src/spec_kitty_events/mission_audit.py`
- `/private/tmp/mission/spec-kitty-events/src/spec_kitty_events/status.py`
- `/private/tmp/mission/spec-kitty-events/src/spec_kitty_events/mission_next.py`

| Field | Current legacy surface | Canonical target |
|-------|------------------------|------------------|
| mission instance identifier | `feature_slug` | `mission_slug` |
| mission numeric identifier | `feature_number` | `mission_number` |
| mission workflow/template identifier | `mission_key` | `mission_type` |

Validation rules:

- No public mission-domain contract may continue exposing `feature_slug` or `feature_number`.
- No public mission-domain contract may continue exposing `mission_key` where it means workflow/template identity.
- Documentation for `Project` identity may describe team-scoped semantics, but enforcement is downstream-owned.

## Relationships

| Source | Relationship | Target |
|--------|--------------|--------|
| Cutover Contract Artifact | governs acceptance of | Event envelope and mission-domain payloads |
| Event | wraps | Mission catalog payloads, runtime payloads, projection payloads |
| Conformance validators/helpers | interpret | Cutover Contract Artifact |
| Downstream repos | enforce | Artifact semantics in runtime gates |
| Migration workflows | rewrite | Legacy historical payloads into canonical payloads |

## State and Transition Rules

### Compatibility gating state

| Input condition | Classification | Outcome |
|----------------|----------------|---------|
| Required cutover signal present, accepted major matches, and no forbidden legacy surfaces present | canonical | Acceptable for canonical validation |
| Required cutover signal missing | pre-cutover | Reject on live ingestion paths |
| Required cutover signal present but accepted major does not match | pre-cutover | Reject on live ingestion paths |
| Forbidden legacy key or event name present | pre-cutover | Reject on live ingestion paths |
| Forbidden legacy aggregate name present | pre-cutover | Reject on live ingestion paths |
| Legacy historical payload in offline rewrite workflow | migration-only | Rewrite into canonical form; do not pass through runtime gate |

### Event-name semantics

| Event name | Meaning after cutover |
|-----------|------------------------|
| MissionCreated | Mission catalog creation |
| MissionClosed | Mission catalog closure |
| MissionCompleted | Mission lifecycle completion only |
| MissionRunCompleted | Mission runtime/run completion only |

## Generated and authoritative artifact rules

- Authoritative published contract artifacts must be rewritten to canonical mission/build terminology.
- Generated or replayable artifacts may be regenerated destructively if their intended semantics are preserved.
- `kitty-specs/*/meta.json` remains planning metadata outside this contract cutover scope.
