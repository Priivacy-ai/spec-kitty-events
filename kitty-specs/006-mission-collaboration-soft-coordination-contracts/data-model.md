# Data Model: Mission Collaboration Soft Coordination Contracts

**Feature**: 006-mission-collaboration-soft-coordination-contracts
**Date**: 2026-02-15

## Identity Models

### ParticipantIdentity

Structured identity for mission participants. SaaS-minted, mission-scoped.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `participant_id` | `str` (min_length=1) | Yes | SaaS-minted, mission-scoped unique identifier |
| `participant_type` | `Literal["human", "llm_context"]` | Yes | Participant category. Extensible in minor versions |
| `display_name` | `str` | No | Human-readable name for display |
| `session_id` | `str` | No | SaaS-issued session identifier |

**Constraints**: Frozen. `participant_type` constrained to known values but designed for extension.

### AuthPrincipalBinding

Roster-level association between an authenticated identity and a mission-scoped participant. Created by SaaS at join time.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `auth_principal_id` | `str` (min_length=1) | Yes | Authenticated identity (opaque to this package) |
| `participant_id` | `str` (min_length=1) | Yes | Mission-scoped participant identifier |
| `bound_at` | `datetime` | Yes | Timestamp when binding was created |

**Constraints**: Frozen. Used in conformance fixtures as context, not embedded in every event payload.

### FocusTarget

Structured reference to what a participant is currently focused on.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `target_type` | `Literal["wp", "step", "file"]` | Yes | Category of focus target |
| `target_id` | `str` (min_length=1) | Yes | Identifier within the target type (e.g., WP ID, step ID, file path) |

**Constraints**: Frozen. Hashable (for use as dict keys in reverse index).

## Event Type Constants

| Constant | Value | Category |
|----------|-------|----------|
| `PARTICIPANT_INVITED` | `"ParticipantInvited"` | Lifecycle |
| `PARTICIPANT_JOINED` | `"ParticipantJoined"` | Lifecycle |
| `PARTICIPANT_LEFT` | `"ParticipantLeft"` | Lifecycle |
| `PRESENCE_HEARTBEAT` | `"PresenceHeartbeat"` | Lifecycle |
| `DRIVE_INTENT_SET` | `"DriveIntentSet"` | Intent |
| `FOCUS_CHANGED` | `"FocusChanged"` | Intent |
| `PROMPT_STEP_EXECUTION_STARTED` | `"PromptStepExecutionStarted"` | Execution |
| `PROMPT_STEP_EXECUTION_COMPLETED` | `"PromptStepExecutionCompleted"` | Execution |
| `CONCURRENT_DRIVER_WARNING` | `"ConcurrentDriverWarning"` | Warning |
| `POTENTIAL_STEP_COLLISION_DETECTED` | `"PotentialStepCollisionDetected"` | Warning |
| `WARNING_ACKNOWLEDGED` | `"WarningAcknowledged"` | Warning |
| `COMMENT_POSTED` | `"CommentPosted"` | Communication |
| `DECISION_CAPTURED` | `"DecisionCaptured"` | Communication |
| `SESSION_LINKED` | `"SessionLinked"` | Session |

`COLLABORATION_EVENT_TYPES: frozenset[str]` — contains all 14 values.

## Payload Models

All payload models are frozen Pydantic v2 BaseModel with `ConfigDict(frozen=True)`.

### Participant Lifecycle Payloads

#### ParticipantInvitedPayload

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `participant_id` | `str` (min_length=1) | Yes | Invited participant |
| `participant_identity` | `ParticipantIdentity` | Yes | Full structured identity |
| `invited_by` | `str` (min_length=1) | Yes | participant_id of inviter |
| `mission_id` | `str` (min_length=1) | Yes | Target mission |

#### ParticipantJoinedPayload

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `participant_id` | `str` (min_length=1) | Yes | Joining participant |
| `participant_identity` | `ParticipantIdentity` | Yes | Full structured identity |
| `mission_id` | `str` (min_length=1) | Yes | Target mission |
| `auth_principal_id` | `str` | No | Auth principal bound at join time (present in live traffic) |

#### ParticipantLeftPayload

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `participant_id` | `str` (min_length=1) | Yes | Departing participant |
| `mission_id` | `str` (min_length=1) | Yes | Mission being left |
| `reason` | `str` | No | Departure reason (e.g., `"disconnect"`, `"explicit"`) |

#### PresenceHeartbeatPayload

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `participant_id` | `str` (min_length=1) | Yes | Heartbeat source |
| `mission_id` | `str` (min_length=1) | Yes | Mission context |
| `session_id` | `str` | No | Specific session sending heartbeat |

