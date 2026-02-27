# Feature Specification: Connector and Sync Lifecycle Contracts

**Feature Branch**: `codex/wp04-events-connector-sync-contracts`
**Created**: 2026-02-27
**Status**: Draft
**Input**: Program WP04 objective for canonical connector and sync lifecycle event contracts
**Requirement Reference**: FR-004

## Problem

Spec Kitty 2.x provides event contracts for missions, work packages, collaboration, glossary, dossier, audit, and decision-point lifecycles, but has no canonical contract family for external connector and sync lifecycle management. Consumers that integrate with external services (GitHub, Jira, Slack, CI providers) lack a deterministic event vocabulary for connector provisioning (connect, health-check, revoke, reconnect), sync ingest operations (idempotent ingest markers, retry, dead-letter, replay outcomes), and external reference linking. Without these contracts, runtime and SaaS consumers implement ad-hoc connector state tracking with inconsistent semantics, no replay safety, and no conformance coverage.

## Goals

- Define one canonical connector lifecycle event family covering `provisioned`, `healthy`, `degraded`, `revoked`, and `reconnected` states.
- Define one canonical sync lifecycle event family covering `ingest_accepted`, `ingest_rejected`, `retry_scheduled`, `dead_lettered`, and `replay_completed` outcomes.
- Provide external reference linking contracts that bind connector-scoped external identifiers (e.g., GitHub PR number, Jira issue key) to internal mission/WP aggregates.
- Enforce idempotent ingest markers (delivery_id + source_event_fingerprint dedup) in sync payload models.
- Guarantee deterministic and replay-safe reduction behavior for both connector and sync event families.
- Document downstream compatibility and adoption steps for `spec-kitty` runtime (spec-kitty-tracker) and `spec-kitty-saas`.

## Non-goals

- Implement actual connector integrations or HTTP/webhook transport layers.
- Build SaaS UI screens for connector management dashboards.
- Implement retry/dead-letter queue infrastructure or message broker bindings.
- Add 1.x compatibility behavior or legacy fallbacks.
- Define provider-specific payload schemas (GitHub-specific, Jira-specific, etc.).

## Locked Constraints

- Connector lifecycle transitions must be deterministic and replay-safe using existing sort/dedup pipeline (`status_event_sort_key`, `dedup_events`).
- Idempotent ingest markers (`delivery_id`, `source_event_fingerprint`) are mandatory on every sync ingest payload.
- External reference linking payloads must carry both the external identifier and the internal aggregate reference.
- Contracts remain additive in 2.x with deterministic JSON schema output.
- No breaking changes to existing event families or public exports.

## Scope

### In scope

- Event constants, enums, and payload models for connector lifecycle events.
- Event constants, enums, and payload models for sync lifecycle events.
- External reference linking payload model.
- Connector lifecycle reducer with deterministic transition rules and anomaly handling.
- Sync lifecycle reducer with idempotent ingest dedup and outcome tracking.
- Conformance fixtures, replay streams, and schema registration for both families.
- Public export and versioning notes for downstream runtime and SaaS consumers.

### Out of scope

- Provider-specific connector implementations (GitHub adapter, Jira adapter, etc.).
- Message broker or queue infrastructure (RabbitMQ, SQS, etc.).
- Webhook ingestion HTTP endpoints or transport security.
- Consumer-specific persistence schema migrations.

## Functional Requirements

- **FR-001**: The library MUST define canonical connector lifecycle constants and event set:
  - `CONNECTOR_PROVISIONED` -> `"ConnectorProvisioned"`
  - `CONNECTOR_HEALTH_CHECKED` -> `"ConnectorHealthChecked"`
  - `CONNECTOR_DEGRADED` -> `"ConnectorDegraded"`
  - `CONNECTOR_REVOKED` -> `"ConnectorRevoked"`
  - `CONNECTOR_RECONNECTED` -> `"ConnectorReconnected"`
  - `CONNECTOR_EVENT_TYPES` as a frozen set containing exactly those five types
  - `ConnectorState` enum containing `provisioned`, `healthy`, `degraded`, `revoked`, `reconnected`

