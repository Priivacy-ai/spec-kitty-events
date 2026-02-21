---
work_package_id: "WP03"
subtasks:
  - "T014"
  - "T015"
  - "T016"
  - "T017"
  - "T018"
  - "T019"
title: "Dossier Fixtures"
phase: "Phase 1 - Foundation"
lane: "planned"
assignee: ""
agent: ""
shell_pid: ""
review_status: ""
reviewed_by: ""
dependencies: ["WP01"]
history:
  - timestamp: "2026-02-21T14:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP03 – Dossier Fixtures

## ⚠️ IMPORTANT: Review Feedback Status

Check `review_status` field above. If `has_feedback`, see Review Feedback section.

---

## Review Feedback

*[Empty initially.]*

---

## Markdown Formatting
Wrap HTML/XML tags in backticks. Use language identifiers in code blocks.

---

## Objectives & Success Criteria

Create the full `dossier/` fixture set: 10 valid JSON fixtures, 3 invalid JSON fixtures, 2 JSONL replay streams, and updated `manifest.json` entries. These fixtures are the shared test data that both `spec-kitty` and `spec-kitty-saas` consumers can reference directly.

**Acceptance gates**:
- [ ] `load_fixtures("dossier")` returns exactly 13 `FixtureCase` objects (no `FileNotFoundError`)
- [ ] `load_replay_stream("dossier-replay-happy-path")` returns a list of ≥5 event dicts
- [ ] `load_replay_stream("dossier-replay-drift-scenario")` returns a list of ≥4 event dicts
- [ ] All 10 valid fixture payloads pass Pydantic validation for their declared event type
- [ ] All 3 invalid fixture payloads fail Pydantic validation (produce ≥1 model violation)

## Context & Constraints

- **Depends on**: WP01 (event type strings and field names must be stable). WP02 wiring is NOT required — fixtures are authored from spec knowledge, not runtime validation.
- **Can run in parallel with WP02** after WP01 completes.
- **Fixture file location**: `src/spec_kitty_events/conformance/fixtures/dossier/`
- **Manifest location**: `src/spec_kitty_events/conformance/fixtures/manifest.json`
- **Naming**: fixture files use snake_case (`dossier_artifact_indexed_valid.json`); manifest `id` fields use kebab-case (`dossier-artifact-indexed-valid`).
- **Key invariant from spec review**: `artifact_class` lives in `artifact_id` (for Indexed events) or `expected_identity` (for Missing events) — NEVER at the top level of any payload.
- **Key invariant**: `manifest_version` lives ONLY in `namespace.manifest_version` — NOT in event payloads.

**Implementation command**:
```bash
spec-kitty implement WP03 --base WP01
```

## Subtasks & Detailed Guidance

### Subtask T014 – Create dossier fixture directory structure

