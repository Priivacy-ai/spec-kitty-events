# Mission Dossier Consumer Contract v2.4.0

This document freezes the consumer contract for Mission Dossier events in `spec-kitty-events` v2.4.0.

## Canonical event types

- `MissionDossierArtifactIndexed`
- `MissionDossierArtifactMissing`
- `MissionDossierSnapshotComputed`
- `MissionDossierParityDriftDetected`

## Namespace identity contract

Namespace identity is the 5-tuple:

- `project_uuid`
- `feature_slug`
- `target_branch`
- `mission_key`
- `manifest_version`

`step_id` is **contextual** and is explicitly excluded from namespace identity.

## Required payload anchors by type

- `MissionDossierArtifactIndexed`: `namespace`, `artifact_id`, `content_ref`, `indexed_at`
- `MissionDossierArtifactMissing`: `namespace`, `expected_identity`, `manifest_step`, `checked_at`
- `MissionDossierSnapshotComputed`: `namespace`, `snapshot_hash`, `artifact_count`, `anomaly_count`, `computed_at`
- `MissionDossierParityDriftDetected`: `namespace`, `expected_hash`, `actual_hash`, `drift_kind`, `detected_at`

## Content transport constraint

Events carry only content references (`content_ref.hash`, provenance metadata) and **must not** embed raw markdown bodies.

## Payload freeze statement

For all consumers in the 2.4.x line, field names and semantic meanings above are considered frozen. Any incompatible change requires a versioned contract bump.

## Consumer verification steps

1. Validate event envelope + payload via conformance validator.
2. Replay `dossier/replay/dossier_happy_path.jsonl` through reducer.
3. Compare reducer output to `dossier/replay/canonical_output_snapshot.json`.
