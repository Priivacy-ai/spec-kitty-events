---
work_package_id: WP06
title: Reducer — Checks, Clarifications, Blocks & Assembly
lane: "doing"
dependencies: [WP05]
base_branch: 007-glossary-semantic-integrity-contracts-WP05
base_commit: 7126c08de30c59ad7421e93d1b514aabd77cd2ab
created_at: '2026-02-16T13:24:09.961343+00:00'
subtasks:
- T025
- T026
- T027
- T028
- T029
- T030
phase: Phase 2 - Reducer Implementation
assignee: ''
agent: "claude-opus"
shell_pid: "24697"
review_status: ''
reviewed_by: ''
history:
- timestamp: '2026-02-16T12:00:00Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP06 – Reducer — Checks, Clarifications, Blocks & Assembly

## ⚠️ IMPORTANT: Review Feedback Status

- **Has review feedback?**: Check the `review_status` field above.
- **You must address all feedback** before your work is complete.

---

## Review Feedback

*[This section is empty initially.]*

---

## Objectives & Success Criteria

- Complete the reducer by implementing processing for `SemanticCheckEvaluated`, `GlossaryClarificationRequested`, `GlossaryClarificationResolved`, and `GenerationBlockedBySemanticConflict` events.
- Implement the clarification burst-cap enforcement (max 3 active per `semantic_check_event_id`).
- Implement final state assembly (freeze all mutable intermediates into `ReducedGlossaryState`).
- `mypy --strict` passes on the complete `glossary.py`.

**Success**: Full event sequence reduces to correct `ReducedGlossaryState` with all facets populated, burst cap enforced, dual-mode working. The reducer is a complete, pure function.

## Context & Constraints

- **Reference**: `src/spec_kitty_events/collaboration.py:599-end` — final assembly pattern.
- **Reference**: `kitty-specs/007-glossary-semantic-integrity-contracts/data-model.md` — ClarificationRecord, ReducedGlossaryState.
- **Burst cap**: Max 3 unresolved clarifications per `semantic_check_event_id` (P2 spec review finding).
- **Concurrent resolution**: Last-write-wins by causal ordering (sort guarantees deterministic order).

**Implementation command**: `spec-kitty implement WP06 --base WP05`

## Subtasks & Detailed Guidance

### Subtask T025 – Implement semantic check processing

- **Purpose**: Track semantic check evaluations in the reducer state.
- **Steps**:
  1. Add mutable intermediate:
     ```python
     semantic_checks: List[SemanticCheckEvaluatedPayload] = []
     ```
  2. Handle `SEMANTIC_CHECK_EVALUATED`:
     ```python
     elif etype == SEMANTIC_CHECK_EVALUATED:
         p = SemanticCheckEvaluatedPayload(**payload_data)
         _check_scope_activated(p.scope_id, active_scopes, event, mode, anomalies)
         semantic_checks.append(p)
     ```
- **Files**: `src/spec_kitty_events/glossary.py` (Section 5).
- **Parallel?**: No.
- **Notes**: Simple append — the semantic check itself doesn't modify glossary state, it records an evaluation result.

### Subtask T026 – Implement clarification request processing with burst cap

- **Purpose**: Track clarification requests and enforce the 3-per-evaluation burst cap.
- **Steps**:
  1. Add mutable intermediate:
     ```python
     clarifications: List[ClarificationRecord] = []
     ```
  2. Handle `GLOSSARY_CLARIFICATION_REQUESTED`:
     ```python
     elif etype == GLOSSARY_CLARIFICATION_REQUESTED:
         p = GlossaryClarificationRequestedPayload(**payload_data)

         # Count active (unresolved) clarifications for this semantic check
         active_for_check = sum(
             1 for c in clarifications
             if c.semantic_check_event_id == p.semantic_check_event_id
             and not c.resolved
         )

         if active_for_check >= 3:
             if mode == "strict":
                 raise SpecKittyEventsError(
                     f"Clarification burst cap exceeded for semantic check "
                     f"'{p.semantic_check_event_id}' in event {event.event_id}"
                 )
             anomalies.append(GlossaryAnomaly(
                 event_id=event.event_id,
                 event_type=event.event_type,
                 reason=(
                     f"Burst cap exceeded: >3 active clarifications for "
                     f"semantic check '{p.semantic_check_event_id}'"
                 ),
             ))
         else:
             clarifications.append(ClarificationRecord(
                 request_event_id=event.event_id,
                 semantic_check_event_id=p.semantic_check_event_id,
                 term=p.term,
             ))
     ```
- **Files**: `src/spec_kitty_events/glossary.py` (Section 5).
- **Parallel?**: No.
- **Notes**: The burst cap check counts only *unresolved* clarifications for the same `semantic_check_event_id`. Resolved clarifications don't count toward the cap. In permissive mode, excess requests are recorded as anomalies but NOT added to the clarifications list (caps at 3). In strict mode, it raises immediately.

### Subtask T027 – Implement clarification resolution processing

