---
work_package_id: "WP02"
subtasks:
  - "T007"
  - "T008"
  - "T009"
  - "T010"
  - "T011"
  - "T012"
  - "T013"
title: "Schemas & Conformance Wiring"
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

# Work Package Prompt: WP02 – Schemas & Conformance Wiring

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

Wire the 8 new JSON schemas, the `dossier` fixture category, 4 event type validator registrations, ~10 public exports, and 3 package-data globs so that the dossier module is fully integrated into the existing conformance infrastructure.

**Acceptance gates**:
- [ ] `python -m spec_kitty_events.schemas.generate --check` exits 0 (8 new schemas committed, no drift)
- [ ] `from spec_kitty_events.conformance import load_fixtures; load_fixtures("dossier")` does NOT raise ValueError
- [ ] `from spec_kitty_events.conformance import validate_event; validate_event({...}, "MissionDossierArtifactIndexed")` dispatches to correct model
- [ ] `from spec_kitty_events import MissionDossierArtifactIndexedPayload, MissionDossierArtifactMissingPayload, MissionDossierSnapshotComputedPayload, MissionDossierParityDriftDetectedPayload, ArtifactIdentity, ContentHashRef, ProvenanceRef, LocalNamespaceTuple, MissionDossierState, reduce_mission_dossier, NamespaceMixedStreamError` — all succeed
- [ ] `mypy --strict src/spec_kitty_events/schemas/generate.py src/spec_kitty_events/conformance/validators.py src/spec_kitty_events/conformance/loader.py src/spec_kitty_events/__init__.py` exits 0

## Context & Constraints

- **Depends on**: WP01 (all dossier models must exist before importing in generate.py/validators.py)
- **Pattern**: `generate.py` already imports from 5 domain modules; add a 6th section for dossier. `validators.py` already has 29 registrations; add 4 more.
- **Schema naming convention**: `{snake_case_model_name}.schema.json` — 8 new files.
- **loader.py line 17**: `_VALID_CATEGORIES = frozenset({...})` — add `"dossier"` to the set literal.
- **pyproject.toml lines 34–51**: `[tool.setuptools.package-data]` section — add 3 globs after the `mission_next` entries.

**Implementation command**:
```bash
spec-kitty implement WP02 --base WP01
```

## Subtasks & Detailed Guidance

### Subtask T007 – Add dossier imports to generate.py and run schema generator

- **Purpose**: Register all 8 dossier Pydantic models in the schema generation pipeline so that build-time generation produces their JSON Schema files.
- **Steps**:
  1. Open `src/spec_kitty_events/schemas/generate.py`.
  2. Add a new import block after the existing `mission_next` imports:
     ```python
     from spec_kitty_events.dossier import (
         ArtifactIdentity,
         ContentHashRef,
         ProvenanceRef,
         LocalNamespaceTuple,
         MissionDossierArtifactIndexedPayload,
         MissionDossierArtifactMissingPayload,
         MissionDossierSnapshotComputedPayload,
         MissionDossierParityDriftDetectedPayload,
     )
     ```
  3. Add 8 entries to `PYDANTIC_MODELS` list (after the `# Mission-next runtime models` block):
     ```python
     # Dossier event contract models
     ("artifact_identity", ArtifactIdentity),
     ("content_hash_ref", ContentHashRef),
     ("provenance_ref", ProvenanceRef),
     ("local_namespace_tuple", LocalNamespaceTuple),
     ("mission_dossier_artifact_indexed_payload", MissionDossierArtifactIndexedPayload),
     ("mission_dossier_artifact_missing_payload", MissionDossierArtifactMissingPayload),
     ("mission_dossier_snapshot_computed_payload", MissionDossierSnapshotComputedPayload),
     ("mission_dossier_parity_drift_detected_payload", MissionDossierParityDriftDetectedPayload),
     ```
  4. Run the generator:
     ```bash
     python3.11 -m spec_kitty_events.schemas.generate
     ```
     This writes 8 new `.schema.json` files to `src/spec_kitty_events/schemas/`.
  5. Inspect the 8 new files to confirm they contain `$schema` and `$id` fields.
- **Files**: `src/spec_kitty_events/schemas/generate.py`, `src/spec_kitty_events/schemas/` (8 new JSON files)
- **Parallel?**: Yes — can happen alongside T009, T010, T012.

