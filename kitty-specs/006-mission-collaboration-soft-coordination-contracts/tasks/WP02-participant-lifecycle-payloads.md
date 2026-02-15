---
work_package_id: WP02
title: Participant Lifecycle Payloads
lane: "doing"
dependencies: [WP01]
base_branch: 006-mission-collaboration-soft-coordination-contracts-WP01
base_commit: f058d167abbbbbd8460757676b7e12ee4fb0ed3b
created_at: '2026-02-15T10:54:55.239478+00:00'
subtasks:
- T008
- T009
- T010
- T011
- T012
phase: Phase 1 - Payload Models
assignee: ''
agent: ''
shell_pid: "53449"
review_status: ''
reviewed_by: ''
history:
- timestamp: '2026-02-15T10:35:14Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP02 – Participant Lifecycle Payloads

## Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above. If it says `has_feedback`, scroll to the **Review Feedback** section immediately.
- **Mark as acknowledged**: Update `review_status: acknowledged` when you begin addressing feedback.

---

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Objectives & Success Criteria

Add the 4 participant lifecycle payload models to `collaboration.py` Section 3:
1. `ParticipantInvitedPayload`
2. `ParticipantJoinedPayload`
3. `ParticipantLeftPayload`
4. `PresenceHeartbeatPayload`

**Success criteria**:
- All 4 payloads are frozen Pydantic v2 models with correct field constraints
- `ParticipantJoinedPayload` includes optional `auth_principal_id` for SaaS-authoritative binding
- All payloads include `participant_id` and `mission_id` as required fields
- All payloads round-trip through `model_dump()` / `model_validate()`
- `mypy --strict` passes on collaboration.py

## Context & Constraints

**Reference documents**:
- Data model: `kitty-specs/006-.../data-model.md` (Participant Lifecycle Payloads section)
- API contract: `kitty-specs/006-.../contracts/collaboration-api.md` (Payload Actor Field Contract)

**Prerequisites**: WP01 must be merged (provides `ParticipantIdentity` model)

**Implementation command**: `spec-kitty implement WP02 --base WP01`

**Pattern**: Follow `MissionStartedPayload` from `lifecycle.py` — frozen BaseModel with Field descriptors and min_length constraints.

## Subtasks & Detailed Guidance

### Subtask T008 – Implement ParticipantInvitedPayload

- **Purpose**: Emitted when a participant is invited to a mission by SaaS.
- **Steps**:
  1. Add to Section 3 of `collaboration.py`:
     ```python
     class ParticipantInvitedPayload(BaseModel):
         """Typed payload for ParticipantInvited events."""
         model_config = ConfigDict(frozen=True)
         participant_id: str = Field(..., min_length=1, description="Invited participant")
         participant_identity: ParticipantIdentity = Field(..., description="Full structured identity")
         invited_by: str = Field(..., min_length=1, description="participant_id of inviter")
         mission_id: str = Field(..., min_length=1, description="Target mission")
     ```
- **Files**: `src/spec_kitty_events/collaboration.py`
- **Parallel?**: Yes (with T009-T011)

### Subtask T009 – Implement ParticipantJoinedPayload

- **Purpose**: Emitted when a participant joins a mission. Core roster-building event.
- **Steps**:
  1. Add to Section 3:
     ```python
     class ParticipantJoinedPayload(BaseModel):
         """Typed payload for ParticipantJoined events."""
         model_config = ConfigDict(frozen=True)
         participant_id: str = Field(..., min_length=1, description="Joining participant")
         participant_identity: ParticipantIdentity = Field(..., description="Full structured identity")
         mission_id: str = Field(..., min_length=1, description="Target mission")
         auth_principal_id: Optional[str] = Field(None, description="Auth principal bound at join time (present in live traffic)")
     ```
- **Files**: `src/spec_kitty_events/collaboration.py`
- **Parallel?**: Yes (with T008, T010, T011)
- **Notes**: `auth_principal_id` is Optional — absent for replay/import scenarios

### Subtask T010 – Implement ParticipantLeftPayload

- **Purpose**: Emitted when a participant leaves a mission (explicit or disconnect).
- **Steps**:
  1. Add to Section 3:
     ```python
     class ParticipantLeftPayload(BaseModel):
         """Typed payload for ParticipantLeft events."""
         model_config = ConfigDict(frozen=True)
         participant_id: str = Field(..., min_length=1, description="Departing participant")
         mission_id: str = Field(..., min_length=1, description="Mission being left")
         reason: Optional[str] = Field(None, description="Departure reason (e.g., 'disconnect', 'explicit')")
     ```
- **Files**: `src/spec_kitty_events/collaboration.py`
- **Parallel?**: Yes (with T008, T009, T011)

### Subtask T011 – Implement PresenceHeartbeatPayload

- **Purpose**: Periodic heartbeat emitted by active participants to signal presence.
- **Steps**:
  1. Add to Section 3:
     ```python
     class PresenceHeartbeatPayload(BaseModel):
         """Typed payload for PresenceHeartbeat events."""
         model_config = ConfigDict(frozen=True)
         participant_id: str = Field(..., min_length=1, description="Heartbeat source")
         mission_id: str = Field(..., min_length=1, description="Mission context")
         session_id: Optional[str] = Field(None, description="Specific session sending heartbeat")
     ```
- **Files**: `src/spec_kitty_events/collaboration.py`
- **Parallel?**: Yes (with T008-T010)

### Subtask T012 – Write unit tests for lifecycle payloads

- **Purpose**: Verify all 4 lifecycle payloads validate correctly.
- **Steps**:
  1. Add tests to `tests/unit/test_collaboration_models.py` (or a new file `tests/unit/test_collaboration_payloads.py`):
     - **ParticipantInvitedPayload**: valid construction with embedded `ParticipantIdentity`, empty `participant_id` rejected, empty `invited_by` rejected, round-trip
     - **ParticipantJoinedPayload**: valid with and without `auth_principal_id`, embedded `ParticipantIdentity`, round-trip
     - **ParticipantLeftPayload**: valid with and without `reason`, round-trip
     - **PresenceHeartbeatPayload**: valid with and without `session_id`, round-trip
  2. Run: `python3.11 -m pytest tests/unit/ -k collaboration -v`
- **Files**: `tests/unit/test_collaboration_payloads.py` (new) or extend existing test file
- **Parallel?**: No — depends on T008-T011

## Test Strategy

- **Unit tests**: `tests/unit/test_collaboration_payloads.py`
- **Run command**: `python3.11 -m pytest tests/unit/test_collaboration_payloads.py -v`
- **mypy check**: `mypy --strict src/spec_kitty_events/collaboration.py`

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Nested Pydantic model serialization | `ParticipantIdentity` may not round-trip as dict | Pydantic v2 handles nested models natively — verify in test |

## Review Guidance

- Verify all 4 payloads use `ConfigDict(frozen=True)`
- Verify `ParticipantJoinedPayload.auth_principal_id` is Optional (not required)
- Verify `ParticipantInvitedPayload` and `ParticipantJoinedPayload` embed `ParticipantIdentity` (not just participant_id)
- Verify all required string fields have `min_length=1`
- Cross-check field names with `data-model.md`

## Completion

```bash
git add -A && git commit -m "feat(WP02): participant lifecycle payloads"
spec-kitty agent tasks move-task WP02 --to for_review --note "Ready for review: 4 lifecycle payloads with tests"
```

## Activity Log

- 2026-02-15T10:35:14Z – system – lane=planned – Prompt created.
