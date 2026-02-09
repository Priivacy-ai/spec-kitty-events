# Data Model: Canonical Event Contract Consolidation

**Feature**: 004-canonical-event-contract
**Date**: 2026-02-09

## Entity Definitions

### Event (extended — models.py)

The existing Event model gains three new fields:

| Field | Type | Required | Default | Validation | Source |
|-------|------|----------|---------|------------|--------|
| event_id | str | Yes | — | ULID, 26 chars | Feature 001 |
| event_type | str | Yes | — | min_length=1 | Feature 001 |
| aggregate_id | str | Yes | — | min_length=1 | Feature 001 |
| payload | Dict[str, Any] | No | {} | — | Feature 001 |
| timestamp | datetime | Yes | — | — | Feature 001 |
| node_id | str | Yes | — | min_length=1 | Feature 001 |
| lamport_clock | int | Yes | — | ge=0 | Feature 001 |
| causation_id | Optional[str] | No | None | ULID, 26 chars | Feature 001 |
| project_uuid | UUID | Yes | — | — | Feature 001 |
| project_slug | Optional[str] | No | None | — | Feature 001 |
| **correlation_id** | **str** | **Yes** | **—** | **ULID, 26 chars** | **Feature 004 (NEW)** |
| **schema_version** | **str** | **No** | **"1.0.0"** | **semver pattern** | **Feature 004 (NEW)** |
| **data_tier** | **int** | **No** | **0** | **ge=0, le=4** | **Feature 004 (NEW)** |

### MissionStatus (lifecycle.py)

```
ACTIVE = "active"
COMPLETED = "completed"
CANCELLED = "cancelled"
```

Terminal states: {COMPLETED, CANCELLED}

### MissionStartedPayload (lifecycle.py)

| Field | Type | Required | Validation |
|-------|------|----------|------------|
| mission_id | str | Yes | min_length=1 |
| mission_type | str | Yes | min_length=1 |
| initial_phase | str | Yes | min_length=1 |
| actor | str | Yes | min_length=1 |

### MissionCompletedPayload (lifecycle.py)

| Field | Type | Required | Validation |
|-------|------|----------|------------|
| mission_id | str | Yes | min_length=1 |
| mission_type | str | Yes | min_length=1 |
| final_phase | str | Yes | min_length=1 |
| actor | str | Yes | min_length=1 |

### MissionCancelledPayload (lifecycle.py)

| Field | Type | Required | Validation |
|-------|------|----------|------------|
| mission_id | str | Yes | min_length=1 |
| reason | str | Yes | min_length=1 |
| actor | str | Yes | min_length=1 |
| cancelled_wp_ids | List[str] | Yes | — |

### PhaseEnteredPayload (lifecycle.py)

| Field | Type | Required | Validation |
|-------|------|----------|------------|
| mission_id | str | Yes | min_length=1 |
| phase_name | str | Yes | min_length=1 |
| previous_phase | Optional[str] | No | min_length=1 if present |
| actor | str | Yes | min_length=1 |

### ReviewRollbackPayload (lifecycle.py)

| Field | Type | Required | Validation |
|-------|------|----------|------------|
| mission_id | str | Yes | min_length=1 |
| review_ref | str | Yes | min_length=1 |
| target_phase | str | Yes | min_length=1 |
| affected_wp_ids | List[str] | Yes | — |
| actor | str | Yes | min_length=1 |

### ReducedMissionState (lifecycle.py)

| Field | Type | Required | Default |
|-------|------|----------|---------|
| mission_id | Optional[str] | No | None |
| mission_status | Optional[MissionStatus] | No | None |
| mission_type | Optional[str] | No | None |
| current_phase | Optional[str] | No | None |
| phases_entered | List[str] | No | [] |
| wp_states | Dict[str, WPState] | No | {} |
| anomalies | List[LifecycleAnomaly] | No | [] |
| event_count | int | No | 0 |
| last_processed_event_id | Optional[str] | No | None |

### LifecycleAnomaly (lifecycle.py)

| Field | Type | Required |
|-------|------|----------|
| event_id | str | Yes |
| event_type | str | Yes |
| reason | str | Yes |

## State Transitions

### Mission Lifecycle

```
(no state) --MissionStarted--> ACTIVE
ACTIVE --MissionCompleted--> COMPLETED (terminal)
ACTIVE --MissionCancelled--> CANCELLED (terminal)
ACTIVE --PhaseEntered--> ACTIVE (current_phase updated)
ACTIVE --ReviewRollback--> ACTIVE (current_phase rolled back)
```

### Precedence Rules

1. **Cancel > re-open**: Concurrent MissionCancelled + any re-activating event at same Lamport clock → CANCELLED wins
2. **Rollback = new event**: ReviewRollback is a new event, never overwrites existing events
3. **Dedup by event_id**: Identical events (same event_id) processed only once

## Relationships

```
Event 1──* MissionStartedPayload (via payload dict + event_type)
Event 1──* MissionCompletedPayload
Event 1──* MissionCancelledPayload
Event 1──* PhaseEnteredPayload
Event 1──* ReviewRollbackPayload
Event 1──* StatusTransitionPayload (Feature 003)
Event 1──* GatePassedPayload / GateFailedPayload (Feature 002)

ReducedMissionState 1──* WPState (from Feature 003 reduce_status_events)
ReducedMissionState 1──* LifecycleAnomaly
```
