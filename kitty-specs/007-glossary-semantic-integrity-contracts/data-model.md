# Data Model: Glossary Semantic Integrity Contracts

**Feature**: 007-glossary-semantic-integrity-contracts
**Date**: 2026-02-16

## Value Objects (embedded in payloads)

### SemanticConflictEntry

Typed conflict entry used within `SemanticCheckEvaluatedPayload.conflicts`.

| Field | Type | Required | Description |
|---|---|---|---|
| `term` | `str` | yes | The conflicting term surface text |
| `nature` | `Literal["overloaded", "drift", "ambiguous"]` | yes | Classification of the conflict |
| `severity` | `Literal["low", "medium", "high"]` | yes | Severity level |
| `description` | `str` | yes | Human-readable explanation of the conflict |

**Validation**: All fields required, no defaults.

## Event Type Constants

| Constant | Value | Payload Model |
|---|---|---|
| `GLOSSARY_SCOPE_ACTIVATED` | `"GlossaryScopeActivated"` | `GlossaryScopeActivatedPayload` |
| `TERM_CANDIDATE_OBSERVED` | `"TermCandidateObserved"` | `TermCandidateObservedPayload` |
| `SEMANTIC_CHECK_EVALUATED` | `"SemanticCheckEvaluated"` | `SemanticCheckEvaluatedPayload` |
| `GLOSSARY_CLARIFICATION_REQUESTED` | `"GlossaryClarificationRequested"` | `GlossaryClarificationRequestedPayload` |
| `GLOSSARY_CLARIFICATION_RESOLVED` | `"GlossaryClarificationResolved"` | `GlossaryClarificationResolvedPayload` |
| `GLOSSARY_SENSE_UPDATED` | `"GlossarySenseUpdated"` | `GlossarySenseUpdatedPayload` |
| `GENERATION_BLOCKED_BY_SEMANTIC_CONFLICT` | `"GenerationBlockedBySemanticConflict"` | `GenerationBlockedBySemanticConflictPayload` |
| `GLOSSARY_STRICTNESS_SET` | `"GlossaryStrictnessSet"` | `GlossaryStrictnessSetPayload` |

Plus: `GLOSSARY_EVENT_TYPES: FrozenSet[str]` containing all 8 values.

## Payload Models (all frozen Pydantic BaseModel)

### GlossaryScopeActivatedPayload

| Field | Type | Required | Description |
|---|---|---|---|
| `mission_id` | `str` | yes | Mission context |
| `scope_id` | `str` | yes | Unique scope identifier |
| `scope_type` | `Literal["spec_kitty_core", "team_domain", "audience_domain", "mission_local"]` | yes | Scope category |
| `glossary_version_id` | `str` | yes | Version of the glossary being activated |

### TermCandidateObservedPayload

| Field | Type | Required | Description |
|---|---|---|---|
| `mission_id` | `str` | yes | Mission context |
| `scope_id` | `str` | yes | Scope the term was observed in |
| `step_id` | `str` | yes | Mission step that produced the term |
| `term_surface` | `str` | yes | Raw text form of the observed term |
| `confidence` | `float` | yes | Confidence score (0.0–1.0) |
| `actor` | `str` | yes | Identity of the actor who triggered observation |
| `step_metadata` | `Dict[str, str]` | no | Mission primitive metadata (default empty dict) |

**Validation**: `confidence` must be ≥0.0 and ≤1.0. `term_surface` min_length=1.

### SemanticCheckEvaluatedPayload

| Field | Type | Required | Description |
|---|---|---|---|
| `mission_id` | `str` | yes | Mission context |
| `scope_id` | `str` | yes | Scope checked against |
| `step_id` | `str` | yes | Step being evaluated |
| `conflicts` | `Tuple[SemanticConflictEntry, ...]` | yes | List of detected conflicts |
| `severity` | `Literal["low", "medium", "high"]` | yes | Overall check severity (max of conflicts) |
| `confidence` | `float` | yes | Overall confidence score (0.0–1.0) |
| `recommended_action` | `Literal["block", "warn", "pass"]` | yes | Action recommendation |
| `effective_strictness` | `Literal["off", "medium", "max"]` | yes | Strictness mode used for this evaluation |
| `step_metadata` | `Dict[str, str]` | no | Mission primitive metadata (default empty dict) |

**Validation**: `confidence` must be ≥0.0 and ≤1.0.

### GlossaryClarificationRequestedPayload

| Field | Type | Required | Description |
|---|---|---|---|
| `mission_id` | `str` | yes | Mission context |
| `scope_id` | `str` | yes | Scope context |
| `step_id` | `str` | yes | Step that triggered clarification |
| `semantic_check_event_id` | `str` | yes | Event ID of the triggering SemanticCheckEvaluated (burst-window key) |
| `term` | `str` | yes | The ambiguous term |
| `question` | `str` | yes | Clarification question text |
| `options` | `Tuple[str, ...]` | yes | Available answer options |
| `urgency` | `Literal["low", "medium", "high"]` | yes | Urgency level |
| `actor` | `str` | yes | Actor who triggered the request |

### GlossaryClarificationResolvedPayload