### Subtask T008 – Verify schema drift check exits 0 and commit schemas

- **Purpose**: Confirm that the committed schema files exactly match the generator output (CI contract).
- **Steps**:
  1. Run drift check:
     ```bash
     python3.11 -m spec_kitty_events.schemas.generate --check
     ```
     Must exit 0 with "All N schemas are up to date." message.
  2. If any drift is reported, re-run the generator (T007) and check again.
  3. Stage and verify the 8 new schema files are present:
     ```bash
     git status src/spec_kitty_events/schemas/
     ```
     Should show 8 new `.schema.json` files untracked or modified.
- **Files**: `src/spec_kitty_events/schemas/*.schema.json` (8 new files)
- **Notes**: This step verifies that the `check_drift()` function in `generate.py` will pass in CI. Do NOT manually edit JSON schema files — always regenerate from models.

### Subtask T009 – Add "dossier" to loader.py _VALID_CATEGORIES

- **Purpose**: Allow `load_fixtures("dossier")` to succeed. Currently it would raise `ValueError: Unknown fixture category: 'dossier'`.
- **Steps**:
  1. Open `src/spec_kitty_events/conformance/loader.py`, line 17.
  2. Current:
     ```python
     _VALID_CATEGORIES = frozenset({"events", "lane_mapping", "edge_cases", "collaboration", "glossary", "mission_next"})
     ```
  3. Updated:
     ```python
     _VALID_CATEGORIES = frozenset({
         "events", "lane_mapping", "edge_cases",
         "collaboration", "glossary", "mission_next",
         "dossier",
     })
     ```
  4. Update the docstring of `load_fixtures()` to include `"dossier"` in the valid values list.
- **Files**: `src/spec_kitty_events/conformance/loader.py`
- **Parallel?**: Yes — independent file edit.

### Subtask T010 – Add 4 event types to validators.py mapping dicts

- **Purpose**: Route the four new dossier event type strings to their Pydantic models and JSON schema names in the dual-layer validator.
- **Steps**:
  1. Open `src/spec_kitty_events/conformance/validators.py`.
  2. Add import after the existing `mission_next` import block:
     ```python
     from spec_kitty_events.dossier import (
         MissionDossierArtifactIndexedPayload,
         MissionDossierArtifactMissingPayload,
         MissionDossierSnapshotComputedPayload,
         MissionDossierParityDriftDetectedPayload,
     )
     ```
  3. Add to `_EVENT_TYPE_TO_MODEL` dict (after mission_next entries):
     ```python
     "MissionDossierArtifactIndexed": MissionDossierArtifactIndexedPayload,
     "MissionDossierArtifactMissing": MissionDossierArtifactMissingPayload,
     "MissionDossierSnapshotComputed": MissionDossierSnapshotComputedPayload,
     "MissionDossierParityDriftDetected": MissionDossierParityDriftDetectedPayload,
     ```
  4. Add to `_EVENT_TYPE_TO_SCHEMA` dict (after mission_next entries):
     ```python
     "MissionDossierArtifactIndexed": "mission_dossier_artifact_indexed_payload",
     "MissionDossierArtifactMissing": "mission_dossier_artifact_missing_payload",
     "MissionDossierSnapshotComputed": "mission_dossier_snapshot_computed_payload",
     "MissionDossierParityDriftDetected": "mission_dossier_parity_drift_detected_payload",
     ```
- **Files**: `src/spec_kitty_events/conformance/validators.py`
- **Parallel?**: Yes — independent file edit.

### Subtask T011 – Add ~10 new exports to __init__.py

