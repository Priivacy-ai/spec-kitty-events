---
work_package_id: WP07
title: Exports and Schema Generation
lane: "done"
dependencies: [WP06]
base_branch: 006-mission-collaboration-soft-coordination-contracts-WP06
base_commit: dc1e5a5c78a3af8ec033970101289c108f0989ab
created_at: '2026-02-15T11:19:09.008361+00:00'
subtasks:
- T038
- T039
- T040
- T041
- T042
phase: Phase 3 - Integration
assignee: ''
agent: "claude-coordinator"
shell_pid: "86895"
review_status: "approved"
reviewed_by: "Robert Douglass"
history:
- timestamp: '2026-02-15T10:35:14Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP07 – Exports and Schema Generation

## Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above. If it says `has_feedback`, scroll to the **Review Feedback** section immediately.
- **Mark as acknowledged**: Update `review_status: acknowledged` when you begin addressing feedback.

---

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Objectives & Success Criteria

Make all collaboration symbols importable from `spec_kitty_events` and generate JSON Schema files:
1. Add 36 new exports to `__init__.py`
2. Register 17 new models in `schemas/generate.py`
3. Generate and commit JSON Schema files
4. Update conformance validators
5. Pass schema drift check

**Success criteria**:
- All 36 symbols importable: `from spec_kitty_events import ParticipantIdentity, reduce_collaboration_events, ...`
- 17 new `.schema.json` files generated in `src/spec_kitty_events/schemas/`
- Schema drift check passes: `python3.11 -m spec_kitty_events.schemas.generate --check`
- No circular import errors
- Total package exports: 68 (existing) + 36 (new) = 104

## Context & Constraints

**Reference documents**:
- Export list: `kitty-specs/006-.../contracts/collaboration-api.md` (Export List section)
- Schema generation pattern: `src/spec_kitty_events/schemas/generate.py`

**Prerequisites**: WP06 must be merged (all models and reducer in collaboration.py)

**Implementation command**: `spec-kitty implement WP07 --base WP06`

**Existing patterns**:
- `__init__.py` organizes imports by module with section comments
- `schemas/generate.py` uses `PYDANTIC_MODELS` list of `(name, ModelClass)` tuples
- Conformance validators map `event_type → payload model`

## Subtasks & Detailed Guidance

### Subtask T038 – Add 36 exports to `__init__.py`

- **Purpose**: Make all collaboration symbols part of the public API.
- **Steps**:
  1. Add a new `# Collaboration event contracts` section to `__init__.py` (after Status section)
  2. Import and export in this order (matching contract):
     ```python
     # Collaboration event contracts
     from spec_kitty_events.collaboration import (
         # Constants (15)
         PARTICIPANT_INVITED,
         PARTICIPANT_JOINED,
         PARTICIPANT_LEFT,
         PRESENCE_HEARTBEAT,
         DRIVE_INTENT_SET,
         FOCUS_CHANGED,
         PROMPT_STEP_EXECUTION_STARTED,
         PROMPT_STEP_EXECUTION_COMPLETED,
         CONCURRENT_DRIVER_WARNING,
         POTENTIAL_STEP_COLLISION_DETECTED,
         WARNING_ACKNOWLEDGED,
         COMMENT_POSTED,
         DECISION_CAPTURED,
         SESSION_LINKED,
         COLLABORATION_EVENT_TYPES,
         # Identity models (3)
         ParticipantIdentity,
         AuthPrincipalBinding,
         FocusTarget,
         # Payload models (14)
         ParticipantInvitedPayload,
         ParticipantJoinedPayload,
         ParticipantLeftPayload,
         PresenceHeartbeatPayload,
         DriveIntentSetPayload,
         FocusChangedPayload,
         PromptStepExecutionStartedPayload,
         PromptStepExecutionCompletedPayload,
         ConcurrentDriverWarningPayload,
         PotentialStepCollisionDetectedPayload,
         WarningAcknowledgedPayload,
         CommentPostedPayload,
         DecisionCapturedPayload,
         SessionLinkedPayload,
         # Reducer output (3)
         ReducedCollaborationState,
         CollaborationAnomaly,
         UnknownParticipantError,
         # Reducer function (1)
         reduce_collaboration_events,
     )
     ```
  3. Verify no circular imports by running: `python3.11 -c "import spec_kitty_events"`
- **Files**: `src/spec_kitty_events/__init__.py`
- **Parallel?**: Yes (with T039)
- **Notes**: Count total exports — should be 104 (68 existing + 36 new)

### Subtask T039 – Register 17 models in schemas/generate.py

