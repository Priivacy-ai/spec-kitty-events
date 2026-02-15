---
work_package_id: WP01
title: Constants and Identity Models
lane: "doing"
dependencies: []
base_branch: main
base_commit: 0697f26d3beaaf8cadb3eb68e938f31c4d05e71d
created_at: '2026-02-15T10:46:29.964505+00:00'
subtasks:
- T001
- T002
- T003
- T004
- T005
- T006
- T007
phase: Phase 0 - Foundation
assignee: ''
agent: "claude-coordinator"
shell_pid: "44934"
review_status: ''
reviewed_by: ''
history:
- timestamp: '2026-02-15T10:35:14Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP01 – Constants and Identity Models

## Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above. If it says `has_feedback`, scroll to the **Review Feedback** section immediately.
- **You must address all feedback** before your work is complete.
- **Mark as acknowledged**: When you understand the feedback and begin addressing it, update `review_status: acknowledged` in the frontmatter.

---

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Objectives & Success Criteria

Create `src/spec_kitty_events/collaboration.py` with:
1. All 14 event type string constants and `COLLABORATION_EVENT_TYPES` frozenset
2. 3 identity/target models: `ParticipantIdentity`, `AuthPrincipalBinding`, `FocusTarget`
3. `UnknownParticipantError` exception class
4. Unit tests covering all models, constants, and exception

**Success criteria**:
- All models are frozen Pydantic v2 with `ConfigDict(frozen=True)`
- `FocusTarget` is hashable (usable as dict key)
- All field constraints (`min_length=1`, `Literal` types) enforced
- `mypy --strict` passes
- All models round-trip through `model_dump()` / `model_validate()`

## Context & Constraints

**Reference documents**:
- Data model: `kitty-specs/006-mission-collaboration-soft-coordination-contracts/data-model.md`
- API contract: `kitty-specs/006-mission-collaboration-soft-coordination-contracts/contracts/collaboration-api.md`
- Research decisions: `kitty-specs/006-mission-collaboration-soft-coordination-contracts/research.md` (R1, R5)

**Architecture**:
- Single `collaboration.py` file following `lifecycle.py` section structure (R1 decision)
- Module starts with constants, then identity models, then exception
- Later WPs will add payload models, output models, and reducer to the same file
- Use `from __future__ import annotations` for forward reference compatibility
- Import patterns: `from pydantic import BaseModel, ConfigDict, Field` and `from typing import ...`
- Exception inherits from `SpecKittyEventsError` (in `models.py`)

**Existing patterns to follow**:
- `lifecycle.py` lines 1-56: section headers with `# ── Section N: Title ──` comments
- `MissionStartedPayload` (lifecycle.py:60-78): frozen Pydantic model with Field descriptors
- `MISSION_EVENT_TYPES` (lifecycle.py:33-39): frozenset of all event type constants

## Subtasks & Detailed Guidance

### Subtask T001 – Create collaboration.py with module structure

- **Purpose**: Establish the file with docstring and section headers that later WPs will fill in.
- **Steps**:
  1. Create `src/spec_kitty_events/collaboration.py`
  2. Add module docstring describing purpose (collaboration event contracts for Feature 006)
  3. Add section headers matching the planned 5-section layout:
     ```python
     # ── Section 1: Constants ──
     # ── Section 2: Identity and Target Models ──
     # ── Section 3: Payload Models ──  (populated by WP02-WP04)
     # ── Section 4: Reducer Output Models ──  (populated by WP05)
     # ── Section 5: Collaboration Reducer ──  (populated by WP06)
     ```
  4. Add imports:
     ```python
     from __future__ import annotations
     from datetime import datetime
     from typing import Dict, FrozenSet, List, Literal, Optional, Sequence, Tuple
     from pydantic import BaseModel, ConfigDict, Field
     from spec_kitty_events.models import SpecKittyEventsError
     ```
- **Files**: `src/spec_kitty_events/collaboration.py` (new)
- **Parallel?**: No — must be done first

### Subtask T002 – Define 14 event type constants and COLLABORATION_EVENT_TYPES

