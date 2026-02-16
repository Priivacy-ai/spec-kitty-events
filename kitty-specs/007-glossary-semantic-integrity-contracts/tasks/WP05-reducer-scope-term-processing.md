---
work_package_id: WP05
title: Reducer — Scope, Strictness & Term Processing
lane: "doing"
dependencies: [WP04]
base_branch: 007-glossary-semantic-integrity-contracts-WP04
base_commit: 1cc294fbe6cea88e0fcd6f32bc53645a7db5cb4d
created_at: '2026-02-16T13:21:34.558635+00:00'
subtasks:
- T019
- T020
- T021
- T022
- T023
- T024
phase: Phase 2 - Reducer Implementation
assignee: ''
agent: "claude-opus"
shell_pid: "22994"
review_status: ''
reviewed_by: ''
history:
- timestamp: '2026-02-16T12:00:00Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP05 – Reducer — Scope, Strictness & Term Processing

## ⚠️ IMPORTANT: Review Feedback Status

- **Has review feedback?**: Check the `review_status` field above.
- **You must address all feedback** before your work is complete.

---

## Review Feedback

*[This section is empty initially.]*

---

## Objectives & Success Criteria

- Replace the placeholder `reduce_glossary_events()` with the real implementation (first half).
- Implement the 5-stage pipeline skeleton (filter → sort → dedup → process → assemble).
- Process `GlossaryScopeActivated`, `GlossaryStrictnessSet`, `TermCandidateObserved`, and `GlossarySenseUpdated` events.
- Dual-mode error handling (strict raises, permissive records anomalies).

**Success**: Reducing a sequence of scope/strictness/term events produces a `ReducedGlossaryState` with correct `active_scopes`, `current_strictness`, `strictness_history`, `term_candidates`, and `term_senses`.

## Context & Constraints

- **Reference**: `src/spec_kitty_events/collaboration.py:539-600` — reducer pipeline to mirror.
- **Reference**: `kitty-specs/007-glossary-semantic-integrity-contracts/research.md` — R1 (reducer pipeline pattern).
- **Late imports**: `dedup_events` and `status_event_sort_key` from `status.py` — import inside function body (matching collaboration.py line 575).
- **Strict/permissive**: Match `reduce_collaboration_events()` dual-mode pattern exactly.

**Implementation command**: `spec-kitty implement WP05 --base WP04`

## Subtasks & Detailed Guidance

### Subtask T019 – Implement reducer skeleton

- **Purpose**: Establish the 5-stage pipeline that all event processing flows through.
- **Steps**:
  1. Replace the placeholder `reduce_glossary_events()` in Section 5 of `glossary.py` with:
     ```python
     def reduce_glossary_events(
         events: Sequence[Event],
         *,
         mode: Literal["strict", "permissive"] = "strict",
     ) -> ReducedGlossaryState:
         """Fold glossary events into projected glossary state.

         Pipeline:
         1. Filter to glossary event types only
         2. Sort by (lamport_clock, timestamp, event_id)
         3. Deduplicate by event_id
         4. Process each event, mutating intermediate state
         5. Assemble frozen ReducedGlossaryState

         Pure function. No I/O. Deterministic for any causal-order-preserving
         permutation.
         """
         from spec_kitty_events.status import dedup_events, status_event_sort_key

         if not events:
             return ReducedGlossaryState()

         # 1. Filter
         glossary_events = [e for e in events if e.event_type in GLOSSARY_EVENT_TYPES]

         if not glossary_events:
             return ReducedGlossaryState()

         # 2. Sort
         sorted_events = sorted(glossary_events, key=status_event_sort_key)

         # 3. Dedup
         unique_events = dedup_events(sorted_events)

         # 4. Process (mutable intermediates)
         # ... (filled in by T020-T024 and WP06)

         # 5. Assemble (filled in by WP06 T029)
         raise NotImplementedError("Assembly not yet implemented")
     ```
  2. Remove the `TYPE_CHECKING` guard for `Event` import — now import it at runtime inside the function body or at module level (since the reducer needs `Event` at runtime, use a runtime import at the top of the function body or import from `spec_kitty_events.models` at module level).
  3. Decide on import approach: since `collaboration.py` imports `SpecKittyEventsError` at module level from `models.py`, it's safe to also import `Event` at module level. Add to the existing imports:
     ```python
     from spec_kitty_events.models import Event, SpecKittyEventsError
     ```
- **Files**: `src/spec_kitty_events/glossary.py` (Section 5).
- **Parallel?**: No — all other subtasks build on this skeleton.
- **Notes**: The late import of `dedup_events` and `status_event_sort_key` is critical — these are in `status.py` which imports from `models.py`. Importing at module level would create a circular dependency.

### Subtask T020 – Implement scope activation processing

- **Purpose**: Track activated glossary scopes in the mutable state.
- **Steps**:
  1. Add mutable intermediate state declarations after dedup:
     ```python
     active_scopes: Dict[str, GlossaryScopeActivatedPayload] = {}
     anomalies: List[GlossaryAnomaly] = []
     mission_id = ""
     ```
  2. In the event processing loop, handle `GLOSSARY_SCOPE_ACTIVATED`:
     ```python
     for event in unique_events:
         payload_data = event.payload
         etype = event.event_type

         if etype == GLOSSARY_SCOPE_ACTIVATED:
             p = GlossaryScopeActivatedPayload(**payload_data)
             active_scopes[p.scope_id] = p
     ```
- **Files**: `src/spec_kitty_events/glossary.py` (Section 5).
- **Parallel?**: No — sequential within the reducer.
- **Notes**: No integrity check needed for scope activation — scopes can be activated at any time.