### Drive Intent and Focus Payloads

#### DriveIntentSetPayload

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `participant_id` | `str` (min_length=1) | Yes | Participant declaring intent |
| `mission_id` | `str` (min_length=1) | Yes | Mission context |
| `intent` | `Literal["active", "inactive"]` | Yes | Drive intent state |

#### FocusChangedPayload

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `participant_id` | `str` (min_length=1) | Yes | Participant changing focus |
| `mission_id` | `str` (min_length=1) | Yes | Mission context |
| `focus_target` | `FocusTarget` | Yes | New focus target |
| `previous_focus_target` | `FocusTarget` | No | Previous focus (if any) |

### Prompt Step Execution Payloads

#### PromptStepExecutionStartedPayload

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `participant_id` | `str` (min_length=1) | Yes | Executing participant (typically llm_context) |
| `mission_id` | `str` (min_length=1) | Yes | Mission context |
| `step_id` | `str` (min_length=1) | Yes | Step identifier |
| `wp_id` | `str` | No | Work package being targeted |
| `step_description` | `str` | No | Human-readable step description |

#### PromptStepExecutionCompletedPayload

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `participant_id` | `str` (min_length=1) | Yes | Completing participant |
| `mission_id` | `str` (min_length=1) | Yes | Mission context |
| `step_id` | `str` (min_length=1) | Yes | Step identifier |
| `wp_id` | `str` | No | Work package targeted |
| `outcome` | `Literal["success", "failure", "skipped"]` | Yes | Step outcome |

### Advisory Warning Payloads

#### ConcurrentDriverWarningPayload

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `warning_id` | `str` (min_length=1) | Yes | Unique warning identifier |
| `mission_id` | `str` (min_length=1) | Yes | Mission context |
| `participant_ids` | `list[str]` (min_length=2) | Yes | All concurrent active drivers on overlapping target |
| `focus_target` | `FocusTarget` | Yes | Shared focus target triggering warning |
| `severity` | `Literal["info", "warning"]` | Yes | Warning severity level |

#### PotentialStepCollisionDetectedPayload

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `warning_id` | `str` (min_length=1) | Yes | Unique warning identifier |
| `mission_id` | `str` (min_length=1) | Yes | Mission context |
| `participant_ids` | `list[str]` (min_length=2) | Yes | Colliding participants |
| `step_id` | `str` (min_length=1) | Yes | Colliding step |
| `wp_id` | `str` | No | Work package context |
| `severity` | `Literal["info", "warning"]` | Yes | Warning severity level |

#### WarningAcknowledgedPayload

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `participant_id` | `str` (min_length=1) | Yes | Acknowledging participant |
| `mission_id` | `str` (min_length=1) | Yes | Mission context |
| `warning_id` | `str` (min_length=1) | Yes | Warning being acknowledged |
| `acknowledgement` | `Literal["continue", "hold", "reassign", "defer"]` | Yes | Response action |

### Communication and Decision Payloads

#### CommentPostedPayload

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `participant_id` | `str` (min_length=1) | Yes | Comment author |
| `mission_id` | `str` (min_length=1) | Yes | Mission context |
| `comment_id` | `str` (min_length=1) | Yes | Unique comment identifier |
| `content` | `str` (min_length=1) | Yes | Comment text |
| `reply_to` | `str` | No | Parent comment_id for threading |

#### DecisionCapturedPayload

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `participant_id` | `str` (min_length=1) | Yes | Decision author |
| `mission_id` | `str` (min_length=1) | Yes | Mission context |
| `decision_id` | `str` (min_length=1) | Yes | Unique decision identifier |
| `topic` | `str` (min_length=1) | Yes | Decision topic/question |
| `chosen_option` | `str` (min_length=1) | Yes | Selected option |
| `rationale` | `str` | No | Reasoning for the decision |
| `referenced_warning_id` | `str` | No | Warning that prompted this decision |

### Session Linking Payload

#### SessionLinkedPayload

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `participant_id` | `str` (min_length=1) | Yes | Participant linking sessions |
| `mission_id` | `str` (min_length=1) | Yes | Mission context |
| `primary_session_id` | `str` (min_length=1) | Yes | Primary session |
| `linked_session_id` | `str` (min_length=1) | Yes | Session being linked |
| `link_type` | `Literal["cli_to_saas", "saas_to_cli"]` | Yes | Direction of link |

## Reducer Output Models

### CollaborationAnomaly

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `event_id` | `str` | Yes | Event that caused the anomaly |
| `event_type` | `str` | Yes | Type of the problematic event |
| `reason` | `str` | Yes | Human-readable anomaly description |