- **Purpose**: Provide typed string constants for all collaboration event types, matching the pattern in `lifecycle.py`.
- **Steps**:
  1. Define all 14 constants exactly as specified in the API contract:
     ```python
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
     ```
  2. Define the frozenset:
     ```python
     COLLABORATION_EVENT_TYPES: FrozenSet[str] = frozenset({
         PARTICIPANT_INVITED, PARTICIPANT_JOINED, PARTICIPANT_LEFT,
         PRESENCE_HEARTBEAT, DRIVE_INTENT_SET, FOCUS_CHANGED,
         PROMPT_STEP_EXECUTION_STARTED, PROMPT_STEP_EXECUTION_COMPLETED,
         CONCURRENT_DRIVER_WARNING, POTENTIAL_STEP_COLLISION_DETECTED,
         WARNING_ACKNOWLEDGED, COMMENT_POSTED, DECISION_CAPTURED,
         SESSION_LINKED,
     })
     ```
- **Files**: `src/spec_kitty_events/collaboration.py`
- **Parallel?**: No — follows T001
- **Notes**: Verify `len(COLLABORATION_EVENT_TYPES) == 14` in test

### Subtask T003 – Implement ParticipantIdentity model

- **Purpose**: SaaS-minted, mission-scoped participant identity model.
- **Steps**:
  1. Implement in Section 2 of `collaboration.py`:
     ```python
     class ParticipantIdentity(BaseModel):
         """SaaS-minted, mission-scoped participant identity."""
         model_config = ConfigDict(frozen=True)
         participant_id: str = Field(..., min_length=1, description="SaaS-minted, mission-scoped unique identifier")
         participant_type: Literal["human", "llm_context"] = Field(..., description="Participant category")
         display_name: Optional[str] = Field(None, description="Human-readable name for display")
         session_id: Optional[str] = Field(None, description="SaaS-issued session identifier")
     ```
  2. Verify frozen behavior: attempting attribute assignment raises error
  3. Verify round-trip: `model_dump()` → `model_validate()` produces equal model
- **Files**: `src/spec_kitty_events/collaboration.py`
- **Parallel?**: Yes (with T004, T005)
- **Notes**: `participant_type` uses `Literal["human", "llm_context"]` — extensible in future minor versions by widening the Literal

### Subtask T004 – Implement AuthPrincipalBinding model

- **Purpose**: Roster-level association between authenticated identity and mission-scoped participant. Created by SaaS at join time.
- **Steps**:
  1. Implement in Section 2:
     ```python
     class AuthPrincipalBinding(BaseModel):
         """Roster-level auth principal to participant binding."""
         model_config = ConfigDict(frozen=True)
         auth_principal_id: str = Field(..., min_length=1, description="Authenticated identity (opaque to this package)")
         participant_id: str = Field(..., min_length=1, description="Mission-scoped participant identifier")
         bound_at: datetime = Field(..., description="Timestamp when binding was created")
     ```
- **Files**: `src/spec_kitty_events/collaboration.py`
- **Parallel?**: Yes (with T003, T005)

### Subtask T005 – Implement FocusTarget model (hashable)

- **Purpose**: Structured reference to what a participant is focused on. Must be hashable for use as dict key in `participants_by_focus`.
- **Steps**:
  1. Implement in Section 2:
     ```python
     class FocusTarget(BaseModel):
         """Structured focus reference. Hashable for use as dict key."""
         model_config = ConfigDict(frozen=True)
         target_type: Literal["wp", "step", "file"] = Field(..., description="Category of focus target")
         target_id: str = Field(..., min_length=1, description="Identifier within the target type")
     ```
  2. **Critical test**: verify hashability:
     ```python
     target = FocusTarget(target_type="wp", target_id="WP03")
     d = {target: frozenset({"p-001"})}  # Must not raise
     assert target in d
     ```
  3. Verify two FocusTarget instances with same values are equal and have same hash
- **Files**: `src/spec_kitty_events/collaboration.py`
- **Parallel?**: Yes (with T003, T004)
- **Notes**: Frozen Pydantic v2 models are hashable by default. Verify this assumption in test.

### Subtask T006 – Implement UnknownParticipantError exception