- **Purpose**: Expose all new dossier types as stable public API symbols accessible via `from spec_kitty_events import ...`.
- **Steps**:
  1. Open `src/spec_kitty_events/__init__.py`.
  2. Add a new import section near the end of existing domain imports:
     ```python
     # Dossier event contracts (v2.4.0)
     from spec_kitty_events.dossier import (
         MISSION_DOSSIER_ARTIFACT_INDEXED,
         MISSION_DOSSIER_ARTIFACT_MISSING,
         MISSION_DOSSIER_SNAPSHOT_COMPUTED,
         MISSION_DOSSIER_PARITY_DRIFT_DETECTED,
         DOSSIER_EVENT_TYPES,
         NamespaceMixedStreamError,
         LocalNamespaceTuple,
         ArtifactIdentity,
         ContentHashRef,
         ProvenanceRef,
         MissionDossierArtifactIndexedPayload,
         MissionDossierArtifactMissingPayload,
         MissionDossierSnapshotComputedPayload,
         MissionDossierParityDriftDetectedPayload,
         ArtifactEntry,
         AnomalyEntry,
         SnapshotSummary,
         DriftRecord,
         MissionDossierState,
         reduce_mission_dossier,
     )
     ```
  3. Add all new names to the `__all__` list (or create one if it doesn't exist — follow existing convention).
- **Files**: `src/spec_kitty_events/__init__.py`
- **Notes**: The exact count (~10 stated in spec) is approximate; include all public symbols. Constants like `MISSION_DOSSIER_ARTIFACT_INDEXED` and `DOSSIER_EVENT_TYPES` are useful to consumers for event type routing.

### Subtask T012 – Add 3 package-data globs to pyproject.toml

- **Purpose**: Ensure that installed-package consumers (e.g., `pip install spec-kitty-events`) include the dossier fixture files. Without these globs, in-repo tests pass but `load_fixtures("dossier")` fails in installed environments.
- **Steps**:
  1. Open `pyproject.toml`, find the `[tool.setuptools.package-data]` section (lines 34–51).
  2. After the `mission_next` entries, add:
     ```toml
     "conformance/fixtures/dossier/valid/*.json",
     "conformance/fixtures/dossier/invalid/*.json",
     "conformance/fixtures/dossier/replay/*.jsonl",
     ```
- **Files**: `pyproject.toml`
- **Parallel?**: Yes — independent file edit.

### Subtask T013 – Smoke-test: all new exports importable

- **Purpose**: Confirm the full wiring is complete and nothing is missing from `__init__.py`.
- **Steps**:
  1. Run in the repo root:
     ```bash
     python3.11 -c "
     from spec_kitty_events import (
         MissionDossierArtifactIndexedPayload,
         MissionDossierArtifactMissingPayload,
         MissionDossierSnapshotComputedPayload,
         MissionDossierParityDriftDetectedPayload,
         ArtifactIdentity, ContentHashRef, ProvenanceRef, LocalNamespaceTuple,
         MissionDossierState, reduce_mission_dossier, NamespaceMixedStreamError,
         DOSSIER_EVENT_TYPES,
     )
     from spec_kitty_events.conformance import load_fixtures
     cases = load_fixtures.__module__  # verifies import
     print('All imports OK')
     "
     ```
     Must print `All imports OK`.
  2. Test validator dispatch:
     ```bash
     python3.11 -c "
     from spec_kitty_events.conformance import validate_event
     result = validate_event({'event_type': 'MissionDossierArtifactIndexed'}, 'MissionDossierArtifactIndexed')
     print('Pydantic dispatch OK, valid:', result.valid)
     "
     ```
     (Will be invalid due to missing fields — that's fine; we just want no KeyError/dispatch failure.)
- **Files**: No file changes (this is a verification step).

## Risks & Mitigations

- **generate.py import order**: mypy may flag circular imports if `dossier.py` imports from `status.py` at module level inside the reducer. The existing pattern (`from spec_kitty_events.status import ...` inside the function body) avoids this — replicate it.
- **validators.py strict typing**: The dicts `_EVENT_TYPE_TO_MODEL` and `_EVENT_TYPE_TO_SCHEMA` are typed; new entries must match the existing value types.

## Review Guidance

1. `python -m spec_kitty_events.schemas.generate --check` exits 0.
2. 8 new `.schema.json` files present in `src/spec_kitty_events/schemas/`.
3. `_VALID_CATEGORIES` in `loader.py` contains `"dossier"`.
4. All 4 event type strings appear in both `_EVENT_TYPE_TO_MODEL` and `_EVENT_TYPE_TO_SCHEMA` in `validators.py`.
5. All new symbols importable from `spec_kitty_events` top level.
6. `pyproject.toml` has 3 new dossier glob lines.

## Activity Log

- 2026-02-21T14:00:00Z – system – lane=planned – Prompt created.
