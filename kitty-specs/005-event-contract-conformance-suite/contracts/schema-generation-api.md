# Schema Generation API Contract

**Feature**: 005-event-contract-conformance-suite
**Date**: 2026-02-12

## Overview

JSON Schema files are generated from Pydantic v2 models at build time and committed to the repository. They serve as the machine-readable contract for cross-language consumers and as the basis for the secondary conformance validation layer.

## Schema File Layout

```
src/spec_kitty_events/schemas/
├── __init__.py                              # Schema loading helpers
├── generate.py                              # Build-time generation script
├── event.schema.json                        # Event model
├── status_transition_payload.schema.json    # StatusTransitionPayload
├── gate_passed_payload.schema.json          # GatePassedPayload
├── gate_failed_payload.schema.json          # GateFailedPayload
├── mission_started_payload.schema.json      # MissionStartedPayload
├── mission_completed_payload.schema.json    # MissionCompletedPayload
├── mission_cancelled_payload.schema.json    # MissionCancelledPayload
├── phase_entered_payload.schema.json        # PhaseEnteredPayload
├── review_rollback_payload.schema.json      # ReviewRollbackPayload
├── lane.schema.json                         # Lane enum
└── sync_lane_v1.schema.json                 # SyncLaneV1 enum
```

## Generation Script

```bash
# Build-time generation (run from repo root):
python -m spec_kitty_events.schemas.generate

# CI drift check:
python -m spec_kitty_events.schemas.generate --check
# Exit code 0: schemas match models
# Exit code 1: drift detected (prints diff)
```

### Generation Rules

1. Use `Model.model_json_schema(mode="serialization")` for each model.
2. Add `$schema` key: `"https://json-schema.org/draft/2020-12/schema"`.
3. Add `$id` key: `"https://spec-kitty.dev/schemas/{name}.json"`.
4. Write with `json.dumps(schema, indent=2, sort_keys=True) + "\n"` for deterministic output.
5. One file per model — self-contained with own `$defs`.

### Enum Schema Generation

For `Lane` and `SyncLaneV1` (which are `str, Enum` and cannot call `model_json_schema()`):

```python
# Use TypeAdapter for enum schema generation:
from pydantic import TypeAdapter
schema = TypeAdapter(Lane).json_schema(mode="serialization")
```

## Schema Loading API

```python
# In src/spec_kitty_events/schemas/__init__.py:

def load_schema(name: str) -> dict[str, Any]:
    """Load a committed JSON Schema by model name.

    Args:
        name: Schema name without extension (e.g., "event", "lane", "sync_lane_v1").

    Returns:
        Parsed JSON Schema dict.

    Raises:
        FileNotFoundError: If no schema exists for the given name.
    """

def schema_path(name: str) -> Path:
    """Return the filesystem path to a committed schema file.

    Args:
        name: Schema name without extension.

    Returns:
        Path to the .schema.json file.
    """

def list_schemas() -> list[str]:
    """List all available schema names."""
```

## CI Drift Check

The drift check is a required CI step in this repository:

```yaml
- name: Check schema drift
  run: python -m spec_kitty_events.schemas.generate --check
```

Behavior:
1. Regenerate all schemas in memory from current Pydantic models.
2. Compare against committed `.schema.json` files byte-for-byte.
3. If any differ: print the diff, exit with code 1.
4. If all match: print "All schemas up to date", exit with code 0.
5. If a model exists without a committed schema: fail with "Missing schema for {model}".
6. If a committed schema has no corresponding model: fail with "Orphaned schema {file}".

## Package Data

Schemas must be bundled as package data so they're available after `pip install`:

```toml
# In pyproject.toml:
[tool.setuptools.package-data]
spec_kitty_events = ["schemas/*.json", "conformance/fixtures/**/*.json"]
```