- **Purpose**: Mark clarification records as resolved, handling concurrent resolutions.
- **Steps**:
  1. Handle `GLOSSARY_CLARIFICATION_RESOLVED`:
     ```python
     elif etype == GLOSSARY_CLARIFICATION_RESOLVED:
         p = GlossaryClarificationResolvedPayload(**payload_data)

         # Find matching clarification record
         found = False
         for i, record in enumerate(clarifications):
             if record.request_event_id == p.clarification_event_id:
                 # Replace with resolved version (last-write-wins for concurrent)
                 clarifications[i] = ClarificationRecord(
                     request_event_id=record.request_event_id,
                     semantic_check_event_id=record.semantic_check_event_id,
                     term=record.term,
                     resolved=True,
                     resolution_event_id=event.event_id,
                 )
                 found = True
                 break

         if not found:
             if mode == "strict":
                 raise SpecKittyEventsError(
                     f"GlossaryClarificationResolved references unknown "
                     f"clarification '{p.clarification_event_id}' "
                     f"in event {event.event_id}"
                 )
             anomalies.append(GlossaryAnomaly(
                 event_id=event.event_id,
                 event_type=event.event_type,
                 reason=(
                     f"Resolution for unknown clarification "
                     f"'{p.clarification_event_id}'"
                 ),
             ))
     ```
- **Files**: `src/spec_kitty_events/glossary.py` (Section 5).
- **Parallel?**: No.
- **Notes**: Since `ClarificationRecord` is frozen, we replace the list entry entirely. For concurrent resolutions (two events for the same clarification), the one processed last (by sort order) wins — the second replacement overwrites the first. Since the list is processed sequentially in sort order, this is deterministic.

### Subtask T028 – Implement generation block processing

- **Purpose**: Track generation block events.
- **Steps**:
  1. Add mutable intermediate:
     ```python
     generation_blocks: List[GenerationBlockedBySemanticConflictPayload] = []
     ```
  2. Handle `GENERATION_BLOCKED_BY_SEMANTIC_CONFLICT`:
     ```python
     elif etype == GENERATION_BLOCKED_BY_SEMANTIC_CONFLICT:
         p = GenerationBlockedBySemanticConflictPayload(**payload_data)
         generation_blocks.append(p)
     ```
- **Files**: `src/spec_kitty_events/glossary.py` (Section 5).
- **Parallel?**: No.
- **Notes**: Simple append. Block events are historical records — they don't modify other state (resolved conflicts don't retroactively remove block records).

### Subtask T029 – Implement final state assembly

- **Purpose**: Freeze all mutable intermediates into the `ReducedGlossaryState` return value.
- **Steps**:
  1. After the event processing loop, add:
     ```python
     # Track bookkeeping
     last_event = unique_events[-1]

     return ReducedGlossaryState(
         mission_id=mission_id,
         active_scopes=active_scopes,
         current_strictness=current_strictness,  # type: ignore[arg-type]
         strictness_history=tuple(strictness_history),
         term_candidates={
             k: tuple(v) for k, v in term_candidates.items()
         },
         term_senses=term_senses,
         clarifications=tuple(clarifications),
         semantic_checks=tuple(semantic_checks),
         generation_blocks=tuple(generation_blocks),
         anomalies=tuple(anomalies),
         event_count=len(unique_events),
         last_processed_event_id=last_event.event_id,
     )
     ```
  2. Remove the `raise NotImplementedError` from the skeleton (T019).
- **Files**: `src/spec_kitty_events/glossary.py` (Section 5).
- **Parallel?**: No — must be the last thing in the function.
- **Notes**: `current_strictness` is a `str` at runtime but typed as `Literal["off", "medium", "max"]` on the model — the `# type: ignore[arg-type]` is needed because the mutable intermediate is typed as `str`. Alternative: type the intermediate as `Literal["off", "medium", "max"]` and use a cast. Choose whichever passes mypy cleanly. `term_candidates` converts `Dict[str, List[...]]` to `Dict[str, Tuple[...]]`.

### Subtask T030 – Run `mypy --strict` on complete `glossary.py`

- **Purpose**: Verify type correctness of the entire module.
- **Steps**:
  1. Run: `mypy --strict src/spec_kitty_events/glossary.py`
  2. Fix any type errors.
  3. Common fixes needed:
     - `Sequence[Event]` type annotation on function parameter
     - `Literal` type narrowing for `current_strictness`
     - `Dict` key/value types matching model field types
- **Files**: `src/spec_kitty_events/glossary.py`.
- **Parallel?**: No — final checkpoint.
- **Notes**: If `from __future__ import annotations` causes runtime issues with Pydantic model construction in the reducer (payload `**payload_data`), use explicit type annotations without future annotations. This is unlikely with Pydantic v2 but worth checking.

## Risks & Mitigations

- **Risk**: Burst cap off-by-one error. **Mitigation**: The cap is `>= 3` (at 3 active, the next one is rejected). Test with exactly 3, 4, and 5 in WP08.
- **Risk**: Concurrent resolution overwrite order. **Mitigation**: Sort guarantees deterministic order; last-write-wins is achieved by sequential processing of sorted events.
- **Risk**: `type: ignore` comments accumulating. **Mitigation**: Minimize by using precise type annotations on intermediates.

## Review Guidance

- Verify burst cap logic: `active_for_check >= 3` means cap is 3 (not 4).
- Verify clarification resolution replaces the list entry (not append).
- Verify generation block processing is append-only (no state mutation).
- Verify final assembly converts all `List` → `tuple` and no mutable state leaks.
- Verify the `NotImplementedError` from T019 is removed.
- Verify `mypy --strict` passes with zero errors.

## Activity Log

- 2026-02-16T12:00:00Z – system – lane=planned – Prompt created.
- 2026-02-16T13:24:10Z – claude-opus – shell_pid=24697 – lane=doing – Assigned agent via workflow command
