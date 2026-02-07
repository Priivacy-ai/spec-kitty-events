# Quickstart: GitHub Gate Observability Contracts
*Phase 1 output for feature 002*

## Overview

This feature adds typed event contracts for GitHub CI gate outcomes to the `spec-kitty-events` library. It enables downstream consumers (CLI, SaaS) to emit structured, validated events when a GitHub check run completes.

## Installation

```bash
pip install spec-kitty-events>=0.2.0a0
```

No new dependencies required — uses existing Pydantic v2.

## Quick Usage

### 1. Map a GitHub conclusion to an event type

```python
from spec_kitty_events import map_check_run_conclusion

event_type = map_check_run_conclusion("success")    # → "GatePassed"
event_type = map_check_run_conclusion("failure")    # → "GateFailed"
event_type = map_check_run_conclusion("neutral")    # → None (ignored, logged)
```

### 2. Construct a validated payload

```python
from spec_kitty_events import GatePassedPayload, GateFailedPayload

payload = GatePassedPayload(
    gate_name="ci/build",
    gate_type="ci",
    conclusion="success",
    external_provider="github",
    check_run_id=123456,
    check_run_url="https://github.com/org/repo/runs/123456",
    delivery_id="webhook-delivery-uuid",
    pr_number=42,  # optional
)
```

### 3. Attach to a generic Event

```python
from spec_kitty_events import Event

event = Event(
    event_id=generate_ulid(),
    event_type="GatePassed",
    aggregate_id="my-project",
    payload=payload.model_dump(),
    timestamp=datetime.now(),
    node_id="worker-1",
    lamport_clock=clock.tick(),
    project_uuid=project_uuid,
)
```

### 4. Handle ignored conclusions with a callback

```python
def count_ignored(conclusion: str, reason: str) -> None:
    metrics.increment(f"gate.ignored.{conclusion}")

event_type = map_check_run_conclusion("skipped", on_ignored=count_ignored)
# Logs via stdlib + calls your callback
```

## Key Points

- **Immutable**: Payload models are frozen — cannot be modified after construction
- **Validated**: Missing required fields raise `ValidationError` at construction time
- **Deterministic**: Every known conclusion maps to exactly one outcome
- **Explicit failures**: Unknown conclusions raise `UnknownConclusionError` — no silent drops
- **Correlation**: `check_run_id`, `check_run_url`, `delivery_id`, and `pr_number` enable tracing back to GitHub
