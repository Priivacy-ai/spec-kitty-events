# Compatibility Guide

This document is the definitive reference for `spec-kitty-events` consumers (CLI and SaaS teams)
migrating from `0.x` to `2.0.0`. It covers the lane mapping contract, required/optional fields
per event type, versioning policy, and CI integration steps.

## Table of Contents

- [Lane Mapping Contract](#lane-mapping-contract)
- [Event Type Field Reference](#event-type-field-reference)
- [Versioning Policy](#versioning-policy)
- [Migration Guide (0.x to 2.0.0)](#migration-guide-0x-to-200)
- [Consumer CI Integration](#consumer-ci-integration)
- [SCHEMA_VERSION Documentation](#schema_version-documentation)
- [Functional Requirements Traceability](#functional-requirements-traceability)

---

## Lane Mapping Contract

The `SyncLaneV1` mapping collapses the 7 canonical `Lane` values into 4 consumer-facing sync
lanes. This mapping is **locked** for the entire 2.x series. Changing any output for a given
input constitutes a breaking change requiring a `3.0.0` release.

### Lane Mapping Table

| Canonical Lane (`Lane`) | Sync Lane (`SyncLaneV1`) | Rationale |
|---|---|---|
| `planned` | `planned` | Direct mapping |
| `claimed` | `planned` | Pre-work state, collapses to planned |
| `in_progress` | `doing` | Consumer-facing alias for active work |
| `for_review` | `for_review` | Direct mapping |
| `done` | `done` | Direct mapping |
| `blocked` | `doing` | Mid-work state, collapses to doing |
| `canceled` | `planned` | Resets to planned in sync model |

### Usage

```python
from spec_kitty_events import Lane, SyncLaneV1, canonical_to_sync_v1

# Function API (recommended)
sync_lane = canonical_to_sync_v1(Lane.IN_PROGRESS)
assert sync_lane == SyncLaneV1.DOING

# Direct mapping access
from spec_kitty_events import CANONICAL_TO_SYNC_V1
assert CANONICAL_TO_SYNC_V1[Lane.BLOCKED] == SyncLaneV1.DOING
```

### Mapping Guarantees

- The `CANONICAL_TO_SYNC_V1` mapping is an **immutable** `MappingProxyType`. It cannot be
  modified at runtime.
- Every `Lane` member has exactly one `SyncLaneV1` target. There are no unmapped lanes.
- The mapping is exercised by conformance fixtures in the `lane_mapping` category.

---

## Event Type Field Reference

### `Event` (envelope)

The `Event` model is the top-level envelope for all events. All payload-specific data goes in the
`payload` dictionary.

| Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `event_id` | `str` (ULID, 26 chars) | Yes | — | Unique event identifier |
| `event_type` | `str` | Yes | — | Event type (e.g., `"WPStatusChanged"`) |
| `aggregate_id` | `str` | Yes | — | Entity this event modifies |
| `payload` | `dict` | No | `{}` | Event-specific data |
| `timestamp` | `datetime` | Yes | — | Wall-clock time (not for ordering) |
| `node_id` | `str` | Yes | — | Emitting node identifier |
| `lamport_clock` | `int` (>= 0) | Yes | — | Lamport logical clock value |
| `causation_id` | `str` (ULID) or `null` | No | `None` | Parent event ID |
| `project_uuid` | `UUID` | Yes | — | Project UUID |
| `project_slug` | `str` or `null` | No | `None` | Human-readable project slug |
| `correlation_id` | `str` (ULID, 26 chars) | Yes | — | Mission execution group ID |
| `schema_version` | `str` (semver) | No | `"1.0.0"` | Envelope schema version |
| `data_tier` | `int` (0-4) | No | `0` | Data sharing tier |

### `WPStatusChanged` (`StatusTransitionPayload`)

| Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `feature_slug` | `str` | Yes | — | Feature identifier |
| `wp_id` | `str` | Yes | — | Work package identifier |
| `from_lane` | `Lane` or `null` | No | `None` | Previous lane (null for initial) |
| `to_lane` | `Lane` | Yes | — | Target lane |
| `actor` | `str` | Yes | — | Actor performing the transition |
| `force` | `bool` | No | `False` | Whether this is a forced transition |
| `reason` | `str` or `null` | No | `None` | Transition reason |
| `execution_mode` | `ExecutionMode` | Yes | — | Worktree or direct repo |
| `review_ref` | `str` or `null` | No | `None` | Review reference (for rollbacks) |
| `evidence` | `DoneEvidence` or `null` | No | `None` | Required evidence for done transitions |

### `GatePassed` (`GatePassedPayload`)

| Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `gate_name` | `str` | Yes | — | CI gate name (e.g., `"ci/build"`) |
| `gate_type` | `"ci"` | Yes | — | Gate type (only `"ci"` supported) |
| `conclusion` | `"success"` | Yes | — | Must be `"success"` |
| `external_provider` | `"github"` | Yes | — | Provider (only `"github"` supported) |
| `check_run_id` | `int` (> 0) | Yes | — | GitHub check run ID |
| `check_run_url` | `AnyHttpUrl` | Yes | — | URL of the check run |
| `delivery_id` | `str` | Yes | — | Webhook delivery idempotency key |
| `pr_number` | `int` (> 0) or `null` | No | `None` | Associated pull request number |

### `GateFailed` (`GateFailedPayload`)

| Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `gate_name` | `str` | Yes | — | CI gate name |
| `gate_type` | `"ci"` | Yes | — | Gate type |
| `conclusion` | `"failure"` / `"timed_out"` / `"cancelled"` / `"action_required"` | Yes | — | Failure conclusion |
| `external_provider` | `"github"` | Yes | — | Provider |
| `check_run_id` | `int` (> 0) | Yes | — | GitHub check run ID |
| `check_run_url` | `AnyHttpUrl` | Yes | — | URL of the check run |
| `delivery_id` | `str` | Yes | — | Webhook delivery idempotency key |
| `pr_number` | `int` (> 0) or `null` | No | `None` | Associated pull request number |

### `MissionStarted` (`MissionStartedPayload`)

| Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `mission_id` | `str` | Yes | — | Mission identifier |
| `mission_type` | `str` | Yes | — | Mission type (e.g., `"software-dev"`) |
| `initial_phase` | `str` | Yes | — | First phase of the mission |
| `actor` | `str` | Yes | — | Actor who started the mission |

### `MissionCompleted` (`MissionCompletedPayload`)

| Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `mission_id` | `str` | Yes | — | Mission identifier |
| `mission_type` | `str` | Yes | — | Mission type |
| `final_phase` | `str` | Yes | — | Last phase before completion |
| `actor` | `str` | Yes | — | Actor who completed the mission |

### `MissionCancelled` (`MissionCancelledPayload`)

| Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `mission_id` | `str` | Yes | — | Mission identifier |
| `reason` | `str` | Yes | — | Cancellation reason |
| `actor` | `str` | Yes | — | Actor who cancelled |
| `cancelled_wp_ids` | `list[str]` | No | `[]` | WP IDs affected by cancellation |

### `PhaseEntered` (`PhaseEnteredPayload`)

| Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `mission_id` | `str` | Yes | — | Mission identifier |
| `phase_name` | `str` | Yes | — | Phase being entered |
| `previous_phase` | `str` or `null` | No | `None` | Phase being exited |
| `actor` | `str` | Yes | — | Actor triggering transition |

### `ReviewRollback` (`ReviewRollbackPayload`)

| Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `mission_id` | `str` | Yes | — | Mission identifier |
| `review_ref` | `str` | Yes | — | Review that triggered rollback |
| `target_phase` | `str` | Yes | — | Phase to roll back to |
| `affected_wp_ids` | `list[str]` | No | `[]` | WP IDs affected by rollback |
| `actor` | `str` | Yes | — | Actor triggering rollback |

---

## Versioning Policy

This project follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html) with these rules
for the `2.x` series:

### Patch Releases (`2.x.Y`)

Bug fixes and documentation corrections only. No API changes.

**Examples**: Fix a typo in a schema description, correct a validator edge case.

### Minor Releases (`2.X.0`)

Additive, backward-compatible changes. Existing consumers are unaffected.

**Examples**:
- New optional fields on existing payload models (with defaults).
- New event types (e.g., `WPDependencyChanged`).
- New mapping versions (e.g., `SyncLaneV2` alongside the existing `SyncLaneV1`).
- New fixture categories or test helpers.
- New JSON schemas for newly added models.

### Major Releases (`3.0.0`)

Any breaking change requires a major version bump.

**Examples**:
- Removing a field from a payload model.
- Changing `SyncLaneV1` mapping output for any input (e.g., `canceled` mapping to `done`
  instead of `planned`).
- Removing an event type.
- Changing a required field to a different type.
- Removing a public export from `__init__.py`.

### Mapping Lock Guarantee

The `SyncLaneV1` mapping (`CANONICAL_TO_SYNC_V1`) is **locked** for the 2.x series:

- Changing the output of `canonical_to_sync_v1()` for any `Lane` input is a **breaking change**
  requiring `3.0.0`.
- New mapping versions (e.g., `SyncLaneV2`) are additive and can ship in any `2.x` minor release.
- Adding new lanes to `Lane` (and mapping them in `CANONICAL_TO_SYNC_V1`) is a minor change
  (`2.x.0`), provided all existing mappings remain unchanged.

---

## Migration Guide (0.x to 2.0.0)

### Step 1: Update Dependency

```toml
# pyproject.toml
dependencies = [
    "spec-kitty-events>=2.0.0rc1,<3.0.0",
]
```

### Step 2: Replace Hardcoded Lane Mappings

```python
# Before (0.x consumer code):
LANE_MAP = {
    "planned": "planned",
    "claimed": "planned",
    "in_progress": "doing",
    "for_review": "for_review",
    "done": "done",
    "blocked": "doing",
    "canceled": "planned",
}
sync_lane = LANE_MAP[raw_lane]

# After (2.0.0):
from spec_kitty_events import Lane, canonical_to_sync_v1

sync_lane = canonical_to_sync_v1(Lane(raw_lane))
```

### Step 3: Replace Local Status Enums

```python
# Before (0.x consumer code):
class SyncStatus(str, Enum):
    PLANNED = "planned"
    DOING = "doing"
    FOR_REVIEW = "for_review"
    DONE = "done"

# After (2.0.0):
from spec_kitty_events import SyncLaneV1

# SyncLaneV1.PLANNED, SyncLaneV1.DOING, SyncLaneV1.FOR_REVIEW, SyncLaneV1.DONE
```

### Step 4: Update Event Constructors

The `Event` model gained three fields in 0.4.0-alpha:
- `correlation_id` (required, ULID string)
- `schema_version` (optional, default `"1.0.0"`)
- `data_tier` (optional, default `0`)

```python
# Before (0.3.x):
event = Event(
    event_id=ulid_str,
    event_type="WPStatusChanged",
    aggregate_id="WP001",
    timestamp=now,
    node_id="alice",
    lamport_clock=1,
    project_uuid=project_uuid,
    payload={"state": "doing"},
)

# After (2.0.0):
event = Event(
    event_id=ulid_str,
    event_type="WPStatusChanged",
    aggregate_id="WP001",
    timestamp=now,
    node_id="alice",
    lamport_clock=1,
    project_uuid=project_uuid,
    correlation_id=correlation_ulid,  # NEW: required
    schema_version="2.0.0",           # NEW: optional (default "1.0.0")
    data_tier=0,                      # NEW: optional (default 0)
    payload={"state": "doing"},
)
```

### Step 5: Add Conformance CI

See [Consumer CI Integration](#consumer-ci-integration) below.

---

## Consumer CI Integration

Add these steps to your CI pipeline to validate conformance with the upstream event contract.
This catches contract drift early, before it reaches production.

### For CLI and SaaS Consumers

#### Step 1: Add Dependency

```bash
pip install "spec-kitty-events[conformance]>=2.0.0rc1,<3.0.0"
```

The `[conformance]` extra adds `jsonschema>=4.21.0,<5.0.0` for full dual-layer validation.

#### Step 2: Run Upstream Conformance Suite

```bash
pytest --pyargs spec_kitty_events.conformance -v
```

This runs the bundled conformance test suite against the installed version of `spec-kitty-events`.
It validates all event types, lane mappings, and edge cases using manifest-driven fixtures.

#### Step 3: Validate Your Own Payloads (Optional)

Use the `validate_event()` API to check payloads your application constructs:

```python
from spec_kitty_events.conformance import validate_event

# Validate a payload you construct
my_payload = {
    "feature_slug": "005-my-feature",
    "wp_id": "WP01",
    "to_lane": "in_progress",
    "actor": "ci-bot",
    "execution_mode": "worktree",
}
result = validate_event(my_payload, "WPStatusChanged", strict=True)
assert result.valid, f"Violations: {result.model_violations}"
```

#### Step 4: Use Consumer Test Helpers (Optional)

Import reusable assertion functions for your own test suites:

```python
from spec_kitty_events.conformance import (
    assert_payload_conforms,
    assert_payload_fails,
    assert_lane_mapping,
)

def test_my_payload_conforms():
    payload = build_my_wp_status_payload()
    assert_payload_conforms(payload, "WPStatusChanged", strict=True)

def test_lane_mapping_contract():
    assert_lane_mapping("in_progress", "doing")
    assert_lane_mapping("blocked", "doing")
    assert_lane_mapping("canceled", "planned")
```

### For spec-kitty-events Contributors

#### Schema Drift Check

After modifying any Pydantic model, verify JSON schemas are up to date:

```bash
python -m spec_kitty_events.schemas.generate --check
```

This compares the generated schemas against the committed `.schema.json` files. If they differ,
regenerate:

```bash
python -m spec_kitty_events.schemas.generate
git add src/spec_kitty_events/schemas/*.schema.json
```

---

## SCHEMA_VERSION Documentation

The `SCHEMA_VERSION` constant (currently `"2.0.0"`) is defined in
`spec_kitty_events.lifecycle` and exported from `spec_kitty_events`:

```python
from spec_kitty_events import SCHEMA_VERSION
assert SCHEMA_VERSION == "2.0.0"
```

### Version Semantics

- `SCHEMA_VERSION` tracks the **event contract version**, not the package version.
- It is set to `"2.0.0"` for the entire 2.x series.
- The `Event.schema_version` field defaults to `"1.0.0"` and can be set per-event to indicate
  which contract version the event was produced under.
- A consumer that only understands schema version `"1.0.0"` can safely ignore events with
  `schema_version="2.0.0"` (forward-compatible envelope).

---

## Functional Requirements Traceability

Every functional requirement (FR-001 through FR-023) from the Feature 005 specification is
addressed across WP01-WP07:

| FR | Description | Addressed In |
|---|---|---|
| FR-001 | `SyncLaneV1` enum with 4 values | WP01 (`status.py`) |
| FR-002 | `CANONICAL_TO_SYNC_V1` immutable mapping | WP01 (`status.py`) |
| FR-003 | `canonical_to_sync_v1()` function | WP01 (`status.py`) |
| FR-004 | All 7 `Lane` values mapped | WP01 (`status.py`) |
| FR-005 | Mapping is frozen (`MappingProxyType`) | WP01 (`status.py`) |
| FR-006 | JSON Schema per Pydantic model | WP02 (`schemas/`) |
| FR-007 | Build-time generation script | WP02 (`schemas/generate.py`) |
| FR-008 | CI drift detection (`--check` flag) | WP02 (`schemas/generate.py`) |
| FR-009 | `load_schema()` and `list_schemas()` API | WP02 (`schemas/__init__.py`) |
| FR-010 | `FixtureCase` frozen dataclass | WP04 (`conformance/loader.py`) |
| FR-011 | `load_fixtures()` with manifest | WP04 (`conformance/loader.py`) |
| FR-012 | `validate_event()` dual-layer validator | WP03 (`conformance/validators.py`) |
| FR-013 | `ConformanceResult` with model/schema buckets | WP03 (`conformance/validators.py`) |
| FR-014 | Graceful degradation without jsonschema | WP03 (`conformance/validators.py`) |
| FR-015 | `pytest --pyargs` entry point | WP05 (`conformance/test_pyargs_entrypoint.py`) |
| FR-016 | Manifest-driven fixture tests | WP05 (`conformance/conftest.py`) |
| FR-017 | Consumer test helpers | WP05 (`conformance/pytest_helpers.py`) |
| FR-018 | Version graduated to 2.0.0rc1 | WP06 (`pyproject.toml`) |
| FR-019 | Compatibility table (this document) | WP07 (`COMPATIBILITY.md`) |
| FR-020 | Changelog with migration notes | WP07 (`CHANGELOG.md`) |
| FR-021 | SCHEMA_VERSION documentation | WP07 (`COMPATIBILITY.md`) |
| FR-022 | `[conformance]` optional extra | WP06 (`pyproject.toml`) |
| FR-023 | Package data for schemas and fixtures | WP02 + WP06 (`pyproject.toml`) |

All 23 functional requirements are addressed. No gaps identified.
