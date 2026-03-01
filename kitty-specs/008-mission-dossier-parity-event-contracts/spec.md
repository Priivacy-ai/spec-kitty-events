# Feature Specification: Mission Dossier Parity Event Contracts

**Feature**: 008-mission-dossier-parity-event-contracts
**Version Target**: 2.4.0
**Branch**: 2.x
**Status**: Draft
**Date**: 2026-02-21
**Mission**: software-dev

---

## 1. Overview

This feature adds canonical event contracts to `spec-kitty-events` that enable deterministic Mission Dossier projection and local-authoritative parity drift signaling. These contracts are the shared integration surface that allows `spec-kitty` (local runtime) and `spec-kitty-saas` (cloud projection) to synchronize dossier state and detect drift without implementation-level coupling.

The dossier contract surface is intentionally tight: four domain events, a set of typed provenance payload objects, a deterministic reducer, and the conformance infrastructure to validate all of the above. No broader event-family expansion is included in this version.

---

## 2. Problem Statement

`spec-kitty` and `spec-kitty-saas` currently have no shared typed contract for communicating mission artifact state, completeness anomalies, or parity drift. Each side invents its own schema, leading to integration gaps, silent omissions, and inability to guarantee that SaaS dashboards show the same mission reality as local workflows.

Without a stable typed contract:
- SaaS cannot deterministically reconstruct mission dossier state from an event stream.
- Missing artifacts appear as empty views rather than explicit anomalies with provenance.
- Parity drift between local and SaaS representations is undetectable at the contract layer.
- Consumer teams (`spec-kitty`, `spec-kitty-saas`) cannot pin and migrate independently.

---

## 3. Goals

1. Define four stable, typed dossier/parity domain events as shared integration contracts.
2. Encode all local namespace tuple fields required for safe local-first baseline scoping.
3. Provide typed provenance payload objects covering artifact identification, content hashing, and source references.
4. Add a deterministic reducer that materializes Mission Dossier projection state from an ordered event stream.
5. Generate JSON schemas and fixture sets (valid, invalid, replay) that both consumers can reference directly.
6. Extend the conformance suite to cover missing-artifact anomalies, parity drift detection, and namespace collision prevention.
7. Publish explicit versioned migration notes so `spec-kitty` and `spec-kitty-saas` can upgrade safely and independently.

---

## 4. Non-Goals

1. Local dashboard implementation (O42 HTTPServer, rendering, navigation UX).
2. SaaS UI behavior, API endpoints, or database schemas.
3. Runtime planner or step-orchestration logic.
4. Global or federated project identity semantics.
5. Dedicated context-transition event types (`MissionStepContextBound`, etc.) — context-transition visibility is carried as diagnostic fields in dossier snapshot and anomaly payloads, not as separate events in this version.
6. Cross-org namespace conflict reconciliation.

---

## 5. Actors and Consumers

| Actor | Role |
|---|---|
| `spec-kitty` (local runtime) | Emits dossier/parity events; consumes reducer to project local dossier state |
| `spec-kitty-saas` (cloud projection) | Consumes event stream to synchronize and render mission dossier; raises drift anomalies |
| Mission reviewer | End consumer who benefits from parity-guaranteed dossier views |
| Contract maintainer | Owns schema versioning, migration notes, and conformance suite |

---

## 6. Domain Language

| Term | Definition |
|---|---|
| **MissionDossier** | Complete, deterministic projection of all mission artifacts, anomalies, and provenance for one mission instance |
| **ArtifactDocument** | One concrete artifact unit (e.g., `spec.md`, `plan.md`, `WP03.md`, review notes) with identity and provenance |
| **ArtifactClass** | Taxonomy value: `input`, `workflow`, `output`, `evidence`, `policy`, `runtime` |
| **ProvenanceRef** | Typed link to event IDs, git SHA/ref, path, revision timestamp, and actor metadata |
| **ParityBaseline** | Stored hash/fingerprint of a dossier snapshot keyed by the local namespace tuple |
| **ParityDrift** | Detected divergence between the current dossier projection and its recorded baseline |
| **LocalNamespaceTuple** | Minimum key set for collision-safe parity scoping: `project_uuid`, `feature_slug`, `target_branch`, `mission_key`, `manifest_version`, optional `step_id` |
| **ArtifactManifest** | Step-aware expected artifact list (KISS shape: `required_always`, `required_by_step`, `optional_always`) |
| **DossierReducer** | Pure function that folds an ordered dossier event stream into a deterministic `MissionDossierState` |

