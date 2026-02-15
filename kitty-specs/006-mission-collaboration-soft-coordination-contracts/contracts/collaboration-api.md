# Collaboration API Contract

**Feature**: 006-mission-collaboration-soft-coordination-contracts
**Module**: `spec_kitty_events.collaboration`
**Date**: 2026-02-15

## Public API Surface

### Constants

```python
# Event type strings
PARTICIPANT_INVITED: str = "ParticipantInvited"
PARTICIPANT_JOINED: str = "ParticipantJoined"
PARTICIPANT_LEFT: str = "ParticipantLeft"
PRESENCE_HEARTBEAT: str = "PresenceHeartbeat"
DRIVE_INTENT_SET: str = "DriveIntentSet"
FOCUS_CHANGED: str = "FocusChanged"
PROMPT_STEP_EXECUTION_STARTED: str = "PromptStepExecutionStarted"
PROMPT_STEP_EXECUTION_COMPLETED: str = "PromptStepExecutionCompleted"
CONCURRENT_DRIVER_WARNING: str = "ConcurrentDriverWarning"
POTENTIAL_STEP_COLLISION_DETECTED: str = "PotentialStepCollisionDetected"
WARNING_ACKNOWLEDGED: str = "WarningAcknowledged"
COMMENT_POSTED: str = "CommentPosted"
DECISION_CAPTURED: str = "DecisionCaptured"
SESSION_LINKED: str = "SessionLinked"

COLLABORATION_EVENT_TYPES: frozenset[str]  # All 14 values
```

### Identity and Target Models

```python
class ParticipantIdentity(BaseModel):
    """SaaS-minted, mission-scoped participant identity."""
    model_config = ConfigDict(frozen=True)
    participant_id: str      # min_length=1
    participant_type: str    # Literal["human", "llm_context"]
    display_name: str | None = None
    session_id: str | None = None

class AuthPrincipalBinding(BaseModel):
    """Roster-level auth principal → participant binding."""
    model_config = ConfigDict(frozen=True)
    auth_principal_id: str   # min_length=1
    participant_id: str      # min_length=1
    bound_at: datetime

class FocusTarget(BaseModel):
    """Structured focus reference. Hashable for use as dict key."""
    model_config = ConfigDict(frozen=True)
    target_type: str         # Literal["wp", "step", "file"]
    target_id: str           # min_length=1
```

### Reducer

```python
def reduce_collaboration_events(
    events: Sequence[Event],
    *,
    mode: Literal["strict", "permissive"] = "strict",
    roster: dict[str, ParticipantIdentity] | None = None,
) -> ReducedCollaborationState:
    """
    Reduce a sequence of collaboration events into materialized state.

    Pipeline: sort → dedup → process → collect anomalies

    Args:
        events: Sequence of Event objects (any event types; non-collaboration
                events are filtered out).
        mode: Enforcement mode.
            - "strict" (default): Raises UnknownParticipantError for events
              from non-rostered participants. Hard errors for integrity violations.
              Requires either full event history (including ParticipantJoined) or
              a seeded roster parameter.
            - "permissive": Records anomalies for integrity violations. For
              replay/import of incomplete historical streams.
        roster: Optional pre-seeded participant roster (participant_id →
                ParticipantIdentity). Enables strict-mode reduction of partial
                event windows without requiring full ParticipantJoined history.
                Seeded participants are treated as already-joined before event
                processing begins.

    Returns:
        ReducedCollaborationState with mission snapshot, indexes, and anomalies.

    Raises:
        UnknownParticipantError: In strict mode, when an event references a
            participant_id not in the mission roster (and not in seeded roster).
    """
```

### Exception

```python
class UnknownParticipantError(SpecKittyEventsError):
    """Raised in strict mode for events from non-rostered participants."""
    participant_id: str
    event_id: str
    event_type: str
```

## Envelope Mapping Contract

All collaboration events MUST follow this envelope mapping:

