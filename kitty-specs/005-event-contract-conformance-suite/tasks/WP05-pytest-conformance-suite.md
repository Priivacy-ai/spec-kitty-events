---
work_package_id: WP05
title: Pytest Conformance Entry Point
lane: planned
dependencies: [WP04]
subtasks: [T029, T030, T031, T032, T033]
history:
- date: '2026-02-12'
  action: created
  by: spec-kitty.tasks
---

# WP05 — Pytest Conformance Entry Point

## Implementation Command

```bash
spec-kitty implement WP05 --base WP04
```

## Objective

Create the pytest conformance suite that consumers run via `pytest --pyargs spec_kitty_events.conformance`. This includes `test_pyargs_entrypoint.py` (manifest-driven conformance tests), `conftest.py` (shared fixtures), and `pytest_helpers.py` (reusable assertion utilities).

## Context

Per research (R2), `pytest --pyargs spec_kitty_events.conformance` resolves the installed package path and runs all `test_*.py` files found there. The conformance tests must:
- Be manifest-driven (read `manifest.json` to discover test cases)
- Test schema validity, fixture validity, lane mapping correctness, round-trip serialization
- Produce clear, actionable failure messages (FR-017)
- Work with `jsonschema` installed (full) or without (Pydantic-only)

**Key files to create**:
- `src/spec_kitty_events/conformance/pytest_helpers.py`
- `src/spec_kitty_events/conformance/conftest.py`
- `src/spec_kitty_events/conformance/test_pyargs_entrypoint.py`

**Key files to modify**:
- `pyproject.toml` — coverage omit for conformance test code

## Subtask Guidance

### T029: Create `pytest_helpers.py` with reusable assertions

**Purpose**: Utility functions that both the shipped conformance tests and consumer tests can import.

**Steps**:
1. Create `src/spec_kitty_events/conformance/pytest_helpers.py`.
2. Implement helpers:

```python
"""Reusable test helpers for spec-kitty-events conformance testing.

Consumers can import these to write their own conformance assertions:
    from spec_kitty_events.conformance.pytest_helpers import (
        assert_payload_conforms,
        assert_payload_fails,
        assert_lane_mapping,
    )
"""
from __future__ import annotations

from typing import Any

from spec_kitty_events.conformance.validators import (
    ConformanceResult,
    validate_event,
)
from spec_kitty_events.status import Lane, SyncLaneV1, canonical_to_sync_v1


def assert_payload_conforms(
    payload: dict[str, Any],
    event_type: str,
    *,
    strict: bool = False,
) -> ConformanceResult:
    """Assert a payload conforms to the canonical contract."""
    result = validate_event(payload, event_type, strict=strict)
    if not result.valid:
        violations = []
        for v in result.model_violations:
            violations.append(f"  Model: {v.field} — {v.message}")
        for v in result.schema_violations:
            violations.append(f"  Schema: {v.json_path} — {v.message}")
        raise AssertionError(
            f"Payload for {event_type!r} failed conformance:\n"
            + "\n".join(violations)
        )
    return result


def assert_payload_fails(
    payload: dict[str, Any],
    event_type: str,
    *,
    strict: bool = False,
) -> ConformanceResult:
    """Assert a payload DOES NOT conform (expected invalid)."""
    result = validate_event(payload, event_type, strict=strict)
    if result.valid:
        raise AssertionError(
            f"Payload for {event_type!r} was expected to fail but passed conformance."
        )
    return result


def assert_lane_mapping(
    canonical_value: str,
    expected_sync_value: str,
) -> None:
    """Assert a canonical lane maps to the expected sync lane."""
    lane = Lane(canonical_value)
    sync = canonical_to_sync_v1(lane)
    assert sync == SyncLaneV1(expected_sync_value), (
        f"Expected {canonical_value!r} → {expected_sync_value!r}, "
        f"got {sync.value!r}"
    )
```

3. Add exports to `conformance/__init__.py` `__all__`.

**Validation**:
- [ ] `from spec_kitty_events.conformance.pytest_helpers import assert_payload_conforms` works
- [ ] `assert_payload_conforms` raises `AssertionError` on invalid payload
- [ ] `assert_payload_fails` raises `AssertionError` on valid payload

