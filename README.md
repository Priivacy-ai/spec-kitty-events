# spec-kitty-events

Event log library with Lamport clocks and systematic error tracking for distributed systems.

**Status**: Alpha (v0.1.1-alpha)

## Features

- **Lamport Clocks**: Establish causal ordering in distributed systems
- **Event Immutability**: Events are immutable (frozen Pydantic models)
- **Conflict Detection**: Detect concurrent events with `is_concurrent()`
- **CRDT Merge Rules**: Merge grow-only sets and counters with CRDT semantics
- **State-Machine Merge**: Resolve state conflicts with priority-based selection
- **Error Logging**: Systematic error tracking with retention policies (Manus pattern)
- **Storage Adapters**: Abstract storage interfaces (bring your own database)
- **Type Safety**: Full mypy --strict compliance with py.typed marker

## Installation

### From Git (Recommended for Alpha)

```bash
pip install git+https://github.com/Priivacy-ai/spec-kitty-events.git@v0.1.1-alpha
```

Or add to `requirements.txt` or `pyproject.toml`:

```toml
# pyproject.toml
dependencies = [
    "spec-kitty-events @ git+https://github.com/Priivacy-ai/spec-kitty-events.git@v0.1.1-alpha",
]
```

### Development Installation

```bash
git clone https://github.com/Priivacy-ai/spec-kitty-events.git
cd spec-kitty-events
pip install -e ".[dev]"
```

## Quick Start

### Basic Event Emission

```python
import uuid
from datetime import datetime
from spec_kitty_events import (
    Event,
    LamportClock,
    InMemoryClockStorage,
    InMemoryEventStore,
)

# Setup
clock_storage = InMemoryClockStorage()
event_store = InMemoryEventStore()
clock = LamportClock(node_id="alice", storage=clock_storage)

# Emit event
clock.tick()
event = Event(
    event_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
    event_type="WPStatusChanged",
    aggregate_id="WP001",
    timestamp=datetime.now(),
    node_id="alice",
    lamport_clock=clock.current(),
    project_uuid=uuid.uuid4(),
    project_slug="my-project",
    payload={"state": "doing"}
)
event_store.save_event(event)
```

### Conflict Detection & Resolution

```python
from spec_kitty_events import is_concurrent, state_machine_merge

# Detect concurrent events
if is_concurrent(event1, event2):
    # Resolve using state-machine merge
    priority_map = {"done": 4, "for_review": 3, "doing": 2, "planned": 1}
    resolution = state_machine_merge([event1, event2], priority_map)
    winner = resolution.merged_event
```

### CRDT Merge

```python
from spec_kitty_events import merge_gset, merge_counter

# Merge grow-only set (tags)
tags = merge_gset([event1, event2, event3])

# Merge counter (deltas)
total = merge_counter([event1, event2, event3])
```

## Architecture

### Storage Adapters

The library provides abstract storage interfaces (`EventStore`, `ClockStorage`, `ErrorStorage`) that you can implement for your persistence layer:

- **InMemoryEventStore**: For testing (not durable)
- **InMemoryClockStorage**: For testing (not durable)
- **InMemoryErrorStorage**: For testing (not durable)

For production, implement adapters for your database (PostgreSQL, SQLite, etc.).

### API Overview

**Core Models**:
- `Event`: Immutable event with causal metadata (lamport_clock, causation_id, project_uuid, project_slug)
- `ErrorEntry`: Error log entry (timestamp, action_attempted, error_message)
- `ConflictResolution`: Result of merge operation

**Clocks**:
- `LamportClock`: Lamport logical clock with tick(), update(), current()

**Conflict Detection**:
- `is_concurrent(e1, e2)`: Detect concurrent events
- `total_order_key(event)`: Deterministic tiebreaker

**Merge Functions**:
- `merge_gset(events)`: CRDT merge for grow-only sets
- `merge_counter(events)`: CRDT merge for counters
- `state_machine_merge(events, priority_map)`: Priority-based state merge

**Error Logging**:
- `ErrorLog`: Append-only error log with retention policy

## Documentation

API reference documentation coming in v0.2.0. For now, refer to:
- Type hints in source code (fully type-annotated with mypy --strict)
- Integration tests in `tests/integration/` for usage examples
- Docstrings in `src/spec_kitty_events/`

## Testing

Run tests with pytest:

```bash
pytest --cov --cov-report=html
```

Type checking:

```bash
mypy src/spec_kitty_events --strict
```

## Requirements

- Python 3.10+
- Pydantic 2.x
- python-ulid

## License

No license information provided. This is a private repository.

## Contributing

This is an alpha release. Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Run tests and type checking
4. Submit a pull request

## Roadmap

**v0.1.1-alpha** (Current):
- ✅ Lamport clocks
- ✅ Event immutability
- ✅ Conflict detection
- ✅ CRDT and state-machine merge
- ✅ Error logging
- ✅ Project identity (project_uuid, project_slug)

**v0.2.0** (Planned):
- [ ] Vector clocks (full happens-before ordering)
- [ ] Persistent storage adapters (SQLite, PostgreSQL)
- [ ] Additional CRDT types (LWW-Register, OR-Set)
- [ ] API reference documentation (Sphinx)

## Support

For issues, questions, or feature requests, please open an issue on GitHub.

---

Generated with [Spec Kitty](https://github.com/robdouglass/SpecKitty)