---

## 7. Feature Scope

### 7.1 Domain Events (4 new event types)

#### 7.1.1 MissionDossierArtifactIndexed

Emitted when an artifact is discovered and successfully catalogued into the mission dossier.

**Payload fields (required)**:
- `namespace` — LocalNamespaceTuple identifying the dossier scope (`manifest_version` is carried here; not duplicated in payload)
- `artifact_id` — ArtifactIdentity (see §7.2); `artifact_class` is defined exclusively in `artifact_id`, not at the top level
- `content_ref` — ContentHashRef (see §7.2)
- `indexed_at` — ISO 8601 timestamp of indexing

**Payload fields (optional)**:
- `provenance` — ProvenanceRef (see §7.2)
- `step_id` — mission YAML step ID if this artifact was indexed in step context
- `supersedes` — artifact_id of a prior version this artifact replaces
- `context_diagnostics` — freeform key/value map for context-transition visibility (e.g., resolved context types, binding sources)

**Reducer effect**: Upserts artifact entry in `MissionDossierState.artifacts`; marks previous version superseded if `supersedes` is set.

#### 7.1.2 MissionDossierArtifactMissing

Emitted when an expected artifact is absent from the dossier at completeness-check time.

**Payload fields (required)**:
- `namespace` — LocalNamespaceTuple
- `expected_identity` — ArtifactIdentity describing the absent artifact (`artifact_class` is defined exclusively here via `ArtifactIdentity.artifact_class`, not as a separate top-level field)
- `manifest_step` — `"required_always"` or a step_id string from `required_by_step`
- `checked_at` — ISO 8601 timestamp of the check

**Payload fields (optional)**:
- `last_known_ref` — ProvenanceRef if the artifact existed in a prior revision
- `remediation_hint` — human-readable recovery instruction
- `context_diagnostics` — key/value map for context-transition visibility

**Reducer effect**: Adds or updates an anomaly entry in `MissionDossierState.anomalies` with type `missing_artifact`.

#### 7.1.3 MissionDossierSnapshotComputed

Emitted when a complete dossier snapshot is materialized and its parity baseline is recorded.

**Payload fields (required)**:
- `namespace` — LocalNamespaceTuple
- `snapshot_hash` — deterministic hash of the full dossier state at snapshot time (hex string)
- `artifact_count` — number of indexed artifacts included in this snapshot
- `anomaly_count` — number of active anomalies at snapshot time
- `computed_at` — ISO 8601 timestamp

**Payload fields (optional)**:
- `algorithm` — hash algorithm used (default `"sha256"`); `manifest_version` is not duplicated here — it is carried exclusively in `namespace.manifest_version`
- `context_diagnostics` — key/value map for context-transition visibility at snapshot time

**Reducer effect**: Sets `MissionDossierState.latest_snapshot`; records baseline for drift comparison.

#### 7.1.4 MissionDossierParityDriftDetected

Emitted when a computed dossier snapshot diverges from the recorded local parity baseline.

**Payload fields (required)**:
- `namespace` — LocalNamespaceTuple
- `expected_hash` — hash from the stored baseline
- `actual_hash` — hash from the current computed snapshot
- `drift_kind` — one of `artifact_added`, `artifact_removed`, `artifact_mutated`, `anomaly_introduced`, `anomaly_resolved`, `manifest_version_changed`
- `detected_at` — ISO 8601 timestamp

