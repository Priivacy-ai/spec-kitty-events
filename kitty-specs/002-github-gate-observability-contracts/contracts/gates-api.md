# API Contract: gates module
*Phase 1 output for feature 002*

## Module: `spec_kitty_events.gates`

### Models

#### `GatePayloadBase`

```python
class GatePayloadBase(BaseModel):
    """Base payload for CI gate outcome events. Not instantiated directly."""

    model_config = ConfigDict(frozen=True)

    gate_name: str                    # e.g., "ci/build", "ci/lint"
    gate_type: Literal["ci"]          # constrained
    conclusion: str                   # raw conclusion from provider
    external_provider: Literal["github"]  # constrained
    check_run_id: int                 # GitHub check run ID (> 0)
    check_run_url: AnyHttpUrl         # GitHub check run URL
    delivery_id: str                  # webhook delivery ID (idempotency key)
    pr_number: Optional[int]          # PR number if applicable (> 0 or None)
```

#### `GatePassedPayload(GatePayloadBase)`

```python
class GatePassedPayload(GatePayloadBase):
    """Payload for a CI gate that concluded successfully."""
    pass
```

#### `GateFailedPayload(GatePayloadBase)`

```python
class GateFailedPayload(GatePayloadBase):
    """Payload for a CI gate that concluded with a failure condition."""
    pass
```

### Exceptions

#### `UnknownConclusionError(SpecKittyEventsError)`

```python
class UnknownConclusionError(SpecKittyEventsError):
    """Raised when a check_run conclusion is not in the known set."""

    def __init__(self, conclusion: str) -> None: ...

    conclusion: str  # the unrecognized value
```

### Functions

#### `map_check_run_conclusion`

```python
def map_check_run_conclusion(
    conclusion: str,
    on_ignored: Optional[Callable[[str, str], None]] = None,
) -> Optional[str]:
    """Map a GitHub check_run conclusion to an event type string.

    Args:
        conclusion: The raw conclusion string from GitHub's check_run API.
            Must be lowercase.
        on_ignored: Optional callback invoked when a conclusion is ignored.
            Receives (conclusion, reason) where reason is "non_blocking".

    Returns:
        "GatePassed" for success conclusions.
        "GateFailed" for failure conclusions.
        None for ignored conclusions (neutral, skipped, stale).

    Raises:
        UnknownConclusionError: If conclusion is not in the known set.
    """
```

### Public API Exports (from `__init__.py`)

New additions to `__all__`:
- `GatePayloadBase`
- `GatePassedPayload`
- `GateFailedPayload`
- `UnknownConclusionError`
- `map_check_run_conclusion`

### Usage Examples

#### Constructing a gate event

```python
from spec_kitty_events import Event, GatePassedPayload

payload = GatePassedPayload(
    gate_name="ci/build",
    gate_type="ci",
    conclusion="success",
    external_provider="github",
    check_run_id=123456,
    check_run_url="https://github.com/org/repo/runs/123456",
    delivery_id="abc-def-ghi",
    pr_number=42,
)

event = Event(
    event_id="01HXYZ...",  # ULID
    event_type="GatePassed",
    aggregate_id="project-123",
    payload=payload.model_dump(),
    timestamp=datetime.now(),
    node_id="saas-worker-1",
    lamport_clock=5,
    project_uuid=uuid.uuid4(),
)
```

#### Mapping a conclusion

```python
from spec_kitty_events import map_check_run_conclusion

event_type = map_check_run_conclusion("success")
# → "GatePassed"

event_type = map_check_run_conclusion("neutral")
# → None (logged as ignored)

event_type = map_check_run_conclusion(
    "skipped",
    on_ignored=lambda c, r: metrics.increment(f"gate.ignored.{c}"),
)
# → None (logged + callback invoked)

event_type = map_check_run_conclusion("bogus")
# → raises UnknownConclusionError("bogus")
```

#### Reconstructing a payload from a stored event

```python
from spec_kitty_events import GateFailedPayload

stored_event = event_store.get("01HXYZ...")
payload = GateFailedPayload.model_validate(stored_event.payload)
print(payload.check_run_url)  # https://github.com/...
```