| Event.field | Wire format | Example | Constraint |
|-------------|------------|---------|------------|
| `aggregate_id` | `"mission/{mission_id}"` | `"mission/M042"` | Type-prefixed string (matches lifecycle convention) |
| `correlation_id` | ULID-26 (`mission_run_id`) | `"01HXYZ..."` (26 chars) | Exactly 26 characters (ULID format, enforced by envelope model) |
| `event_type` | One of `COLLABORATION_EVENT_TYPES` | `"ParticipantJoined"` | Must be one of 14 constants |
| `node_id` | Emitting process identity | `"saas-node-1"` | min_length=1 |
| `lamport_clock` | Monotonically increasing per node | `42` | int >= 0 |

**Critical**: `aggregate_id` MUST use the `"mission/"` prefix. Raw `mission_id` without prefix will fragment aggregates if other producers use the prefixed form. The `correlation_id` MUST be a ULID — freeform strings will fail envelope validation.

## Payload Actor Field Contract

| Payload Category | Actor Field | Type | Description |
|-----------------|------------|------|-------------|
| Single-actor (12 payloads) | `participant_id` | `str` | The acting participant |
| Multi-actor warnings (2 payloads) | `participant_ids` | `list[str]` | All affected participants |

**Single-actor payloads**: ParticipantInvitedPayload, ParticipantJoinedPayload, ParticipantLeftPayload, PresenceHeartbeatPayload, DriveIntentSetPayload, FocusChangedPayload, PromptStepExecutionStartedPayload, PromptStepExecutionCompletedPayload, WarningAcknowledgedPayload, CommentPostedPayload, DecisionCapturedPayload, SessionLinkedPayload

**Multi-actor payloads**: ConcurrentDriverWarningPayload, PotentialStepCollisionDetectedPayload

## Strict Mode Enforcement Points

The reducer checks membership at these points (strict mode only):

1. **Any event with `participant_id`**: participant must be in roster (prior `ParticipantJoined` processed)
2. **Any event with `participant_ids`**: all participant_ids must be in roster
3. **`WarningAcknowledged`**: referenced `warning_id` must exist in warning timeline
4. **`PromptStepExecutionCompleted`**: matching `PromptStepExecutionStarted` must exist
5. **`PresenceHeartbeat` / `FocusChanged` / `DriveIntentSet`**: participant must not have departed

In permissive mode, all of the above record `CollaborationAnomaly` instead of raising.

Exception: Duplicate `ParticipantLeft` records an anomaly in **both** modes (protocol error, not a membership violation).

## Export List

All symbols exported from `spec_kitty_events.__init__`:

```python
# Collaboration constants (15)
"PARTICIPANT_INVITED", "PARTICIPANT_JOINED", "PARTICIPANT_LEFT",
"PRESENCE_HEARTBEAT", "DRIVE_INTENT_SET", "FOCUS_CHANGED",
"PROMPT_STEP_EXECUTION_STARTED", "PROMPT_STEP_EXECUTION_COMPLETED",
"CONCURRENT_DRIVER_WARNING", "POTENTIAL_STEP_COLLISION_DETECTED",
"WARNING_ACKNOWLEDGED", "COMMENT_POSTED", "DECISION_CAPTURED",
"SESSION_LINKED", "COLLABORATION_EVENT_TYPES",

# Collaboration identity models (3)
"ParticipantIdentity", "AuthPrincipalBinding", "FocusTarget",

# Collaboration payload models (14)
"ParticipantInvitedPayload", "ParticipantJoinedPayload",
"ParticipantLeftPayload", "PresenceHeartbeatPayload",
"DriveIntentSetPayload", "FocusChangedPayload",
"PromptStepExecutionStartedPayload", "PromptStepExecutionCompletedPayload",
"ConcurrentDriverWarningPayload", "PotentialStepCollisionDetectedPayload",
"WarningAcknowledgedPayload", "CommentPostedPayload",
"DecisionCapturedPayload", "SessionLinkedPayload",

# Collaboration reducer output (3)
"ReducedCollaborationState", "CollaborationAnomaly", "UnknownParticipantError",

# Collaboration reducer function (1)
"reduce_collaboration_events",
```

**Total new exports**: 36 symbols
**Total package exports after feature 006**: 68 + 36 = 104 symbols
