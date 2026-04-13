# Data Model: Additive Event Contracts for Charter Phase 4/5/6

**Date**: 2026-04-13
**Mission ID**: `01KP343JBG2V7WSWSDJ0HD76BR`

## Entity Overview

This tranche introduces 3 new Pydantic payload models across 2 domain modules and reuses 2 existing value objects. No new enums, reducers, or state models are defined.

```
┌─────────────────────────────────────┐
│          Event (envelope)           │
│  schema_version="3.0.0" (unchanged) │
│  event_type → dispatches to payload │
└──────────────┬──────────────────────┘
               │ payload dict
    ┌──────────┼──────────────────────────────┐
    │          │                              │
    ▼          ▼                              ▼
┌──────────┐ ┌──────────────────┐ ┌──────────────────┐
│ Profile  │ │ Retrospective    │ │ Retrospective    │
│ Invocn.  │ │ Completed        │ │ Skipped          │
│ Started  │ │ Payload          │ │ Payload          │
│ Payload  │ └────────┬─────────┘ └──────────────────┘
└────┬─────┘          │
     │                │ artifact_ref (optional)
     │                ▼
     │          ┌──────────────┐
     │          │ ProvenanceRef│  (reused from dossier.py)
     │          └──────────────┘
     │ actor
     ▼
┌────────────────────┐
│RuntimeActorIdentity│  (reused from mission_next.py)
└────────────────────┘
```

## New Entities

### ProfileInvocationStartedPayload

**Module**: `src/spec_kitty_events/profile_invocation.py`
**Config**: `ConfigDict(frozen=True, extra="forbid")`
**Event type string**: `"ProfileInvocationStarted"`

| Field | Type | Required | Validation | Description |
|-------|------|----------|------------|-------------|
| `mission_id` | `str` | Yes | `min_length=1` | Mission being executed |
| `run_id` | `str` | Yes | `min_length=1` | Run identifier from MissionRunStarted |
| `step_id` | `str` | Yes | `min_length=1` | Step being executed |
| `action` | `str` | Yes | `min_length=1` | Bound action name |
| `profile_slug` | `str` | Yes | `min_length=1` | Resolved agent profile slug |
| `profile_version` | `Optional[str]` | No | `min_length=1` if present | Profile version string |
| `actor` | `RuntimeActorIdentity` | Yes | Nested model validation | Runtime actor identity |
| `governance_scope` | `Optional[str]` | No | `min_length=1` if present | Governance scope identifier |

### RetrospectiveCompletedPayload

**Module**: `src/spec_kitty_events/retrospective.py`
**Config**: `ConfigDict(frozen=True, extra="forbid")`
**Event type string**: `"RetrospectiveCompleted"`

| Field | Type | Required | Validation | Description |
|-------|------|----------|------------|-------------|
| `mission_id` | `str` | Yes | `min_length=1` | Mission identifier |
| `actor` | `str` | Yes | `min_length=1` | Actor who triggered the retrospective |
| `trigger_source` | `Literal["runtime", "operator", "policy"]` | Yes | Literal validation | What initiated the retrospective |
| `artifact_ref` | `Optional[ProvenanceRef]` | No | Nested model validation | Reference to retro artifact |
| `completed_at` | `str` | Yes | `min_length=1` (ISO 8601) | Completion timestamp |

### RetrospectiveSkippedPayload

**Module**: `src/spec_kitty_events/retrospective.py`
**Config**: `ConfigDict(frozen=True, extra="forbid")`
**Event type string**: `"RetrospectiveSkipped"`

| Field | Type | Required | Validation | Description |
|-------|------|----------|------------|-------------|
| `mission_id` | `str` | Yes | `min_length=1` | Mission identifier |
| `actor` | `str` | Yes | `min_length=1` | Actor who decided to skip |
| `trigger_source` | `Literal["runtime", "operator", "policy"]` | Yes | Literal validation | What would have initiated the retrospective |
| `skip_reason` | `str` | Yes | `min_length=1` | Why the retrospective was skipped |
| `skipped_at` | `str` | Yes | `min_length=1` (ISO 8601) | Skip decision timestamp |

