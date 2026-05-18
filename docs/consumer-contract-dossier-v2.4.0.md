# Consumer Contract: Mission Dossier Events — v2.4.0

> Archived historical document.
>
> This page describes the pre-cutover `2.4.0` dossier contract and is not
> current consumer guidance for `spec-kitty-events` `3.0.0`.
>
> The canonical live contract now uses the `3.0.0` cutover artifact, fail-closed
> validation, and canonical mission taxonomy. In particular, public live
> contracts should not treat `feature_slug` or `mission_key` as canonical
> mission-domain fields.

**Status**: Archived historical reference only.
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

---

## 7. Backward Transitions: The Review-Rejection Family

The **review-rejection transition family** is the named set of legitimate
forced backward lane transitions in `WPStatusChanged` events:

| `from_lane`   | `to_lane` |
|---------------|-----------|
| `in_progress` | `planned` |
| `for_review`  | `planned` |
| `in_review`   | `planned` |
| `approved`    | `planned` |

These transitions arise from user-deliberate rewinds in the work-package
lifecycle — most commonly a review rejection that returns a WP to `planned`
for re-implementation. They are not infrastructure events and they are not
graph errors.

### Wire requirements

For every event in the family, the emitting agent MUST set:

1. `force = True` — explicit acknowledgement that the transition is a
   user-deliberate rewind, not a forward step.
2. `reason` — a non-empty string. Enforced by the existing
   `StatusTransitionPayload` model validator
   (`force=True requires a non-empty reason`).

Recommended canonical `reason` shape:

```
backward rewind: <from_lane> -> <to_lane>[: <feedback-ref>]
```

- `<from_lane>` / `<to_lane>` are the literal `Lane` enum values.
- `<feedback-ref>` is optional. When present, the recommended URI shape is
  `feedback://<mission-slug>/<wp-id>/<timestamp>-<hash>.md`.

Optional but recommended:

- `review_ref` — URI-shaped pointer to the review feedback artifact. Same
  value as `<feedback-ref>` above when both are populated.
- A separate `ForceMetadata` record carrying the structured
  `(actor, reason)` audit pair, attached at the carrying `Event` envelope
  level. Consumers MAY rely on payload `reason` alone; `ForceMetadata` is
  for structured audit pipelines.

The wire payload shape is otherwise unchanged from
`StatusTransitionPayload`. No new fields, no removed fields.

### Unforced backward transitions are contract-invalid

A `WPStatusChanged` event with a `from_lane → to_lane` pair drawn from the
family table but `force = False` is **contract-invalid**.

The four family pairs enforced by the guard are:

| `from_lane`   | `to_lane` |
|---------------|-----------|
| `in_progress` | `planned` |
| `for_review`  | `planned` |
| `in_review`   | `planned` |
| `approved`    | `planned` |

- `validate_transition()` rejects such events via the **explicit
  review-rejection family guard**, which runs ahead of (and independent
  of) the lane matrix check. The guard fires regardless of whether
  `review_ref` or `reason` are populated, so the failure isolates to the
  missing `force = True`.
- The emitted violation message names the family explicitly. Consumers
  MAY route on the canonical substrings ``force=True`` and
  ``review-rejection`` in the violation list — both substrings are part
  of the published contract.
- Bootstrap-planned events (`from_lane = None`, `to_lane = planned`,
  `force = True`) are NOT part of the review-rejection family and are
  NOT subject to this guard; see the bootstrap-planned section below.
- Consumers (materializers, projection engines, durable drain workers) MAY
  reject these events as graph violations and SHOULD classify them as
  **business-rule rejections**, not transient infrastructure failures.
- The CLI emit path in `spec-kitty` MUST NOT produce unforced backward
  transitions: either fail locally with a guidance message, or
  auto-promote `force=True` and synthesize a canonical `reason` per the
  recommended shape.

### Relationship to `ReviewRollback`

`ReviewRollbackPayload` (declared in `src/spec_kitty_events/lifecycle.py`)
is a **mission-level** event recording the higher-level intent of a review
rejection (`mission_id`, `review_ref`, `target_phase`, `affected_wp_ids`,
`actor`). It is NOT a substitute for the per-WP `WPStatusChanged` events
in the family. The two are complementary records:

- `ReviewRollback` = "the mission rolled back to phase X because of review
  Y, affecting WPs [A, B, C]".
- `WPStatusChanged(force=True, ...)` per affected WP = "WP-A moved from
  `in_review` to `planned` as part of that rollback".

Consumers projecting state should reduce both event streams. Emitters MAY
emit only the per-WP `WPStatusChanged` events when no mission-level
rollback occurred (e.g. a single reviewer rejecting a single WP).

### Distinction from bootstrap-planned events

A forced `* → planned` transition with `from_lane = None` is a
**bootstrap-planned event**, not a review-rejection. The contract
distinguishes them:

- Bootstrap-planned: `from_lane is None`, `to_lane = planned`,
  `force = True`, `reason` typically explains initial seeding. Identified
  by `is_bootstrap_planned_event()`.
- Review-rejection family member:
  `from_lane in {in_progress, for_review, in_review, approved}`,
  `to_lane = planned`, `force = True`, `reason` follows the recommended
  backward-rewind shape.

A consumer must not classify a bootstrap-planned event as a review
rejection or vice versa.

### Forward-transition guards unaffected

Forward-transition guard semantics — including but not limited to
`planned → claimed`, `in_progress → for_review`, `in_review → approved` —
are unchanged by this contract section. `force = True` is reserved for
documented backward families and terminal-lane exits. It MUST NOT be used
to bypass forward guards or evidence requirements.

### Conformance fixtures

| Manifest id | Path | Purpose |
|---|---|---|
| `wp-review-rejection-cycle-replay` | `src/spec_kitty_events/conformance/fixtures/edge_cases/replay/wp_review_rejection_cycle.jsonl` | Full lifecycle replay stream including one review-rejection round-trip (`planned → claimed → in_progress → for_review → in_review → planned → claimed → in_progress → for_review → in_review → approved`). |
| `wp-status-changed-approved-rewind-valid` | `src/spec_kitty_events/conformance/fixtures/edge_cases/valid/wp_status_changed_approved_rewind.json` | Positive single-event `approved → planned` with `force=True` + reason (synthetic minimal mirror of the planning#16 evidence-pack shape). |
| `wp-status-changed-unforced-in-review-to-planned-invalid` | `src/spec_kitty_events/conformance/fixtures/edge_cases/invalid/wp_status_changed_unforced_in_review_to_planned.json` | Negative single-event `in_review → planned` with `force=False`. Validator MUST reject. |

Sibling missions cite these by manifest id when authoring regression
tests.

### Cross-references

- Mirror section: `src/spec_kitty_events/status.py` module docstring —
  "Review-Rejection Transition Family".
- Pydantic model: `StatusTransitionPayload`.
- Validator: `validate_transition()`.
- Bootstrap discriminator: `is_bootstrap_planned_event()`.
- Mission-level rollback event: `ReviewRollbackPayload`
  (`src/spec_kitty_events/lifecycle.py`).
- Planning issue: `Priivacy-ai/spec-kitty-planning#16`.
