---
work_package_id: WP02
title: Conformance Fixtures, Replay Scenarios, Compatibility Notes, Tests
lane: planned
dependencies:
- WP01
requirement_refs:
- FR-008
- FR-009
- FR-010
---

# Work Package Prompt: WP02 - Conformance Fixtures, Replay Scenarios, Compatibility Notes, Tests

## Objective

Deliver conformance-grade connector and sync lifecycle fixtures and replay scenarios, register schemas and validators, complete export/versioning/downstream-impact documentation for additive 2.x adoption, and package fixture assets for distribution.

## In-Scope Areas

- `src/spec_kitty_events/conformance/validators.py`
- `src/spec_kitty_events/conformance/loader.py`
- `src/spec_kitty_events/conformance/fixtures/manifest.json`
- `src/spec_kitty_events/conformance/fixtures/connector/{valid,invalid,replay}` (new)
- `src/spec_kitty_events/conformance/fixtures/sync/{valid,invalid,replay}` (new)
- `src/spec_kitty_events/schemas/generate.py` and generated schema files
- `src/spec_kitty_events/__init__.py` and package version notes
- `pyproject.toml` package-data configuration
- Conformance and property tests for connector and sync replay safety

## Implementation Instructions

### Fixture Category Registration

1. Register `connector` and `sync` fixture categories in `src/spec_kitty_events/conformance/loader.py`, following the existing pattern for `decisionpoint`.

### Connector Fixtures (FR-008)

2. Add connector fixture directory structure:
   ```
   src/spec_kitty_events/conformance/fixtures/connector/
   ├── valid/
   │   ├── connector-provisioned-github.json
   │   ├── connector-provisioned-jira.json
   │   ├── connector-health-checked-healthy.json
   │   ├── connector-health-checked-degraded.json
   │   ├── connector-degraded-timeout.json
   │   └── connector-reconnected-automatic.json
   ├── invalid/
   │   ├── connector-missing-connector-id.json
   │   ├── connector-missing-endpoint-url.json
   │   ├── connector-invalid-health-status.json
   │   └── connector-missing-revocation-reason.json
   └── replay/
       ├── connector-lifecycle-full.jsonl
       └── connector-lifecycle-full_output.json
   ```

3. Create 6 valid connector fixtures. Each fixture is a complete payload JSON matching the corresponding frozen payload model:
   - `connector-provisioned-github.json`: ConnectorProvisioned for a GitHub connector with all mandatory fields.
   - `connector-provisioned-jira.json`: ConnectorProvisioned for a Jira connector.
   - `connector-health-checked-healthy.json`: ConnectorHealthChecked with `health_status="healthy"`, `latency_ms=42.5`.
   - `connector-health-checked-degraded.json`: ConnectorHealthChecked with `health_status="degraded"`, `latency_ms=3200.0`.
   - `connector-degraded-timeout.json`: ConnectorDegraded with `degradation_reason="connection_timeout"`.
   - `connector-reconnected-automatic.json`: ConnectorReconnected with `previous_state="degraded"`, `reconnect_strategy="automatic"`.

4. Create 4 invalid connector fixtures:
   - `connector-missing-connector-id.json`: ConnectorProvisioned payload missing `connector_id` field.
   - `connector-missing-endpoint-url.json`: ConnectorProvisioned payload missing `endpoint_url` field.
   - `connector-invalid-health-status.json`: ConnectorHealthChecked with `health_status="unknown"` (not in enum).
   - `connector-missing-revocation-reason.json`: ConnectorRevoked payload missing `revocation_reason` field.

5. Create 1 connector replay stream (`connector-lifecycle-full.jsonl`) as a 6-event JSONL file tracing: ConnectorProvisioned -> ConnectorHealthChecked (healthy) -> ConnectorDegraded -> ConnectorReconnected -> ConnectorHealthChecked (healthy) -> ConnectorRevoked. Commit golden reducer output as `connector-lifecycle-full_output.json`.

