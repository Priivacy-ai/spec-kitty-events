# Quickstart: Glossary Semantic Integrity Contracts

**Feature**: 007-glossary-semantic-integrity-contracts
**Date**: 2026-02-16

## Prerequisites

- Python 3.10+
- `spec-kitty-events` installed from `2.x` branch

```bash
# From spec-kitty-events repo root (on 2.x branch):
pip install -e ".[dev]"
```

## Importing Glossary Contracts

```python
from spec_kitty_events import (
    # Event type constants
    GLOSSARY_SCOPE_ACTIVATED,
    TERM_CANDIDATE_OBSERVED,
    SEMANTIC_CHECK_EVALUATED,
    GLOSSARY_CLARIFICATION_REQUESTED,
    GLOSSARY_CLARIFICATION_RESOLVED,
    GLOSSARY_SENSE_UPDATED,
    GENERATION_BLOCKED_BY_SEMANTIC_CONFLICT,
    GLOSSARY_STRICTNESS_SET,
    GLOSSARY_EVENT_TYPES,
    # Payload models
    GlossaryScopeActivatedPayload,
    TermCandidateObservedPayload,
    SemanticCheckEvaluatedPayload,
    SemanticConflictEntry,
    GlossaryClarificationRequestedPayload,
    GlossaryClarificationResolvedPayload,
    GlossarySenseUpdatedPayload,
    GenerationBlockedBySemanticConflictPayload,
    GlossaryStrictnessSetPayload,
    # Reducer
    reduce_glossary_events,
    ReducedGlossaryState,
    GlossaryAnomaly,
)
```

## Creating Glossary Events

```python
from spec_kitty_events import Event

# 1. Activate a glossary scope
scope_event = Event(
    event_id="01HXYZ...",
    event_type=GLOSSARY_SCOPE_ACTIVATED,
    aggregate_id="mission-001",
    payload=GlossaryScopeActivatedPayload(
        mission_id="mission-001",
        scope_id="scope-team-domain",
        scope_type="team_domain",
        glossary_version_id="v1",
    ).model_dump(),
    timestamp="2026-02-16T10:00:00Z",
    node_id="cli-agent",
    lamport_clock=1,
    correlation_id="01HXYZ...",
    schema_version="2.0.0",
)

# 2. Observe a term candidate
term_event = Event(
    event_id="01HXYZ...",
    event_type=TERM_CANDIDATE_OBSERVED,
    aggregate_id="mission-001",
    payload=TermCandidateObservedPayload(
        mission_id="mission-001",
        scope_id="scope-team-domain",
        step_id="step-specify",
        term_surface="dashboard",
        confidence=0.7,
        actor="human-alice",
        step_metadata={"primitive": "specify"},
    ).model_dump(),
    timestamp="2026-02-16T10:01:00Z",
    node_id="cli-agent",
    lamport_clock=2,
    correlation_id="01HXYZ...",
    schema_version="2.0.0",
)
```

## Reducing Glossary Events

```python
# Collect all events from your event store
events = event_store.load_events("mission-001")

# Reduce to glossary state (strict mode — raises on violations)
state = reduce_glossary_events(events, mode="strict")

# Inspect the state
print(f"Active scopes: {list(state.active_scopes.keys())}")
print(f"Current strictness: {state.current_strictness}")
print(f"Generation blocks: {len(state.generation_blocks)}")

# Permissive mode — records anomalies instead of raising
state = reduce_glossary_events(events, mode="permissive")
for anomaly in state.anomalies:
    print(f"Anomaly: {anomaly.reason} (event {anomaly.event_id})")
```

## Checking for Generation Blocks

```python
state = reduce_glossary_events(events, mode="strict")

if state.generation_blocks:
    for block in state.generation_blocks:
        print(f"Step {block.step_id} blocked by {len(block.conflict_event_ids)} conflicts")
        print(f"Blocking policy: {block.blocking_strictness}")
```

## Running Tests

```bash
# Run all tests
python3.11 -m pytest

# Run glossary-specific tests
python3.11 -m pytest tests/test_glossary.py tests/test_glossary_reducer.py

# Run with mypy strict checking
mypy --strict src/spec_kitty_events/glossary.py
```

## Key Design Points

1. **Strictness is mission-wide** — `GlossaryStrictnessSet` applies to the entire mission, not per scope.
2. **Burst cap is per semantic check** — Clarification requests grouped by `semantic_check_event_id`, max 3 active per group.
3. **Actor is a simple string** — Not the full `ParticipantIdentity` model from collaboration domain.
4. **Step references use metadata** — `step_metadata: Dict[str, str]` carries mission primitive metadata. No hardcoded step names.
5. **Reducer is a pure function** — No I/O, deterministic for any causal-order-preserving permutation.
