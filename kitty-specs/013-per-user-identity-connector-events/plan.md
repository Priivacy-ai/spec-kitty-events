# Implementation Plan: Per-User Identity in Connector Events

**Branch**: `2.x` | **Date**: 2026-03-05 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `kitty-specs/013-per-user-identity-connector-events/spec.md`

## Summary

Extend the connector lifecycle event contracts to carry per-user identity. Add an optional `user_id` field to all five existing connector payload models, introduce two new event types (`UserConnected`, `UserDisconnected`) with required `user_id`, add a `UserConnectionStatus` model and `user_connections` roster to `ReducedConnectorState`, and bump `CONNECTOR_SCHEMA_VERSION` from `2.7.0` to `2.8.0`. All changes are additive-only with full backward compatibility.

## Technical Context

**Language/Version**: Python 3.10+ (mypy target), 3.11 for tests
**Primary Dependencies**: Pydantic v2 (existing), Hypothesis (property tests)
**Storage**: N/A (pure event contract library)
**Testing**: pytest + Hypothesis, `mypy --strict`, 98%+ coverage
**Target Platform**: Python library (pip installable)
**Project Type**: Single Python package (`src/spec_kitty_events/`)
**Performance Goals**: Deterministic reducer, no performance-critical paths
**Constraints**: All models `ConfigDict(frozen=True)`, additive-only changes, no breaking exports
**Scale/Scope**: ~6 new exports, ~2 modified models, ~100 lines of new code

## Constitution Check

*No constitution file found. Section skipped.*

## Project Structure

### Documentation (this feature)

```
kitty-specs/013-per-user-identity-connector-events/
├── plan.md              # This file
├── research.md          # Phase 0 output (minimal — no unknowns)
├── data-model.md        # Phase 1 output
├── contracts/           # Phase 1 output (JSON schemas)
└── tasks.md             # Phase 2 output (/spec-kitty.tasks)
```

### Source Code (repository root)

```
src/spec_kitty_events/
├── connector.py          # Modified: user_id on payloads, new event types,
│                         #   UserConnectionStatus, reducer roster logic
├── __init__.py           # Modified: re-export new symbols
└── schemas/
    ├── user_connected_payload.schema.json         # New
    ├── user_disconnected_payload.schema.json      # New
    ├── user_connection_status.schema.json         # New
    ├── connector_provisioned_payload.schema.json  # Regenerated (user_id added)
    ├── connector_health_checked_payload.schema.json
    ├── connector_degraded_payload.schema.json
    ├── connector_revoked_payload.schema.json
    └── connector_reconnected_payload.schema.json

tests/
├── unit/
│   └── test_connector.py     # Extended: user_id field tests, new payloads
├── test_connector_reducer.py # Extended: roster tests, backward compat
└── property/
    └── test_connector_determinism.py  # Extended: new event types in pool
```

**Structure Decision**: Single project, existing layout. All changes in `connector.py` with schema regeneration and test extensions.

## Design Decisions

### D1: user_id field placement

`user_id: Optional[str] = None` added to all five existing payload models. `Optional` with `None` default ensures backward compatibility — pre-migration events without `user_id` validate and reduce correctly.

### D2: UserConnected / UserDisconnected are connector-family events

These new event types are added to `CONNECTOR_EVENT_TYPES` frozenset. They share the same reducer (`reduce_connector_events`). Inside the reducer, they update only `user_connections` — they do not participate in binding-level state transitions (`current_state`, `transition_log`).

### D3: UserConnectionStatus is a simple roster entry

```python
class UserConnectionStatus(BaseModel):
    model_config = ConfigDict(frozen=True)
    user_id: str
    state: ConnectorState
    last_event_at: Optional[datetime] = None
```

The roster is `tuple[UserConnectionStatus, ...]` on `ReducedConnectorState`. One entry per distinct `user_id` seen, reflecting only the latest state. No per-user transition logs.

### D4: Reducer roster update logic

During the fold, when a connector event has `user_id` set (whether it's a binding-level event like `ConnectorDegraded` or a user-level event like `UserConnected`):
- Look up or create a mutable roster entry keyed by `user_id`
- Update `state` to the target state of the event
- Update `last_event_at` to the event's `recorded_at` timestamp

`UserDisconnected` maps to `ConnectorState.REVOKED` for roster purposes.
`UserConnected` maps to `ConnectorState.PROVISIONED` for roster purposes.

### D5: Schema version 2.8.0

SemVer minor bump. Additive changes only — new optional field, new event types, new output model field. No breaking changes.

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Existing tests break from schema version change | Low | Low | Single assertion update (`"2.7.0"` → `"2.8.0"`) |
| Reducer determinism broken by roster | Low | High | Property tests with Hypothesis extended to include user events |
| JSON schema drift from regeneration | Low | Medium | CI drift check already exists; regenerate all connector schemas |
