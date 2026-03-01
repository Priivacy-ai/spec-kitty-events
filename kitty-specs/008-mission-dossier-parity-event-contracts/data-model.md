# Data Model: Mission Dossier Parity Event Contracts

**Feature**: 008-mission-dossier-parity-event-contracts
**Date**: 2026-02-21
**Source module**: `src/spec_kitty_events/dossier.py`

---

## 1. Exception

### NamespaceMixedStreamError

```
NamespaceMixedStreamError(ValueError)
```

Raised by `reduce_mission_dossier()` when the input stream contains events with differing
`namespace` tuples. Message must include both the expected namespace (from first event) and
the offending namespace (from the conflicting event).

Exported from `__init__.py`.

---

## 2. Provenance Sub-Types (Value Objects)

All models: `ConfigDict(frozen=True)`.

### LocalNamespaceTuple

Minimum collision-safe key for parity baseline scoping.

| Field | Type | Required | Constraints |
|---|---|---|---|
| `project_uuid` | `str` | yes | `min_length=1`; expected UUID format |
| `feature_slug` | `str` | yes | `min_length=1` |
| `target_branch` | `str` | yes | `min_length=1` |
| `mission_key` | `str` | yes | `min_length=1` |
| `manifest_version` | `str` | yes | `min_length=1`; semver string |
| `step_id` | `Optional[str]` | no | default `None` |

**Identity key**: all six fields form the collision-safe key. Two `LocalNamespaceTuple` instances
with identical values across all six fields are considered the same namespace.

### ArtifactIdentity

Canonical identity for one artifact instance.

| Field | Type | Required | Constraints |
|---|---|---|---|
| `mission_key` | `str` | yes | `min_length=1` |
| `path` | `str` | yes | `min_length=1`; repository-relative path |
| `artifact_class` | `Literal[...]` | yes | one of `"input"`, `"workflow"`, `"output"`, `"evidence"`, `"policy"`, `"runtime"` |
| `run_id` | `Optional[str]` | no | default `None` |
| `wp_id` | `Optional[str]` | no | default `None` |

**Single source of truth**: `artifact_class` is defined exclusively in `ArtifactIdentity`;
no event payload duplicates this field at the top level.

### ContentHashRef

Content fingerprint with optional size and encoding metadata.

| Field | Type | Required | Constraints |
|---|---|---|---|
| `hash` | `str` | yes | `min_length=1`; hex-encoded |
| `algorithm` | `Literal[...]` | yes | one of `"sha256"`, `"sha512"`, `"md5"` |
| `size_bytes` | `Optional[int]` | no | `ge=0`; default `None` |
| `encoding` | `Optional[str]` | no | default `None` |

### ProvenanceRef

Source trace linking artifact to authoritative origin.

| Field | Type | Required | Constraints |
|---|---|---|---|
| `source_event_ids` | `Optional[Tuple[str, ...]]` | no | default `None` |
| `git_sha` | `Optional[str]` | no | default `None` |
| `git_ref` | `Optional[str]` | no | default `None` |
| `actor_id` | `Optional[str]` | no | default `None` |
| `actor_kind` | `Optional[Literal["human", "llm", "system"]]` | no | default `None` |
| `revised_at` | `Optional[str]` | no | ISO 8601 string; default `None` |

---

## 3. Event Payload Models

All models: `ConfigDict(frozen=True)`.

### MissionDossierArtifactIndexedPayload

| Field | Type | Required | Notes |
|---|---|---|---|
| `namespace` | `LocalNamespaceTuple` | yes | Carries `manifest_version` — not duplicated at top level |
| `artifact_id` | `ArtifactIdentity` | yes | Carries `artifact_class` — not duplicated at top level |
| `content_ref` | `ContentHashRef` | yes | |
| `indexed_at` | `str` | yes | ISO 8601 |
| `provenance` | `Optional[ProvenanceRef]` | no | |
| `step_id` | `Optional[str]` | no | Mission YAML step ID |
| `supersedes` | `Optional[ArtifactIdentity]` | no | Prior version replaced by this artifact |
| `context_diagnostics` | `Optional[Dict[str, str]]` | no | Context-transition visibility |

### MissionDossierArtifactMissingPayload

| Field | Type | Required | Notes |
|---|---|---|---|
| `namespace` | `LocalNamespaceTuple` | yes | |
| `expected_identity` | `ArtifactIdentity` | yes | Carries `path` + `artifact_class` of missing artifact |
| `manifest_step` | `str` | yes | `"required_always"` or step_id string |
| `checked_at` | `str` | yes | ISO 8601 |
| `last_known_ref` | `Optional[ProvenanceRef]` | no | |
| `remediation_hint` | `Optional[str]` | no | |
| `context_diagnostics` | `Optional[Dict[str, str]]` | no | |

### MissionDossierSnapshotComputedPayload

| Field | Type | Required | Notes |
|---|---|---|---|
| `namespace` | `LocalNamespaceTuple` | yes | Carries `manifest_version` — not duplicated at top level |
| `snapshot_hash` | `str` | yes | Hex-encoded deterministic hash |
| `artifact_count` | `int` | yes | `ge=0` |
| `anomaly_count` | `int` | yes | `ge=0` |
| `computed_at` | `str` | yes | ISO 8601 |
| `algorithm` | `Optional[Literal["sha256", "sha512", "md5"]]` | no | default `"sha256"` |
| `context_diagnostics` | `Optional[Dict[str, str]]` | no | |

### MissionDossierParityDriftDetectedPayload

