# Decision Moment `01M0FTVXSW7FW2SZC9F2QWS9BP`

- **Mission:** `dossier-invalid-fixture-coverage-01M0FSN4`
- **Origin flow:** `plan`
- **Slot key:** `plan.fixtures.violation-choice`
- **Input key:** `violation_choice`
- **Status:** `resolved`
- **Created:** `2026-08-20T14:58:09.852116+00:00`
- **Resolved:** `2026-08-20T15:01:03.705029+00:00`
- **Opened by:** `cli`
- **Other answer:** `false`

## Question

Which specific violation should each new invalid fixture exercise? (ArtifactMissing: manifest_step empty string, violating min_length=1. SnapshotComputed: pick one of negative artifact_count/anomaly_count violating ge=0, or an invalid algorithm literal.)

## Options

- SnapshotComputed: negative artifact_count
- SnapshotComputed: invalid algorithm literal
- Other

## Final answer

ArtifactMissing: manifest_step empty string (min_length=1 violation). SnapshotComputed: negative artifact_count (ge=0 violation) — chosen over invalid algorithm literal to keep the violation category distinct from the existing enum/Literal fixture.

## Rationale

_(none)_

## Change log

- `2026-08-20T14:58:09.852116+00:00` — opened
- `2026-08-20T15:01:03.705029+00:00` — resolved (final_answer="ArtifactMissing: manifest_step empty string (min_length=1 violation). SnapshotComputed: negative artifact_count (ge=0 violation) — chosen over invalid algorithm literal to keep the violation category distinct from the existing enum/Literal fixture.")