- **Purpose**: Enable JSON Schema generation for all collaboration Pydantic models.
- **Steps**:
  1. Read `src/spec_kitty_events/schemas/generate.py` to understand the `PYDANTIC_MODELS` list pattern
  2. Add 17 new entries (3 identity + 14 payload models):
     ```python
     # Collaboration identity models
     ("participant_identity", ParticipantIdentity),
     ("auth_principal_binding", AuthPrincipalBinding),
     ("focus_target", FocusTarget),
     # Collaboration payload models
     ("participant_invited_payload", ParticipantInvitedPayload),
     ("participant_joined_payload", ParticipantJoinedPayload),
     ("participant_left_payload", ParticipantLeftPayload),
     ("presence_heartbeat_payload", PresenceHeartbeatPayload),
     ("drive_intent_set_payload", DriveIntentSetPayload),
     ("focus_changed_payload", FocusChangedPayload),
     ("prompt_step_execution_started_payload", PromptStepExecutionStartedPayload),
     ("prompt_step_execution_completed_payload", PromptStepExecutionCompletedPayload),
     ("concurrent_driver_warning_payload", ConcurrentDriverWarningPayload),
     ("potential_step_collision_detected_payload", PotentialStepCollisionDetectedPayload),
     ("warning_acknowledged_payload", WarningAcknowledgedPayload),
     ("comment_posted_payload", CommentPostedPayload),
     ("decision_captured_payload", DecisionCapturedPayload),
     ("session_linked_payload", SessionLinkedPayload),
     ```
  3. Add corresponding imports from `spec_kitty_events.collaboration`
  4. Do NOT register reducer output models (`ReducedCollaborationState`, etc.) — they are internal reducer state, not event schemas
- **Files**: `src/spec_kitty_events/schemas/generate.py`
- **Parallel?**: Yes (with T038)
- **Notes**: Use snake_case names matching Pydantic convention for schema file naming

### Subtask T040 – Generate and commit JSON Schema files

- **Purpose**: Run the schema generator and commit the output.
- **Steps**:
  1. Run: `python3.11 -m spec_kitty_events.schemas.generate`
  2. Verify 17 new `.schema.json` files created in `src/spec_kitty_events/schemas/`
  3. Verify each schema file is valid JSON and has `"title"` matching the model name
  4. Stage and note the new files (will be committed with the WP)
- **Files**: `src/spec_kitty_events/schemas/*.schema.json` (17 new files)
- **Parallel?**: No — depends on T039

### Subtask T041 – Update conformance validators

- **Purpose**: Enable conformance validation for collaboration event payloads.
- **Steps**:
  1. Read `src/spec_kitty_events/conformance/validators.py` to understand the event_type → model mapping
  2. Add all 14 collaboration event types to the mapping:
     ```python
     "ParticipantInvited": ParticipantInvitedPayload,
     "ParticipantJoined": ParticipantJoinedPayload,
     "ParticipantLeft": ParticipantLeftPayload,
     "PresenceHeartbeat": PresenceHeartbeatPayload,
     # ... etc for all 14
     ```
  3. Import the payload models from collaboration module
- **Files**: `src/spec_kitty_events/conformance/validators.py`
- **Parallel?**: No — depends on T038 (imports must work)

### Subtask T042 – Run schema drift check

- **Purpose**: Verify committed schemas match generated schemas (no drift).
- **Steps**:
  1. Run: `python3.11 -m spec_kitty_events.schemas.generate --check`
  2. Verify exit code 0 (no drift)
  3. If drift detected: re-generate and re-commit
  4. Run full test suite: `python3.11 -m pytest -x`
  5. Run mypy: `mypy --strict src/spec_kitty_events/`
- **Files**: N/A (verification step)
- **Parallel?**: No — final verification

## Test Strategy

- **Import verification**: `python3.11 -c "from spec_kitty_events import ParticipantIdentity, reduce_collaboration_events"`
- **Schema check**: `python3.11 -m spec_kitty_events.schemas.generate --check`
- **Full suite**: `python3.11 -m pytest -x`
- **mypy**: `mypy --strict src/spec_kitty_events/`

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Circular import between collaboration.py and __init__.py | ImportError at startup | collaboration.py imports from models.py and status.py only; __init__.py imports from collaboration.py — no cycle |
| Schema generation fails on complex types (FocusTarget nested, Tuple) | Missing schema files | Pydantic v2 TypeAdapter handles nested models — verify |

## Review Guidance

- Verify exactly 36 new symbols exported from `__init__.py`
- Verify 17 new schema files exist and are valid JSON
- Verify schema drift check passes
- Verify conformance validator covers all 14 event types
- Verify no circular imports: `python3.11 -c "import spec_kitty_events"` succeeds
- Count total exports: should be 104

## Completion

```bash
git add -A && git commit -m "feat(WP07): exports and schema generation for collaboration"
spec-kitty agent tasks move-task WP07 --to for_review --note "Ready for review: 36 exports, 17 schemas, conformance validators"
```

## Activity Log

- 2026-02-15T10:35:14Z – system – lane=planned – Prompt created.
- 2026-02-15T11:19:09Z – claude-coordinator – shell_pid=86895 – lane=doing – Assigned agent via workflow command
- 2026-02-15T11:22:48Z – claude-coordinator – shell_pid=86895 – lane=for_review – Ready for review: 36 exports, 17 schemas, conformance validators
- 2026-02-15T11:22:49Z – claude-coordinator – shell_pid=86895 – lane=done – Review passed: exports, schemas, conformance all verified