**Payload fields (optional)**:
- `artifact_ids_changed` — list of artifact_id values involved in drift (when determinable)
- `rebuild_hint` — instruction for restoring parity from canonical sources
- `context_diagnostics` — key/value map

**Reducer effect**: Appends drift record to `MissionDossierState.drift_history`; marks state as `parity_drifted`.

---

### 7.2 Typed Provenance Payload Objects

These are reusable payload sub-types, not events. They are used as fields within the four event payloads above.

#### ArtifactIdentity

Canonical identity for one artifact instance.

| Field | Type | Required | Description |
|---|---|---|---|
| `mission_key` | string | yes | Mission identifier (e.g., slugified mission YAML name) |
| `run_id` | string | no | Mission run ULID/UUID if artifact is run-scoped |
| `wp_id` | string | no | Work package identifier if artifact is WP-scoped |
| `path` | string | yes | Repository-relative path (e.g., `kitty-specs/008-.../spec.md`) |
| `artifact_class` | string | yes | One of the six ArtifactClass values |

#### ContentHashRef

Opaque content fingerprint with optional size and encoding metadata.

| Field | Type | Required | Description |
|---|---|---|---|
| `hash` | string | yes | Hex-encoded content hash |
| `algorithm` | string | yes | Hash algorithm: `sha256`, `sha512`, `md5` (default `sha256`) |
| `size_bytes` | integer | no | Content byte size |
| `encoding` | string | no | Content encoding if not UTF-8 (e.g., `base64`) |

#### ProvenanceRef

Source trace connecting an artifact or event to its authoritative origin.

| Field | Type | Required | Description |
|---|---|---|---|
| `source_event_ids` | list[string] | no | Event IDs that produced/updated this artifact |
| `git_sha` | string | no | Git commit SHA where artifact was last modified |
| `git_ref` | string | no | Git branch or tag reference |
| `actor_id` | string | no | Actor identifier (user slug, agent ID, or system label) |
| `actor_kind` | string | no | `human`, `llm`, or `system` |
| `revised_at` | string | no | ISO 8601 timestamp of last revision |

#### LocalNamespaceTuple

Minimum collision-safe key for parity baseline scoping.

| Field | Type | Required | Description |
|---|---|---|---|
| `project_uuid` | string | yes | Local project UUID from sync identity management |
| `feature_slug` | string | yes | Human-readable feature slug (e.g., `008-mission-dossier-...`) |
| `target_branch` | string | yes | Git branch targeted by this mission run |
| `mission_key` | string | yes | Mission identifier |
| `manifest_version` | string | yes | Semver of the artifact manifest in use |
| `step_id` | string | no | Mission YAML step ID for step-scoped baselines |

---

### 7.3 Dossier Reducer

A pure, side-effect-free function that folds an ordered stream of dossier events into a `MissionDossierState` projection.

**Input**: ordered list of `Event` envelope objects (standard spec-kitty-events envelope)
**Output**: `MissionDossierState` dataclass (frozen, deterministic)

**`MissionDossierState` fields**:
- `namespace` — LocalNamespaceTuple (established from the first dossier event in the stream; all subsequent events must carry an identical namespace tuple)
- `artifacts` — mapping of `path` → `ArtifactEntry` (indexed artifacts, with superseded flag)
- `anomalies` — list of `AnomalyEntry` (missing artifacts and other anomalies)
- `latest_snapshot` — optional `SnapshotSummary` (hash, counts, computed_at)
- `drift_history` — list of `DriftRecord` (all drift events seen in stream)
- `parity_status` — `"clean"` | `"drifted"` | `"unknown"` (derived from reducer logic)

**Reducer guarantees**:
1. Same input event stream → identical `MissionDossierState` output (determinism).
2. Event ordering is by `(lamport_clock, timestamp, event_id)` ascending — all three fields are used as the sort key to guarantee a stable total order. `event_id` is the final tiebreaker; this matches the existing pattern in `mission_next.py` and `status.py`.
3. Duplicate events (same `event_id`) are silently deduplicated before sorting and reduction.
4. Unknown event types are skipped without error.
5. Reducer is a pure function with no I/O, no global state, no randomness.
6. **Single-namespace invariant**: If any event in the input stream carries a `namespace` field that differs from the stream's first dossier event namespace, the reducer raises `NAMESPACE_MIXED_STREAM` immediately without partial reduction. Callers must partition streams by namespace before calling the reducer. Auto-partitioning is not provided in v1.