- **Purpose**: Establish the three subdirectories needed before writing fixture files.
- **Steps**:
  ```bash
  mkdir -p src/spec_kitty_events/conformance/fixtures/dossier/valid
  mkdir -p src/spec_kitty_events/conformance/fixtures/dossier/invalid
  mkdir -p src/spec_kitty_events/conformance/fixtures/dossier/replay
  ```
  Add `.gitkeep` files or write the first fixture file to each directory immediately (git won't track empty dirs).
- **Files**: 3 new directories

### Subtask T015 – Write 10 valid fixture JSON files

- **Purpose**: Provide happy-path, edge-case, and variant fixture payloads that demonstrate correct dossier event contracts.
- **Steps**: Create each file in `src/spec_kitty_events/conformance/fixtures/dossier/valid/`. All payloads must be **the event payload only** (not the full Event envelope) — matching the existing fixture format used by other categories.

  **Required namespace stub** (reuse in every fixture):
  ```json
  "namespace": {
    "project_uuid": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "feature_slug": "008-mission-dossier-parity-event-contracts",
    "target_branch": "2.x",
    "mission_key": "software-dev",
    "manifest_version": "1.0.0"
  }
  ```

  **Required ArtifactIdentity stub**:
  ```json
  "artifact_id": {
    "mission_key": "software-dev",
    "path": "kitty-specs/008-mission-dossier-parity-event-contracts/spec.md",
    "artifact_class": "input"
  }
  ```

  **File 1**: `dossier_artifact_indexed_valid.json` — minimal happy-path indexed artifact
  ```json
  {
    "namespace": { ...namespace stub... },
    "artifact_id": {
      "mission_key": "software-dev",
      "path": "kitty-specs/008-mission-dossier-parity-event-contracts/spec.md",
      "artifact_class": "input"
    },
    "content_ref": {
      "hash": "abc123def456",
      "algorithm": "sha256"
    },
    "indexed_at": "2026-02-21T14:00:00Z"
  }
  ```
  Event type: `MissionDossierArtifactIndexed`

  **File 2**: `dossier_artifact_indexed_supersedes.json` — artifact replacing prior version
  Same as File 1 but add:
  ```json
  "supersedes": {
    "mission_key": "software-dev",
    "path": "kitty-specs/008-mission-dossier-parity-event-contracts/spec.md",
    "artifact_class": "input"
  }
  ```
  Increment `hash` to `"def456abc789"`.

  **File 3**: `dossier_artifact_indexed_with_provenance.json` — full provenance populated
  Add to File 1:
  ```json
  "provenance": {
    "git_sha": "a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2",
    "git_ref": "2.x",
    "actor_id": "claude-sonnet-4-6",
    "actor_kind": "llm",
    "revised_at": "2026-02-21T14:00:00Z"
  },
  "step_id": "specify"
  ```

  **File 4**: `dossier_artifact_missing_required_always.json` — required_always completeness check
  ```json
  {
    "namespace": { ...namespace stub... },
    "expected_identity": {
      "mission_key": "software-dev",
      "path": "kitty-specs/008-mission-dossier-parity-event-contracts/plan.md",
      "artifact_class": "workflow"
    },
    "manifest_step": "required_always",
    "checked_at": "2026-02-21T14:05:00Z"
  }
  ```
  Event type: `MissionDossierArtifactMissing`

  **File 5**: `dossier_artifact_missing_required_by_step.json` — step-scoped completeness check
  Same as File 4 but `manifest_step: "plan"` (a step_id string).

  **File 6**: `dossier_snapshot_computed_clean.json` — zero anomaly snapshot
  ```json
  {
    "namespace": { ...namespace stub... },
    "snapshot_hash": "deadbeef1234deadbeef1234deadbeef12345678",
    "artifact_count": 3,
    "anomaly_count": 0,
    "computed_at": "2026-02-21T14:10:00Z",
    "algorithm": "sha256"
  }
  ```
  Event type: `MissionDossierSnapshotComputed`

  **File 7**: `dossier_snapshot_computed_with_anomalies.json` — non-zero anomaly count
  Same as File 6 but `anomaly_count: 1`, `artifact_count: 2`.

  **File 8**: `dossier_parity_drift_artifact_added.json` — drift kind artifact_added
  ```json
  {
    "namespace": { ...namespace stub... },
    "expected_hash": "deadbeef1234deadbeef1234deadbeef12345678",
    "actual_hash": "cafebabe5678cafebabe5678cafebabe56789012",
    "drift_kind": "artifact_added",
    "detected_at": "2026-02-21T14:15:00Z"
  }
  ```
  Event type: `MissionDossierParityDriftDetected`

  **File 9**: `dossier_parity_drift_artifact_mutated.json` — drift kind artifact_mutated
  Same as File 8 but `drift_kind: "artifact_mutated"` and different `actual_hash`.

  **File 10**: `dossier_namespace_collision_coverage.json` — two distinct namespace tuples (valid payload; used by namespace collision test)
  Use `MissionDossierArtifactIndexedPayload` format as a single valid fixture with an alternate `feature_slug` (for example `009-another-feature`). This fixture pairs with another valid indexed fixture that uses the standard namespace to prove tuple uniqueness in namespace-collision tests.
  ```json
  {
    "namespace": {
      "project_uuid": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
      "feature_slug": "009-another-feature",
      "target_branch": "2.x",
      "mission_key": "software-dev",
      "manifest_version": "1.0.0"
    },
    "artifact_id": {
      "mission_key": "software-dev",
      "path": "kitty-specs/009-another-feature/spec.md",
      "artifact_class": "input"
    },
    "content_ref": { "hash": "fedcba987654", "algorithm": "sha256" },
    "indexed_at": "2026-02-21T14:20:00Z"
  }
  ```

- **Files**: 10 JSON files in `dossier/valid/`
- **Parallel?**: Yes — can be written alongside T016 and T017.

### Subtask T016 – Write 3 invalid fixture JSON files

- **Purpose**: Provide invalid payloads that fail Pydantic/schema validation, used by conformance tests to verify that the validator correctly rejects bad input.
- **Steps**: Create each file in `src/spec_kitty_events/conformance/fixtures/dossier/invalid/`.

  **File 1**: `dossier_parity_drift_namespace_mismatch.json` — namespace missing required field
  ```json
  {
    "namespace": {
      "project_uuid": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
      "feature_slug": "008-mission-dossier-parity-event-contracts"
    },
    "expected_hash": "deadbeef",
    "actual_hash": "cafebabe",
    "drift_kind": "artifact_added",
    "detected_at": "2026-02-21T14:00:00Z"
  }
  ```
  Missing `target_branch`, `mission_key`, `manifest_version` — Pydantic must reject.
  Event type: `MissionDossierParityDriftDetected`

  **File 2**: `dossier_artifact_indexed_missing_path.json` — artifact_identity.path absent
  ```json
  {
    "namespace": { "project_uuid": "a1b2c3d4-e5f6-7890-abcd-ef1234567890", "feature_slug": "008-mission-dossier-parity-event-contracts", "target_branch": "2.x", "mission_key": "software-dev", "manifest_version": "1.0.0" },
    "artifact_id": {
      "mission_key": "software-dev",
      "artifact_class": "input"
    },
    "content_ref": { "hash": "abc123", "algorithm": "sha256" },
    "indexed_at": "2026-02-21T14:00:00Z"
  }
  ```
  Missing `artifact_id.path` — Pydantic must reject.
  Event type: `MissionDossierArtifactIndexed`

  **File 3**: `dossier_artifact_indexed_invalid_class.json` — unrecognized artifact_class
  ```json
  {
    "namespace": { "project_uuid": "a1b2c3d4-e5f6-7890-abcd-ef1234567890", "feature_slug": "008-mission-dossier-parity-event-contracts", "target_branch": "2.x", "mission_key": "software-dev", "manifest_version": "1.0.0" },
    "artifact_id": {
      "mission_key": "software-dev",
      "path": "kitty-specs/008/spec.md",
      "artifact_class": "INVALID_CLASS"
    },
    "content_ref": { "hash": "abc123", "algorithm": "sha256" },
    "indexed_at": "2026-02-21T14:00:00Z"
  }
  ```
  `artifact_class: "INVALID_CLASS"` is not a valid Literal value — Pydantic must reject.
  Event type: `MissionDossierArtifactIndexed`

- **Files**: 3 JSON files in `dossier/invalid/`
- **Parallel?**: Yes.

### Subtask T017 – Write 2 JSONL replay streams

- **Purpose**: Provide ordered event streams for reducer integration tests. Each line is a complete Event envelope (not just payload) in the standard spec-kitty-events format.
- **Steps**: Create each file in `src/spec_kitty_events/conformance/fixtures/dossier/replay/`.

  **Event envelope template** (all required fields from `event.schema.json`):
  ```json
  {
    "event_id": "01JNREXAMPLE0000000000001",
    "event_type": "MissionDossierArtifactIndexed",
    "aggregate_id": "mission-software-dev",
    "timestamp": "2026-02-21T14:00:00.000Z",
    "node_id": "local-node-001",
    "lamport_clock": 1,
    "project_uuid": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "correlation_id": "01JNRCORRELATION0000000001",
    "payload": { ...payload dict... }
  }
  ```
  Use valid ULID strings for `event_id` and `correlation_id` (26 chars, base32 Crockford, uppercase). Sequential `lamport_clock` values.

  **File 1**: `dossier_happy_path.jsonl` — 6 events

  Line 1 (`lamport_clock: 1`): `MissionDossierArtifactIndexed` — spec.md as input
  Line 2 (`lamport_clock: 2`): `MissionDossierArtifactIndexed` — plan.md as workflow
  Line 3 (`lamport_clock: 3`): `MissionDossierArtifactIndexed` — tasks.md as workflow
  Line 4 (`lamport_clock: 4`): `MissionDossierSnapshotComputed` — 3 artifacts, 0 anomalies, hash "aaa..."
  Line 5 (`lamport_clock: 5`): `MissionDossierArtifactIndexed` — spec.md v2 (supersedes line 1)
  Line 6 (`lamport_clock: 6`): `MissionDossierSnapshotComputed` — 3 artifacts (1 superseded → still 3 in catalog, but effective is 3), 0 anomalies, hash "bbb..."

  **File 2**: `dossier_drift_scenario.jsonl` — 5 events

  Line 1 (`lamport_clock: 1`): `MissionDossierArtifactIndexed` — spec.md
  Line 2 (`lamport_clock: 2`): `MissionDossierArtifactIndexed` — plan.md
  Line 3 (`lamport_clock: 3`): `MissionDossierSnapshotComputed` — 2 artifacts, 0 anomalies, hash "ccc..."
  Line 4 (`lamport_clock: 4`): `MissionDossierArtifactMissing` — tasks.md missing (manifest_step: "tasks")
  Line 5 (`lamport_clock: 5`): `MissionDossierParityDriftDetected` — expected "ccc...", actual "ddd...", drift_kind "anomaly_introduced"

  Use a shared `correlation_id` across all events in each file. Use a shared `project_uuid` and `namespace.project_uuid` matching the correlation.

- **Files**: 2 JSONL files in `dossier/replay/`
- **Parallel?**: Yes — can be written alongside T015 and T016.

### Subtask T018 – Add 15 entries to manifest.json

- **Purpose**: Register all 13 fixture cases and 2 replay streams in the manifest so the loader can find and load them.
- **Steps**:
  1. Open `src/spec_kitty_events/conformance/fixtures/manifest.json`.
  2. Add 13 fixture case entries to the `"fixtures"` array. Each entry format (copy from existing mission_next entries for structure):
     ```json
     {
       "id": "dossier-artifact-indexed-valid",
       "path": "dossier/valid/dossier_artifact_indexed_valid.json",
       "event_type": "MissionDossierArtifactIndexed",
       "expected_result": "valid",
       "notes": "Happy-path: spec.md indexed as input artifact",
       "min_version": "2.4.0"
     }
     ```
  3. Add 2 replay stream entries:
     ```json
     {
       "id": "dossier-replay-happy-path",
       "path": "dossier/replay/dossier_happy_path.jsonl",
       "fixture_type": "replay_stream",
       "event_type": "mixed",
       "expected_result": "valid",
       "notes": "6-event happy-path stream: 3 indexed, 2 snapshots, 1 supersedes",
       "min_version": "2.4.0"
     }
     ```

  **Complete list of 13 fixture case entries** (id → expected_result):
  - `dossier-artifact-indexed-valid` → `valid`
  - `dossier-artifact-indexed-supersedes` → `valid`
  - `dossier-artifact-indexed-with-provenance` → `valid`
  - `dossier-artifact-missing-required-always` → `valid`
  - `dossier-artifact-missing-required-by-step` → `valid`
  - `dossier-snapshot-computed-clean` → `valid`
  - `dossier-snapshot-computed-with-anomalies` → `valid`
  - `dossier-parity-drift-artifact-added` → `valid`
  - `dossier-parity-drift-artifact-mutated` → `valid`
  - `dossier-namespace-collision-coverage` → `valid`
  - `dossier-parity-drift-namespace-mismatch` → `invalid`
  - `dossier-artifact-indexed-missing-path` → `invalid`
  - `dossier-artifact-indexed-invalid-class` → `invalid`

  **Plus 2 replay stream entries**:
  - `dossier-replay-happy-path` (fixture_type: replay_stream)
  - `dossier-replay-drift-scenario` (fixture_type: replay_stream)

- **Files**: `src/spec_kitty_events/conformance/fixtures/manifest.json`
- **Notes**: Preserve existing manifest structure. `"version"` field at the manifest root should remain `"2.0.0"` — it documents the manifest schema version, not the event library version.

### Subtask T019 – Verify fixture loading

- **Purpose**: Confirm that the loader finds and parses all fixtures correctly before WP04 tests are written.
- **Steps**:
  1. Run:
     ```bash
     python3.11 -c "
     from spec_kitty_events.conformance import load_fixtures, load_replay_stream
     cases = load_fixtures('dossier')
     print(f'Loaded {len(cases)} fixture cases (expected 13)')
     assert len(cases) == 13, f'Got {len(cases)}'
     happy = load_replay_stream('dossier-replay-happy-path')
     print(f'Happy path stream: {len(happy)} events')
     drift = load_replay_stream('dossier-replay-drift-scenario')
     print(f'Drift stream: {len(drift)} events')
     print('All fixture loads OK')
     "
     ```
  2. If any `FileNotFoundError` → check file names match manifest paths exactly (snake_case, relative to fixtures dir).
  3. If `ValueError: Unknown fixture category` → WP02 T009 (loader.py) must be done first.
- **Files**: No file changes (verification step).
- **Notes**: WP02 (T009) must complete before this verification can pass (the `"dossier"` category must be registered). If WP02 isn't done yet, run T019 after merging WP02.

## Risks & Mitigations

- **Fixture JSON format**: Fixtures contain only the payload dict, NOT the Event envelope. The loader calls `validate_event(payload_dict, event_type)`. If you accidentally include envelope fields (`event_id`, `lamport_clock`, etc.) in valid fixture JSON, the Pydantic model will accept them as extra fields (if `extra="allow"`) or reject them (if `extra="forbid"`). Check existing fixtures to match the convention.
- **JSONL ULIDs**: Use correctly formatted 26-char uppercase Crockford base32 strings. Generate with `python3.11 -c "import time; ts = int(time.time() * 1000); print(format(ts, '010X') + 'AAAAAAAAAAAAAAAA')"` or just use well-formed static strings.
- **Manifest path separators**: Use forward slashes (`dossier/valid/file.json`) not backslashes — the loader uses `Path` which handles OS differences, but the manifest strings use forward slashes per existing convention.

## Review Guidance

1. `load_fixtures("dossier")` returns exactly 13 cases — run the T019 verification command.
2. Both replay streams load without error.
3. `artifact_class` does NOT appear as a top-level field in any valid fixture JSON.
4. `manifest_version` does NOT appear as a top-level payload field in any fixture JSON.
5. Invalid fixtures produce model violations when validated (can verify with `validate_event(payload, event_type)`).
6. All fixture files are present in git staging.

## Activity Log

- 2026-02-21T14:00:00Z – system – lane=planned – Prompt created.