- **Purpose**: Raised in strict mode when an event references a `participant_id` not in the mission roster.
- **Steps**:
  1. Implement after the identity models (still in Section 2 or as a standalone section):
     ```python
     class UnknownParticipantError(SpecKittyEventsError):
         """Raised in strict mode for events from non-rostered participants."""
         def __init__(self, participant_id: str, event_id: str, event_type: str) -> None:
             self.participant_id = participant_id
             self.event_id = event_id
             self.event_type = event_type
             super().__init__(
                 f"Unknown participant {participant_id!r} in event {event_id} "
                 f"(type={event_type}). Not in mission roster."
             )
     ```
  2. Verify it can be raised and caught as both `UnknownParticipantError` and `SpecKittyEventsError`
  3. Verify the `participant_id`, `event_id`, `event_type` attributes are accessible
- **Files**: `src/spec_kitty_events/collaboration.py`
- **Parallel?**: Yes (with T003-T005)
- **Notes**: Inherits from `SpecKittyEventsError` (already in `models.py`)

### Subtask T007 – Write unit tests for identity models, constants, and exception

- **Purpose**: Comprehensive test coverage for all WP01 deliverables.
- **Steps**:
  1. Create `tests/unit/test_collaboration_models.py`
  2. Test categories:
     - **Constants**: verify all 14 constants are strings, `COLLABORATION_EVENT_TYPES` has exactly 14 elements, no duplicates
     - **ParticipantIdentity**: valid construction, frozen, empty `participant_id` rejected (`min_length=1`), invalid `participant_type` rejected, optional fields default to None, round-trip
     - **AuthPrincipalBinding**: valid construction, frozen, empty `auth_principal_id` rejected, `bound_at` accepts datetime, round-trip
     - **FocusTarget**: valid construction, frozen, hashable (usable as dict key), empty `target_id` rejected, invalid `target_type` rejected, equal instances have same hash
     - **UnknownParticipantError**: can be raised, caught as `SpecKittyEventsError`, attributes accessible, message format
  3. Run: `python3.11 -m pytest tests/unit/test_collaboration_models.py -v`
  4. Run: `mypy --strict src/spec_kitty_events/collaboration.py`
- **Files**: `tests/unit/test_collaboration_models.py` (new)
- **Parallel?**: No — depends on T001-T006

## Test Strategy

- **Unit tests**: `tests/unit/test_collaboration_models.py`
- **Run command**: `python3.11 -m pytest tests/unit/test_collaboration_models.py -v`
- **mypy check**: `mypy --strict src/spec_kitty_events/collaboration.py`
- **Coverage target**: 100% of WP01 code (constants, 3 models, 1 exception)

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| FocusTarget not hashable | Blocks `participants_by_focus` dict in WP05/WP06 | Frozen Pydantic models hash by default — verify in T005 test |
| `from __future__ import annotations` breaks runtime type checks | Runtime Pydantic validation | Pydantic v2 handles PEP 604 annotations correctly — verify |
| Circular import with models.py | Import error | `SpecKittyEventsError` is a simple exception in models.py — no circular risk |

## Review Guidance

- Verify all 14 event type constants match the values in `data-model.md` and `contracts/collaboration-api.md`
- Verify `COLLABORATION_EVENT_TYPES` frozenset contains exactly the 14 defined constants
- Verify all models use `ConfigDict(frozen=True)` and have `min_length=1` on required string fields
- Verify `FocusTarget` hashability test exists and passes
- Verify `UnknownParticipantError` inherits from `SpecKittyEventsError` and has all 3 attributes
- Verify `mypy --strict` passes with no errors

## Completion

When all subtasks are complete, commit and move to review:

```bash
git add -A && git commit -m "feat(WP01): constants and identity models for collaboration"
spec-kitty agent tasks move-task WP01 --to for_review --note "Ready for review: 14 constants, 3 identity models, exception, unit tests"
```

## Activity Log

- 2026-02-15T10:35:14Z – system – lane=planned – Prompt created.
- 2026-02-15T10:46:30Z – claude-coordinator – shell_pid=44934 – lane=doing – Assigned agent via workflow command