---

### 7.4 JSON Schemas

One schema file per event payload type and per provenance sub-type, following existing naming convention (`{type_snake_case}.schema.json`). Schemas are generated at build time from Pydantic models and committed.

**New schemas** (8 total):
- `mission_dossier_artifact_indexed_payload.schema.json`
- `mission_dossier_artifact_missing_payload.schema.json`
- `mission_dossier_snapshot_computed_payload.schema.json`
- `mission_dossier_parity_drift_detected_payload.schema.json`
- `artifact_identity.schema.json`
- `content_hash_ref.schema.json`
- `provenance_ref.schema.json`
- `local_namespace_tuple.schema.json`

CI drift check must fail if committed schemas diverge from generated output.

---

### 7.5 Fixtures

**Fixture categories** (added to conformance manifest):

**Loader and packaging requirements**:
- `"dossier"` must be added to the list of valid category strings in `loader.py` alongside the existing six categories (`events`, `lane_mapping`, `edge_cases`, `collaboration`, `glossary`, `mission_next`). Calling `load_fixtures("dossier")` with the current list raises an error; that must be fixed.
- `pyproject.toml` package-data globs must include `conformance/fixtures/dossier/**/*` so that installed-package conformance usage finds the fixtures. In-repo tests pass regardless, but installed consumers would silently miss fixtures without this glob.

#### `dossier/` — new category with the following cases:

| fixture_id | valid | notes |
|---|---|---|
| `dossier-artifact-indexed-valid` | true | happy-path: spec.md indexed as input artifact |
| `dossier-artifact-indexed-supersedes` | true | artifact replaces prior version with `supersedes` field |
| `dossier-artifact-indexed-with-provenance` | true | full provenance fields populated |
| `dossier-artifact-missing-required-always` | true | required_always manifest check fires anomaly |
| `dossier-artifact-missing-required-by-step` | true | step-scoped completeness check fires anomaly |
| `dossier-snapshot-computed-clean` | true | happy-path snapshot with zero anomalies |
| `dossier-snapshot-computed-with-anomalies` | true | snapshot with non-zero anomaly count |
| `dossier-parity-drift-artifact-added` | true | drift kind `artifact_added` |
| `dossier-parity-drift-artifact-mutated` | true | drift kind `artifact_mutated` |
| `dossier-parity-drift-namespace-mismatch` | false | invalid: namespace tuple missing required fields |
| `dossier-artifact-indexed-missing-path` | false | invalid: artifact_identity.path absent |
| `dossier-artifact-indexed-invalid-class` | false | invalid: unrecognized artifact_class value |
| `dossier-namespace-collision-coverage` | true | two distinct namespace tuples; asserts key tuple uniqueness |

**Replay stream** (`dossier/replay/`):
- `dossier_happy_path.jsonl` — ordered stream: Indexed × 3 → SnapshotComputed (clean) → Indexed (supersedes) → SnapshotComputed (updated)
- `dossier_drift_scenario.jsonl` — ordered stream: Indexed × 2 → SnapshotComputed → ArtifactMissing → ParityDriftDetected

---

### 7.6 Conformance Suite Extensions

**New test coverage** added to existing pytest conformance suite:

