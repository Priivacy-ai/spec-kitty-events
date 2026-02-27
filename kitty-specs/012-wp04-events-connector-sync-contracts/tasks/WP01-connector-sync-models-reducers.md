---
work_package_id: WP01
title: Connector and Sync Models, Constants, Schemas, Validators, Reducers
lane: "doing"
dependencies: []
base_branch: codex/wp04-events-connector-sync-contracts
base_commit: b208aad4aaa4fdce08c1fdca1681134b54331d6c
created_at: '2026-02-27T12:21:46.457708+00:00'
agent: "codex"
shell_pid: "54810"
review_status: has_feedback
reviewed_by: Robert Douglass
requirement_refs:
- FR-001
- FR-002
- FR-003
- FR-004
- FR-005
- FR-006
- FR-007
review_feedback_file: /private/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-review-feedback-WP01.md
---

# Work Package Prompt: WP01 - Connector and Sync Models, Constants, Schemas, Validators, Reducers

## Objective

Create the canonical connector lifecycle and sync lifecycle contract core in the events package: constants, frozen payload models with mandatory fields and idempotent ingest markers, external reference linking model, deterministic reducers for both families, and schema/validator wiring.

## In-Scope Areas

- `src/spec_kitty_events/connector.py` (new module)
- `src/spec_kitty_events/sync.py` (new module)
- `src/spec_kitty_events/schemas/generate.py` (add connector and sync models to generation list)
- `src/spec_kitty_events/conformance/validators.py` (register connector and sync event type -> model mappings)
- Deterministic reducer behavior using `status_event_sort_key` and `dedup_events`
- Unit and reducer tests for both lifecycle families

## Implementation Instructions

### Connector Lifecycle Module (`connector.py`)

1. Add connector lifecycle constants and event family set:
   - `CONNECTOR_PROVISIONED = "ConnectorProvisioned"`
   - `CONNECTOR_HEALTH_CHECKED = "ConnectorHealthChecked"`
   - `CONNECTOR_DEGRADED = "ConnectorDegraded"`
   - `CONNECTOR_REVOKED = "ConnectorRevoked"`
   - `CONNECTOR_RECONNECTED = "ConnectorReconnected"`
   - `CONNECTOR_EVENT_TYPES = frozenset({...})` containing exactly those five types
   - `CONNECTOR_SCHEMA_VERSION = "2.7.0"`

2. Add connector lifecycle enums:
   - `ConnectorState` with values: `provisioned`, `healthy`, `degraded`, `revoked`, `reconnected`
   - `HealthStatus` with values: `healthy`, `degraded`, `unreachable`
   - `ReconnectStrategy` with values: `automatic`, `manual`, `backoff`

3. Implement frozen payload models for each connector lifecycle event. All models share mandatory base fields: `connector_id` (str), `connector_type` (str), `provider` (str), `mission_id` (str), `project_uuid` (UUID), `actor_id` (str), `actor_type` (str, one of "human", "service", "system"), `endpoint_url` (AnyHttpUrl), `recorded_at` (datetime). Event-specific additional fields:
   - `ConnectorProvisionedPayload`: `credentials_ref` (str), `config_hash` (str)
   - `ConnectorHealthCheckedPayload`: `health_status` (HealthStatus), `latency_ms` (float, >= 0)
   - `ConnectorDegradedPayload`: `degradation_reason` (str), `last_healthy_at` (datetime)
   - `ConnectorRevokedPayload`: `revocation_reason` (str)
   - `ConnectorReconnectedPayload`: `previous_state` (ConnectorState), `reconnect_strategy` (ReconnectStrategy)

4. Implement `reduce_connector_events(events)` with deterministic pipeline:
   - Sort using `status_event_sort_key`, dedup using `dedup_events`, filter to `CONNECTOR_EVENT_TYPES`, fold transitions, freeze output.
   - Allowed transitions: `None -> provisioned`, `provisioned -> healthy|degraded|revoked`, `healthy -> degraded|revoked`, `degraded -> healthy|revoked|reconnected`, `revoked -> reconnected`, `reconnected -> healthy|degraded|revoked`.
   - Record `ConnectorAnomaly` entries for invalid transitions, unknown event types within the family, and malformed payloads without crashing reduction.
   - Output: `ReducedConnectorState` with fields for `connector_id`, `current_state`, `provider`, `last_health_check`, `anomalies`, `event_count`, `transition_log`.

### Sync Lifecycle Module (`sync.py`)