### Sync Fixtures (FR-008)

6. Add sync fixture directory structure:
   ```
   src/spec_kitty_events/conformance/fixtures/sync/
   ├── valid/
   │   ├── sync-ingest-accepted-batch.json
   │   ├── sync-ingest-accepted-single.json
   │   ├── sync-ingest-rejected-schema-mismatch.json
   │   ├── sync-retry-scheduled-first-attempt.json
   │   ├── sync-dead-lettered-max-retries.json
   │   └── sync-replay-completed-full.json
   ├── invalid/
   │   ├── sync-missing-delivery-id.json
   │   ├── sync-missing-source-fingerprint.json
   │   ├── sync-negative-retry-attempt.json
   │   └── sync-missing-failure-reason.json
   └── replay/
       ├── sync-ingest-lifecycle.jsonl
       └── sync-ingest-lifecycle_output.json
   ```

7. Create 6 valid sync fixtures:
   - `sync-ingest-accepted-batch.json`: SyncIngestAccepted with `ingest_batch_id`, `ingested_count=15`.
   - `sync-ingest-accepted-single.json`: SyncIngestAccepted with `ingested_count=1`.
   - `sync-ingest-rejected-schema-mismatch.json`: SyncIngestRejected with `rejection_reason="payload_schema_mismatch"`.
   - `sync-retry-scheduled-first-attempt.json`: SyncRetryScheduled with `retry_attempt=1`, `max_retries=3`.
   - `sync-dead-lettered-max-retries.json`: SyncDeadLettered with `total_attempts=3`, `failure_reason="max_retries_exceeded"`.
   - `sync-replay-completed-full.json`: SyncReplayCompleted with `replayed_count=42`, `replay_source="dead_letter_queue"`.

8. Create 4 invalid sync fixtures:
   - `sync-missing-delivery-id.json`: SyncIngestAccepted payload missing `delivery_id` field.
   - `sync-missing-source-fingerprint.json`: SyncIngestAccepted payload missing `source_event_fingerprint` field.
   - `sync-negative-retry-attempt.json`: SyncRetryScheduled with `retry_attempt=0` (must be >= 1).
   - `sync-missing-failure-reason.json`: SyncDeadLettered payload missing `failure_reason` field.

9. Create 2 valid external-reference-linked fixtures:
   - `external-ref-linked-github-pr.json`: ExternalReferenceLinked binding a GitHub PR to a mission WP.
   - `external-ref-linked-jira-issue.json`: ExternalReferenceLinked binding a Jira issue to a mission.

10. Create 1 sync replay stream (`sync-ingest-lifecycle.jsonl`) as a 7-event JSONL file tracing: SyncIngestAccepted -> SyncIngestAccepted (different delivery_id) -> SyncIngestRejected -> SyncRetryScheduled -> SyncRetryScheduled (attempt 2) -> SyncDeadLettered -> SyncReplayCompleted. Commit golden reducer output as `sync-ingest-lifecycle_output.json`.

### Mixed Replay Stream (FR-008)

11. Create 1 mixed replay stream (`mixed-connector-sync-lifecycle.jsonl`) under a shared `replay/` directory containing interleaved connector and sync events (at least 10 events). Commit separate golden outputs: `mixed-connector-sync-lifecycle_connector_output.json` and `mixed-connector-sync-lifecycle_sync_output.json`.

### Manifest Entries

12. Add manifest entries for all connector, sync, and external-reference fixtures. Every entry MUST carry `min_version: "2.7.0"`. Follow the existing manifest entry format from decisionpoint fixtures.

### Schema Generation

13. Extend `src/spec_kitty_events/schemas/generate.py` to include connector and sync payload models. Run generation and commit the resulting `*.schema.json` files.

### Public Exports and Versioning