1. **Missing-artifact anomaly**: Verify `MissionDossierArtifactMissing` payload validates, manifest_step field accepts both `required_always` and step_id string, and invalid fixtures correctly fail.
2. **Parity drift detection**: Verify `MissionDossierParityDriftDetected` payload validates for all `drift_kind` enum values; assert reducer correctly sets `parity_status = "drifted"` after drift event.
3. **Namespace collision prevention**: Load two fixture payloads with distinct namespace tuples; assert their key tuples never collide (covers project_uuid × feature_slug × target_branch × mission_key × manifest_version × step_id combinations).
4. **Reducer determinism**: Given the `dossier_happy_path.jsonl` and `dossier_drift_scenario.jsonl` replay streams, apply reducer in multiple orderings (with deduplicated invariant) and assert identical output for canonical ordering.
5. **Round-trip schema conformance**: All valid fixtures pass both Pydantic layer and JSON Schema layer (dual-layer); all invalid fixtures produce at least one violation in either layer.

---

### 7.7 Exports and Public API

**New exports** added to `spec_kitty_events/__init__.py` (~8 additions):

- `MissionDossierArtifactIndexedPayload`
- `MissionDossierArtifactMissingPayload`
- `MissionDossierSnapshotComputedPayload`
- `MissionDossierParityDriftDetectedPayload`
- `ArtifactIdentity`
- `ContentHashRef`
- `ProvenanceRef`
- `LocalNamespaceTuple`
- `MissionDossierState`
- `reduce_mission_dossier` (reducer function)

Expected total: ~10 new exports (exact count pending implementation).

---

### 7.8 Changelog and Consumer Migration

**CHANGELOG.md entry** for v2.4.0:

```
## 2.4.0 — Mission Dossier Parity Event Contracts

### Added
- MissionDossierArtifactIndexedPayload
- MissionDossierArtifactMissingPayload
- MissionDossierSnapshotComputedPayload
- MissionDossierParityDriftDetectedPayload
- ArtifactIdentity, ContentHashRef, ProvenanceRef, LocalNamespaceTuple (provenance payload objects)
- MissionDossierState, reduce_mission_dossier (deterministic dossier reducer)
- 8 new JSON schemas for dossier events and provenance sub-types
- 13 fixture cases + 2 replay streams in dossier/ conformance category
- Conformance suite: missing-artifact, parity-drift, namespace-collision, reducer-determinism test coverage

### Migration: spec-kitty consumers
- Pin: `spec-kitty-events>=2.4.0,<3.0.0`
- No breaking changes to existing exports (Event envelope, WPStatusChanged, lifecycle/collab/glossary/mission-next families remain unchanged).
- New dossier events require the local namespace tuple fields; validate with validate_event() before emitting.
- Reducer consumes standard Event envelopes; no event wrapper changes needed.

### Migration: spec-kitty-saas consumers
- Pin: `spec-kitty-events>=2.4.0,<3.0.0`
- Import the four dossier payload models and use validate_event() for ingestion-side validation.
- Load fixture replay streams (dossier/replay/*.jsonl) for integration test baselines.
- Namespace collision prevention: always include full LocalNamespaceTuple when keying parity baselines.
```

---

## 8. User Scenarios and Testing

### Scenario A — Happy-path artifact indexing and snapshot

1. Local runtime indexes `spec.md` as an `input` artifact.
2. Emits `MissionDossierArtifactIndexed` with populated ArtifactIdentity and ContentHashRef.
3. Reducer folds event → `MissionDossierState.artifacts["kitty-specs/.../spec.md"]` is populated.
4. Local runtime emits `MissionDossierSnapshotComputed`.
5. Reducer sets `latest_snapshot`; `parity_status` = `"clean"`.
6. SaaS ingests the two events; identical reducer output.

### Scenario B — Missing artifact anomaly

1. Completeness check finds `plan.md` absent at the `plan` step.
2. Local runtime emits `MissionDossierArtifactMissing` with `expected_identity` (ArtifactIdentity carrying `path` and `artifact_class`) and `manifest_step: "plan"`.
3. Reducer adds anomaly entry; `anomaly_count` > 0 in next snapshot.
4. SaaS dossier view shows `plan.md` as explicit missing anomaly (not empty/silent).

### Scenario C — Parity drift detection