- **FR-002**: Each connector lifecycle payload model MUST be frozen and MUST require these fields: `connector_id`, `connector_type`, `provider`, `mission_id`, `project_uuid`, `actor_id`, `actor_type`, `endpoint_url`, `recorded_at`. The `ConnectorHealthChecked` payload MUST additionally require `health_status` (healthy/degraded/unreachable) and `latency_ms`. The `ConnectorDegraded` payload MUST additionally require `degradation_reason` and `last_healthy_at`. The `ConnectorRevoked` payload MUST additionally require `revocation_reason`. The `ConnectorReconnected` payload MUST additionally require `previous_state` and `reconnect_strategy`.

- **FR-003**: The library MUST define canonical sync lifecycle constants and event set:
  - `SYNC_INGEST_ACCEPTED` -> `"SyncIngestAccepted"`
  - `SYNC_INGEST_REJECTED` -> `"SyncIngestRejected"`
  - `SYNC_RETRY_SCHEDULED` -> `"SyncRetryScheduled"`
  - `SYNC_DEAD_LETTERED` -> `"SyncDeadLettered"`
  - `SYNC_REPLAY_COMPLETED` -> `"SyncReplayCompleted"`
  - `SYNC_EVENT_TYPES` as a frozen set containing exactly those five types
  - `SyncOutcome` enum containing `accepted`, `rejected`, `retry_scheduled`, `dead_lettered`, `replay_completed`

- **FR-004**: Each sync lifecycle payload model MUST be frozen and MUST require these idempotency fields: `delivery_id`, `source_event_fingerprint`, `connector_id`, `mission_id`, `recorded_at`. The `SyncIngestAccepted` payload MUST additionally require `ingest_batch_id` and `ingested_count`. The `SyncIngestRejected` payload MUST additionally require `rejection_reason` and `rejected_payload_ref`. The `SyncRetryScheduled` payload MUST additionally require `retry_attempt`, `max_retries`, and `next_retry_at`. The `SyncDeadLettered` payload MUST additionally require `failure_reason`, `total_attempts`, and `dead_letter_ref`. The `SyncReplayCompleted` payload MUST additionally require `replay_id`, `replayed_count`, and `replay_source`.

- **FR-005**: The library MUST define an `ExternalReferenceLinked` event with payload model requiring: `link_id`, `connector_id`, `external_provider`, `external_ref_type`, `external_ref_id`, `external_ref_url`, `internal_aggregate_type`, `internal_aggregate_id`, `mission_id`, `linked_by`, and `recorded_at`.

- **FR-006**: The connector lifecycle reducer MUST implement deterministic transitions using sorted-plus-deduped input. Allowed transitions are: `None -> provisioned`, `provisioned -> healthy|degraded|revoked`, `healthy -> degraded|revoked`, `degraded -> healthy|revoked|reconnected`, `revoked -> reconnected`, `reconnected -> healthy|degraded|revoked`. No transitions out of terminal `revoked` state except `reconnected`.

- **FR-007**: The sync lifecycle reducer MUST implement idempotent ingest tracking by deduplicating on `(delivery_id, source_event_fingerprint)` pairs. It MUST track cumulative ingest/reject/retry/dead-letter/replay counts and maintain an ordered outcome log.

- **FR-008**: Conformance coverage MUST include connector and sync fixtures and tests: at least 6 valid connector fixtures, 4 invalid connector fixtures, 6 valid sync fixtures, 4 invalid sync fixtures, 2 valid external-reference-linked fixtures, and 3 replay streams (one connector lifecycle, one sync lifecycle, one mixed) with committed golden outputs.

- **FR-009**: Replay safety MUST be verified by reducer tests and property checks proving deterministic output across event permutations and duplicate-event input for both connector and sync reducers.

- **FR-010**: The connector and sync contract families MUST be exported through the public package API and documented in versioning/export notes for consumers. All new fixtures and manifest entries MUST carry `min_version: "2.7.0"`, and downstream impact notes MUST explicitly state additive 2.x adoption steps for `spec-kitty-tracker` and `spec-kitty-saas`.