5. Add sync lifecycle constants and event family set:
   - `SYNC_INGEST_ACCEPTED = "SyncIngestAccepted"`
   - `SYNC_INGEST_REJECTED = "SyncIngestRejected"`
   - `SYNC_RETRY_SCHEDULED = "SyncRetryScheduled"`
   - `SYNC_DEAD_LETTERED = "SyncDeadLettered"`
   - `SYNC_REPLAY_COMPLETED = "SyncReplayCompleted"`
   - `SYNC_EVENT_TYPES = frozenset({...})` containing exactly those five types
   - `SYNC_SCHEMA_VERSION = "2.7.0"`

6. Add sync lifecycle enums:
   - `SyncOutcome` with values: `accepted`, `rejected`, `retry_scheduled`, `dead_lettered`, `replay_completed`

7. Implement frozen payload models for each sync lifecycle event. All models share mandatory idempotency base fields: `delivery_id` (str), `source_event_fingerprint` (str), `connector_id` (str), `mission_id` (str), `recorded_at` (datetime). Event-specific additional fields:
   - `SyncIngestAcceptedPayload`: `ingest_batch_id` (str), `ingested_count` (int, > 0)
   - `SyncIngestRejectedPayload`: `rejection_reason` (str), `rejected_payload_ref` (str)
   - `SyncRetryScheduledPayload`: `retry_attempt` (int, >= 1), `max_retries` (int, >= 1), `next_retry_at` (datetime)
   - `SyncDeadLetteredPayload`: `failure_reason` (str), `total_attempts` (int, >= 1), `dead_letter_ref` (str)
   - `SyncReplayCompletedPayload`: `replay_id` (str), `replayed_count` (int, >= 0), `replay_source` (str)

8. Implement `ExternalReferenceLinkedPayload` frozen model with fields: `link_id` (str), `connector_id` (str), `external_provider` (str), `external_ref_type` (str), `external_ref_id` (str), `external_ref_url` (AnyHttpUrl), `internal_aggregate_type` (str), `internal_aggregate_id` (str), `mission_id` (str), `linked_by` (str), `recorded_at` (datetime). Add constant `EXTERNAL_REFERENCE_LINKED = "ExternalReferenceLinked"`.

9. Implement `reduce_sync_events(events)` with deterministic pipeline:
   - Sort using `status_event_sort_key`, dedup using `dedup_events`, filter to `SYNC_EVENT_TYPES`, fold outcomes.
   - Implement idempotent ingest tracking: deduplicate on `(delivery_id, source_event_fingerprint)` pairs. If a pair is seen more than once, skip the duplicate and record a `SyncAnomaly`.
   - Track cumulative counts: `accepted_count`, `rejected_count`, `retry_count`, `dead_letter_count`, `replay_count`.
   - Maintain an ordered `outcome_log` of `(event_id, outcome, delivery_id)` tuples.
   - Output: `ReducedSyncState` with fields for `connector_id`, `outcome_counts`, `outcome_log`, `seen_delivery_pairs`, `anomalies`, `event_count`.

### Wiring

10. Add connector and sync payload models to `src/spec_kitty_events/schemas/generate.py` schema generation list (following the existing pattern for `decisionpoint` models).

11. Register connector and sync event type -> model mappings in `src/spec_kitty_events/conformance/validators.py` (following the existing pattern for `decisionpoint` mappings).

### Tests

12. Add `tests/unit/test_connector.py` covering:
    - All five payload models validate with correct required fields.
    - Payload models reject missing mandatory fields.
    - ConnectorState and HealthStatus enums have expected members.
    - CONNECTOR_EVENT_TYPES contains exactly 5 members.

13. Add `tests/unit/test_sync.py` covering:
    - All five sync payload models validate with correct required fields plus idempotency fields.
    - ExternalReferenceLinkedPayload validates with all required fields.
    - Payload models reject missing mandatory fields.
    - SyncOutcome enum has expected members.
    - SYNC_EVENT_TYPES contains exactly 5 members.

14. Add `tests/test_connector_reducer.py` covering:
    - Happy-path lifecycle: provisioned -> healthy -> degraded -> reconnected -> healthy.
    - Revocation path: provisioned -> revoked -> reconnected.
    - Invalid transition recording (anomaly, no crash).
    - Duplicate event dedup behavior.
    - Empty event stream produces empty reduced state.

15. Add `tests/test_sync_reducer.py` covering:
    - Happy-path ingest: accepted, accepted (different delivery_id), rejected.
    - Idempotent dedup: same `(delivery_id, source_event_fingerprint)` pair produces anomaly on second occurrence.
    - Retry -> dead-letter sequence.
    - Replay completion tracking.
    - Cumulative count correctness.
    - Empty event stream produces empty reduced state.