1. Snapshot computed with hash H1; baseline stored.
2. Additional artifact indexed since last snapshot; hash now H2.
3. Drift check emits `MissionDossierParityDriftDetected` (drift_kind `artifact_added`).
4. Reducer marks `parity_status = "drifted"`.
5. SaaS shows drift badge; `rebuild_hint` guides recovery.

### Scenario D — Namespace collision prevention

1. Two concurrent features share the same `feature_slug` (human error).
2. Their `project_uuid` values differ, so their namespace tuples are distinct.
3. Conformance test asserts no key tuple collision across both namespaces.

### Scenario E — Replay stream reducer determinism

1. `dossier_happy_path.jsonl` replayed in canonical lamport order.
2. Same stream re-replayed with deduplicated events.
3. Both produce identical `MissionDossierState` output.

---

## 9. Functional Requirements

1. Four dossier event payload models validate through the existing dual-layer conformance engine (Pydantic primary + JSON Schema secondary).
2. All four event types are registered in `validators.py`'s `_EVENT_TYPE_TO_MODEL` and `_EVENT_TYPE_TO_SCHEMA` mappings.
3. `LocalNamespaceTuple` carries all six namespace fields (`project_uuid`, `feature_slug`, `target_branch`, `mission_key`, `manifest_version`, optional `step_id`); missing required fields fail validation.
4. `artifact_class` has a single source of truth: `ArtifactIdentity.artifact_class`. It is NOT a top-level field on any event payload. `ArtifactIdentity.artifact_class` is constrained to the six ArtifactClass values; unknown values fail validation.
5. `manifest_version` has a single source of truth: `LocalNamespaceTuple.manifest_version`. Event payloads do not carry a separate `manifest_version` field.
6. `MissionDossierParityDriftDetected.drift_kind` is constrained to the six defined drift kinds; unknown values fail validation.
7. Reducer sorts events by `(lamport_clock, timestamp, event_id)` ascending before deduplication and reduction — identical to the three-field sort used in `mission_next.py` and `status.py`.
8. Reducer raises `NAMESPACE_MIXED_STREAM` if any event's namespace tuple differs from the first dossier event's namespace tuple. Partial reduction is not performed; the caller must partition streams by namespace before calling the reducer.
9. Reducer silently skips unknown event types without raising exceptions.
10. Duplicate events (matching `event_id`) are deduplicated before sorting and reduction.
11. JSON schemas are generated from Pydantic models; CI fails if committed schemas diverge.
12. `"dossier"` is registered in `loader.py`'s valid-category list; `load_fixtures("dossier")` succeeds without error.
13. `pyproject.toml` package-data globs include `conformance/fixtures/dossier/**/*` so fixtures are present in installed packages.
14. All 13 fixture cases load without error and produce expected validation results.
15. Both replay streams load via `load_replay_stream()` and are foldable by the reducer.
16. Conformance suite test coverage added for all five test categories in §7.6.
17. All new payload types and the reducer function are exported from `spec_kitty_events/__init__.py`.
18. CHANGELOG.md includes explicit consumer migration notes with version pins for `spec-kitty` and `spec-kitty-saas`.

---

## 10. Non-Functional Requirements

1. **Determinism**: Reducer output is byte-identical for identical event streams across Python versions and platforms (within Python 3.10+ supported range).
2. **No I/O in reducer**: Reducer is a pure function; all I/O happens at the caller layer.
3. **Backward compatibility**: No existing exports, schema files, or fixture manifests are modified incompatibly; all additions are additive.
4. **Test coverage**: New modules maintain ≥98% line coverage consistent with project policy.
5. **mypy compliance**: All new modules pass `mypy --strict` with Python 3.10 target.
6. **Schema fidelity**: Committed JSON schemas match generated output exactly (CI drift check enforced).
7. **Fixture integrity**: Invalid fixtures must produce at least one model or schema violation; valid fixtures must produce zero violations in both layers.

---

## 11. Success Criteria

