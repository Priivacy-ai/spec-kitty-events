# Data Model — Executable Event Timestamp Semantics

This mission does NOT change the wire format. It strengthens the semantic meaning of one existing field (`Event.timestamp`) and introduces a documented, consumer-owned concept (`received_at`).

## Canonical Envelope Field (unchanged shape, strengthened semantics)

| Field | Type | Required | Producer Semantics |
|-------|------|----------|--------------------|
| `timestamp` | string (ISO-8601 UTC) / `datetime` | yes | Producer-assigned wall-clock occurrence time. The moment the modelled event occurred on the producing system (CLI machine, runtime worker, tracker subsystem). It is the only canonical event time. Consumers MUST preserve this value through ingestion, persistence, projection, reduction, and any downstream serialization. Consumers MUST NOT overwrite this value with their own clock at receipt, drain, replay, or materialization. |

**Rule R-T-01 (producer wins)**: The producer's `timestamp` is the canonical occurrence time for the event. There is no automatic fallback to server clocks.

**Rule R-T-02 (no name collision)**: Consumers MUST NOT store receipt/import/ingest/server-clock time under any field whose unqualified name is `timestamp`. Consumer storage of receipt time MUST use a clearly distinct field name (recommended: `received_at`).

**Rule R-T-03 (additive ordering invariance)**: Reducer ordering and replay ordering MUST continue to rely on `lamport_clock`/`node_id` rules. Strengthening `timestamp` semantics does not change ordering, per mission constraint C-004.

## Consumer-Owned Concept (documented, not on the wire)

| Name | Owner | Semantics |
|------|-------|-----------|
| `received_at` | consumer storage | The moment the consumer received, drained, or persisted the event. Useful for diagnostics, sync dashboards, and audit. MUST NOT be substituted for `timestamp` in canonical projections, scorecards, or activity feeds. |

`received_at` is NOT a field on the canonical envelope. It is a recommended name for whatever per-consumer column or attribute a consumer chooses to store its own receipt/import time in. The conformance helper does not require it; it only forbids substituting any such value for `timestamp`.

## Conformance Helper (consumer-side)

```python
from datetime import datetime
from typing import Callable
from spec_kitty_events.conformance import (
    assert_producer_occurrence_preserved,
    TimestampSubstitutionError,
)
```

Signature shape:

```python
def assert_producer_occurrence_preserved(
    envelope: dict,                          # the canonical event envelope (dict or Event)
    persisted_occurrence_time: datetime,     # the consumer's persisted occurrence-time value
) -> None:
    """Raise TimestampSubstitutionError if persisted_occurrence_time != envelope['timestamp']."""
```

`TimestampSubstitutionError(field_name, expected, actual)` is exposed for typed handling.

## Fixture Shape

Each fixture is a JSON document at `src/spec_kitty_events/conformance/fixtures/timestamp_semantics/<class>/<name>.json`:

```json
{
  "fixture_kind": "timestamp_semantics",
  "envelope": {
    "event_id": "01J6XW9KQT7M0YB3N4R5CQZ2EX",
    "event_type": "WPStatusChanged",
    "aggregate_id": "wp-001",
    "payload": {},
    "timestamp": "2026-01-01T00:00:00+00:00",
    "build_id": "...",
    "node_id": "...",
    "lamport_clock": 1,
    "correlation_id": "01J6XW9KQT7M0YB3N4R5CQZ2EX",
    "project_uuid": "00000000-0000-0000-0000-000000000000"
  },
  "consumer_simulation": {
    "received_at": "2026-05-15T10:00:00+00:00",
    "persisted_occurrence_time": "2026-01-01T00:00:00+00:00"
  },
  "expectation": "valid"
}
```

For the invalid case, `consumer_simulation.persisted_occurrence_time` equals `consumer_simulation.received_at` (the consumer overwrote it), and `expectation` is `"invalid"`. The conformance test loads these fixtures and runs the helper accordingly.

## Cross-reference

This mission also updates the canonical authoritative document at `kitty-specs/teamspace-event-contract-foundation-01KQHDE4/data-model.md` to record Rule R-T-01, R-T-02, R-T-03 and the recommended `received_at` consumer convention. The mission's own `data-model.md` is the working/design view; the canonical contract document is the audit-of-record.
