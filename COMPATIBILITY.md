# Compatibility Guide

This document is the definitive reference for `spec-kitty-events` consumers (CLI and SaaS teams)
migrating from `0.x` to `2.0.0`. It covers the lane mapping contract, required/optional fields
per event type, versioning policy, and CI integration steps.

## Table of Contents

- [Lane Mapping Contract](#lane-mapping-contract)
- [Event Type Field Reference](#event-type-field-reference)
- [Collaboration Event Contracts](#collaboration-event-contracts)
- [Mission-Next Runtime Contracts](#mission-next-runtime-contracts)
- [Versioning Policy](#versioning-policy)
- [Migration Guide (0.x to 2.0.0)](#migration-guide-0x-to-200)
- [Consumer CI Integration](#consumer-ci-integration)
- [SCHEMA_VERSION Documentation](#schema_version-documentation)
- [Functional Requirements Traceability](#functional-requirements-traceability)

---

## Lane Mapping Contract

The `SyncLaneV1` mapping collapses the 7 canonical `Lane` values into 4 consumer-facing sync
lanes. This mapping is **locked** for the entire 2.x series. Changing any output for a given
input constitutes a breaking change requiring a `3.0.0` release.

### Lane Mapping Table

| Canonical Lane (`Lane`) | Sync Lane (`SyncLaneV1`) | Rationale |
|---|---|---|
| `planned` | `planned` | Direct mapping |
| `claimed` | `planned` | Pre-work state, collapses to planned |
| `in_progress` | `doing` | Consumer-facing alias for active work |
| `for_review` | `for_review` | Direct mapping |
| `done` | `done` | Direct mapping |
| `blocked` | `doing` | Mid-work state, collapses to doing |
| `canceled` | `planned` | Resets to planned in sync model |

### Usage

```python
from spec_kitty_events import Lane, SyncLaneV1, canonical_to_sync_v1

# Function API (recommended)
sync_lane = canonical_to_sync_v1(Lane.IN_PROGRESS)
assert sync_lane == SyncLaneV1.DOING

# Direct mapping access
from spec_kitty_events import CANONICAL_TO_SYNC_V1
assert CANONICAL_TO_SYNC_V1[Lane.BLOCKED] == SyncLaneV1.DOING
```

### Mapping Guarantees

- The `CANONICAL_TO_SYNC_V1` mapping is an **immutable** `MappingProxyType`. It cannot be
  modified at runtime.
- Every `Lane` member has exactly one `SyncLaneV1` target. There are no unmapped lanes.
- The mapping is exercised by conformance fixtures in the `lane_mapping` category.

---

## Event Type Field Reference

### `Event` (envelope)

The `Event` model is the top-level envelope for all events. All payload-specific data goes in the
`payload` dictionary.

| Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `event_id` | `str` (ULID, 26 chars) | Yes | — | Unique event identifier |
| `event_type` | `str` | Yes | — | Event type (e.g., `"WPStatusChanged"`) |
| `aggregate_id` | `str` | Yes | — | Entity this event modifies |
| `payload` | `dict` | No | `{}` | Event-specific data |
| `timestamp` | `datetime` | Yes | — | Wall-clock time (not for ordering) |
| `node_id` | `str` | Yes | — | Emitting node identifier |
| `lamport_clock` | `int` (>= 0) | Yes | — | Lamport logical clock value |
| `causation_id` | `str` (ULID) or `null` | No | `None` | Parent event ID |
| `project_uuid` | `UUID` | Yes | — | Project UUID |
| `project_slug` | `str` or `null` | No | `None` | Human-readable project slug |
| `correlation_id` | `str` (ULID, 26 chars) | Yes | — | Mission execution group ID |
| `schema_version` | `str` (semver) | No | `"1.0.0"` | Envelope schema version |
| `data_tier` | `int` (0-4) | No | `0` | Data sharing tier |

### `WPStatusChanged` (`StatusTransitionPayload`)

| Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `feature_slug` | `str` | Yes | — | Feature identifier |
| `wp_id` | `str` | Yes | — | Work package identifier |
| `from_lane` | `Lane` or `null` | No | `None` | Previous lane (null for initial) |
| `to_lane` | `Lane` | Yes | — | Target lane |
| `actor` | `str` | Yes | — | Actor performing the transition |
| `force` | `bool` | No | `False` | Whether this is a forced transition |
| `reason` | `str` or `null` | No | `None` | Transition reason |
| `execution_mode` | `ExecutionMode` | Yes | — | Worktree or direct repo |
| `review_ref` | `str` or `null` | No | `None` | Review reference (for rollbacks) |
| `evidence` | `DoneEvidence` or `null` | No | `None` | Required evidence for done transitions |

### `GatePassed` (`GatePassedPayload`)

| Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `gate_name` | `str` | Yes | — | CI gate name (e.g., `"ci/build"`) |
| `gate_type` | `"ci"` | Yes | — | Gate type (only `"ci"` supported) |
| `conclusion` | `"success"` | Yes | — | Must be `"success"` |
| `external_provider` | `"github"` | Yes | — | Provider (only `"github"` supported) |
| `check_run_id` | `int` (> 0) | Yes | — | GitHub check run ID |
| `check_run_url` | `AnyHttpUrl` | Yes | — | URL of the check run |
| `delivery_id` | `str` | Yes | — | Webhook delivery idempotency key |
| `pr_number` | `int` (> 0) or `null` | No | `None` | Associated pull request number |

### `GateFailed` (`GateFailedPayload`)

| Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `gate_name` | `str` | Yes | — | CI gate name |
| `gate_type` | `"ci"` | Yes | — | Gate type |
| `conclusion` | `"failure"` / `"timed_out"` / `"cancelled"` / `"action_required"` | Yes | — | Failure conclusion |
| `external_provider` | `"github"` | Yes | — | Provider |
| `check_run_id` | `int` (> 0) | Yes | — | GitHub check run ID |
| `check_run_url` | `AnyHttpUrl` | Yes | — | URL of the check run |
| `delivery_id` | `str` | Yes | — | Webhook delivery idempotency key |
| `pr_number` | `int` (> 0) or `null` | No | `None` | Associated pull request number |

### `MissionStarted` (`MissionStartedPayload`)

| Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `mission_id` | `str` | Yes | — | Mission identifier |
| `mission_type` | `str` | Yes | — | Mission type (e.g., `"software-dev"`) |
| `initial_phase` | `str` | Yes | — | First phase of the mission |
| `actor` | `str` | Yes | — | Actor who started the mission |

### `MissionCompleted` (`MissionCompletedPayload`)

| Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `mission_id` | `str` | Yes | — | Mission identifier |
| `mission_type` | `str` | Yes | — | Mission type |
| `final_phase` | `str` | Yes | — | Last phase before completion |
| `actor` | `str` | Yes | — | Actor who completed the mission |

### `MissionCancelled` (`MissionCancelledPayload`)

| Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `mission_id` | `str` | Yes | — | Mission identifier |
| `reason` | `str` | Yes | — | Cancellation reason |
| `actor` | `str` | Yes | — | Actor who cancelled |
| `cancelled_wp_ids` | `list[str]` | No | `[]` | WP IDs affected by cancellation |

### `PhaseEntered` (`PhaseEnteredPayload`)

| Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `mission_id` | `str` | Yes | — | Mission identifier |
| `phase_name` | `str` | Yes | — | Phase being entered |
| `previous_phase` | `str` or `null` | No | `None` | Phase being exited |
| `actor` | `str` | Yes | — | Actor triggering transition |

### `ReviewRollback` (`ReviewRollbackPayload`)

| Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `mission_id` | `str` | Yes | — | Mission identifier |
| `review_ref` | `str` | Yes | — | Review that triggered rollback |
| `target_phase` | `str` | Yes | — | Phase to roll back to |
| `affected_wp_ids` | `list[str]` | No | `[]` | WP IDs affected by rollback |
| `actor` | `str` | Yes | — | Actor triggering rollback |

---

## Collaboration Event Contracts

Added in **2.1.0** (Feature 006). N-participant mission collaboration with advisory coordination
(soft locks, not hard locks).

### Event Type Reference Table

All 14 collaboration event types with their key fields and categories:

| Category | Event Type | Payload Model | Key Fields |
|---|---|---|---|
| Participant Lifecycle | `ParticipantInvited` | `ParticipantInvitedPayload` | `participant_id`, `participant_identity`, `invited_by`, `mission_id` |
| Participant Lifecycle | `ParticipantJoined` | `ParticipantJoinedPayload` | `participant_id`, `participant_identity`, `mission_id`, `auth_principal_id` (optional) |
| Participant Lifecycle | `ParticipantLeft` | `ParticipantLeftPayload` | `participant_id`, `mission_id`, `reason` (optional) |
| Participant Lifecycle | `PresenceHeartbeat` | `PresenceHeartbeatPayload` | `participant_id`, `mission_id`, `session_id` (optional) |
| Drive Intent & Focus | `DriveIntentSet` | `DriveIntentSetPayload` | `participant_id`, `mission_id`, `intent` (`"active"` / `"inactive"`) |
| Drive Intent & Focus | `FocusChanged` | `FocusChangedPayload` | `participant_id`, `mission_id`, `focus_target`, `previous_focus_target` (optional) |
| Step Execution | `PromptStepExecutionStarted` | `PromptStepExecutionStartedPayload` | `participant_id`, `mission_id`, `step_id`, `wp_id` (optional) |
| Step Execution | `PromptStepExecutionCompleted` | `PromptStepExecutionCompletedPayload` | `participant_id`, `mission_id`, `step_id`, `outcome` (`"success"` / `"failure"` / `"skipped"`) |
| Advisory Warnings | `ConcurrentDriverWarning` | `ConcurrentDriverWarningPayload` | `warning_id`, `mission_id`, `participant_ids`, `focus_target`, `severity` |
| Advisory Warnings | `PotentialStepCollisionDetected` | `PotentialStepCollisionDetectedPayload` | `warning_id`, `mission_id`, `participant_ids`, `step_id`, `severity` |
| Advisory Warnings | `WarningAcknowledged` | `WarningAcknowledgedPayload` | `participant_id`, `mission_id`, `warning_id`, `acknowledgement` |
| Communication | `CommentPosted` | `CommentPostedPayload` | `participant_id`, `mission_id`, `comment_id`, `content`, `reply_to` (optional) |
| Communication | `DecisionCaptured` | `DecisionCapturedPayload` | `participant_id`, `mission_id`, `decision_id`, `topic`, `chosen_option` |
| Session | `SessionLinked` | `SessionLinkedPayload` | `participant_id`, `mission_id`, `primary_session_id`, `linked_session_id`, `link_type` |

### Identity and Target Models

| Model | Purpose | Key Fields |
|---|---|---|
| `ParticipantIdentity` | SaaS-minted, mission-scoped participant identity | `participant_id`, `participant_type` (`"human"` / `"llm_context"`), `display_name`, `session_id` |
| `AuthPrincipalBinding` | Auth principal to participant binding | `auth_principal_id`, `participant_id`, `bound_at` |
| `FocusTarget` | Structured focus reference (hashable) | `target_type` (`"wp"` / `"step"` / `"file"`), `target_id` |

### Reducer Contract

```python
reduce_collaboration_events(
    events: Sequence[Event],
    *,
    mode: Literal["strict", "permissive"] = "strict",
    roster: Optional[Dict[str, ParticipantIdentity]] = None,
) -> ReducedCollaborationState
```

**Modes**:

- **Strict** (default): Raises `UnknownParticipantError` when an event references a participant
  not in the roster. Appropriate for production event replay where the roster is complete.
- **Permissive**: Records a `CollaborationAnomaly` for each violation instead of raising. Useful
  for debugging, partial replays, and log analysis.

**Seeded roster**: When `roster` is provided (`Dict[str, ParticipantIdentity]`), participants are
pre-populated before event processing begins. Events can reference these participants without a
prior `ParticipantJoined` event. This supports partial-window reduction where a consumer replays
only a subset of events.

**Pipeline**:

1. **Filter**: Keep only events with `event_type in COLLABORATION_EVENT_TYPES`
2. **Sort**: Order by `(lamport_clock, timestamp, event_id)` for deterministic processing
3. **Dedup**: Remove duplicate `event_id` values (reuses `dedup_events()` from status module)
4. **Process**: Fold each event into mutable intermediate state
5. **Assemble**: Build frozen `ReducedCollaborationState`

**Output**: `ReducedCollaborationState` with 15 fields including `participants`, `active_drivers`,
`focus_by_participant`, `participants_by_focus` (reverse index), `warnings`, `decisions`,
`comments`, `active_executions`, `linked_sessions`, `anomalies`, and `event_count`.

### Envelope Mapping Convention

Collaboration events follow the same `Event` envelope as lifecycle events:

- **`aggregate_id`**: `"mission/{mission_id}"` format (matches lifecycle events)
- **`correlation_id`**: ULID-26 format (exactly 26 characters)
- **`event_type`**: One of the 14 collaboration event type constants
- **`payload`**: Dictionary matching the corresponding typed payload model

### SaaS-Authoritative Participation Model

The collaboration contract uses a **SaaS-authoritative** participation model:

- **`participant_id`** is SaaS-minted and mission-scoped. The SaaS backend assigns participant
  identifiers when participants are invited or join a mission.
- **CLI must not invent identities**. CLI agents receive their `participant_id` from the SaaS
  backend during session establishment.
- **Auth principal binding**: The `auth_principal_id` field on `ParticipantJoinedPayload` records
  the authenticated identity of the joining participant. This is populated by the SaaS backend
  at join time and binds the auth principal to the mission-scoped participant.
- **Strict mode enforces roster membership**: In strict mode, every event that references a
  `participant_id` must have that participant already in the roster (via `ParticipantInvited`,
  `ParticipantJoined`, or seeded `roster` parameter). Events from unknown participants raise
  `UnknownParticipantError`.

### Advisory Warning Semantics

The collaboration model uses **advisory warnings**, not hard locks:

- **No hard locks**: `ConcurrentDriverWarning` and `PotentialStepCollisionDetected` are
  informational signals. They do not block or prevent any action.
- **Acknowledgement actions**: When a participant acknowledges a warning via
  `WarningAcknowledged`, they select one of four actions:
  - `"continue"` -- proceed despite the warning
  - `"hold"` -- pause current work voluntarily
  - `"reassign"` -- hand off the conflicting work to another participant
  - `"defer"` -- postpone the conflicting work
- **Warning emitters**: Warning events may be emitted by:
  - CLI observers that detect concurrent focus or step execution locally
  - SaaS backend fallback inference that detects conflicts from the event stream
- **Soft coordination**: The system provides visibility into potential conflicts but does not
  enforce resolution. Participants retain full autonomy over their actions.

---

## Mission-Next Runtime Contracts

Added in **2.3.0**. These contracts define typed payloads for run-scoped mission execution events
emitted by the spec-kitty-runtime engine.

### Event Type Reference

| Event Type | Payload Model | Description |
|---|---|---|
| `MissionRunStarted` | `MissionRunStartedPayload` | Run initiated with actor identity |
| `NextStepIssued` | `NextStepIssuedPayload` | Step dispatched to an agent |
| `NextStepAutoCompleted` | `NextStepAutoCompletedPayload` | Step completed with result |
| `DecisionInputRequested` | `DecisionInputRequestedPayload` | Decision required from user/service |
| `DecisionInputAnswered` | `DecisionInputAnsweredPayload` | Decision answered |
| `MissionRunCompleted` | `MissionRunCompletedPayload` | Run reached terminal state |
| `NextStepPlanned` | *(reserved — no payload)* | Reserved constant; deferred until runtime emits |

### `MissionCompleted` vs `MissionRunCompleted`

These are distinct event types in different domains:

| Aspect | Lifecycle `MissionCompleted` | Mission-Next `MissionRunCompleted` |
|---|---|---|
| Module | `lifecycle.py` | `mission_next.py` |
| Scope | Mission-level (all phases done) | Run-level (single execution) |
| Payload | `MissionCompletedPayload` (mission_id, mission_type, final_phase, actor) | `MissionRunCompletedPayload` (run_id, mission_key, actor) |
| Key field | `mission_id` (str) | `run_id` (str) |
| Actor type | `str` | `RuntimeActorIdentity` (structured) |

**Migration note**: The runtime currently emits `"MissionCompleted"` as the event_type for run
completion (in `engine.py:309`). During the compatibility window, the mission-next reducer accepts
`"MissionCompleted"` as an alias for `"MissionRunCompleted"` when processing run-scoped events.
The conformance validator continues to map `"MissionCompleted"` to the lifecycle
`MissionCompletedPayload` for validation purposes.

### RuntimeActorIdentity

Mirrors the runtime's `ActorIdentity` schema:

| Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `actor_id` | `str` | Yes | — | Unique actor identifier |
| `actor_type` | `"human"` / `"llm"` / `"service"` | Yes | — | Actor category |
| `display_name` | `str` | No | `""` | Human-readable name |
| `provider` | `str` or `null` | No | `None` | e.g., `"anthropic"`, `"openai"` |
| `model` | `str` or `null` | No | `None` | e.g., `"claude-opus-4-6"` |
| `tool` | `str` or `null` | No | `None` | Tool identifier |

### Replay Fixture Stream (v2.3.1)

A canonical 8-event JSONL replay stream is provided for integration testing.
Each line is a complete `Event` envelope that can be deserialized and fed through
the mission-next reducer.

| # | Event Type | Key Detail | Lamport |
|---|---|---|---|
| 1 | `MissionRunStarted` | run_id=replay-run-001, LLM actor | 1 |
| 2 | `NextStepIssued` | step-setup-env | 2 |
| 3 | `NextStepAutoCompleted` | step-setup-env (success) | 3 |
| 4 | `NextStepIssued` | step-configure-db | 4 |
| 5 | `DecisionInputRequested` | input:db-password | 5 |
| 6 | `DecisionInputAnswered` | use-env-var, human actor | 6 |
| 7 | `NextStepAutoCompleted` | step-configure-db (success) | 7 |
| 8 | `MissionRunCompleted` | terminal state | 8 |

**Expected reducer output**: `run_status=COMPLETED`, `completed_steps=("step-setup-env", "step-configure-db")`, zero anomalies, `event_count=8`.

**Programmatic access**:

```python
from spec_kitty_events.conformance import load_replay_stream
from spec_kitty_events import Event, reduce_mission_next_events

envelopes = load_replay_stream("mission-next-replay-full-lifecycle")
events = [Event(**env) for env in envelopes]
state = reduce_mission_next_events(events)
assert state.run_status.value == "completed"
assert len(state.completed_steps) == 2
```

### Reducer Correctness Verification (v2.3.1)

The mission-next reducer (`reduce_mission_next_events()`) implements three correctness guards
that prevent silent data corruption:

| Bug Class | Guard | Location |
|---|---|---|
| Lifecycle `MissionCompleted` alias collision | Payload validation gate: `MissionCompleted` events are only accepted as run-completion if their payload validates as `MissionRunCompletedPayload`. Lifecycle payloads (with `mission_id`, `mission_type`, `final_phase`) are rejected with an anomaly. | `mission_next.py:297-311` |
| `run_id` consistency | Every post-start handler (`NextStepIssued`, `NextStepAutoCompleted`, `DecisionInputRequested`, `DecisionInputAnswered`, `MissionRunCompleted`) checks that the event's `run_id` matches the established run. Mismatches produce an anomaly. | `mission_next.py:372,391,413,440,461` |
| Malformed payload resilience | Every payload parse is wrapped in `try/except`. Invalid payloads produce an anomaly instead of crashing the reducer. | All handler blocks |

These guards are exercised by 80 tests with 100% line coverage on `mission_next.py`.

---

## Versioning Policy

This project follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html) with these rules
for the `2.x` series:

### Patch Releases (`2.x.Y`)

Bug fixes and documentation corrections only. No API changes.

**Examples**: Fix a typo in a schema description, correct a validator edge case.

### Minor Releases (`2.X.0`)

Additive, backward-compatible changes. Existing consumers are unaffected.

**Examples**:
- New optional fields on existing payload models (with defaults).
- New event types (e.g., `WPDependencyChanged`).
- New mapping versions (e.g., `SyncLaneV2` alongside the existing `SyncLaneV1`).
- New fixture categories or test helpers.
- New JSON schemas for newly added models.

### Major Releases (`3.0.0`)

Any breaking change requires a major version bump.

**Examples**:
- Removing a field from a payload model.
- Changing `SyncLaneV1` mapping output for any input (e.g., `canceled` mapping to `done`
  instead of `planned`).
- Removing an event type.
- Changing a required field to a different type.
- Removing a public export from `__init__.py`.

### Mapping Lock Guarantee

The `SyncLaneV1` mapping (`CANONICAL_TO_SYNC_V1`) is **locked** for the 2.x series:

- Changing the output of `canonical_to_sync_v1()` for any `Lane` input is a **breaking change**
  requiring `3.0.0`.
- New mapping versions (e.g., `SyncLaneV2`) are additive and can ship in any `2.x` minor release.
- Adding new lanes to `Lane` (and mapping them in `CANONICAL_TO_SYNC_V1`) is a minor change
  (`2.x.0`), provided all existing mappings remain unchanged.

---

## Migration Guide (0.x to 2.0.0)

### Step 1: Update Dependency

```toml
# pyproject.toml
dependencies = [
    "spec-kitty-events>=2.0.0rc1,<3.0.0",
]
```

### Step 2: Replace Hardcoded Lane Mappings

```python
# Before (0.x consumer code):
LANE_MAP = {
    "planned": "planned",
    "claimed": "planned",
    "in_progress": "doing",
    "for_review": "for_review",
    "done": "done",
    "blocked": "doing",
    "canceled": "planned",
}
sync_lane = LANE_MAP[raw_lane]

# After (2.0.0):
from spec_kitty_events import Lane, canonical_to_sync_v1

sync_lane = canonical_to_sync_v1(Lane(raw_lane))
```

### Step 3: Replace Local Status Enums

```python
# Before (0.x consumer code):
class SyncStatus(str, Enum):
    PLANNED = "planned"
    DOING = "doing"
    FOR_REVIEW = "for_review"
    DONE = "done"

# After (2.0.0):
from spec_kitty_events import SyncLaneV1

# SyncLaneV1.PLANNED, SyncLaneV1.DOING, SyncLaneV1.FOR_REVIEW, SyncLaneV1.DONE
```

### Step 4: Update Event Constructors

The `Event` model gained three fields in 0.4.0-alpha:
- `correlation_id` (required, ULID string)
- `schema_version` (optional, default `"1.0.0"`)
- `data_tier` (optional, default `0`)

```python
# Before (0.3.x):
event = Event(
    event_id=ulid_str,
    event_type="WPStatusChanged",
    aggregate_id="WP001",
    timestamp=now,
    node_id="alice",
    lamport_clock=1,
    project_uuid=project_uuid,
    payload={"state": "doing"},
)

# After (2.0.0):
event = Event(
    event_id=ulid_str,
    event_type="WPStatusChanged",
    aggregate_id="WP001",
    timestamp=now,
    node_id="alice",
    lamport_clock=1,
    project_uuid=project_uuid,
    correlation_id=correlation_ulid,  # NEW: required
    schema_version="2.0.0",           # NEW: optional (default "1.0.0")
    data_tier=0,                      # NEW: optional (default 0)
    payload={"state": "doing"},
)
```

### Step 5: Add Conformance CI

See [Consumer CI Integration](#consumer-ci-integration) below.

---

## Consumer CI Integration

Add these steps to your CI pipeline to validate conformance with the upstream event contract.
This catches contract drift early, before it reaches production.

### For CLI and SaaS Consumers

#### Step 1: Add Dependency

```bash
pip install "spec-kitty-events[conformance]>=2.0.0rc1,<3.0.0"
```

The `[conformance]` extra adds `jsonschema>=4.21.0,<5.0.0` for full dual-layer validation.

#### Step 2: Run Upstream Conformance Suite

```bash
pytest --pyargs spec_kitty_events.conformance -v
```

This runs the bundled conformance test suite against the installed version of `spec-kitty-events`.
It validates all event types, lane mappings, and edge cases using manifest-driven fixtures.

#### Step 3: Validate Your Own Payloads (Optional)

Use the `validate_event()` API to check payloads your application constructs:

```python
from spec_kitty_events.conformance import validate_event

# Validate a payload you construct
my_payload = {
    "feature_slug": "005-my-feature",
    "wp_id": "WP01",
    "to_lane": "in_progress",
    "actor": "ci-bot",
    "execution_mode": "worktree",
}
result = validate_event(my_payload, "WPStatusChanged", strict=True)
assert result.valid, f"Violations: {result.model_violations}"
```

#### Step 4: Use Consumer Test Helpers (Optional)

Import reusable assertion functions for your own test suites:

```python
from spec_kitty_events.conformance import (
    assert_payload_conforms,
    assert_payload_fails,
    assert_lane_mapping,
)

def test_my_payload_conforms():
    payload = build_my_wp_status_payload()
    assert_payload_conforms(payload, "WPStatusChanged", strict=True)

def test_lane_mapping_contract():
    assert_lane_mapping("in_progress", "doing")
    assert_lane_mapping("blocked", "doing")
    assert_lane_mapping("canceled", "planned")
```

### For spec-kitty-events Contributors

#### Schema Drift Check

After modifying any Pydantic model, verify JSON schemas are up to date:

```bash
python -m spec_kitty_events.schemas.generate --check
```

This compares the generated schemas against the committed `.schema.json` files. If they differ,
regenerate:

```bash
python -m spec_kitty_events.schemas.generate
git add src/spec_kitty_events/schemas/*.schema.json
```

---

## SCHEMA_VERSION Documentation

The `SCHEMA_VERSION` constant (currently `"2.0.0"`) is defined in
`spec_kitty_events.lifecycle` and exported from `spec_kitty_events`:

```python
from spec_kitty_events import SCHEMA_VERSION
assert SCHEMA_VERSION == "2.0.0"
```

### Version Semantics

- `SCHEMA_VERSION` tracks the **event contract version**, not the package version.
- It is set to `"2.0.0"` for the entire 2.x series.
- The `Event.schema_version` field defaults to `"1.0.0"` and can be set per-event to indicate
  which contract version the event was produced under.
- A consumer that only understands schema version `"1.0.0"` can safely ignore events with
  `schema_version="2.0.0"` (forward-compatible envelope).

---

## Functional Requirements Traceability

Every functional requirement (FR-001 through FR-023) from the Feature 005 specification is
addressed across WP01-WP07:

| FR | Description | Addressed In |
|---|---|---|
| FR-001 | `SyncLaneV1` enum with 4 values | WP01 (`status.py`) |
| FR-002 | `CANONICAL_TO_SYNC_V1` immutable mapping | WP01 (`status.py`) |
| FR-003 | `canonical_to_sync_v1()` function | WP01 (`status.py`) |
| FR-004 | All 7 `Lane` values mapped | WP01 (`status.py`) |
| FR-005 | Mapping is frozen (`MappingProxyType`) | WP01 (`status.py`) |
| FR-006 | JSON Schema per Pydantic model | WP02 (`schemas/`) |
| FR-007 | Build-time generation script | WP02 (`schemas/generate.py`) |
| FR-008 | CI drift detection (`--check` flag) | WP02 (`schemas/generate.py`) |
| FR-009 | `load_schema()` and `list_schemas()` API | WP02 (`schemas/__init__.py`) |
| FR-010 | `FixtureCase` frozen dataclass | WP04 (`conformance/loader.py`) |
| FR-011 | `load_fixtures()` with manifest | WP04 (`conformance/loader.py`) |
| FR-012 | `validate_event()` dual-layer validator | WP03 (`conformance/validators.py`) |
| FR-013 | `ConformanceResult` with model/schema buckets | WP03 (`conformance/validators.py`) |
| FR-014 | Graceful degradation without jsonschema | WP03 (`conformance/validators.py`) |
| FR-015 | `pytest --pyargs` entry point | WP05 (`conformance/test_pyargs_entrypoint.py`) |
| FR-016 | Manifest-driven fixture tests | WP05 (`conformance/conftest.py`) |
| FR-017 | Consumer test helpers | WP05 (`conformance/pytest_helpers.py`) |
| FR-018 | Version graduated to 2.0.0rc1 | WP06 (`pyproject.toml`) |
| FR-019 | Compatibility table (this document) | WP07 (`COMPATIBILITY.md`) |
| FR-020 | Changelog with migration notes | WP07 (`CHANGELOG.md`) |
| FR-021 | SCHEMA_VERSION documentation | WP07 (`COMPATIBILITY.md`) |
| FR-022 | `[conformance]` optional extra | WP06 (`pyproject.toml`) |
| FR-023 | Package data for schemas and fixtures | WP02 + WP06 (`pyproject.toml`) |

All 23 functional requirements are addressed. No gaps identified.