## Reused Value Objects (no changes)

### RuntimeActorIdentity

**Source**: `src/spec_kitty_events/mission_next.py`
**Used by**: `ProfileInvocationStartedPayload.actor`

| Field | Type | Required |
|-------|------|----------|
| `actor_id` | `str` | Yes |
| `actor_type` | `str` (pattern: `^(human\|llm\|service)$`) | Yes |
| `display_name` | `str` | No (default `""`) |
| `provider` | `Optional[str]` | No |
| `model` | `Optional[str]` | No |
| `tool` | `Optional[str]` | No |

### ProvenanceRef

**Source**: `src/spec_kitty_events/dossier.py`
**Used by**: `RetrospectiveCompletedPayload.artifact_ref`

| Field | Type | Required |
|-------|------|----------|
| `source_event_ids` | `Optional[Tuple[str, ...]]` | No |
| `git_sha` | `Optional[str]` | No |
| `git_ref` | `Optional[str]` | No |
| `actor_id` | `Optional[str]` | No |
| `actor_kind` | `Optional[Literal["human", "llm", "system"]]` | No |
| `revised_at` | `Optional[str]` | No |

## Constants and Type Sets

### Profile Invocation Domain

```python
PROFILE_INVOCATION_SCHEMA_VERSION: str = "3.1.0"

PROFILE_INVOCATION_STARTED: str = "ProfileInvocationStarted"
PROFILE_INVOCATION_COMPLETED: str = "ProfileInvocationCompleted"   # Reserved
PROFILE_INVOCATION_FAILED: str = "ProfileInvocationFailed"         # Reserved

PROFILE_INVOCATION_EVENT_TYPES: FrozenSet[str] = frozenset({
    PROFILE_INVOCATION_STARTED,
    PROFILE_INVOCATION_COMPLETED,  # Reserved — payload deferred
    PROFILE_INVOCATION_FAILED,     # Reserved — payload deferred
})
```

### Retrospective Domain

```python
RETROSPECTIVE_SCHEMA_VERSION: str = "3.1.0"

RETROSPECTIVE_COMPLETED: str = "RetrospectiveCompleted"
RETROSPECTIVE_SKIPPED: str = "RetrospectiveSkipped"

RETROSPECTIVE_EVENT_TYPES: FrozenSet[str] = frozenset({
    RETROSPECTIVE_COMPLETED,
    RETROSPECTIVE_SKIPPED,
})
```

## Conformance Dispatch Additions (WP04)

### _EVENT_TYPE_TO_MODEL additions

```python
"ProfileInvocationStarted": ProfileInvocationStartedPayload,
"RetrospectiveCompleted": RetrospectiveCompletedPayload,
"RetrospectiveSkipped": RetrospectiveSkippedPayload,
```

### _EVENT_TYPE_TO_SCHEMA additions

```python
"ProfileInvocationStarted": "profile_invocation_started_payload",
"RetrospectiveCompleted": "retrospective_completed_payload",
"RetrospectiveSkipped": "retrospective_skipped_payload",
```

## Package Export Additions (WP04)

New symbols added to `__init__.py` imports and `__all__`:

```python
# Profile invocation contracts (3.1.0)
PROFILE_INVOCATION_SCHEMA_VERSION
PROFILE_INVOCATION_STARTED
PROFILE_INVOCATION_COMPLETED    # Reserved
PROFILE_INVOCATION_FAILED       # Reserved
PROFILE_INVOCATION_EVENT_TYPES
ProfileInvocationStartedPayload

# Retrospective contracts (3.1.0)
RETROSPECTIVE_SCHEMA_VERSION
RETROSPECTIVE_COMPLETED
RETROSPECTIVE_SKIPPED
RETROSPECTIVE_EVENT_TYPES
RetrospectiveCompletedPayload
RetrospectiveSkippedPayload
```

## State Transitions

None. No reducers or state machines are introduced in this tranche. Both domains emit terminal signals that do not transition through intermediate states.
