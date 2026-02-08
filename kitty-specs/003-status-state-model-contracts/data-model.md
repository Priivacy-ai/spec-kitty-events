# Data Model: Status State Model Contracts

**Feature**: 003-status-state-model-contracts
**Date**: 2026-02-08

## Entity Definitions

### Lane (str, Enum)

7 canonical status lane values.

| Value | String | Terminal | Notes |
|-------|--------|----------|-------|
| PLANNED | `"planned"` | No | Initial/default lane |
| CLAIMED | `"claimed"` | No | Actor has taken ownership |
| IN_PROGRESS | `"in_progress"` | No | Active implementation |
| FOR_REVIEW | `"for_review"` | No | Awaiting review |
| DONE | `"done"` | Yes | Completed with evidence |
| BLOCKED | `"blocked"` | No | Blocked by external dependency |
| CANCELED | `"canceled"` | Yes | Permanently canceled |

**Alias map** (input normalization only):

| Alias | Canonical |
|-------|-----------|
| `doing` | `in_progress` |

### ExecutionMode (str, Enum)

| Value | String | Description |
|-------|--------|-------------|
| WORKTREE | `"worktree"` | Worktree-based implementation |
| DIRECT_REPO | `"direct_repo"` | Direct repository implementation |

### RepoEvidence (frozen BaseModel)

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| repo | str | Yes | min_length=1 |
| branch | str | Yes | min_length=1 |
| commit | str | Yes | min_length=1 |
| files_touched | Optional[List[str]] | No | Default: None |

### VerificationEntry (frozen BaseModel)

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| command | str | Yes | min_length=1 |
| result | str | Yes | min_length=1 |
| summary | Optional[str] | No | Default: None |

### ReviewVerdict (frozen BaseModel)

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| reviewer | str | Yes | min_length=1 |
| verdict | str | Yes | min_length=1 |
| reference | Optional[str] | No | Default: None |

### DoneEvidence (frozen BaseModel)

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| repos | List[RepoEvidence] | Yes | min_length=1 (at least one repo) |
| verification | List[VerificationEntry] | Yes | Default: [] (can be empty) |
| review | ReviewVerdict | Yes | Required |

### ForceMetadata (frozen BaseModel)

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| force | bool | Yes | Default: True |
| actor | str | Yes | min_length=1 |
| reason | str | Yes | min_length=1 |

### StatusTransitionPayload (frozen BaseModel)

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| feature_slug | str | Yes | min_length=1 |
| wp_id | str | Yes | min_length=1 |
| from_lane | Optional[Lane] | No | None for initial events; aliases normalized |
| to_lane | Lane | Yes | Aliases normalized |
| actor | str | Yes | min_length=1 |
| force | bool | No | Default: False |
| reason | Optional[str] | No | Required when force=True |
| execution_mode | ExecutionMode | Yes | |
| review_ref | Optional[str] | No | Required for for_review->in_progress |
| evidence | Optional[DoneEvidence] | No | Required for transitions to done |

**Pydantic model validators** (cross-field):
1. When `force=True`: `reason` must not be None and must be non-empty
2. When `to_lane=done`: `evidence` must not be None
3. Lane alias normalization on `from_lane` and `to_lane` via `@field_validator`

### TransitionValidationResult (frozen dataclass)

| Field | Type | Required | Default |
|-------|------|----------|---------|
| valid | bool | Yes | |
| violations | Tuple[str, ...] | Yes | () |

### WPState (frozen BaseModel)

Per-work-package reduced state.

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| wp_id | str | Yes | min_length=1 |
| current_lane | Lane | Yes | |
| last_event_id | str | Yes | ULID |
| last_transition_at | datetime | Yes | UTC |
| evidence | Optional[DoneEvidence] | No | Present when lane=done |

### TransitionAnomaly (frozen BaseModel)

Records an invalid transition encountered during reduction.

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| event_id | str | Yes | ULID of the problematic event |
| wp_id | str | Yes | |
| from_lane | Optional[Lane] | No | |
| to_lane | Lane | Yes | |
| reason | str | Yes | Human-readable explanation |

### ReducedStatus (frozen BaseModel)

Output of the reference reducer.

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| wp_states | Dict[str, WPState] | Yes | Keyed by wp_id |
| anomalies | List[TransitionAnomaly] | Yes | Default: [] |
| event_count | int | Yes | Total events processed |
| last_processed_event_id | Optional[str] | No | ULID of last event |

## State Machine: Transition Matrix

### Default Transitions (force=False)

| From | To | Guard Conditions |
|------|----|-----------------|
| None | planned | Initial event only |
| planned | claimed | actor required |
| claimed | in_progress | (consumer validates workspace) |
| in_progress | for_review | (subtask evidence or force) |
| for_review | done | evidence required (DoneEvidence) |
| for_review | in_progress | review_ref required |
| in_progress | planned | reason required (abandon/reassign) |
| * (non-terminal) | blocked | |
| blocked | in_progress | |
| * (non-terminal) | canceled | |

### Force Transitions

When `force=True`, `actor` and `reason` are required. Force allows:
- Any transition from terminal lanes (`done`, `canceled`)
- Any non-standard transition between non-terminal lanes

### Terminal Lanes

`done` and `canceled` are terminal. Transitions FROM these lanes require `force=True`.

## Relationship to Existing Event Model

```
Event (existing, unchanged)
├── event_id: str (ULID)
├── event_type: "WPStatusChanged"
├── aggregate_id: str (feature_slug or wp composite key)
├── payload: Dict[str, Any]  ← StatusTransitionPayload.model_dump()
├── timestamp: datetime
├── node_id: str
├── lamport_clock: int
├── causation_id: Optional[str]
├── project_uuid: UUID
└── project_slug: Optional[str]
```

The `StatusTransitionPayload` serializes into `Event.payload`. The reducer deserializes it back during replay.