14. Export all connector and sync public API symbols from `src/spec_kitty_events/__init__.py`. Add a versioning/export notes block in the module docstring following the pattern established by the DecisionPoint 2.6.0 block. Update `__all__` with the new symbol names.

15. Add downstream impact notes for:
    - **spec-kitty-tracker**: Pin `spec-kitty-events>=2.7.0`. Import `reduce_connector_events` and `reduce_sync_events` for connector/sync state projection. Use `CONNECTOR_EVENT_TYPES` and `SYNC_EVENT_TYPES` frozen sets for stream filtering.
    - **spec-kitty-saas**: Pin `spec-kitty-events>=2.7.0`. Connector and sync schemas available via `spec_kitty_events.schemas.load_schema()`. Conformance fixtures include `"connector"` and `"sync"` categories for integration test suites.

### Package Data

16. Update `pyproject.toml` package-data globs to include:
    - `conformance/fixtures/connector/valid/*.json`
    - `conformance/fixtures/connector/invalid/*.json`
    - `conformance/fixtures/connector/replay/*.jsonl`
    - `conformance/fixtures/connector/replay/*_output.json`
    - `conformance/fixtures/sync/valid/*.json`
    - `conformance/fixtures/sync/invalid/*.json`
    - `conformance/fixtures/sync/replay/*.jsonl`
    - `conformance/fixtures/sync/replay/*_output.json`

### Tests

17. Add `tests/test_connector_conformance.py` covering:
    - All 6 valid connector fixtures pass conformance validation.
    - All 4 invalid connector fixtures fail conformance validation with expected error categories.
    - Connector replay stream produces output matching committed golden file.

18. Add `tests/test_sync_conformance.py` covering:
    - All 6 valid sync fixtures pass conformance validation.
    - All 4 invalid sync fixtures fail conformance validation with expected error categories.
    - Both valid external-reference-linked fixtures pass validation.
    - Sync replay stream produces output matching committed golden file.

19. Add `tests/property/test_connector_determinism.py` covering:
    - Hypothesis property test: connector reducer output is identical for any permutation of the same event set.
    - Hypothesis property test: duplicate connector events produce identical output to the deduplicated set.

20. Add `tests/property/test_sync_determinism.py` covering:
    - Hypothesis property test: sync reducer output is identical for any permutation of the same event set.
    - Hypothesis property test: duplicate `(delivery_id, source_event_fingerprint)` pairs are idempotently deduplicated.

## Reviewer Checklist

- [ ] Fixture counts and manifest entries meet minimum coverage: 6 valid + 4 invalid connector, 6 valid + 4 invalid sync, 2 external-ref, 3 replay streams.
- [ ] All manifest entries carry `min_version: "2.7.0"`.
- [ ] Invalid fixtures include missing mandatory fields and enum validation failures, not only type errors.
- [ ] Replay streams validate and match committed golden reducer outputs exactly.
- [ ] Connector and sync schemas are generated deterministically and checked in.
- [ ] Public exports and downstream adoption notes are complete and additive-only.
- [ ] Package-data configuration includes all connector and sync fixture assets.
- [ ] No naming collision between sync lifecycle events and existing `SyncLaneV1` mapping concepts.

## Acceptance Checks

- `python3.11 -m pytest tests/test_connector_conformance.py tests/test_sync_conformance.py -v`
- `python3.11 -m pytest tests/property/test_connector_determinism.py tests/property/test_sync_determinism.py -v`
- `python3.11 -m pytest --pyargs spec_kitty_events.conformance`
- `python3.11 -m pytest tests/ -q`

## Dependencies

- Depends on WP01.

## PR Requirements

- Include fixture inventory table (valid/invalid/replay/reducer-output) for both connector and sync families in PR description.
- Cite FR coverage explicitly: FR-008, FR-009, FR-010.
- Include downstream migration note block: required version pin, exported symbols, and expected consumer code touchpoints for both spec-kitty-tracker and spec-kitty-saas.
