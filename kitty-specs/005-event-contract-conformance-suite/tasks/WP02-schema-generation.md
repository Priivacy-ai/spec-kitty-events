---
work_package_id: WP02
title: Schema Subpackage and Generation Script
lane: "doing"
dependencies: [WP01]
base_branch: 005-event-contract-conformance-suite-WP01
base_commit: 1c16bd2a704cc44184e768fda496a645fe9356b1
created_at: '2026-02-12T10:25:26.669407+00:00'
subtasks: [T007, T008, T009, T010, T011, T012, T013]
shell_pid: "76117"
agent: "codex"
review_status: "has_feedback"
reviewed_by: "Robert Douglass"
history:
- date: '2026-02-12'
  action: created
  by: spec-kitty.tasks
---

# WP02 — Schema Subpackage and Generation Script

## Implementation Command

```bash
spec-kitty implement WP02 --base WP01
```

## Objective

Create the `src/spec_kitty_events/schemas/` subpackage with a loader API, build-time generation script, CI drift detection, and all 11 JSON Schema files generated from the existing Pydantic v2 models.

## Context

Per research (R1), Pydantic v2 generates JSON Schema Draft 2020-12. Each model produces a self-contained schema with its own `$defs`. The generation script must:
- Use `model_json_schema(mode="serialization")` for Pydantic models
- Use `TypeAdapter(EnumClass).json_schema(mode="serialization")` for `Lane` and `SyncLaneV1` enums
- Add `$schema` and `$id` keys manually
- Use `json.dumps(schema, indent=2, sort_keys=True) + "\n"` for deterministic output

**Key files to create**:
- `src/spec_kitty_events/schemas/__init__.py`
- `src/spec_kitty_events/schemas/generate.py`
- 11 `.schema.json` files
- `tests/unit/test_schemas.py`
- `tests/integration/test_schema_drift.py`

**Key files to modify**:
- `pyproject.toml` — package-data and optional dependencies

## Subtask Guidance

### T007: Create `schemas/__init__.py` with loader API

**Purpose**: Provide a public API for loading committed JSON Schema files by name.

**Steps**:
1. Create `src/spec_kitty_events/schemas/__init__.py`.
2. Implement three functions:

```python
"""JSON Schema artifacts for spec-kitty-events models."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_SCHEMA_DIR = Path(__file__).parent


def schema_path(name: str) -> Path:
    """Return filesystem path to a committed schema file."""
    path = _SCHEMA_DIR / f"{name}.schema.json"
    if not path.exists():
        raise FileNotFoundError(f"No schema found for '{name}'. Available: {list_schemas()}")
    return path


def load_schema(name: str) -> dict[str, Any]:
    """Load a committed JSON Schema by model name."""
    return json.loads(schema_path(name).read_text(encoding="utf-8"))  # type: ignore[no-any-return]


def list_schemas() -> list[str]:
    """List all available schema names."""
    return sorted(
        p.stem.replace(".schema", "")
        for p in _SCHEMA_DIR.glob("*.schema.json")
    )
```

3. Ensure all functions have proper type annotations for `mypy --strict`.

**Validation**:
- [ ] `load_schema("event")` returns a dict after schemas are generated
- [ ] `schema_path("event")` returns a `Path` to `event.schema.json`
- [ ] `list_schemas()` returns a sorted list of schema names
- [ ] `load_schema("nonexistent")` raises `FileNotFoundError`

### T008: Create `schemas/generate.py` with model registry

**Purpose**: Build-time script that generates JSON Schema files from Pydantic models.

