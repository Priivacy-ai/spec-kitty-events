# Implementation Plan: Connector and Sync Lifecycle Contracts

**Branch**: `codex/wp04-events-connector-sync-contracts` | **Date**: 2026-02-27 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/kitty-specs/012-wp04-events-connector-sync-contracts/spec.md`

## Summary

Add canonical connector lifecycle and sync lifecycle contract families to `spec-kitty-events` with idempotent ingest markers, external reference linking, deterministic reducer transitions, conformance fixtures, and explicit versioning/export notes for downstream `spec-kitty-tracker` and `spec-kitty-saas` consumers.

## Technical Context

**Language/Version**: Python >=3.10, strict typing via mypy
**Primary Dependencies**: pydantic v2, pytest, hypothesis, jsonschema (conformance extra)
**Storage**: N/A (pure event contract package)
**Testing**: pytest unit/integration/property/conformance suites
**Target Platform**: PyPI package consumed by `spec-kitty-tracker` and `spec-kitty-saas`
**Project Type**: Single package (`src/spec_kitty_events/`)
**Current Package Version**: 2.6.0
**Planned Contract Min Version**: 2.7.0 (additive 2.x)

## Current Modules and Touchpoints

Planned source touchpoints in this repository:

- `src/spec_kitty_events/connector.py` (new): Connector lifecycle constants, enums, payloads, reducer, output models.
- `src/spec_kitty_events/sync.py` (new): Sync lifecycle constants, enums, payloads, reducer, output models. Includes `ExternalReferenceLinkedPayload`.
- `src/spec_kitty_events/status.py` (reuse only): deterministic sort/dedup helpers via `status_event_sort_key` and `dedup_events`.
- `src/spec_kitty_events/conformance/validators.py`: register connector and sync event type -> model and schema mappings.
- `src/spec_kitty_events/conformance/loader.py`: add `connector` and `sync` fixture categories.
- `src/spec_kitty_events/conformance/fixtures/manifest.json`: add valid/invalid/replay and reducer-output fixture entries for connector and sync families.
- `src/spec_kitty_events/conformance/fixtures/connector/{valid,invalid,replay}` (new): Connector lifecycle fixture files.
- `src/spec_kitty_events/conformance/fixtures/sync/{valid,invalid,replay}` (new): Sync lifecycle fixture files.
- `src/spec_kitty_events/schemas/generate.py`: include connector and sync payload models in deterministic schema generation list.
- `src/spec_kitty_events/schemas/*.schema.json`: committed generated schemas for connector and sync payloads.
- `src/spec_kitty_events/__init__.py`: public exports for connector and sync constants/models/reducers.

Planned test touchpoints:

- `tests/unit/test_connector.py`
- `tests/unit/test_sync.py`
- `tests/test_connector_reducer.py`
- `tests/test_sync_reducer.py`
- `tests/property/test_connector_determinism.py`
- `tests/property/test_sync_determinism.py`
- `tests/test_connector_conformance.py`
- `tests/test_sync_conformance.py`

## Schema and Versioning Touchpoints

- Add `CONNECTOR_SCHEMA_VERSION = "2.7.0"` in the connector module.
- Add `SYNC_SCHEMA_VERSION = "2.7.0"` in the sync module.
- Add conformance manifest entries for connector and sync fixtures with `min_version: "2.7.0"`.
- Ensure schema generation is deterministic (`sort_keys=True` JSON output in schema generator flow).
- Publish connector and sync API through `__init__.py` export list.
- Version/export notes must call out additive 2.x contract introduction and required consumer pin (`>=2.7.0`).

## Execution Plan

### Phase 1 (WP01): Contract Core -- Models, Constants, Schemas, Validators, Reducers

- Define connector lifecycle event constants, state enum, and frozen payload models with mandatory fields.
- Define sync lifecycle event constants, outcome enum, and frozen payload models with mandatory idempotency fields.
- Define `ExternalReferenceLinkedPayload` with mandatory external/internal binding fields.
- Implement connector lifecycle reducer with deterministic transitions and anomaly recording.
- Implement sync lifecycle reducer with idempotent ingest dedup and cumulative outcome tracking.
- Add unit tests for payload validation, transition correctness, idempotent dedup, and anomaly behavior.
- Wire connector and sync models into schema generation and conformance validator mappings.

### Phase 2 (WP02): Conformance Fixtures, Replay Scenarios, Compatibility Notes, Tests

- Add conformance fixtures (valid, invalid, replay, golden outputs) for connector, sync, and external reference families.
- Register connector and sync fixture categories in conformance loader.
- Add manifest entries with `min_version: "2.7.0"`.
- Add replay determinism tests and property checks for both reducers.
- Add public export/versioning/downstream impact notes.
- Package fixture assets for wheel/sdist distribution.

## Risks

| Risk | Impact | Mitigation |
|---|---|---|
| Naming overlap with existing sync-related concepts (`SyncLaneV1`, `canonical_to_sync_v1`) | Consumer confusion between lane-sync mapping and sync-lifecycle events | Use dedicated `sync` event family prefix and explicit namespace separation in module docs |
| Idempotent dedup complexity for `(delivery_id, source_event_fingerprint)` pairs | False positive dedup if fingerprinting is inconsistent across providers | Define fingerprint as opaque string, push provider-specific hashing to caller, validate non-empty |
| Connector state machine complexity with `reconnected` re-entry | Ambiguous transitions when connectors cycle through degraded/reconnected multiple times | Cap reducer anomaly-free cycles and record anomalies for repeated degraded-reconnected loops |
| Non-deterministic replay output from dual-reducer (connector + sync) | Broken SaaS/runtime projections when replaying mixed streams | Keep strict sort+dedup pipeline per family and commit separate golden replay outputs |
| Versioning drift across fixtures/schema/exports | Partial adoption failures downstream | Gate merge on manifest/schema/export checks and explicit min-version assertions |

## Acceptance Gate

All of the following must pass before the feature is considered complete:

1. `python3.11 -m mypy --strict src/spec_kitty_events/connector.py src/spec_kitty_events/sync.py`
2. `python3.11 -m pytest tests/unit/test_connector.py tests/unit/test_sync.py tests/test_connector_reducer.py tests/test_sync_reducer.py -v`
3. `python3.11 -m pytest tests/property/test_connector_determinism.py tests/property/test_sync_determinism.py -v`
4. `python3.11 -m pytest tests/test_connector_conformance.py tests/test_sync_conformance.py -v`
5. `python3.11 -m pytest --pyargs spec_kitty_events.conformance`
6. `python3.11 -m pytest tests/ -q` (no regressions)
7. Public import smoke check succeeds for all connector and sync exports from `spec_kitty_events`.