### Subtask T021 – Implement strictness set processing

- **Purpose**: Track mission-wide strictness mode and history.
- **Steps**:
  1. Add mutable intermediates:
     ```python
     current_strictness: str = "medium"
     strictness_history: List[GlossaryStrictnessSetPayload] = []
     ```
  2. Handle `GLOSSARY_STRICTNESS_SET`:
     ```python
     elif etype == GLOSSARY_STRICTNESS_SET:
         p = GlossaryStrictnessSetPayload(**payload_data)
         current_strictness = p.new_strictness
         strictness_history.append(p)
     ```
- **Files**: `src/spec_kitty_events/glossary.py` (Section 5).
- **Parallel?**: No.
- **Notes**: Default is `"medium"` if no strictness event received. History preserves the full payload for audit.

### Subtask T022 – Implement term candidate observation processing

- **Purpose**: Track observed term candidates grouped by term_surface.
- **Steps**:
  1. Add mutable intermediate:
     ```python
     term_candidates: Dict[str, List[TermCandidateObservedPayload]] = {}
     ```
  2. Handle `TERM_CANDIDATE_OBSERVED`:
     ```python
     elif etype == TERM_CANDIDATE_OBSERVED:
         p = TermCandidateObservedPayload(**payload_data)
         _check_scope_activated(p.scope_id, active_scopes, event, mode, anomalies)
         term_candidates.setdefault(p.term_surface, []).append(p)
     ```
  3. Extract the scope check into a helper:
     ```python
     def _check_scope_activated(
         scope_id: str,
         active_scopes: Dict[str, GlossaryScopeActivatedPayload],
         event: Event,
         mode: str,
         anomalies: List[GlossaryAnomaly],
     ) -> None:
         if scope_id not in active_scopes:
             if mode == "strict":
                 raise SpecKittyEventsError(
                     f"Event {event.event_id} references unactivated scope '{scope_id}'"
                 )
             anomalies.append(GlossaryAnomaly(
                 event_id=event.event_id,
                 event_type=event.event_type,
                 reason=f"References unactivated scope '{scope_id}'",
             ))
     ```
- **Files**: `src/spec_kitty_events/glossary.py` (Section 5 + helper above reducer).
- **Parallel?**: No.
- **Notes**: The helper `_check_scope_activated` will be reused by sense update processing (T023) and clarification processing (WP06).

### Subtask T023 – Implement sense update processing

- **Purpose**: Track current term senses with integrity check for unobserved terms.
- **Steps**:
  1. Add mutable intermediate:
     ```python
     term_senses: Dict[str, GlossarySenseUpdatedPayload] = {}
     ```
  2. Handle `GLOSSARY_SENSE_UPDATED`:
     ```python
     elif etype == GLOSSARY_SENSE_UPDATED:
         p = GlossarySenseUpdatedPayload(**payload_data)
         _check_scope_activated(p.scope_id, active_scopes, event, mode, anomalies)
         # Integrity check: term must have been observed
         if p.term_surface not in term_candidates:
             if mode == "strict":
                 raise SpecKittyEventsError(
                     f"GlossarySenseUpdated for unobserved term '{p.term_surface}' "
                     f"in event {event.event_id}"
                 )
             anomalies.append(GlossaryAnomaly(
                 event_id=event.event_id,
                 event_type=event.event_type,
                 reason=f"Sense update for unobserved term '{p.term_surface}'",
             ))
         term_senses[p.term_surface] = p  # Last write wins
     ```
- **Files**: `src/spec_kitty_events/glossary.py` (Section 5).
- **Parallel?**: No.
- **Notes**: The integrity check for unobserved term is a key edge case from the spec. In permissive mode, the anomaly is recorded but the sense update still proceeds (the term is still tracked even if it wasn't formally observed).

### Subtask T024 – Extract mission_id from first event

- **Purpose**: Set `mission_id` on the reduced state from the first processed event.
- **Steps**:
  1. At the start of the event loop (before the first iteration), extract mission_id:
     ```python
     # Extract mission_id from first event's payload
     first_payload = unique_events[0].payload
     mission_id = str(first_payload.get("mission_id", ""))
     ```
  2. This runs once, before the main processing loop.
- **Files**: `src/spec_kitty_events/glossary.py` (Section 5).
- **Parallel?**: No.
- **Notes**: All glossary payloads have `mission_id`. Extracting from the first event matches the collaboration reducer pattern.

## Risks & Mitigations

- **Risk**: `payload_data` might not match the expected Pydantic model fields exactly. **Mitigation**: Pydantic v2 `**payload_data` construction will raise `ValidationError` on mismatches — this is correct behavior (events with bad payloads should fail loudly).
- **Risk**: Circular import from `Event` import. **Mitigation**: Import `Event` from `spec_kitty_events.models` at module level (same as `SpecKittyEventsError`). The late imports are only for `status.py` utilities.

## Review Guidance

- Verify late imports of `dedup_events` and `status_event_sort_key` are inside the function body.
- Verify `_check_scope_activated` helper is defined above the reducer function.
- Verify `mode` parameter defaults to `"strict"`.
- Verify empty-input short-circuit returns `ReducedGlossaryState()` (with defaults).
- Verify term_candidates uses `setdefault` + `append` (not overwrite).
- Verify term_senses uses last-write-wins (`term_senses[p.term_surface] = p`).

## Activity Log

- 2026-02-16T12:00:00Z – system – lane=planned – Prompt created.
- 2026-02-16T13:21:34Z – claude-opus – shell_pid=22994 – lane=doing – Assigned agent via workflow command