| Field | Type | Required | Notes |
|---|---|---|---|
| `namespace` | `LocalNamespaceTuple` | yes | |
| `expected_hash` | `str` | yes | Baseline hash |
| `actual_hash` | `str` | yes | Current computed hash |
| `drift_kind` | `Literal[...]` | yes | One of the six drift kinds |
| `detected_at` | `str` | yes | ISO 8601 |
| `artifact_ids_changed` | `Optional[Tuple[ArtifactIdentity, ...]]` | no | |
| `rebuild_hint` | `Optional[str]` | no | |
| `context_diagnostics` | `Optional[Dict[str, str]]` | no | |

**DriftKind values**: `"artifact_added"`, `"artifact_removed"`, `"artifact_mutated"`,
`"anomaly_introduced"`, `"anomaly_resolved"`, `"manifest_version_changed"`

---

## 4. Reducer Output Models

All models: `ConfigDict(frozen=True)`.

### ArtifactEntry

One artifact slot in the projected dossier.

| Field | Type | Required | Notes |
|---|---|---|---|
| `identity` | `ArtifactIdentity` | yes | |
| `content_ref` | `ContentHashRef` | yes | Most recent version |
| `indexed_at` | `str` | yes | ISO 8601 of most recent indexing |
| `provenance` | `Optional[ProvenanceRef]` | no | |
| `superseded` | `bool` | yes | `True` if a newer version has been indexed |
| `step_id` | `Optional[str]` | no | |

### AnomalyEntry

One active anomaly in the projected dossier.

| Field | Type | Required | Notes |
|---|---|---|---|
| `anomaly_type` | `Literal["missing_artifact"]` | yes | Extensible in future versions |
| `expected_identity` | `ArtifactIdentity` | yes | |
| `manifest_step` | `str` | yes | |
| `checked_at` | `str` | yes | ISO 8601 |
| `remediation_hint` | `Optional[str]` | no | |

### SnapshotSummary

Summary of the most recently computed dossier snapshot.

| Field | Type | Required | Notes |
|---|---|---|---|
| `snapshot_hash` | `str` | yes | |
| `artifact_count` | `int` | yes | |
| `anomaly_count` | `int` | yes | |
| `computed_at` | `str` | yes | ISO 8601 |
| `algorithm` | `str` | yes | default `"sha256"` |

### DriftRecord

One entry in the drift history.

| Field | Type | Required | Notes |
|---|---|---|---|
| `expected_hash` | `str` | yes | |
| `actual_hash` | `str` | yes | |
| `drift_kind` | `str` | yes | DriftKind value |
| `detected_at` | `str` | yes | ISO 8601 |

### MissionDossierState

Top-level reducer output. Root projection of all dossier events.

| Field | Type | Required | Notes |
|---|---|---|---|
| `namespace` | `Optional[LocalNamespaceTuple]` | no | `None` if stream had no dossier events |
| `artifacts` | `Dict[str, ArtifactEntry]` | yes | Key: `artifact_identity.path` |
| `anomalies` | `Tuple[AnomalyEntry, ...]` | yes | All active anomalies |
| `latest_snapshot` | `Optional[SnapshotSummary]` | no | Most recent snapshot |
| `drift_history` | `Tuple[DriftRecord, ...]` | yes | All drift events in order |
| `parity_status` | `Literal["clean", "drifted", "unknown"]` | yes | Derived from reducer state |
| `event_count` | `int` | yes | Total dossier events processed (after dedup) |

**`parity_status` derivation**:
- `"clean"` — at least one snapshot computed AND no drift events seen since latest snapshot
- `"drifted"` — at least one drift event seen; or drift event after latest snapshot
- `"unknown"` — no snapshot computed yet (initial state)

---

## 5. Event Type Constants

```python
MISSION_DOSSIER_ARTIFACT_INDEXED: str = "MissionDossierArtifactIndexed"
MISSION_DOSSIER_ARTIFACT_MISSING: str = "MissionDossierArtifactMissing"
MISSION_DOSSIER_SNAPSHOT_COMPUTED: str = "MissionDossierSnapshotComputed"
MISSION_DOSSIER_PARITY_DRIFT_DETECTED: str = "MissionDossierParityDriftDetected"

DOSSIER_EVENT_TYPES: FrozenSet[str] = frozenset({
    MISSION_DOSSIER_ARTIFACT_INDEXED,
    MISSION_DOSSIER_ARTIFACT_MISSING,
    MISSION_DOSSIER_SNAPSHOT_COMPUTED,
    MISSION_DOSSIER_PARITY_DRIFT_DETECTED,
})
```

---

## 6. Conformance Wiring

### loader.py

```python
_VALID_CATEGORIES = frozenset({
    "events", "lane_mapping", "edge_cases",
    "collaboration", "glossary", "mission_next",
    "dossier",  # ← ADD
})
```

### validators.py additions

```python
_EVENT_TYPE_TO_MODEL additions:
    "MissionDossierArtifactIndexed":    MissionDossierArtifactIndexedPayload,
    "MissionDossierArtifactMissing":    MissionDossierArtifactMissingPayload,
    "MissionDossierSnapshotComputed":   MissionDossierSnapshotComputedPayload,
    "MissionDossierParityDriftDetected": MissionDossierParityDriftDetectedPayload,

_EVENT_TYPE_TO_SCHEMA additions:
    "MissionDossierArtifactIndexed":    "mission_dossier_artifact_indexed_payload",
    "MissionDossierArtifactMissing":    "mission_dossier_artifact_missing_payload",
    "MissionDossierSnapshotComputed":   "mission_dossier_snapshot_computed_payload",
    "MissionDossierParityDriftDetected": "mission_dossier_parity_drift_detected_payload",
```

### pyproject.toml additions

```toml
"conformance/fixtures/dossier/valid/*.json",
"conformance/fixtures/dossier/invalid/*.json",
"conformance/fixtures/dossier/replay/*.jsonl",
```
