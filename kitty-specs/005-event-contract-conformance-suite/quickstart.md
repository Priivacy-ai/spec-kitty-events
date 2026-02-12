# Quickstart: Event Contract Conformance Suite

**Feature**: 005-event-contract-conformance-suite
**Date**: 2026-02-12

## For Package Developers (spec-kitty-events)

### Setup

```bash
pip install -e ".[dev,conformance]"
```

### Adding/Modifying a Model

1. Edit the Pydantic model in `src/spec_kitty_events/`.
2. Regenerate schemas: `python -m spec_kitty_events.schemas.generate`
3. Review the diff in `src/spec_kitty_events/schemas/*.schema.json`.
4. Update fixtures if needed in `src/spec_kitty_events/conformance/fixtures/`.
5. Run tests: `python3.11 -m pytest`
6. Run conformance: `python3.11 -m pytest --pyargs spec_kitty_events.conformance`
7. Commit both model changes and schema files together.

### CI Checks

- `python -m spec_kitty_events.schemas.generate --check` — fails if committed schemas diverge from models.
- `python3.11 -m pytest --pyargs spec_kitty_events.conformance` — full conformance suite.

## For Consumer Developers (spec-kitty CLI / spec-kitty-saas)

### Installation

```bash
# Core models + mapping API (no optional deps):
pip install "spec-kitty-events>=2.0.0,<3.0.0"

# With conformance suite (adds jsonschema):
pip install "spec-kitty-events[conformance]>=2.0.0,<3.0.0"
```

### Using the Lane Mapping

```python
from spec_kitty_events import Lane, SyncLaneV1, canonical_to_sync_v1

# Convert canonical lane to sync lane
sync = canonical_to_sync_v1(Lane.BLOCKED)
assert sync == SyncLaneV1.DOING

# Use in payload construction
status_value = sync.value  # "doing"
```

### Validating Your Payloads

```python
from spec_kitty_events.conformance import validate_event

result = validate_event(
    payload=my_event_dict,
    event_type="WPStatusChanged",
    strict=False,  # True in CI to require JSON Schema check
)

if not result.valid:
    for v in result.model_violations:
        print(f"Model: {v.field} — {v.message}")
    for v in result.schema_violations:
        print(f"Schema: {v.json_path} — {v.message}")
```

### Running Conformance in CI

```yaml
# Add to your CI pipeline:
- name: Install spec-kitty-events with conformance
  run: pip install "spec-kitty-events[conformance]>=2.0.0,<3.0.0"

- name: Run upstream conformance suite
  run: pytest --pyargs spec_kitty_events.conformance -v
```

### Migration from 0.4.x to 2.0.0

1. Update dependency: `spec-kitty-events>=2.0.0,<3.0.0`
2. Replace hardcoded lane mappings with `canonical_to_sync_v1()`.
3. Replace local status enum with `SyncLaneV1` import.
4. Add conformance CI step.
5. See `CHANGELOG.md` for full migration notes and compatibility table.
