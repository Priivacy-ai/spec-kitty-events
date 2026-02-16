# Contract: Glossary Semantic Integrity Events

**Feature**: 007-glossary-semantic-integrity-contracts
**Schema Version**: 2.0.0
**Date**: 2026-02-16

## Event Type Registry

All glossary events use the existing `Event` envelope model from `spec_kitty_events.models`. The `event_type` field identifies the glossary event type, and the `payload` dict contains the typed payload fields.

### Event Types (8 total)

| Event Type | Domain | Direction | Description |
|---|---|---|---|
| `GlossaryScopeActivated` | Scope lifecycle | Emitted once per scope activation | A glossary scope is activated for a mission |
| `TermCandidateObserved` | Term extraction | Emitted per observed term | A new or uncertain term appears in mission input |
| `SemanticCheckEvaluated` | Semantic gate | Emitted per step evaluation | Pre-generation semantic check completed |
| `GlossaryClarificationRequested` | Clarification | Emitted per clarification needed | Policy requires human/actor clarification |
| `GlossaryClarificationResolved` | Clarification | Emitted per resolution | Clarification question answered |
| `GlossarySenseUpdated` | Term evolution | Emitted per sense change | Term meaning created or updated |
| `GenerationBlockedBySemanticConflict` | Enforcement | Emitted per block decision | High-severity conflict blocked LLM generation |
| `GlossaryStrictnessSet` | Configuration | Emitted per policy change | Mission-wide strictness mode changed |

## Payload Contracts

### GlossaryScopeActivatedPayload

```
mission_id: str (required)
scope_id: str (required)
scope_type: "spec_kitty_core" | "team_domain" | "audience_domain" | "mission_local" (required)
glossary_version_id: str (required)
```

### TermCandidateObservedPayload

```
mission_id: str (required)
scope_id: str (required)
step_id: str (required)
term_surface: str (required, min_length=1)
confidence: float (required, 0.0–1.0)
actor: str (required)
step_metadata: Dict[str, str] (optional, default={})
```

### SemanticCheckEvaluatedPayload

```
mission_id: str (required)
scope_id: str (required)
step_id: str (required)
conflicts: Tuple[SemanticConflictEntry, ...] (required)
severity: "low" | "medium" | "high" (required)
confidence: float (required, 0.0–1.0)
recommended_action: "block" | "warn" | "pass" (required)
effective_strictness: "off" | "medium" | "max" (required)
step_metadata: Dict[str, str] (optional, default={})
```

**SemanticConflictEntry** (embedded value object):
```
term: str (required)
nature: "overloaded" | "drift" | "ambiguous" (required)
severity: "low" | "medium" | "high" (required)
description: str (required)
```

### GlossaryClarificationRequestedPayload

```
mission_id: str (required)
scope_id: str (required)
step_id: str (required)
semantic_check_event_id: str (required)  # burst-window grouping key
term: str (required)
question: str (required)
options: Tuple[str, ...] (required)
urgency: "low" | "medium" | "high" (required)
actor: str (required)
```

### GlossaryClarificationResolvedPayload

```
mission_id: str (required)
clarification_event_id: str (required)  # references originating request
selected_meaning: str (required)
actor: str (required)
```

### GlossarySenseUpdatedPayload

```
mission_id: str (required)
scope_id: str (required)
term_surface: str (required, min_length=1)
before_sense: Optional[str] (optional, None if first definition)
after_sense: str (required)
reason: str (required)
actor: str (required)
```

### GenerationBlockedBySemanticConflictPayload

```
mission_id: str (required)
step_id: str (required)
conflict_event_ids: Tuple[str, ...] (required, min_length=1)
blocking_strictness: "medium" | "max" (required)  # never "off"
step_metadata: Dict[str, str] (optional, default={})
```

### GlossaryStrictnessSetPayload

```
mission_id: str (required)
new_strictness: "off" | "medium" | "max" (required)
previous_strictness: Optional["off" | "medium" | "max"] (optional, None if initial)
actor: str (required)
```

## Reducer Contract

### Function Signature

```
reduce_glossary_events(
    events: Sequence[Event],
    *,
    mode: Literal["strict", "permissive"] = "strict",
) -> ReducedGlossaryState
```

### Pipeline (5-stage)

1. **Filter**: Keep only events with `event_type` in `GLOSSARY_EVENT_TYPES`
2. **Sort**: By `(lamport_clock, timestamp, event_id)` — deterministic total order
3. **Dedup**: Discard duplicate `event_id` entries
4. **Process**: Iterate events, updating mutable intermediate state
5. **Assemble**: Freeze all mutable state into `ReducedGlossaryState`

### Mode Behavior

| Condition | Strict Mode | Permissive Mode |
|---|---|---|
| Event for unactivated scope | Raises error | Records anomaly, continues |
| SenseUpdated for unobserved term | Raises error | Records anomaly, continues |
| Burst cap exceeded (>3 per check) | Raises error | Records anomaly, caps at 3 |
| Empty input | Returns empty state | Returns empty state |

### Determinism Guarantee

The reducer MUST produce identical output for any causal-order-preserving permutation of the same event set. This is enforced by the sort step (total order on lamport_clock + timestamp + event_id).

## Conformance Fixtures (3 required)

### Fixture 1: High-Severity Block

**Path**: `conformance/fixtures/glossary/valid/`
**Scenario**: Unresolved high-severity conflict blocks generation.
**Event sequence**:
1. `GlossaryScopeActivated` — activate a scope
2. `GlossaryStrictnessSet` — set mode to `medium`
3. `TermCandidateObserved` — observe ambiguous term
4. `SemanticCheckEvaluated` — severity=high, recommended_action=block
5. `GenerationBlockedBySemanticConflict` — step blocked

**Expected reduced state**: `generation_blocks` tuple is non-empty, contains reference to the blocking check.

### Fixture 2: Medium-Severity Warn

**Path**: `conformance/fixtures/glossary/valid/`
**Scenario**: Medium-severity conflict warns without blocking.
**Event sequence**:
1. `GlossaryScopeActivated` — activate scope
2. `TermCandidateObserved` — observe term
3. `SemanticCheckEvaluated` — severity=medium, recommended_action=warn

**Expected reduced state**: `semantic_checks` tuple contains the warning event, `generation_blocks` is empty.

### Fixture 3: Clarification Burst Cap

**Path**: `conformance/fixtures/glossary/valid/`
**Scenario**: Burst cap limits active clarifications to 3 per semantic check.
**Event sequence**:
1. `GlossaryScopeActivated` — activate scope
2. `SemanticCheckEvaluated` — check with 5 conflicts
3. 5x `GlossaryClarificationRequested` — all referencing same `semantic_check_event_id`

**Expected reduced state**: At most 3 unresolved clarification records for that `semantic_check_event_id`.

## Hard Invariants (from spec)

1. High-severity unresolved conflicts MUST produce `GenerationBlockedBySemanticConflict` — no alternative path.
2. All glossary state MUST be reconstructable from `reduce_glossary_events()` — no side-channel store.
3. Step references use `step_metadata` dict — no hardcoded step-name strings.