**Steps**:
1. Create `src/spec_kitty_events/schemas/generate.py`.
2. Define a model registry mapping schema names to model classes:
   ```python
   from pydantic import TypeAdapter
   from spec_kitty_events.models import Event
   from spec_kitty_events.status import (
       Lane, SyncLaneV1, StatusTransitionPayload,
   )
   from spec_kitty_events.gates import GatePassedPayload, GateFailedPayload
   from spec_kitty_events.lifecycle import (
       MissionStartedPayload, MissionCompletedPayload,
       MissionCancelledPayload, PhaseEnteredPayload,
       ReviewRollbackPayload,
   )

   # Models that have model_json_schema()
   PYDANTIC_MODELS: dict[str, type] = {
       "event": Event,
       "status_transition_payload": StatusTransitionPayload,
       "gate_passed_payload": GatePassedPayload,
       "gate_failed_payload": GateFailedPayload,
       "mission_started_payload": MissionStartedPayload,
       "mission_completed_payload": MissionCompletedPayload,
       "mission_cancelled_payload": MissionCancelledPayload,
       "phase_entered_payload": PhaseEnteredPayload,
       "review_rollback_payload": ReviewRollbackPayload,
   }

   # Enums that use TypeAdapter
   ENUM_TYPES: dict[str, type] = {
       "lane": Lane,
       "sync_lane_v1": SyncLaneV1,
   }
   ```
3. Implement `generate_schema(name, model_or_enum)` that:
   - For Pydantic models: calls `model.model_json_schema(mode="serialization")`
   - For enums: calls `TypeAdapter(enum_cls).json_schema(mode="serialization")`
   - Adds `$schema` and `$id` keys
   - Returns the schema dict
4. Implement `generate_all()` that generates all schemas and writes to disk.
5. Use `json.dumps(schema, indent=2, sort_keys=True) + "\n"` for deterministic output.

**Validation**:
- [ ] `python -m spec_kitty_events.schemas.generate` produces 11 `.schema.json` files
- [ ] Each file is valid JSON
- [ ] Each file has `$schema` and `$id` keys
- [ ] Output is deterministic (running twice produces identical files)

### T009: Implement `--check` mode for CI drift detection

**Purpose**: CI can verify committed schemas match current models without modifying files.

