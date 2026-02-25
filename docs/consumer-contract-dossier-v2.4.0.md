# Consumer Contract: Mission Dossier Events — v2.4.0

**Status**: Payload shape FROZEN for this release wave.
**Package**: `spec-kitty-events==2.4.0`

---

## 1. Event Types

| Event Type | Constant | Description |
|---|---|---|
| `MissionDossierArtifactIndexed` | `MISSION_DOSSIER_ARTIFACT_INDEXED` | An artifact has been indexed into the dossier |
| `MissionDossierArtifactMissing` | `MISSION_DOSSIER_ARTIFACT_MISSING` | An expected artifact was not found |
| `MissionDossierSnapshotComputed` | `MISSION_DOSSIER_SNAPSHOT_COMPUTED` | A deterministic snapshot of dossier state was computed |
| `MissionDossierParityDriftDetected` | `MISSION_DOSSIER_PARITY_DRIFT_DETECTED` | A parity drift was detected between snapshots |

All four types are members of `DOSSIER_EVENT_TYPES` (frozenset).

---

## 2. Required Fields per Event Type

### MissionDossierArtifactIndexed

| Field | Type | Required | Notes |
|---|---|---|---|
| `namespace` | `LocalNamespaceTuple` | yes | 5-tuple + optional step_id |
| `artifact_id` | `ArtifactIdentity` | yes | Carries artifact_class |
| `content_ref` | `ContentHashRef` | yes | Hash + algorithm |
| `indexed_at` | `str` (ISO 8601) | yes | |
| `provenance` | `ProvenanceRef` | no | |
| `step_id` | `str` | no | Per-artifact step context |
| `supersedes` | `ArtifactIdentity` | no | Prior version identity |
| `context_diagnostics` | `Dict[str, str]` | no | |

### MissionDossierArtifactMissing

| Field | Type | Required | Notes |
|---|---|---|---|
| `namespace` | `LocalNamespaceTuple` | yes | |
| `expected_identity` | `ArtifactIdentity` | yes | Path + class of missing artifact |
| `manifest_step` | `str` | yes | `"required_always"` or step_id |
| `checked_at` | `str` (ISO 8601) | yes | |
| `last_known_ref` | `ProvenanceRef` | no | |
| `remediation_hint` | `str` | no | |
| `context_diagnostics` | `Dict[str, str]` | no | |

### MissionDossierSnapshotComputed

| Field | Type | Required | Notes |
|---|---|---|---|
| `namespace` | `LocalNamespaceTuple` | yes | manifest_version lives here only |
| `snapshot_hash` | `str` | yes | Hex-encoded deterministic hash |
| `artifact_count` | `int` (≥0) | yes | |
| `anomaly_count` | `int` (≥0) | yes | |
| `computed_at` | `str` (ISO 8601) | yes | |
| `algorithm` | `AlgorithmT` | no | Default: `"sha256"` |
| `context_diagnostics` | `Dict[str, str]` | no | |

### MissionDossierParityDriftDetected

| Field | Type | Required | Notes |
|---|---|---|---|
| `namespace` | `LocalNamespaceTuple` | yes | |
| `expected_hash` | `str` | yes | |
| `actual_hash` | `str` | yes | |
| `drift_kind` | `DriftKindT` | yes | See allowed values below |
| `detected_at` | `str` (ISO 8601) | yes | |
| `artifact_ids_changed` | `Tuple[ArtifactIdentity, ...]` | no | |
| `rebuild_hint` | `str` | no | |
| `context_diagnostics` | `Dict[str, str]` | no | |

**DriftKindT values**: `"artifact_added"`, `"artifact_removed"`, `"artifact_mutated"`, `"anomaly_introduced"`, `"anomaly_resolved"`, `"manifest_version_changed"`

---

## 3. Namespace Identity

Namespace identity is a **5-tuple**:

```
(project_uuid, feature_slug, target_branch, mission_key, manifest_version)
```

`step_id` is **NOT** part of namespace identity. It is optional per-event context. When a stream contains events with multiple distinct `step_id` values, the reducer normalizes `namespace.step_id` to `None` in the output state.

The reducer raises `NamespaceMixedStreamError` if events span multiple 5-tuple namespaces.

---

## 4. Content Constraint

Dossier events carry **hash and provenance references only** — no markdown body content. The `content_ref` field contains a hex-encoded content hash, algorithm identifier, and optional size/encoding metadata. Actual file content is never embedded in event payloads.

---

## 5. Payload Shape Freeze

The field schemas defined above are **frozen for the v2.4.0 release wave**. No further field additions, removals, or type changes will occur within this version. Consumers can depend on these shapes without risk of churn.

Breaking changes (field removal, type change, namespace identity mutation) require a semver major bump per SyncLaneV1 mapping rules.

---

## 6. Upgrade Instructions

### Install

```bash
pip install "spec-kitty-events==2.4.0"
```

### Verify installation

```python
from spec_kitty_events.dossier import (
    DOSSIER_EVENT_TYPES,
    reduce_mission_dossier,
    MissionDossierState,
    LocalNamespaceTuple,
)

# Confirm all 4 event types present
assert len(DOSSIER_EVENT_TYPES) == 4
```

### Verify reducer against canonical fixture

```python
import json
from importlib.resources import files

from spec_kitty_events.conformance import load_replay_stream
from spec_kitty_events.dossier import reduce_mission_dossier
from spec_kitty_events.models import Event

# Load and reduce happy-path fixture
raw = load_replay_stream("dossier-replay-happy-path")
events = [Event(**e) for e in raw]
state = reduce_mission_dossier(events)

# Load canonical expected output
fixture_path = (
    files("spec_kitty_events.conformance.fixtures.dossier.replay")
    / "canonical_output_snapshot.json"
)
expected = json.loads(fixture_path.read_text())

# Compare
assert state.model_dump(mode="json") == expected, "Reducer output does not match canonical snapshot"
```

### Downstream repo integration

Both downstream repos should:
1. Add `spec-kitty-events>=2.4.0,<3.0.0` to their dependencies
2. Import and use the `reduce_mission_dossier()` reducer for event processing
3. Run the canonical fixture verification above as a CI smoke test