### T030: Create `conftest.py` with shared fixtures

**Purpose**: Provide pytest fixtures available to all conformance tests.

**Steps**:
1. Create `src/spec_kitty_events/conformance/conftest.py`.
2. Fixtures:

```python
"""Shared pytest fixtures for conformance tests."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest


@pytest.fixture
def fixtures_dir() -> Path:
    """Path to the conformance fixtures directory."""
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def manifest(fixtures_dir: Path) -> dict[str, Any]:
    """Loaded manifest.json contents."""
    manifest_path = fixtures_dir / "manifest.json"
    return json.loads(manifest_path.read_text(encoding="utf-8"))  # type: ignore[no-any-return]


@pytest.fixture
def fixture_cases(manifest: dict[str, Any], fixtures_dir: Path) -> list[dict[str, Any]]:
    """All fixture cases with loaded payloads."""
    cases = []
    for entry in manifest["fixtures"]:
        fixture_path = fixtures_dir / entry["path"]
        payload = json.loads(fixture_path.read_text(encoding="utf-8"))
        cases.append({
            **entry,
            "payload": payload,
        })
    return cases
```

**Validation**:
- [ ] `fixtures_dir` fixture returns correct path
- [ ] `manifest` fixture loads manifest.json
- [ ] `fixture_cases` fixture has loaded payloads

### T031: Create `test_pyargs_entrypoint.py` with manifest-driven tests

**Purpose**: The primary conformance test file consumers run via `pytest --pyargs`.

**Steps**:
1. Create `src/spec_kitty_events/conformance/test_pyargs_entrypoint.py`.
2. Implement manifest-driven tests:

```python
"""Conformance test suite for spec-kitty-events.

Run: pytest --pyargs spec_kitty_events.conformance
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from spec_kitty_events.conformance.pytest_helpers import (
    assert_lane_mapping,
    assert_payload_conforms,
    assert_payload_fails,
)
from spec_kitty_events.schemas import list_schemas, load_schema
from spec_kitty_events.status import Lane, SyncLaneV1, CANONICAL_TO_SYNC_V1


# --- Manifest-driven fixture tests ---

_FIXTURES_DIR = Path(__file__).parent / "fixtures"
_MANIFEST = json.loads(
    (_FIXTURES_DIR / "manifest.json").read_text(encoding="utf-8")
)


def _fixture_ids() -> list[str]:
    return [f["id"] for f in _MANIFEST["fixtures"]]


def _fixture_params() -> list[dict[str, Any]]:
    params = []
    for entry in _MANIFEST["fixtures"]:
        fixture_path = _FIXTURES_DIR / entry["path"]
        payload = json.loads(fixture_path.read_text(encoding="utf-8"))
        params.append({**entry, "payload": payload})
    return params


@pytest.mark.parametrize("case", _fixture_params(), ids=_fixture_ids())
def test_fixture_conformance(case: dict[str, Any]) -> None:
    """Validate each fixture against its expected result."""
    if case["expected_result"] == "valid":
        assert_payload_conforms(case["payload"], case["event_type"])
    else:
        assert_payload_fails(case["payload"], case["event_type"])


# --- Lane mapping tests ---

def test_lane_mapping_v1_completeness() -> None:
    """All canonical lanes have a sync mapping."""
    assert set(CANONICAL_TO_SYNC_V1.keys()) == set(Lane)


def test_lane_mapping_v1_output_type() -> None:
    """All mapping outputs are SyncLaneV1 members."""
    for sync_lane in CANONICAL_TO_SYNC_V1.values():
        assert isinstance(sync_lane, SyncLaneV1)


@pytest.mark.parametrize("lane", list(Lane), ids=[l.value for l in Lane])
def test_lane_mapping_v1_each_lane(lane: Lane) -> None:
    """Each canonical lane maps to a SyncLaneV1."""
    result = CANONICAL_TO_SYNC_V1[lane]
    assert isinstance(result, SyncLaneV1)


# --- Schema integrity tests ---

def test_all_schemas_present() -> None:
    """All expected schemas exist."""
    schemas = list_schemas()
    assert len(schemas) >= 11


@pytest.mark.parametrize("name", list_schemas())
def test_schema_is_valid_json_schema(name: str) -> None:
    """Each schema file is a valid JSON Schema document."""
    schema = load_schema(name)
    assert "$schema" in schema
    assert "$id" in schema


# --- Round-trip serialization tests ---

def test_event_round_trip() -> None:
    """Event model round-trips through JSON."""
    from spec_kitty_events.models import Event
    event = Event(
        event_id="01JEXAMPLE00000000000000A",
        event_type="TestEvent",
        aggregate_id="agg-001",
        timestamp="2026-01-01T00:00:00Z",
        node_id="node-1",
        lamport_clock=1,
        project_uuid="550e8400-e29b-41d4-a716-446655440000",
        correlation_id="01JEXAMPLE00000000000000B",
    )
    data = event.model_dump(mode="json")
    restored = Event.model_validate(data)
    assert restored == event
```