## Reviewer Checklist

- [ ] Event names and constants exactly match the spec (FR-001 through FR-005).
- [ ] All mandatory fields are present and validated on every payload model.
- [ ] Idempotent ingest markers (`delivery_id`, `source_event_fingerprint`) are mandatory on all sync payloads.
- [ ] Connector reducer transition rules match the allowed transition table in FR-006.
- [ ] Sync reducer idempotent dedup on `(delivery_id, source_event_fingerprint)` is correctly implemented per FR-007.
- [ ] ExternalReferenceLinkedPayload has all required fields per FR-005.
- [ ] Reducer outputs are deterministic for reordered input and deduped duplicates.
- [ ] Schema generation and conformance validator wiring are complete.
- [ ] No unrelated modules or legacy families are modified unnecessarily.

## Acceptance Checks

- `python3.11 -m mypy --strict src/spec_kitty_events/connector.py src/spec_kitty_events/sync.py`
- `python3.11 -m pytest tests/unit/test_connector.py tests/unit/test_sync.py tests/test_connector_reducer.py tests/test_sync_reducer.py -v`

## Dependencies

- None.

## PR Requirements

- Include a contract summary listing all event names, required payload fields, transition rules, and idempotency invariants.
- Cite FR coverage explicitly: FR-001, FR-002, FR-003, FR-004, FR-005, FR-006, FR-007.
- Include test evidence for connector transitions, sync idempotent dedup, and deterministic reduction.

## Review Feedback

**Reviewed by**: Robert Douglass
**Status**: ❌ Changes Requested
**Date**: 2026-02-27
**Feedback file**: `/private/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-review-feedback-WP01.md`

# WP01 Review Feedback (Codex)

## Finding 1 (P1): Commit generated JSON schemas for new 2.7.0 payloads
- Evidence: `src/spec_kitty_events/schemas/generate.py` registers connector/sync payloads (`connector_*`, `sync_*`, `external_reference_linked`) but corresponding `*.schema.json` artifacts were not committed.
- Impact: `python -m spec_kitty_events.schemas.generate --check` fails; strict conformance validation for these events cannot load schemas.
- Required change:
  - Generate and commit all new schema artifacts for connector/sync payloads.
  - Verify `list_schemas()`/`load_schema()` can resolve each newly mapped schema.

## Finding 2 (P1): Package metadata version mismatch
- Evidence: `src/spec_kitty_events/__init__.py` sets `__version__ = "2.7.0"` while `pyproject.toml` still reports `version = "2.6.0"`.
- Impact: runtime/package metadata divergence; placeholder/version consistency tests fail.
- Required change:
  - Update `pyproject.toml` version to `2.7.0` so runtime and package metadata align.

## Acceptance checks for re-review
- `python3.11 -m mypy --strict src/spec_kitty_events/connector.py src/spec_kitty_events/sync.py`
- `python3.11 -m pytest tests/unit/test_connector.py tests/unit/test_sync.py tests/test_connector_reducer.py tests/test_sync_reducer.py -v`
- `python3.11 -m pytest tests/ -q`
- `python3.11 -m spec_kitty_events.schemas.generate --check`


## Activity Log

- 2026-02-27T12:21:46Z – coordinator – shell_pid=54810 – lane=doing – Assigned agent via workflow command
- 2026-02-27T12:33:08Z – coordinator – shell_pid=54810 – lane=for_review – Ready for review: connector.py (5 event types, 3 enums, 5 payload models, reducer with FR-006 transitions), sync.py (5 event types, 5 payload models with idempotency fields, ExternalReferenceLinkedPayload, reducer with FR-007 dedup), schema/validator wiring, 112 tests pass, mypy --strict clean
- 2026-02-27T12:33:39Z – codex – shell_pid=54810 – lane=doing – Started review via workflow command
- 2026-02-27T12:38:18Z – codex – shell_pid=54810 – lane=planned – Moved to planned
- 2026-02-27T12:38:30Z – coordinator – shell_pid=54810 – lane=doing – Started implementation via workflow command
- 2026-02-27T12:42:34Z – coordinator – shell_pid=54810 – lane=for_review – Ready for re-review: 2.7.0 version parity fixed, connector/sync schemas committed, full suite 1390 passing, schema --check green
- 2026-02-27T12:42:48Z – codex – shell_pid=54810 – lane=doing – Started review via workflow command