**Constraints**: Frozen. Follows `LifecycleAnomaly` / `TransitionAnomaly` pattern.

### ReducedCollaborationState

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `mission_id` | `str` | Yes | Mission this state represents |
| `participants` | `dict[str, ParticipantIdentity]` | Yes | Active participant roster (participant_id → identity) |
| `departed_participants` | `dict[str, ParticipantIdentity]` | Yes | Historical departed participants |
| `presence` | `dict[str, datetime]` | Yes | Last heartbeat timestamp per participant_id |
| `active_drivers` | `frozenset[str]` | Yes | participant_ids with active drive intent |
| `focus_by_participant` | `dict[str, FocusTarget]` | Yes | Current focus per participant |
| `participants_by_focus` | `dict[FocusTarget, frozenset[str]]` | Yes | Reverse index: focus → participant set |
| `warnings` | `tuple[WarningEntry, ...]` | Yes | Ordered warning timeline |
| `decisions` | `tuple[DecisionEntry, ...]` | Yes | Ordered decision history |
| `comments` | `tuple[CommentEntry, ...]` | Yes | Ordered comment history |
| `active_executions` | `dict[str, list[str]]` | Yes | In-flight step_ids per participant_id |
| `linked_sessions` | `dict[str, list[str]]` | Yes | Linked session_ids per participant_id |
| `anomalies` | `tuple[CollaborationAnomaly, ...]` | Yes | Non-fatal issues encountered |
| `event_count` | `int` | Yes | Total events processed |
| `last_processed_event_id` | `str` | Yes | Last event_id in processed sequence |

**Constraints**: Frozen.

### WarningEntry (internal to ReducedCollaborationState)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `warning_id` | `str` | Yes | Warning identifier |
| `event_id` | `str` | Yes | Event that created this warning |
| `warning_type` | `str` | Yes | `"ConcurrentDriverWarning"` or `"PotentialStepCollisionDetected"` |
| `participant_ids` | `tuple[str, ...]` | Yes | Affected participants |
| `acknowledgements` | `dict[str, str]` | Yes | participant_id → acknowledgement action |

### DecisionEntry (internal to ReducedCollaborationState)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `decision_id` | `str` | Yes | Decision identifier |
| `event_id` | `str` | Yes | Event that captured this decision |
| `participant_id` | `str` | Yes | Decision author |
| `topic` | `str` | Yes | Decision topic |
| `chosen_option` | `str` | Yes | Selected option |
| `referenced_warning_id` | `str` | No | Related warning |

### CommentEntry (internal to ReducedCollaborationState)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `comment_id` | `str` | Yes | Comment identifier |
| `event_id` | `str` | Yes | Event that posted this comment |
| `participant_id` | `str` | Yes | Comment author |
| `content` | `str` | Yes | Comment text |
| `reply_to` | `str` | No | Parent comment_id |

## Exception

### UnknownParticipantError

Raised in strict mode when an event references a `participant_id` not in the mission roster.

| Field | Type | Description |
|-------|------|-------------|
| `participant_id` | `str` | The unrecognized participant_id |
| `event_id` | `str` | The event that triggered the error |
| `event_type` | `str` | The event type |

Inherits from `SpecKittyEventsError` (existing base exception).

## Envelope Mapping Convention

All collaboration events follow canonical envelope mapping:

| Event Field | Collaboration Mapping |
|-------------|----------------------|
| `aggregate_id` | `mission_id` |
| `correlation_id` | `mission_run_id` |
| `event_type` | One of 14 `COLLABORATION_EVENT_TYPES` |
| `node_id` | Emitting process/node (not participant identity) |

## State Transitions

### Participant Lifecycle

```
(absent) → ParticipantInvited → ParticipantJoined → [active] → ParticipantLeft → (departed)
                                                        ↑                              |
                                                        └──── (may rejoin) ────────────┘
```

### Drive Intent

```
(no intent) → DriveIntentSet(active) → [active driver] → DriveIntentSet(inactive) → (no intent)
                     ↑                                              |
                     └──────────────────────────────────────────────┘
```

### Step Execution

```
(idle) → PromptStepExecutionStarted → [executing] → PromptStepExecutionCompleted → (idle)
```

### Warning Lifecycle

```
ConcurrentDriverWarning / PotentialStepCollisionDetected → [open]
    → WarningAcknowledged(continue) → [acknowledged: continuing]
    → WarningAcknowledged(hold) → [acknowledged: holding]
    → WarningAcknowledged(reassign) → [acknowledged: reassigning]
    → WarningAcknowledged(defer) → [acknowledged: deferred]
```