3. Use `pytest.mark.parametrize` with manifest data for data-driven testing.
4. Include non-manifest tests for schema integrity and round-trip serialization.

**Validation**:
- [ ] `pytest --pyargs spec_kitty_events.conformance -v` runs and passes
- [ ] Test output shows individual fixture IDs as test names
- [ ] Failure messages are clear and actionable

### T032: Add coverage omit for conformance directory

**Purpose**: Conformance test code shouldn't inflate the library's own coverage metrics.

**Steps**:
1. Update `pyproject.toml` `[tool.coverage.run]` omit:
   ```toml
   [tool.coverage.run]
   source = ["src/spec_kitty_events"]
   omit = ["*/tests/*", "*/__pycache__/*", "*/conformance/test_*", "*/conformance/conftest.py"]
   ```
2. The conformance `validators.py`, `__init__.py`, and `pytest_helpers.py` SHOULD be covered (they're library code). Only test files and conftest are excluded.

**Validation**:
- [ ] `python3.11 -m pytest --cov` doesn't count `test_pyargs_entrypoint.py` or `conftest.py` as source

### T033: Verify `pytest --pyargs` works end-to-end

**Purpose**: Prove the complete consumer workflow functions.

**Steps**:
1. Run `pip install -e ".[dev,conformance]"` to refresh the install.
2. Run `pytest --pyargs spec_kitty_events.conformance -v`.
3. Verify all tests are collected and pass.
4. Verify test names include fixture IDs from manifest.
5. Verify schema tests and lane mapping tests also run.

**Validation**:
- [ ] `pytest --pyargs spec_kitty_events.conformance` exits 0
- [ ] Tests are collected from the installed package location
- [ ] All manifest-driven tests appear in output with their IDs

## Definition of Done

- [ ] `pytest_helpers.py` with `assert_payload_conforms`, `assert_payload_fails`, `assert_lane_mapping`
- [ ] `conftest.py` with `fixtures_dir`, `manifest`, `fixture_cases` pytest fixtures
- [ ] `test_pyargs_entrypoint.py` with manifest-driven tests, lane mapping tests, schema tests
- [ ] `pytest --pyargs spec_kitty_events.conformance` passes end-to-end
- [ ] Coverage omit excludes conformance test files
- [ ] `mypy --strict` passes on new files
- [ ] Full test suite still passes: `python3.11 -m pytest`

## Risks

- **conftest.py discovery**: pytest may not automatically discover `conftest.py` inside installed packages. If fixtures aren't found, move shared setup into `test_pyargs_entrypoint.py` directly.
- **Manifest loading at collection time**: `_MANIFEST` and `_fixture_params()` load JSON at import time during collection. If fixtures are missing, collection will fail with a clear error (which is desirable).
- **Lane mapping fixture format**: Lane mapping fixtures have a different structure (array of objects) vs event fixtures (single object). The `load_fixtures()` API handles this via the manifest, but `test_pyargs_entrypoint.py` also has dedicated lane mapping tests.

## Reviewer Guidance

- Run `pytest --pyargs spec_kitty_events.conformance -v` and verify output shows meaningful test names.
- Verify a deliberately broken fixture causes a clear test failure.
- Verify lane mapping tests cover all 7 lanes.
- Verify schema integrity tests cover all 11 schemas.
- Verify coverage omit works (conformance test files not in coverage report).
