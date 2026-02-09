---
work_package_id: WP01
title: Event Envelope Extension + Test Migration
lane: "doing"
dependencies: []
base_branch: main
base_commit: 3de3d25be62a16aa64f308cd90983ff668b81ae6
created_at: '2026-02-09T11:37:20.985808+00:00'
subtasks: [T001, T002, T003, T004, T005, T006, T007]
shell_pid: "8128"
agent: "claude-opus"
history:
- date: '2026-02-09'
  agent: claude-opus
  action: created
  note: Generated from /spec-kitty.tasks
---

# WP01: Event Envelope Extension + Test Migration

## Objective

Extend the Event model with three new fields (correlation_id, schema_version, data_tier) and update all existing tests and docstring examples to work with the new required `correlation_id` field. This is the foundation WP — all subsequent WPs depend on this.

## Context

The existing Event model in `src/spec_kitty_events/models.py` has 10 fields. This WP adds 3 new fields per the canonical event contract spec (FR-001 through FR-004):

- `correlation_id` (str, required, ULID format) — groups all events in a mission execution
- `schema_version` (str, default "1.0.0", semver pattern) — envelope version for compat
- `data_tier` (int, default 0, range 0-4) — progressive data sharing tier

The `correlation_id` field is **required** with no default. This means every existing Event() construction in tests (~106 across 14 files) must be updated. The recommended approach is to create a test helper function.

## Implementation Command

```bash
spec-kitty implement WP01
```

## Detailed Guidance

### T001: Add New Fields to Event Model

**File**: `src/spec_kitty_events/models.py`

Add three new fields to the `Event` class, after the existing `project_slug` field:

```python
correlation_id: str = Field(
    ...,
    min_length=26,
    max_length=26,
    description="ULID grouping all events in the same mission execution"
)
schema_version: str = Field(
    default="1.0.0",
    pattern=r"^\d+\.\d+\.\d+$",
    description="Envelope schema version (semver)"
)
data_tier: int = Field(
    default=0,
    ge=0,
    le=4,
    description="Progressive data sharing tier (0=local, 4=telemetry)"
)
```

**Validation rules**:
- `correlation_id`: Same ULID format as `event_id` and `causation_id` (26 chars, min/max length)
- `schema_version`: Semver pattern `^\d+\.\d+\.\d+$` — rejects "1.0", "v1.0.0", empty string
- `data_tier`: Integer 0-4 inclusive. Default 0 (local-only). Rejects negative, 5+, non-integer

**Preserve existing fields exactly as-is**. Do not change any existing field's validation, type, or default.

### T002: Create Test Helper in conftest.py

