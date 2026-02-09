---
work_package_id: WP02
title: Lifecycle Payload Models
lane: "for_review"
dependencies: []
base_branch: 004-canonical-event-contract-WP01
base_commit: 9ad0795ce86fc43e76608f4aa0bf1c80b7dbe183
created_at: '2026-02-09T11:43:55.157119+00:00'
subtasks: [T008, T009, T010, T011, T012, T013]
agent: claude-opus
shell_pid: '11768'
history:
- date: '2026-02-09'
  agent: claude-opus
  action: created
  note: Generated from /spec-kitty.tasks
---

# WP02: Lifecycle Payload Models

## Objective

Create the `lifecycle.py` module with all mission-level event type constants, MissionStatus enum, and typed payload models for all lifecycle event types (FR-005 through FR-015).

## Context

This WP creates the contract surface — the typed payload models that spec-kitty CLI and spec-kitty-saas will consume. The module follows the established patterns from `gates.py` (Feature 002) and `status.py` (Feature 003):
- All models use `ConfigDict(frozen=True)`
- All string fields have `min_length=1`
- Constants use UPPER_SNAKE_CASE strings

**Reference**: Read `src/spec_kitty_events/gates.py` for the gate payload pattern and `src/spec_kitty_events/status.py` (Section 1: Enums, Section 2: Evidence Models) for the enum and evidence model patterns.

## Implementation Command

```bash
spec-kitty implement WP02 --base WP01
```

## Detailed Guidance

### T008: Create lifecycle.py Module

**File**: `src/spec_kitty_events/lifecycle.py` (NEW)

Create the file with module docstring and section markers:

```python
"""Mission lifecycle event contracts for the canonical event schema.

This module defines typed payload models for all mission-level lifecycle
events, the MissionStatus enum, event type constants, and the SCHEMA_VERSION
constant. It is part of the canonical event contract (Feature 004).

Sections:
    1. Constants (SCHEMA_VERSION, event type strings)
    2. MissionStatus Enum
    3. Lifecycle Payload Models
    4. Lifecycle Reducer Output Models (added in WP03)
    5. Lifecycle Reducer (added in WP03)
"""

from enum import Enum
from typing import FrozenSet, List, Optional

from pydantic import BaseModel, ConfigDict, Field
```

### T009: Implement MissionStatus Enum

**Location**: `src/spec_kitty_events/lifecycle.py` — Section 2

```python
class MissionStatus(str, Enum):
    """Mission lifecycle states."""
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

TERMINAL_MISSION_STATUSES: FrozenSet[MissionStatus] = frozenset({
    MissionStatus.COMPLETED,
    MissionStatus.CANCELLED,
})
```

**Design notes**:
- Use `(str, Enum)` pattern matching `Lane(str, Enum)` from Feature 003 for Python 3.10 compat
- Terminal states follow the same pattern as `TERMINAL_LANES` in status.py
- COMPLETED and CANCELLED are terminal — once reached, mission cannot transition out (anomaly if attempted)

### T010: Implement Constants

**Location**: `src/spec_kitty_events/lifecycle.py` — Section 1

```python
SCHEMA_VERSION: str = "1.0.0"

# Event type string constants
MISSION_STARTED: str = "MissionStarted"
MISSION_COMPLETED: str = "MissionCompleted"
MISSION_CANCELLED: str = "MissionCancelled"
PHASE_ENTERED: str = "PhaseEntered"
REVIEW_ROLLBACK: str = "ReviewRollback"

MISSION_EVENT_TYPES: FrozenSet[str] = frozenset({
    MISSION_STARTED,
    MISSION_COMPLETED,
    MISSION_CANCELLED,
    PHASE_ENTERED,
    REVIEW_ROLLBACK,
})
```

**Design notes**:
- `SCHEMA_VERSION` is the envelope version, not the library version. It starts at "1.0.0".
- Event type strings match PascalCase convention established by `WP_STATUS_CHANGED = "WPStatusChanged"` in status.py
- `MISSION_EVENT_TYPES` frozenset enables checking if an event is mission-level vs WP-level

### T011: Implement MissionStartedPayload and MissionCompletedPayload

**Location**: `src/spec_kitty_events/lifecycle.py` — Section 3

```python
class MissionStartedPayload(BaseModel):
    """Typed payload for MissionStarted events."""
    model_config = ConfigDict(frozen=True)

    mission_id: str = Field(..., min_length=1, description="Mission identifier")
    mission_type: str = Field(..., min_length=1, description="Mission type (e.g., 'software-dev', 'research', 'plan')")
    initial_phase: str = Field(..., min_length=1, description="First phase of the mission")
    actor: str = Field(..., min_length=1, description="Actor who started the mission")


class MissionCompletedPayload(BaseModel):
    """Typed payload for MissionCompleted events."""
    model_config = ConfigDict(frozen=True)

    mission_id: str = Field(..., min_length=1, description="Mission identifier")
    mission_type: str = Field(..., min_length=1, description="Mission type")
    final_phase: str = Field(..., min_length=1, description="Last phase before completion")
    actor: str = Field(..., min_length=1, description="Actor who completed the mission")
```

**Design notes**:
- All fields required, no defaults — mission events always have full context
- `mission_type` accepts any string (e.g., "software-dev", "research", "plan") — validation of valid types is the mission DSL's concern
- `initial_phase`/`final_phase` accept any string — phase validation is the DSL's concern

### T012: Implement MissionCancelledPayload, PhaseEnteredPayload, ReviewRollbackPayload

