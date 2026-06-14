# Changelog

All notable changes to spec-kitty-events will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [6.1.0] - 2026-06-14

### Added

- **Canonical contracts for two post-mission lifecycle events** (`MissionReopened`,
  `FollowUpRecorded`) — additive, wire-compatible. Added `MissionReopenedPayload`
  and `FollowUpRecordedPayload` pydantic models (`ConfigDict(frozen=True,
  extra="forbid")`), the `MISSION_REOPENED`/`FOLLOW_UP_RECORDED` type constants,
  membership in `MISSION_EVENT_TYPES`, package-root re-exports, and
  `_EVENT_TYPE_TO_MODEL` registry entries. Field shapes mirror the producer call
  sites in `spec-kitty/src/specify_cli/status/lifecycle_events.py`
  (`emit_mission_reopened` / `emit_follow_up_recorded`) and the mission
  data-model `mission-lifecycle-dispatch-drg-closeout-01KV0S99/data-model.md`.
  `MissionReopened` carries `mission_id`, `mission_slug`, `reason`, `reopened_by`,
  `reopened_at`, and optional `cleared_merge`. `FollowUpRecorded` carries
  `mission_id`, `mission_slug`, a `follow_up_type` discriminator (`"commit"`/`"pr"`),
  conditional `commit_sha`/`pr_number`, `recorded_by`, and `recorded_at`; a
  model-level validator enforces the commit-vs-pr conditional-required rule.
  Consumer: spec-kitty mission `01KV0S99` (PR Priivacy-ai/spec-kitty#1926).
  No JSON-schema entry yet (the schema layer is optional secondary).
- **`reduce_lifecycle_events` post-mission semantics** for the two new events.
  Because `MissionReopened`/`FollowUpRecorded` are members of
  `MISSION_EVENT_TYPES`, they now flow through the lifecycle reducer with
  explicit handlers placed *before* the generic post-terminal guard (which would
  otherwise misfire and flag them as `Event after terminal state` anomalies).
  A `MissionReopened` is valid only when the mission is terminal and transitions
  it to the new actionable `MissionStatus.REOPENED` state (non-terminal, so a
  fresh `MissionCompleted` is processed normally); a `FollowUpRecorded` is valid
  only when terminal and leaves `mission_status` unchanged (a recorded fact).
  Inverse contract: either event arriving before completion (mission not in a
  terminal state) is itself flagged as a `… before completion` anomaly. All
  other event semantics and existing anomaly detection are preserved.
- `MissionStatus.REOPENED = "reopened"` enum member (actionable, NOT in
  `TERMINAL_MISSION_STATUSES`).

## [6.0.0] - 2026-06-07

### Breaking

- **`genesis` added to the canonical `Lane` vocabulary** (major bump per
  `contracts/lane-vocabulary.md`: adding a canonical lane is a contract change).
  `genesis` is the non-display, pre-finalize **origin** lane: a work-package
  with no recorded lane events derives as `genesis` until `finalize-tasks` seeds
  it to `planned`. It is producer-side only — never a display/summary lane.
  Consumers that exhaustively switch over `Lane` (or pin `len(Lane) == 9`) must
  handle the new member. The on-wire envelope `schema_version` is **unchanged**
  at `3.0.0` — this widens the accepted lane value set without changing the
  wire-format shape.

### Added

- `Lane.GENESIS = "genesis"` enum member.
- `(genesis -> planned)` as a first-class allowed transition (the finalize-tasks
  seed; no `force` required). `genesis -> canceled` is allowed via the generic
  non-terminal cancel rule. All other edges into/out of `genesis` are rejected.
- `CANONICAL_TO_SYNC_V1[genesis] = planned` and
  `CANONICAL_TO_SYNC_V2[genesis] = planned` (sync mappings remain total).
- `NON_DISPLAY_LANES = {Lane.GENESIS}` and ordered `DISPLAY_LANES` so consumers
  do not infer board, summary, or UI lanes from every `Lane` member.
- Regenerated `lane.schema.json` / `status_transition_payload.schema.json` to
  include `genesis`.

### Migration

- Downstream consumers (CLI, `spec-kitty-saas`) must update their
  `spec-kitty-events` constraint to `>=6.0.0` and accept `from_lane="genesis"`
  on `WPStatusChanged`. Until they do, a genesis seed cannot fan out as a valid
  payload — producers gate on the installed package's lane capability.
- Consumers that render board columns, lane filters, summary chips, or progress
  rows must derive those surfaces from `DISPLAY_LANES`, not `Lane`, because
  `genesis` is canonical on the wire but not user-displayable.

## [5.2.0] - 2026-05-22

### Added

- **Canonical event-type contracts for seven previously-uncontracted SaaS-bound events** (additive, wire-compatible). Added pydantic payload models and `_EVENT_TYPE_TO_MODEL` entries for `WPAssigned`, `BuildRegistered`, `BuildHeartbeat`, `HistoryAdded`, `ErrorLogged`, `DependencyResolved`, `MissionOriginBound`. Each model uses `ConfigDict(frozen=True, extra="forbid")`. Field shapes are derived from the canonical producer call sites in `spec-kitty/src/specify_cli/sync/emitter.py` (commit `43305c12c`, lines 720–1431). Mission: `canonical-producer-contracts-legacy-envelope-01KS7JM3`. Canonical authority: `kitty-specs/canonical-producer-contracts-legacy-envelope-01KS7JM3/data-model.md`.

- **`LOCAL_ONLY_EVENT_TYPES` machine-readable classification surface** (additive). New `frozenset[str]` exported from the package root. Empty in this release — every CLI-emitted event audited as of `spec-kitty` `43305c12c` routes through `SpecKittyEventEmitter._emit()` (the SaaS-bound central path). The surface is published so downstream consumers (CLI canonical-producer lint, SaaS adapter) can import the set and adjust enforcement without re-shipping a contract.

- **`legacy_envelope_v1` named compatibility contract** (additive). New `spec_kitty_events.legacy` module exporting `LegacyEnvelopeNormalizer`, `NormalizedEnvelope`, `UnnormalizableLegacyDiagnostic`, `NormalizationResult`, `LEGACY_ENVELOPE_CONTRACT_NAME`, and `RECOGNIZED_LEGACY_SHAPES`. Three named legacy shapes are recognized in v1: `pre_3_0_envelope` (pre-3.0 envelopes missing `project_uuid`; minted via deterministic `uuid5(NAMESPACE_URL || 'spec-kitty-events/legacy', f'{node_id}/{build_id}')`), `feature_keys_envelope` (retired `feature_slug` / `feature_number` keys mapped to `mission_slug` / `mission_number`), and `awaiting_review_synonym` (payload `to_lane = "awaiting-review"` mapped to canonical `"in_review"`). Un-normalizable rows surface as structured `UnnormalizableLegacyDiagnostic` rather than silent passes. Audit-preserving: both result variants carry the original `raw` dict. Phase 3 (`spec-kitty-saas#274`) consumes this contract to replace the implicit `_should_validate_strict_envelope()` carve-out. Canonical authority: `kitty-specs/canonical-producer-contracts-legacy-envelope-01KS7JM3/contracts/legacy-envelope-v1.md`.

- **Legacy-envelope conformance fixtures**. Added `conformance/fixtures/legacy/pre_3_0_envelope_normalizes.json` (normalization-success) and `conformance/fixtures/legacy/unrecognized_legacy_diagnostic.json` (un-normalizable). Both registered in `manifest.json` under `event_type: "LegacyEnvelope"` with `fixture_type: "legacy_normalization"`.

### Changed

- **`validate_event()` enforces `validate_transition()` for `WPStatusChanged`** (semantically tighter, wire-compatible). When the pydantic shape layer accepts a `WPStatusChanged` payload, `validate_event()` now also runs the `status.validate_transition()` business-rule check. Unforced backward review-rejection transitions (the rc14→rc22 drift signature) now fail through the public conformance gate with `ModelViolation` entries that preserve the documented routing substrings `force=True` and `review-rejection`. The new behavior is gated behind a `_SEMANTIC_VALIDATORS` registry so future event types with business rules plug in additively. Mission: `canonical-producer-contracts-legacy-envelope-01KS7JM3`.

- **Pyargs conformance entrypoint extracts `.input` from wrapper fixtures**. Fixtures whose on-disk shape is `{class, expected, input, notes, [expected_error_code]}` (class_taxonomy, historical_row_raw, lane_mapping_legacy, legacy normalization) are now correctly routed: the test extracts `entry["input"]` before calling `validate_event`. Lane-mapping and legacy-envelope fixtures are excluded from the `validate_event` parametrization via `event_type` / `fixture_type` filters and exercised by dedicated tests. Diagnostic-taxonomy fixtures whose `event_type` is a sentinel (e.g. `"<missing>"`) are also excluded.

- **Stale `wp-status-changed-invalid-lane` fixture corrected**. The fixture's `to_lane` value was `"in_review"`, which has been canonical since 3.0. Replaced with `"in_reveiw"` (typo) so the Lane enum genuinely rejects it. Manifest notes updated.

- **Stale `alias_doing_normalized` fixture corrected**. The fixture used `from_lane: planned, to_lane: doing` which after alias normalization (`doing → in_progress`) produced an illegal `planned → in_progress` transition. Changed `from_lane` to `claimed` so the resulting `claimed → in_progress` transition is legal under `_ALLOWED_TRANSITIONS`. The fixture's original intent (alias normalizes to canonical) is preserved.

## [5.1.0] - 2026-05-17

### Changed

- **Executable timestamp semantics** (additive, wire-compatible). The
  `Event.timestamp` field's documentation, model docstring, and committed
  JSON Schema description now explicitly state that the value is the
  producer-assigned wall-clock occurrence time, and that consumers MUST NOT
  substitute server-receipt, import, drain, or replay time for it. The wire
  identifier (`timestamp`) is unchanged. Mission:
  `executable-event-timestamp-semantics-01KRNME2`.
  Canonical authority: `kitty-specs/teamspace-event-contract-foundation-01KQHDE4/data-model.md`
  (Timestamp Semantics: Rules R-T-01 producer wins, R-T-02 no name collision,
  R-T-03 ordering invariance).

### Added

- **Backward-transition replay conformance fixture** (additive,
  wire-compatible). Added the review-rejection cycle replay fixture under
  `conformance/fixtures/edge_cases/replay/` and included it in package data so
  consumers can exercise forced backward-transition handling directly from the
  wheel.

- `spec_kitty_events.conformance.assert_producer_occurrence_preserved` and
  `spec_kitty_events.conformance.TimestampSubstitutionError` — reusable
  consumer-side conformance helper and typed error for asserting that a
  consumer's persisted occurrence-time value equals the producer's canonical
  `timestamp`. Consumers SHOULD add a regression test calling this helper
  against the new committed fixtures in
  `src/spec_kitty_events/conformance/fixtures/timestamp_semantics/`.

### Migration Note

Consumers that previously stored server-receipt, import, drain, or replay
time under a column or field literally named `timestamp` (and used that value
as canonical event occurrence time in projections, scorecards, audit logs,
or activity feeds) must:

1. Add a separately named slot for receipt time (recommended: `received_at`).
2. Preserve the producer's `timestamp` end-to-end through ingestion and
   projection.
3. Add a regression test calling
   `assert_producer_occurrence_preserved(envelope, persisted_occurrence_time)`
   against the "old producer / recent receipt" fixture to prove the ingestion
   path does not collapse the two values.

## [5.0.0] - 2026-05-01

> **Package 5.0.0; envelope schema remains 3.0.0.** This release is a
> major **package** bump for contract behaviour changes; the on-wire
> envelope `schema_version` is unchanged at `3.0.0` (the
> cutover-contract version pinned by
> `spec_kitty_events.cutover.CUTOVER_ARTIFACT.cutover_contract_version`).
> Producers must continue to emit `schema_version="3.0.0"`.

### Breaking Changes

- **`in_review` is now a canonical lane** (FR-001, FR-002). Consumers that
  previously rejected `in_review` as an unknown lane now accept it. Update
  consumer code that switches on the lane vocabulary's exact membership.

- **Payload contracts reconciled** (FR-003, FR-004). `MissionCreatedPayload`,
  `WPStatusChangedPayload`, and `MissionClosedPayload` are now the single
  source of truth; CLI and SaaS producers must conform. See the reconciliation
  log in `kitty-specs/teamspace-event-contract-foundation-01KQHDE4/contracts/payload-reconciliation.md`.

- **Recursive forbidden-key validator** (FR-005). The package now rejects
  envelopes containing legacy keys (`feature_slug`, `feature_number`,
  `mission_key`, plus the audit-derived expansion) at any depth, including
  inside array elements. The public cutover gate
  (`assert_canonical_cutover_signal`) now routes through the recursive
  walker too — pre-bump it only checked the top level and the immediate
  payload.

### Added

- `ValidationError` and `ValidationErrorCode` for structured rejection
  reporting (NFR-006).
- `forbidden_keys` module with `FORBIDDEN_LEGACY_KEYS` and the recursive
  validator.
- Eight-class conformance fixture suite covering canonical envelopes,
  historical synthesized envelopes, every rejection class, raw historical
  rows, and lane-mapping legacy.
- `COMPATIBILITY.md` section: local-CLI compatibility vs TeamSpace ingress
  validity.

### Fixed

- `MissionClosed` payload disagreement between CLI emission and library
  model (resolved per the reconciliation log).

---

## 4.0.0 — 2026-04-23

### Breaking

- **DecisionPoint contract frozen for Decision Moment V1.** `DecisionPointOpenedPayload`, `DecisionPointDiscussingPayload`, and `DecisionPointResolvedPayload` are now Pydantic v2 discriminated unions keyed by `origin_surface` (`"adr"` or `"planning_interview"`). Existing 3.x ADR producers must add `origin_surface: "adr"` to every DecisionPoint payload.
- **`DecisionPointResolved` (interview variant) requires `terminal_outcome`** (`"resolved" | "deferred" | "canceled"`). No grace period — 4.x validators fail closed. Cross-field constraints on `final_answer`/`rationale`/`other_answer` are enforced by a Pydantic `model_validator`.

### Added

- `DecisionPointWidened` event type for Slack-backed widening of an interview-origin Decision Moment. Carries `channel`, `teamspace_ref`, `default_channel_ref`, `thread_ref`, `invited_participants`, `widened_by`, timestamps.
- `WIDENED` state in `DecisionPointState` enum. Duplicate `DecisionPointWidened` for the same `decision_point_id` is idempotent.
- Interview-origin fields on `DecisionPointOpened`: `origin_flow` (`charter`/`specify`/`plan`), `question`, `options`, `input_key`, `step_id`.
- V1 projection fields on `ReducedDecisionPointState`: `origin_surface`, `origin_flow`, `question`, `options`, `input_key`, `step_id`, `widening`, `terminal_outcome`, `final_answer`, `other_answer`, `summary`, `actual_participants`, `resolved_by`, `closed_locally_while_widened`, `closure_message`.
- Shared models: `SummaryBlock`, `TeamspaceRef`, `DefaultChannelRef`, `ThreadRef`, `ClosureMessageRef`, `WideningProjection`, `ParticipantExternalRefs`.
- `ParticipantIdentity` extended with optional `external_refs` (Slack/Teamspace IDs carried losslessly for replay).
- New reducer anomaly kind: `origin_mismatch` (events for the same `decision_point_id` with inconsistent `origin_surface`).
- Six golden replay fixtures for every V1 scenario, plus invalid conformance fixtures for schema enforcement.

### Unchanged / compatible

- `DecisionInputRequested` and `DecisionInputAnswered` payloads remain 3.x-compatible.
- ADR semantics on `DecisionPointOpenedAdrPayload`, `DecisionPointDiscussingAdrPayload`, `DecisionPointResolvedAdrPayload` are preserved exactly.
- `DecisionPointOverridden` accepts existing 3.x payloads; the optional new `origin_surface` field is additive.

### Behaviour rules

- `DecisionInputAnswered` is emitted ONLY when a real final answer is written back. Deferred and canceled terminal outcomes do NOT emit a `DecisionInputAnswered`.
- When the mission owner answers locally while a widened Slack discussion is open, `DecisionPointResolved.closed_locally_while_widened=true` is set. `closed_locally_while_widened=true` is only legal when a prior `DecisionPointWidened` exists for the same `decision_point_id`; otherwise the reducer raises an `invalid_transition` anomaly and the field is projected as `false`.

### Migration

- 3.x ADR producers: add `origin_surface: "adr"` to every DecisionPoint payload. No other field changes required.
- 3.x `DecisionInput*` producers: no changes required.
- New interview-origin producers (`spec-kitty#757`, `spec-kitty#758`): use `DecisionPointOpenedInterviewPayload`, `DecisionPointWidenedPayload`, `DecisionPointDiscussingInterviewPayload`, `DecisionPointResolvedInterviewPayload`.

### Internal

- `DECISIONPOINT_SCHEMA_VERSION` bumped from `"2.6.0"` to `"3.0.0"`.

---

## 3.3.0 — Mission Analytics Contracts (2026-04-22)

### Added

- Added canonical analytics payload contracts:
  `TokenUsageRecordedPayload` and `DiffSummaryRecordedPayload`.
- Added `TOKEN_USAGE_RECORDED`, `DIFF_SUMMARY_RECORDED`, and
  `ANALYTICS_EVENT_TYPES` exports.
- Added committed JSON schemas and conformance fixtures for the analytics
  payload family.

### Why

- `spec-kitty` and `spec-kitty-saas` now have a canonical contract surface for
  Mission Scorecard token/cost accounting and diff-summary reporting.
- Downstream consumers no longer need repo-local telemetry schemas for these
  analytics records.

## 2.9.0 — Approved Lane Contract (2026-04-04)

### Added

- Added canonical `Lane.APPROVED` to the status state model.
- Added `SyncLaneV2`, `CANONICAL_TO_SYNC_V2`, and `canonical_to_sync_v2()` for
  consumers that need an explicit `approved` board column.
- Added committed `sync_lane_v2.schema.json`.

### Changed

- `SyncLaneV1` remains locked for existing inputs, and now maps the additive
  `approved` canonical lane to legacy `done`.
- Expanded status transition validation to cover the full 8-lane workflow used
  by current Spec Kitty runtimes:
  `in_progress -> approved`, `for_review -> approved`, `approved -> done`,
  `for_review -> planned`, `approved -> in_progress`, and `approved -> planned`.
- `approved` transitions now require evidence, matching runtime emission.

### Migration

- Consumers that only need the legacy 4-lane sync model can stay on
  `canonical_to_sync_v1()`.
- Consumers that need to distinguish `approved` from `done` should move to
  `canonical_to_sync_v2()` or consume canonical `Lane` values directly.

## 2.4.0 — Mission Dossier Parity Event Contracts (2026-02-21)

### Added

**Domain events (4 new event types)**:
- `MissionDossierArtifactIndexedPayload` — emitted when an artifact is catalogued
- `MissionDossierArtifactMissingPayload` — emitted when an expected artifact is absent
- `MissionDossierSnapshotComputedPayload` — emitted when a dossier snapshot is computed
- `MissionDossierParityDriftDetectedPayload` — emitted when drift vs baseline is detected

**Provenance payload objects**:
- `LocalNamespaceTuple` — 5-field namespace key for collision-safe parity baseline scoping
- `ArtifactIdentity` — canonical artifact identity (path, class, run, wp scoping)
- `ContentHashRef` — content fingerprint (hash, algorithm, size, encoding)
- `ProvenanceRef` — source trace (event IDs, git SHA/ref, actor metadata)

**Reducer**:
- `MissionDossierState` — deterministic dossier projection output
- `reduce_mission_dossier(events)` — pure reducer: filter → sort → dedup → namespace-check → fold
- `NamespaceMixedStreamError` — raised when event stream spans multiple namespace tuples

**Conformance infrastructure**:
- 8 new JSON schemas in `src/spec_kitty_events/schemas/`
- 13 fixture cases + 2 replay streams in `conformance/fixtures/dossier/`
- `dossier` fixture category registered in `load_fixtures()`
- 5 new conformance test categories (§7.6)

### Key Invariants

- `artifact_class` is exclusively in `ArtifactIdentity` — never a top-level event payload field
- `manifest_version` is exclusively in `LocalNamespaceTuple` — never in event payloads
- Reducer sort key: `(lamport_clock, timestamp, event_id)` — three-field total order
- `NamespaceMixedStreamError` carries both expected and offending namespace tuples in the message

### Migration: spec-kitty consumers

**Version pin**: `spec-kitty-events>=2.4.0,<3.0.0`

No breaking changes. All existing exports (Event envelope, WPStatusChanged,
lifecycle, collaboration, glossary, mission-next families) are unchanged.

To emit dossier events:

```python
from spec_kitty_events import (
    MissionDossierArtifactIndexedPayload,
    LocalNamespaceTuple, ArtifactIdentity, ContentHashRef,
    MISSION_DOSSIER_ARTIFACT_INDEXED,
)
```

Always include a full `LocalNamespaceTuple` with all 5 required fields.
Use `validate_event(payload_dict, event_type)` to validate before emitting.

To reduce a dossier event stream:

```python
from spec_kitty_events import reduce_mission_dossier, NamespaceMixedStreamError
try:
    state = reduce_mission_dossier(events)
except NamespaceMixedStreamError:
    # partition stream by namespace first
    ...
```

### Migration: spec-kitty-saas consumers

**Version pin**: `spec-kitty-events>=2.4.0,<3.0.0`

No breaking changes. Import the four dossier payload models for ingestion-side validation:

```python
from spec_kitty_events import (
    MissionDossierArtifactIndexedPayload,
    MissionDossierArtifactMissingPayload,
    MissionDossierSnapshotComputedPayload,
    MissionDossierParityDriftDetectedPayload,
)
from spec_kitty_events.conformance import validate_event, load_replay_stream
```

Use fixture replay streams for integration test baselines:

```python
events = load_replay_stream("dossier-replay-happy-path")
events = load_replay_stream("dossier-replay-drift-scenario")
```

Namespace collision prevention: always include the full `LocalNamespaceTuple` when
keying parity baselines. The reducer rejects mixed-namespace streams; callers must
partition by namespace before calling `reduce_mission_dossier()`.

---

## [2.3.1] - 2026-02-17

### Added

- **Canonical replay fixture stream**: `full_lifecycle.jsonl` in
  `conformance/fixtures/mission_next/replay/` -- 8-event JSONL stream covering
  the full mission-next lifecycle. Each line is a complete `Event` envelope.
  Consumers replay through projections for integration testing.
- `load_replay_stream()` in `spec_kitty_events.conformance` for programmatic
  replay fixture access.

### Fixed

- **First tagged release with mission-next contracts**: v2.3.0 was committed
  but never tagged. This release (v2.3.1) is the first tagged release shipping
  the mission-next reducer with all three correctness guards:
  - Lifecycle `MissionCompleted` alias collision rejected via payload validation
  - `run_id` consistency enforced on all post-start events
  - Malformed payloads converted to anomalies (no reducer crash)

## [2.3.0] - 2026-02-17

### Added

- **Mission-next runtime contracts**: 7 event type constants (`MissionRunStarted`,
  `NextStepPlanned`, `NextStepIssued`, `NextStepAutoCompleted`,
  `DecisionInputRequested`, `DecisionInputAnswered`, `MissionRunCompleted`)
  and `MISSION_NEXT_EVENT_TYPES` frozenset.
- `RuntimeActorIdentity` value object mirroring the runtime's `ActorIdentity`
  schema (human, llm, service actor types with provider/model/tool metadata).
- 6 typed payload models for run-scoped mission execution events.
- `MissionRunStatus` enum (`RUNNING`, `COMPLETED`) with `TERMINAL_RUN_STATUSES`.
- `MissionNextAnomaly` and `ReducedMissionRunState` reducer output models.
- `reduce_mission_next_events()` — deterministic reducer for mission run state
  materialization with step tracking, decision lifecycle, and anomaly detection.
- Compatibility alias — `"MissionCompleted"` accepted as `"MissionRunCompleted"`
  for run-scoped events during migration window.
- `NextStepPlanned` reserved constant (payload contract deferred until runtime emits).
- 7 new JSON Schema files for mission-next models (44 total).
- 9 conformance payload fixtures (6 valid, 3 invalid) in `mission_next/` category.
- Hypothesis property tests for reducer determinism (200 permutations) and
  idempotent dedup (100 examples).
- 22 new exports (total package exports: 126).

## [2.2.0] - 2026-02-17

### Added

- **UUID event ID acceptance** (backward-compatible): Envelope fields (`event_id`,
  `causation_id`, `correlation_id`) now accept ULID (26-char Crockford base32),
  hyphenated UUID (36-char), and bare hex UUID (32-char).
- `normalize_event_id()` public function for canonical ID normalization.
  Exported in `__init__.py`.
- JSON Schema patterns widened for all 3 inbound formats with strict Crockford
  base32 validation for ULIDs.
- 2 new conformance fixtures: `event-uuid-hyphenated`, `event-uuid-bare`.

### Changed

- **ULID canonicalization**: 26-char ULID IDs are now uppercased to canonical form
  and validated against Crockford base32 charset (I, L, O, U rejected).
- **UUID canonicalization**: UUID IDs lowercased to canonical hyphenated form.

## [2.1.0] - 2026-02-15

### Added

- **Collaboration event contracts** (Feature 006):
  - 14 new event type constants and `COLLABORATION_EVENT_TYPES` frozenset
  - 3 identity/target models: `ParticipantIdentity`, `AuthPrincipalBinding`, `FocusTarget`
  - 14 typed payload models for participant lifecycle, drive intent, focus, step execution,
    advisory warnings, communication, and session linking
  - `ReducedCollaborationState` materialized view with 15 fields
  - `reduce_collaboration_events()` -- dual-mode reducer (strict/permissive) with seeded roster
    support
  - `UnknownParticipantError` for strict mode enforcement
  - `CollaborationAnomaly` for non-fatal issue recording
  - 17 new JSON Schema files for collaboration models (28 total)
  - 7 conformance payload fixtures (5 valid, 2 invalid)
  - Hypothesis property tests for reducer determinism
  - Performance benchmark (10K events in <1s)
- 36 new exports (total package exports: 104)
- SaaS-authoritative participation model documentation
- Canonical envelope mapping convention

### Changed

- **Version**: Graduated from `2.0.0rc1` to `2.1.0`.
- **Public API**: 104 exports in `__init__.py` (up from 68 in 2.0.0rc1). Added 14 event type
  constants, 3 identity/target models, 14 payload models, 3 reducer/error models, and
  `COLLABORATION_EVENT_TYPES` frozenset and `reduce_collaboration_events` function.

## [2.0.0rc1] - 2026-02-12

### Added

- **Lane Mapping Contract** (Feature 005, WP01): `SyncLaneV1` enum with 4 consumer-facing lanes
  (`planned`, `doing`, `for_review`, `done`), `CANONICAL_TO_SYNC_V1` immutable mapping, and
  `canonical_to_sync_v1()` function. Consumers import this instead of hardcoding the 7-to-4 lane
  mapping. See [COMPATIBILITY.md](COMPATIBILITY.md) for the full mapping table.
- **JSON Schema Artifacts** (Feature 005, WP02): 11 JSON Schema files generated from Pydantic v2
  models, committed as canonical contract documents. Build-time generation script with CI drift
  detection (`python -m spec_kitty_events.schemas.generate --check`). Schemas available via
  `load_schema()` and `list_schemas()` from `spec_kitty_events.schemas`.
- **Conformance Validator API** (Feature 005, WP03): `validate_event()` with dual-layer validation
  (Pydantic primary + JSON Schema secondary). Returns structured `ConformanceResult` with separate
  `model_violations` and `schema_violations` buckets. Graceful degradation when `jsonschema` is not
  installed (unless `strict=True`).
- **Canonical Fixtures** (Feature 005, WP04): Manifest-driven fixture suite with `load_fixtures()`
  and `FixtureCase` dataclass for programmatic access. Categories: `events`, `lane_mapping`,
  `edge_cases`. Bundled as package data.
- **Conformance Test Suite** (Feature 005, WP05): Pytest-runnable via
  `pytest --pyargs spec_kitty_events.conformance`. Manifest-driven tests covering all event types,
  lane mappings, and edge cases. Consumer test helpers: `assert_payload_conforms()`,
  `assert_payload_fails()`, `assert_lane_mapping()`.
- **`[conformance]` Optional Extra** (Feature 005, WP06):
  `pip install spec-kitty-events[conformance]` adds `jsonschema>=4.21.0,<5.0.0` for full
  dual-layer validation.

### Changed

- **Version**: Graduated from `0.4.0-alpha` to `2.0.0rc1` (PEP 440 compliant).
- **SCHEMA_VERSION**: Updated to `"2.0.0"` (locked for the 2.x series lifetime).
- **Public API**: 68 exports in `__init__.py` (up from 65 in 0.4.0-alpha). Added `SyncLaneV1`,
  `CANONICAL_TO_SYNC_V1`, and `canonical_to_sync_v1`.

### Migration from 0.4.x

> Full migration guide in [COMPATIBILITY.md](COMPATIBILITY.md).

1. **Update dependency pin**:
   ```toml
   # pyproject.toml
   dependencies = [
       "spec-kitty-events>=2.0.0rc1,<3.0.0",
   ]
   ```

2. **Replace hardcoded lane mappings** with the canonical contract:
   ```python
   # Before (consumer code):
   LANE_MAP = {"planned": "planned", "in_progress": "doing", ...}
   sync = LANE_MAP[lane_value]

   # After:
   from spec_kitty_events import Lane, SyncLaneV1, canonical_to_sync_v1
   sync_lane = canonical_to_sync_v1(Lane.IN_PROGRESS)  # SyncLaneV1.DOING
   ```

3. **Replace local status enums** with `SyncLaneV1` import:
   ```python
   # Before:
   class MyStatus(str, Enum):
       PLANNED = "planned"
       DOING = "doing"
       ...

   # After:
   from spec_kitty_events import SyncLaneV1
   # Use SyncLaneV1.PLANNED, SyncLaneV1.DOING, etc.
   ```

4. **Add conformance CI step** (recommended):
   ```bash
   pip install "spec-kitty-events[conformance]>=2.0.0rc1,<3.0.0"
   pytest --pyargs spec_kitty_events.conformance -v
   ```

5. **Event model changes**: The `Event` model now requires `correlation_id` (ULID) and includes
   `schema_version` (default `"1.0.0"`) and `data_tier` (default `0`). If you construct `Event`
   instances directly, add `correlation_id` to your constructors.

## [0.4.0-alpha] - 2026-02-09

### Added

- **Canonical Event Contract** (Feature 004): `correlation_id`, `schema_version`, `data_tier`
  fields on `Event` model. Mission lifecycle event contracts: `MissionStarted`, `MissionCompleted`,
  `MissionCancelled`, `PhaseEntered`, `ReviewRollback` with typed payload models.
- **Lifecycle Reducer**: `reduce_lifecycle_events()` with cancel-beats-re-open precedence,
  rollback-aware phase tracking, and deterministic ordering.
- **Mission Constants**: `SCHEMA_VERSION`, `MISSION_EVENT_TYPES`, `TERMINAL_MISSION_STATUSES`,
  `MissionStatus` enum.
- **Lifecycle Output Models**: `LifecycleAnomaly`, `ReducedMissionState`.

## [0.3.0-alpha] - 2026-02-08

### Added

- **Status State Model Contracts** (Feature 003): 7-lane canonical status model with `Lane` enum,
  transition validation, and deterministic reducer.
- **Enums**: `Lane` (7 lanes), `ExecutionMode` (worktree | direct_repo).
- **Evidence Models**: `RepoEvidence`, `VerificationEntry`, `ReviewVerdict`, `DoneEvidence`.
- **Transition Models**: `ForceMetadata`, `StatusTransitionPayload` (immutable, cross-field
  validated), `TransitionValidationResult`, `TransitionError`.
- **Reducer**: `reduce_status_events()` with rollback-aware precedence, `WPState`,
  `TransitionAnomaly`, `ReducedStatus`.
- **Utilities**: `normalize_lane()` (alias handling), `validate_transition()`,
  `status_event_sort_key()`, `dedup_events()`.
- **Constants**: `TERMINAL_LANES`, `LANE_ALIASES`, `WP_STATUS_CHANGED`.

## [0.2.0-alpha] - 2026-02-07

### Added

- **GitHub Gate Observability Contracts** (Feature 002): `GatePayloadBase`, `GatePassedPayload`,
  `GateFailedPayload` models. `map_check_run_conclusion()` for deterministic mapping from GitHub
  `check_run` conclusion strings to event types. `UnknownConclusionError` exception.
- Ignored conclusions (`neutral`, `skipped`, `stale`) logged with optional callback.

## [0.1.1-alpha] - 2026-02-07

### Added

- `project_uuid` field on `Event` model (required, `uuid.UUID`).
- `project_slug` field on `Event` model (optional, `str`, default `None`).

### Breaking Changes

- All `Event()` constructors must now include `project_uuid` parameter.

## [0.1.0-alpha] - 2026-01-27

### Added

- **Core Event Model**: Immutable `Event` with causal metadata (Pydantic frozen). ULID event IDs,
  Lamport clocks, causation chains.
- **Lamport Clocks**: `LamportClock` with `tick()`, `update()`, `current()`.
- **Conflict Detection**: `is_concurrent()`, `total_order_key()`, `topological_sort()`.
- **CRDT Merge Functions**: `merge_gset()` (grow-only sets), `merge_counter()` (with dedup).
- **State-Machine Merge**: `state_machine_merge()` with priority-based winner selection.
- **Error Logging**: `ErrorLog` with append-only semantics and retention policy.
- **Storage Adapters**: Abstract base classes (`EventStore`, `ClockStorage`, `ErrorStorage`) and
  in-memory implementations.
- **Type Safety**: Full `mypy --strict` compliance, `py.typed` marker (PEP 561).

---

[2.3.1]: https://github.com/Priivacy-ai/spec-kitty-events/compare/v2.3.0...v2.3.1
[2.3.0]: https://github.com/Priivacy-ai/spec-kitty-events/compare/v2.2.0...v2.3.0
[2.2.0]: https://github.com/Priivacy-ai/spec-kitty-events/compare/v2.1.0...v2.2.0
[2.1.0]: https://github.com/Priivacy-ai/spec-kitty-events/compare/v2.0.0rc1...v2.1.0
[2.0.0rc1]: https://github.com/Priivacy-ai/spec-kitty-events/compare/v0.4.0-alpha...v2.0.0rc1
[0.4.0-alpha]: https://github.com/Priivacy-ai/spec-kitty-events/compare/v0.3.0-alpha...v0.4.0-alpha
[0.3.0-alpha]: https://github.com/Priivacy-ai/spec-kitty-events/compare/v0.2.0-alpha...v0.3.0-alpha
[0.2.0-alpha]: https://github.com/Priivacy-ai/spec-kitty-events/compare/v0.1.1-alpha...v0.2.0-alpha
[0.1.1-alpha]: https://github.com/Priivacy-ai/spec-kitty-events/compare/v0.1.0-alpha...v0.1.1-alpha
[0.1.0-alpha]: https://github.com/Priivacy-ai/spec-kitty-events/releases/tag/v0.1.0-alpha