1. All 13 dossier fixture cases pass the conformance loader without errors; valid/invalid expectations match actual validation results.
2. Both replay streams reduce to deterministic `MissionDossierState` output across repeated calls.
3. Five new conformance test categories (missing-artifact, parity-drift, namespace-collision, reducer-determinism, round-trip schema) execute and pass in CI.
4. `spec-kitty` and `spec-kitty-saas` can pin `spec-kitty-events>=2.4.0,<3.0.0` and import all new payload types and the reducer without modification to existing code.
5. Namespace tuple validation prevents cross-feature baseline collisions in conformance tests.
6. CHANGELOG.md version 2.4.0 section is present and includes explicit migration notes for both consumers.

---

## 12. Key Entities

| Entity | Description |
|---|---|
| `MissionDossierArtifactIndexedPayload` | Pydantic model for artifact discovery event |
| `MissionDossierArtifactMissingPayload` | Pydantic model for missing-artifact anomaly event |
| `MissionDossierSnapshotComputedPayload` | Pydantic model for dossier snapshot event |
| `MissionDossierParityDriftDetectedPayload` | Pydantic model for parity drift event |
| `ArtifactIdentity` | Provenance sub-type: canonical artifact identity |
| `ContentHashRef` | Provenance sub-type: content fingerprint |
| `ProvenanceRef` | Provenance sub-type: source trace |
| `LocalNamespaceTuple` | Provenance sub-type: parity scoping key |
| `MissionDossierState` | Reducer output: deterministic dossier projection |
| `reduce_mission_dossier` | Pure reducer function |
| `ArtifactClass` | Enum: `input`, `workflow`, `output`, `evidence`, `policy`, `runtime` |
| `DriftKind` | Enum: six drift detection categories |

---

## 13. Dependencies

1. `spec-kitty-events` 2.x codebase (branch `2.x`) — existing conformance, schemas, and models.
2. Pydantic v2 — for model definitions and schema generation.
3. `jsonschema>=4.21.0,<5.0.0` — for secondary schema validation layer (`[conformance]` extra).
4. Existing `dedup_events()` from `status.py` — reused by reducer for deduplication.
5. `generate.py` schema generation pipeline — extended for new models.
6. CI pipeline — extended with `--check` drift validation for new schemas.

---

## 14. Assumptions

1. The `2.x` branch is the authoritative development target; changes do not need to be backported to `main` until a release merge.
2. `ArtifactClass` and `DriftKind` are treated as `Literal` string constraints (not Python Enum classes) to match existing patterns in the codebase.
3. `LocalNamespaceTuple` is a standalone Pydantic model, not a type alias, to support JSON schema generation.
4. Context-transition visibility is satisfied by the optional `context_diagnostics` dict field on each event payload; no new event types are added for context transitions in this version.
5. Reducer consumes the standard `Event` envelope objects (existing spec); it does not define a new envelope format.
6. `project_uuid` is assumed to be a valid UUID string (format validation via regex or UUID type); cross-org uniqueness is not enforced in this version.
7. Fixture replay streams use the existing JSONL format and `load_replay_stream()` API with no API changes.

---

## 15. Risks

| Risk | Mitigation |
|---|---|
| Namespace tuple definition drifts between `spec-kitty`, `spec-kitty-saas`, and `spec-kitty-events` | `LocalNamespaceTuple` is the single typed source of truth; consumers import it directly |
| Reducer non-determinism under concurrent event orderings | Three-field sort key `(lamport_clock, timestamp, event_id)` guarantees stable total order; property tests (Hypothesis) verify determinism across permutations |
| Reducer silently mixing namespaces | `NAMESPACE_MIXED_STREAM` error raised immediately on namespace mismatch; no partial state is returned |
| Fixture anomaly/invalid cases accidentally pass validation | Conformance suite asserts both that invalid fixtures fail AND that valid fixtures pass; CI enforces both |
| Schema drift between Pydantic models and committed JSON files | CI `--check` mode exits 1 on any drift; no manual schema editing allowed |
| Consumer migration breakage from export naming conflicts | All new export names use `MissionDossier*` prefix; no existing names are modified |
