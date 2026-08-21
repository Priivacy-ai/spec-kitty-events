# Data Model: Dossier Invalid Fixture Coverage

No new domain entities, payload models, or schema fields are introduced by this mission (spec C-001). This document describes the two new fixture artifacts and the manifest entries that register them — the only data this mission adds.

## Entity: Invalid conformance fixture (JSON file)

A JSON file under `src/spec_kitty_events/conformance/fixtures/dossier/invalid/` representing a `MissionDossier*` payload that must fail `validate_event()`. Structurally a plain payload dict matching the target Pydantic model's field shape, with exactly one field/rule deliberately broken and everything else identical to a valid sibling fixture.

**Invariant**: Exactly one constraint violated per fixture; the violation must target an actively-enforced Pydantic constraint (`Literal`, `min_length`, `ge`, `extra="forbid"`), never a docstring-only convention (e.g. an ISO-8601 timestamp field, which is a plain unconstrained `str` in every dossier payload model and would silently validate regardless of format).

### Fixture 1: `dossier_artifact_missing_empty_step.json`

Payload for `MissionDossierArtifactMissingPayload`. Modeled on the existing valid fixture `dossier_artifact_missing_required_always.json`, with one field changed:

| Field | Value | Note |
|---|---|---|
| `namespace` | (same as valid sibling) | `LocalNamespaceTuple` — untouched |
| `expected_identity` | (same as valid sibling) | `ArtifactIdentity` — untouched |
| `manifest_step` | `""` (empty string) | **Violation**: `min_length=1` on this field (`dossier.py:143-147`) rejects it |
| `checked_at` | (same as valid sibling) | Plain `str`, no format validator — left as a valid-looking ISO-8601 string since it is not the intended violation target |

### Fixture 2: `dossier_snapshot_computed_negative_count.json`

Payload for `MissionDossierSnapshotComputedPayload`. Modeled on the existing valid fixture `dossier_snapshot_computed_clean.json`, with one field changed:

| Field | Value | Note |
|---|---|---|
| `namespace` | (same as valid sibling) | `LocalNamespaceTuple` — untouched |
| `snapshot_hash` | (same as valid sibling) | Untouched |
| `artifact_count` | `-1` | **Violation**: `ge=0` on this field (`dossier.py:171`) rejects it |
| `anomaly_count` | `0` (same as valid sibling) | Left valid — only one field is broken |
| `computed_at` | (same as valid sibling) | Untouched |
| `algorithm` | `"sha256"` (same as valid sibling) | Left valid — this mission does not use an invalid-`Literal` violation here (see research.md rationale) |

## Entity: Manifest entry (`fixtures/manifest.json` array element)

Existing schema (unchanged), one entry per fixture:

| Field | Type | Value for Fixture 1 | Value for Fixture 2 |
|---|---|---|---|
| `id` | string | `dossier-artifact-missing-empty-step` | `dossier-snapshot-computed-negative-count` |
| `path` | string | `dossier/invalid/dossier_artifact_missing_empty_step.json` | `dossier/invalid/dossier_snapshot_computed_negative_count.json` |
| `event_type` | string | `MissionDossierArtifactMissing` | `MissionDossierSnapshotComputed` |
| `expected_result` | string | `invalid` | `invalid` |
| `notes` | string | `manifest_step is an empty string — violates min_length=1` | `artifact_count is negative (-1) — violates ge=0` |
| `min_version` | string | `2.4.0` (matches every other dossier entry) | `2.4.0` |

**Invariant**: Every file under `fixtures/dossier/invalid/` has exactly one corresponding manifest entry, and vice versa (NFR-002) — `load_fixtures()` has no other way to discover a fixture.

## State / relationships

None — these are static golden fixtures with no lifecycle, no relationships to other entities, and no state transitions. They are consumed once per test run by `load_fixtures("dossier")` and passed through `validate_event()`.
