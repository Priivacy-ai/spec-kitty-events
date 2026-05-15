# Contract: Executable Timestamp Semantics

## Overview

Consumers of the `spec-kitty-events` canonical envelope MUST preserve the producer's `timestamp` through ingestion, persistence, projection, reduction, and any downstream serialization. Consumers MAY additionally record their own receipt/import time under a clearly distinct field (`received_at`).

## Producer Obligations

- The producer SHALL assign `timestamp` to the wall-clock moment the modelled event occurred on the producing system.
- The producer SHALL use UTC ISO-8601.
- The producer SHALL NOT replace an existing `timestamp` when re-emitting a historical event during backfill or replay.

## Consumer Obligations

- The consumer SHALL parse the incoming envelope's `timestamp` once and persist it without modification.
- The consumer SHALL NOT substitute `datetime.now()`, `timezone.now()`, `auto_now_add=True`, server clock, or any other receipt-time value for `timestamp` in any field, column, or projection that downstream code interprets as canonical event occurrence time.
- The consumer MAY persist receipt time under a separately named field (`received_at`). The consumer SHALL NOT use receipt time as a fallback for ordering, age, completion time, or activity time in canonical projections.
- The consumer SHALL run `assert_producer_occurrence_preserved(envelope, persisted_occurrence_time)` in at least one regression test that exercises the full ingestion path with a fixture from `spec_kitty_events.conformance` whose producer `timestamp` is materially older than its receipt-time annotation.

## Failure Mode

If a consumer's persisted occurrence time does not equal the envelope `timestamp`, the helper raises `TimestampSubstitutionError(field_name, expected, actual)`. The error MUST surface:

- the field/column name that diverged (consumer-supplied)
- the expected producer `timestamp`
- the actual substituted value

Consumers SHALL treat this error as a fail-closed compatibility violation and SHALL NOT catch and silently swallow it in production code paths.

## Reusable Helper Reference

```python
from spec_kitty_events.conformance import (
    assert_producer_occurrence_preserved,
    TimestampSubstitutionError,
)
```

## Test Vectors (fixtures)

- `valid/old_producer_recent_receipt.json` — producer `timestamp` = `2026-01-01T00:00:00+00:00`, `received_at` ≥ 30 days later, `persisted_occurrence_time` equals producer `timestamp`. Helper MUST pass.
- `valid/live_event_producer_equals_receipt.json` — producer `timestamp` equals `received_at`. Helper MUST pass.
- `invalid/consumer_substituted_receipt_time.json` — `persisted_occurrence_time` equals `received_at` and does NOT equal producer `timestamp`. Helper MUST raise `TimestampSubstitutionError`.