**File**: `tests/conftest.py` (create if doesn't exist)

Create a helper function that builds Event objects with sensible defaults for the new required fields, reducing boilerplate in test updates:

```python
from datetime import datetime, timezone
from uuid import uuid4
from ulid import ULID
from spec_kitty_events import Event


def make_event(**overrides: object) -> Event:
    """Build an Event with defaults for all required fields.

    Callers override specific fields as needed. This avoids updating
    every Event() call when new required fields are added.
    """
    defaults = {
        "event_id": str(ULID()),
        "event_type": "TestEvent",
        "aggregate_id": "test-001",
        "payload": {},
        "timestamp": datetime.now(timezone.utc),
        "node_id": "test-node",
        "lamport_clock": 0,
        "project_uuid": uuid4(),
        "correlation_id": str(ULID()),
    }
    defaults.update(overrides)
    return Event(**defaults)  # type: ignore[arg-type]
```

**Important**: The helper provides `correlation_id` by default. Tests that explicitly test correlation_id validation should NOT use this helper — they should construct Event() directly.

### T003: Update Unit Test Files

**Files to update** (7 files, ~78 Event() calls):

1. **`tests/unit/test_conflict.py`** (~25 calls) — Heaviest file. Add `correlation_id=str(ULID())` to each Event() call. Consider using `make_event()` helper where the test doesn't depend on specific field values.

2. **`tests/unit/test_merge.py`** (~18 calls) — Similar approach. Events in merge tests often need specific `lamport_clock` and `aggregate_id` values, so use `make_event(lamport_clock=5, aggregate_id="wp01")` pattern.

3. **`tests/unit/test_models.py`** (~15 calls) — Some tests specifically validate Event construction. For those, add correlation_id explicitly. For others, use helper.

4. **`tests/unit/test_crdt.py`** (~10 calls) — CRDT tests use Events primarily as data containers. Use `make_event()` helper.

5. **`tests/unit/test_storage.py`** (~6 calls) — Storage tests. Use `make_event()` helper.

6. **`tests/unit/test_status.py`** (~3 calls) — Status reducer tests construct Events with specific event_type and payload. Use `make_event(event_type="WPStatusChanged", payload={...})`.

7. **`tests/unit/test_gates.py`** (~1 call) — Minimal. Single Event call, add correlation_id.

**Strategy**: For each file:
1. Add `from conftest import make_event` (or `from tests.conftest import make_event`)
2. Replace Event() calls that don't need specific field values with `make_event(field=value)` calls
3. For tests that explicitly validate Event construction, add `correlation_id=str(ULID())` directly
4. Run `python3.11 -m pytest tests/unit/<file>` after each file to verify

### T004: Update Integration Test Files

**Files to update** (4 files, ~24 calls):

1. **`tests/integration/test_quickstart.py`** (~11 calls) — These are end-to-end examples. Update all Event() calls with correlation_id.

2. **`tests/integration/test_conflict_resolution.py`** (~7 calls) — Conflict scenarios need events with same aggregate_id but different node_ids. Use `make_event()`.

3. **`tests/integration/test_event_emission.py`** (~4 calls) — Event emission tests. Add correlation_id.

4. **`tests/integration/test_adapters.py`** (~2 calls) — Adapter tests. Add correlation_id.

### T005: Update Property Test Files

**Files to update** (3 files, ~4 calls):

1. **`tests/property/test_crdt_laws.py`** (~2 calls) — Hypothesis strategies that generate Events. Update the strategy to include correlation_id.

2. **`tests/property/test_determinism.py`** (~1 call) — Update Event generation strategy.

3. **`tests/property/test_status_determinism.py`** (~1 call) — Update Event generation strategy. This file's Hypothesis strategy generates WPStatusChanged events — add correlation_id to the strategy.

**Important**: For Hypothesis strategies, add `correlation_id=st.builds(lambda: str(ULID()))` to the strategy builder, or use a fixed value since correlation_id doesn't affect ordering.

### T006: Update Docstring Examples in Source Modules

**Files to update** (~10 docstring examples):

1. **`src/spec_kitty_events/merge.py`** — Update Event examples in docstrings
2. **`src/spec_kitty_events/crdt.py`** — Update Event examples in docstrings
3. **`src/spec_kitty_events/conflict.py`** — Update Event examples in docstrings
4. **`src/spec_kitty_events/topology.py`** — Update Event examples in docstrings

For each: add `correlation_id="01HX..."` (26-char ULID string) to Event() examples in docstrings.

### T007: Add Unit Tests for New Event Fields

**File**: `tests/unit/test_models.py` (append to existing file)

Add tests for the three new fields:

**correlation_id tests**:
- Valid ULID string accepted
- String shorter than 26 chars rejected (ValidationError)
- String longer than 26 chars rejected (ValidationError)
- Missing correlation_id rejected (ValidationError — it's required)
- Round-trip: to_dict() → from_dict() preserves correlation_id

**schema_version tests**:
- Default value is "1.0.0"
- Valid semver "2.1.3" accepted
- Invalid "1.0" rejected (pattern mismatch)
- Invalid "v1.0.0" rejected (pattern mismatch)
- Round-trip preserves schema_version

**data_tier tests**:
- Default value is 0
- Values 0, 1, 2, 3, 4 accepted
- Value -1 rejected (ge=0)
- Value 5 rejected (le=4)
- Non-integer rejected
- Round-trip preserves data_tier

## Definition of Done

- [ ] Event model has all 3 new fields with correct validation
- [ ] All existing tests pass with `python3.11 -m pytest` (zero failures)
- [ ] New field validation tests pass
- [ ] `mypy --strict src/spec_kitty_events/models.py` passes
- [ ] Docstring examples are syntactically correct

## Risks

- **Missing Event() call sites**: Use `grep -rn "Event(" tests/ src/` to find ALL sites. Missing even one causes test failure.
- **Hypothesis strategies**: Property tests may need strategy updates for the new required field. If a strategy generates Events, it must include correlation_id.
- **Import resolution**: The `conftest.py` helper must be importable by all test files. Use pytest's automatic conftest discovery (place in `tests/` directory).

## Reviewer Guidance

1. Verify ALL Event() construction sites were updated (grep for `Event(` — no occurrences should lack correlation_id)
2. Verify new field validation is correct (test the validation rules, not just happy path)
3. Verify round-trip serialization (to_dict/from_dict) preserves new fields
4. Run `python3.11 -m pytest` — must have zero failures
5. Run `mypy --strict src/spec_kitty_events/models.py` — must pass

## Activity Log

- 2026-02-09T11:37:21Z – claude-opus – shell_pid=8128 – lane=doing – Assigned agent via workflow command