| Field | Type | Required | Description |
|---|---|---|---|
| `mission_id` | `str` | yes | Mission context |
| `clarification_event_id` | `str` | yes | Event ID of the originating clarification request |
| `selected_meaning` | `str` | yes | The chosen or entered meaning |
| `actor` | `str` | yes | Identity of the resolving actor |

### GlossarySenseUpdatedPayload

| Field | Type | Required | Description |
|---|---|---|---|
| `mission_id` | `str` | yes | Mission context |
| `scope_id` | `str` | yes | Scope of the term |
| `term_surface` | `str` | yes | Term being updated |
| `before_sense` | `Optional[str]` | no | Previous sense value (None if first definition) |
| `after_sense` | `str` | yes | New sense value |
| `reason` | `str` | yes | Why the sense was changed |
| `actor` | `str` | yes | Actor who made the change |

### GenerationBlockedBySemanticConflictPayload

| Field | Type | Required | Description |
|---|---|---|---|
| `mission_id` | `str` | yes | Mission context |
| `step_id` | `str` | yes | Step that was blocked |
| `conflict_event_ids` | `Tuple[str, ...]` | yes | Event IDs of the unresolved SemanticCheckEvaluated events |
| `blocking_strictness` | `Literal["medium", "max"]` | yes | Policy mode that triggered the block |
| `step_metadata` | `Dict[str, str]` | no | Mission primitive metadata (default empty dict) |

**Validation**: `blocking_strictness` cannot be `"off"` (no blocks in off mode). `conflict_event_ids` must be non-empty (min_length=1 on tuple).

### GlossaryStrictnessSetPayload

| Field | Type | Required | Description |
|---|---|---|---|
| `mission_id` | `str` | yes | Mission context |
| `new_strictness` | `Literal["off", "medium", "max"]` | yes | The new strictness mode |
| `previous_strictness` | `Optional[Literal["off", "medium", "max"]]` | no | Previous mode (None if initial setting) |
| `actor` | `str` | yes | Actor who changed the setting |

## Reducer Output Models

### GlossaryAnomaly

Non-fatal issue recorded by the reducer in permissive mode.

| Field | Type | Required | Description |
|---|---|---|---|
| `event_id` | `str` | yes | ID of the event that caused the anomaly |
| `event_type` | `str` | yes | Type of the problematic event |
| `reason` | `str` | yes | Human-readable explanation |

### ReducedGlossaryState

Frozen projected state produced by `reduce_glossary_events()`.

| Field | Type | Default | Description |
|---|---|---|---|
| `mission_id` | `str` | `""` | Mission context (extracted from first event) |
| `active_scopes` | `Dict[str, GlossaryScopeActivatedPayload]` | `{}` | scope_id → activation payload |
| `current_strictness` | `Literal["off", "medium", "max"]` | `"medium"` | Latest mission-wide strictness mode |
| `strictness_history` | `Tuple[GlossaryStrictnessSetPayload, ...]` | `()` | Ordered history of strictness changes |
| `term_candidates` | `Dict[str, Tuple[TermCandidateObservedPayload, ...]]` | `{}` | term_surface → observed candidates |
| `term_senses` | `Dict[str, GlossarySenseUpdatedPayload]` | `{}` | term_surface → latest sense update |
| `clarifications` | `Tuple[ClarificationRecord, ...]` | `()` | Ordered clarification timeline |
| `semantic_checks` | `Tuple[SemanticCheckEvaluatedPayload, ...]` | `()` | Ordered check history |
| `generation_blocks` | `Tuple[GenerationBlockedBySemanticConflictPayload, ...]` | `()` | Ordered block history |
| `anomalies` | `Tuple[GlossaryAnomaly, ...]` | `()` | Non-fatal issues |
| `event_count` | `int` | `0` | Total glossary events processed |
| `last_processed_event_id` | `Optional[str]` | `None` | Last event_id in sequence |

### ClarificationRecord (reducer internal)

Tracks clarification state for burst-cap enforcement.

| Field | Type | Required | Description |
|---|---|---|---|
| `request_event_id` | `str` | yes | Event ID of the clarification request |
| `semantic_check_event_id` | `str` | yes | Burst-window grouping key |
| `term` | `str` | yes | The ambiguous term |
| `resolved` | `bool` | yes | Whether a resolution has been received |
| `resolution_event_id` | `Optional[str]` | no | Event ID of the resolution (if resolved) |

## State Transitions

### Strictness Mode (mission-wide)

```
[initial: medium] → off | medium | max
                      ↕       ↕       ↕
                  (any mode can transition to any other mode)
```

Set by `GlossaryStrictnessSet` event. Default is `medium` if no strictness event received.

### Clarification Lifecycle

```
[requested] → [resolved]
    ↓
(burst cap: max 3 active per semantic_check_event_id)
```

### Term Sense Lifecycle

```
[unobserved] → [observed via TermCandidateObserved]
                    ↓
              [sense defined via GlossarySenseUpdated]
                    ↓
              [sense updated via GlossarySenseUpdated] (repeatable)
```

**Invariant**: GlossarySenseUpdated requires a prior TermCandidateObserved for the same term in the same scope (strict mode enforced).