**Steps**:
1. Add `argparse` to `generate.py` with a `--check` flag.
2. In check mode:
   - Generate all schemas in memory (don't write to disk)
   - Compare against committed `.schema.json` files byte-for-byte
   - If any differ: print the file name and a diff, exit with code 1
   - If any model lacks a committed schema: print "Missing schema for {name}", exit 1
   - If any committed schema has no model: print "Orphaned schema {file}", exit 1
   - If all match: print "All schemas up to date", exit 0
3. Add `if __name__ == "__main__":` block for `python -m` invocation.

**Validation**:
- [ ] `python -m spec_kitty_events.schemas.generate --check` exits 0 when schemas are current
- [ ] After modifying a model, `--check` exits 1 with meaningful output

### T010: Generate all 11 `.schema.json` files

**Purpose**: Produce the committed schema artifacts.

**Steps**:
1. Run the generation script to produce all 11 files.
2. Verify each file:
   - `event.schema.json` — has properties for all Event fields
   - `status_transition_payload.schema.json` — includes Lane enum in `$defs`
   - `gate_passed_payload.schema.json` — conclusion is `const: "success"`
   - `gate_failed_payload.schema.json` — conclusion is enum of 4 values
   - 5 lifecycle payload schemas
   - `lane.schema.json` — enum of 7 string values
   - `sync_lane_v1.schema.json` — enum of 4 string values
3. All files committed to `src/spec_kitty_events/schemas/`.

**Validation**:
- [ ] 11 `.schema.json` files exist in `src/spec_kitty_events/schemas/`
- [ ] Each is valid JSON Schema Draft 2020-12
- [ ] `python -m spec_kitty_events.schemas.generate --check` passes

### T011: Update `pyproject.toml`

**Purpose**: Bundle schema files as package data and add `[conformance]` optional extra.

**Steps**:
1. Update `[tool.setuptools.package-data]`:
   ```toml
   [tool.setuptools.package-data]
   spec_kitty_events = ["py.typed", "schemas/*.json", "conformance/fixtures/**/*.json"]
   ```
2. Add `[conformance]` optional dependency:
   ```toml
   [project.optional-dependencies]
   dev = [
       "pytest>=7.0.0",
       "pytest-cov>=4.0.0",
       "hypothesis>=6.0.0",
       "mypy>=1.0.0",
   ]
   conformance = [
       "jsonschema>=4.21.0,<5.0.0",
   ]
   ```
3. After changes, run `pip install -e ".[dev,conformance]"` to verify install.

**Validation**:
- [ ] `pip install -e ".[dev,conformance]"` succeeds
- [ ] Schema files are discoverable after install (test with `load_schema("event")`)
- [ ] `import jsonschema` works after installing with `[conformance]`

### T012: Unit tests for schema loader API

**Purpose**: Test the `schemas/__init__.py` loader functions.

**Steps**:
1. Create `tests/unit/test_schemas.py`.
2. Test cases:
   - `test_list_schemas_returns_all_names`: Assert 11 schema names returned.
   - `test_load_schema_returns_dict`: Load `"event"` schema, assert it's a dict.
   - `test_load_schema_has_schema_key`: Assert `$schema` key is present.
   - `test_load_schema_has_id_key`: Assert `$id` key is present.
   - `test_load_schema_nonexistent_raises`: Assert `FileNotFoundError` for bad name.
   - `test_schema_path_returns_path`: Assert result is a `Path` and file exists.
   - `test_all_schemas_are_valid_json`: Load each schema, verify it parses as JSON.

**Validation**:
- [ ] All tests pass: `python3.11 -m pytest tests/unit/test_schemas.py -v`

### T013: Integration test for schema drift detection

**Purpose**: Test the `--check` mode end-to-end.

**Steps**:
1. Create `tests/integration/test_schema_drift.py`.
2. Test cases:
   - `test_schema_drift_check_passes`: Run `generate --check` via subprocess, assert exit code 0.
   - `test_schema_drift_check_detects_modification`: Temporarily modify a schema file, run `--check`, assert exit code 1, restore file.
3. Use `subprocess.run` to invoke `python -m spec_kitty_events.schemas.generate --check`.

**Validation**:
- [ ] Both integration tests pass: `python3.11 -m pytest tests/integration/test_schema_drift.py -v`

## Definition of Done

- [ ] `src/spec_kitty_events/schemas/` subpackage exists with `__init__.py` and `generate.py`
- [ ] 11 `.schema.json` files are generated and committed
- [ ] `python -m spec_kitty_events.schemas.generate --check` exits 0
- [ ] `pyproject.toml` has package-data for `.json` files and `[conformance]` extra
- [ ] Schema loader API works: `load_schema()`, `schema_path()`, `list_schemas()`
- [ ] Unit and integration tests pass
- [ ] `mypy --strict` passes on new files
- [ ] Full test suite still passes: `python3.11 -m pytest`

## Risks

- **Enum schema generation**: `Lane` and `SyncLaneV1` are `(str, Enum)`, not Pydantic models. Use `TypeAdapter(Lane).json_schema(mode="serialization")` instead of `model_json_schema()`.
- **Pydantic schema output stability**: The exact output of `model_json_schema()` may vary between Pydantic minor versions. Pin `pydantic>=2.0.0,<3.0.0` and commit the generated files for stability.
- **`sort_keys=True` determinism**: Ensure all dict comparisons in `--check` mode use the same serialization settings.

## Reviewer Guidance

- Verify all 11 expected schema files are present and non-empty.
- Spot-check at least one schema file for correct structure (`$schema`, `$id`, `properties`, `required`).
- Verify `--check` mode works by modifying one schema and confirming it catches the diff.
- Verify `pyproject.toml` changes don't break the existing dev install.

## Activity Log

- 2026-02-12T10:25:27Z – claude-opus – shell_pid=64094 – lane=doing – Assigned agent via workflow command
- 2026-02-12T10:31:23Z – claude-opus – shell_pid=64094 – lane=for_review – Ready for review: schemas/ subpackage with loader API, generate.py with --check mode, 11 JSON schemas, unit+integration tests. 449 tests pass, mypy clean.
- 2026-02-12T10:31:29Z – codex – shell_pid=71572 – lane=doing – Started review via workflow command
- 2026-02-12T10:33:24Z – codex – shell_pid=71572 – lane=planned – Moved to planned
- 2026-02-12T10:33:51Z – claude-opus – shell_pid=73719 – lane=doing – Started implementation via workflow command
- 2026-02-12T10:35:02Z – claude-opus – shell_pid=73719 – lane=for_review – Fixed orphan detection per Codex review. 450 tests pass, mypy clean. --check now detects orphaned schema files.
- 2026-02-12T10:35:08Z – codex – shell_pid=76117 – lane=doing – Started review via workflow command
