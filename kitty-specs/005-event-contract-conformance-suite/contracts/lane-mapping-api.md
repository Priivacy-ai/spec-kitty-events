# Lane Mapping API Contract

**Feature**: 005-event-contract-conformance-suite
**Date**: 2026-02-12
**Status**: Locked (V1)

## Overview

The lane mapping API provides a first-class, importable contract for converting between the canonical 7-lane status model and the 4-lane sync model used by downstream consumers (CLI and SaaS).

## Public API Surface

### SyncLaneV1

```python
class SyncLaneV1(str, Enum):
    PLANNED = "planned"
    DOING = "doing"
    FOR_REVIEW = "for_review"
    DONE = "done"
```

**Contract**: Exactly 4 members. Immutable for V1 lifetime.

### CANONICAL_TO_SYNC_V1

```python
CANONICAL_TO_SYNC_V1: MappingProxyType[Lane, SyncLaneV1]
```

**Mapping table**:

| Canonical Lane | Sync Lane V1 | Rationale |
|----------------|--------------|-----------|
| `PLANNED` | `PLANNED` | Direct mapping |
| `CLAIMED` | `PLANNED` | Claimed is pre-work, collapses to planned |
| `IN_PROGRESS` | `DOING` | Consumer-facing alias |
| `FOR_REVIEW` | `FOR_REVIEW` | Direct mapping |
| `DONE` | `DONE` | Direct mapping |
| `BLOCKED` | `DOING` | Blocked is mid-work, collapses to doing |
| `CANCELED` | `PLANNED` | Canceled resets to planned in sync model |

**Contract**: Total function — every `Lane` member has exactly one mapping. Deterministic and idempotent.

### canonical_to_sync_v1

```python
def canonical_to_sync_v1(lane: Lane) -> SyncLaneV1:
    """Apply the V1 canonical-to-sync lane mapping.

    Args:
        lane: A canonical Lane enum value.

    Returns:
        The corresponding SyncLaneV1 value.

    Raises:
        KeyError: If lane is not in the V1 mapping (should never happen).
    """
```

## Versioning Policy

- **V1 is locked**: Changing the output for any input lane is a breaking change requiring a `3.0.0` major version bump.
- **New versions are additive**: `SyncLaneV2`, `CANONICAL_TO_SYNC_V2`, `canonical_to_sync_v2()` can be added in a `2.x` minor release without altering V1.
- **Consumers import explicitly**: `from spec_kitty_events import canonical_to_sync_v1` — version is in the name.

## Consumer Integration

```python
# In spec-kitty CLI (emit.py):
from spec_kitty_events import Lane, SyncLaneV1, canonical_to_sync_v1

sync_lane = canonical_to_sync_v1(canonical_lane)
# Use sync_lane.value for wire format
```

```python
# In spec-kitty-saas (emitter.py):
from spec_kitty_events import canonical_to_sync_v1

# Validate emitted status value
assert canonical_to_sync_v1(Lane.BLOCKED) == SyncLaneV1.DOING
```