**Location**: `src/spec_kitty_events/lifecycle.py` — Section 3 (continued)

```python
class MissionCancelledPayload(BaseModel):
    """Typed payload for MissionCancelled events."""
    model_config = ConfigDict(frozen=True)

    mission_id: str = Field(..., min_length=1, description="Mission identifier")
    reason: str = Field(..., min_length=1, description="Reason for cancellation (required)")
    actor: str = Field(..., min_length=1, description="Actor who cancelled the mission")
    cancelled_wp_ids: List[str] = Field(default_factory=list, description="WP IDs affected by cancellation")


class PhaseEnteredPayload(BaseModel):
    """Typed payload for PhaseEntered events."""
    model_config = ConfigDict(frozen=True)

    mission_id: str = Field(..., min_length=1, description="Mission identifier")
    phase_name: str = Field(..., min_length=1, description="Phase being entered")
    previous_phase: Optional[str] = Field(None, min_length=1, description="Phase being exited (None for initial)")
    actor: str = Field(..., min_length=1, description="Actor triggering phase transition")


class ReviewRollbackPayload(BaseModel):
    """Typed payload for ReviewRollback events."""
    model_config = ConfigDict(frozen=True)

    mission_id: str = Field(..., min_length=1, description="Mission identifier")
    review_ref: str = Field(..., min_length=1, description="Reference to the review that triggered rollback")
    target_phase: str = Field(..., min_length=1, description="Phase to roll back to")
    affected_wp_ids: List[str] = Field(default_factory=list, description="WP IDs affected by rollback")
    actor: str = Field(..., min_length=1, description="Actor triggering rollback")
```

**Design notes**:
- `MissionCancelledPayload.reason` is required (min_length=1) per FR-007 — cancellation must be justified
- `MissionCancelledPayload.cancelled_wp_ids` defaults to empty list — not all cancellations affect WPs
- `PhaseEnteredPayload.previous_phase` is Optional — None for the initial phase entry
- `ReviewRollbackPayload.review_ref` is required — rollbacks must reference the triggering review
- `ReviewRollbackPayload.affected_wp_ids` defaults to empty list — rollback may not always affect specific WPs

### T013: Add Unit Tests

**File**: `tests/unit/test_lifecycle.py` (NEW)

Write comprehensive tests for all models and constants:

**MissionStatus tests**:
- Enum values: ACTIVE="active", COMPLETED="completed", CANCELLED="cancelled"
- Terminal statuses: COMPLETED and CANCELLED in TERMINAL_MISSION_STATUSES
- ACTIVE not in TERMINAL_MISSION_STATUSES
- String comparison: `MissionStatus.ACTIVE == "active"` (because str, Enum)

**Constants tests**:
- SCHEMA_VERSION == "1.0.0"
- MISSION_STARTED == "MissionStarted"
- All 5 event type strings in MISSION_EVENT_TYPES
- MISSION_EVENT_TYPES is a frozenset (immutable)
- "WPStatusChanged" NOT in MISSION_EVENT_TYPES (that's a WP event, not mission)

**Payload model tests** (for each of the 5 models):
- Valid construction with all required fields → success
- Missing each required field → Pydantic ValidationError
- Empty string for required str fields → Pydantic ValidationError (min_length=1)
- Frozen: attempt to modify field → raises error
- Round-trip: `model.model_dump()` → `ModelClass(**dumped)` produces identical model
- `model_dump()` returns a plain dict (for Event.payload usage)

**PhaseEnteredPayload specific**:
- previous_phase=None → accepted
- previous_phase="" → Pydantic ValidationError (min_length=1 when present)

**MissionCancelledPayload specific**:
- cancelled_wp_ids=[] → accepted (empty list is valid)
- cancelled_wp_ids=["WP01", "WP02"] → accepted

**ReviewRollbackPayload specific**:
- affected_wp_ids=[] → accepted
- review_ref="" → Pydantic ValidationError

## Definition of Done

- [ ] `src/spec_kitty_events/lifecycle.py` exists with all 5 payload models + enum + constants
- [ ] All models are frozen (`ConfigDict(frozen=True)`)
- [ ] All required fields reject empty strings (`min_length=1`)
- [ ] Unit tests in `tests/unit/test_lifecycle.py` pass
- [ ] `mypy --strict src/spec_kitty_events/lifecycle.py` passes
- [ ] Existing tests still pass (`python3.11 -m pytest`)

## Risks

- **Pydantic v2 `(str, Enum)` behavior**: Test that `MissionStatus.ACTIVE == "active"` works. The `Lane(str, Enum)` pattern in Feature 003 confirms this works.
- **Optional[str] with min_length**: Pydantic v2 enforces min_length even for Optional fields when a value is provided. Test that `previous_phase=None` is accepted but `previous_phase=""` is rejected.

## Reviewer Guidance

1. Verify all 5 payload models match the data-model.md field definitions
2. Verify ConfigDict(frozen=True) on every model
3. Verify min_length=1 on every required str field
4. Verify constants match PascalCase event type convention
5. Verify MISSION_EVENT_TYPES contains exactly 5 strings
6. Run `python3.11 -m pytest tests/unit/test_lifecycle.py` — all pass

## Activity Log

- 2026-02-09T11:43:55Z – claude-opus – shell_pid=11768 – lane=doing – Assigned agent via workflow command
- 2026-02-09T11:45:57Z – claude-opus – shell_pid=11768 – lane=for_review – Ready for review: lifecycle.py with MissionStatus enum, 5 payload models, 5 event type constants. 402 tests pass, 99% coverage, mypy clean.
