# Implementation Plan: Mission Dossier Parity Event Contracts

**Branch**: `2.x` | **Date**: 2026-02-21 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `kitty-specs/008-mission-dossier-parity-event-contracts/spec.md`

---

## Summary

Add canonical Mission Dossier and parity drift event contracts to `spec-kitty-events` v2.4.0,
following the established flat domain-module pattern (`mission_next.py`). The implementation
consists of a single new module `dossier.py` containing all typed provenance payload objects,
four event payload models, a `NamespaceMixedStreamError(ValueError)` exception, and the
`reduce_mission_dossier()` reducer. Supporting work: 8 JSON schemas, 13 fixture cases + 2 replay
streams under a new `dossier/` conformance category, loader + package-data + validator wiring,
and explicit consumer migration notes in CHANGELOG.md.

---

## Technical Context

**Language/Version**: Python 3.10+ (mypy `--strict` enforced; `from __future__ import annotations` in all new files)
**Primary Dependencies**: Pydantic v2 (`ConfigDict(frozen=True)`, `Field`, `BaseModel`), `jsonschema>=4.21.0,<5.0.0` (optional `[conformance]` extra)
**Storage**: N/A — pure library, no runtime I/O in reducer
**Testing**: pytest + Hypothesis (`@given`, `@settings(max_examples=200)` for determinism property tests)
**Target Platform**: Python library; installed package + in-repo dev usage
**Project Type**: Single-package library (`src/spec_kitty_events/`)
**Performance Goals**: Reducer must be deterministic; no latency targets (pure function, no I/O)
**Constraints**: No I/O inside reducer; no global state; `mypy --strict` must pass; ≥98% coverage

---

## Constitution Check

Constitution file: **absent** (`.kittify/memory/constitution.md` not found). Check skipped.

---

## Project Structure

### Documentation (this feature)

```
kitty-specs/008-mission-dossier-parity-event-contracts/
├── plan.md          ← this file
├── research.md      ← Phase 0 (inline, no external research needed)
├── data-model.md    ← Phase 1: entity field tables
└── contracts/       ← Phase 1: Python type stubs + payload field listings
```

### Source Code (concrete paths from repository root)

```
src/spec_kitty_events/
├── dossier.py                        ← NEW: all domain types, reducer, exception
├── schemas/
│   ├── generate.py                   ← MODIFY: add dossier imports to PYDANTIC_MODELS
│   ├── artifact_identity.schema.json                          ← NEW (8 schemas)
│   ├── content_hash_ref.schema.json
│   ├── provenance_ref.schema.json
│   ├── local_namespace_tuple.schema.json
│   ├── mission_dossier_artifact_indexed_payload.schema.json
│   ├── mission_dossier_artifact_missing_payload.schema.json
│   ├── mission_dossier_snapshot_computed_payload.schema.json
│   └── mission_dossier_parity_drift_detected_payload.schema.json
├── conformance/
│   ├── loader.py                     ← MODIFY: add "dossier" to _VALID_CATEGORIES
│   ├── validators.py                 ← MODIFY: add 4 event types to mapping dicts
│   ├── fixtures/
│   │   ├── manifest.json             ← MODIFY: add 13 cases + 2 replay entries
│   │   └── dossier/                  ← NEW fixture directory
│   │       ├── valid/                ← 10 valid fixture JSON files
│   │       ├── invalid/              ← 3 invalid fixture JSON files
│   │       └── replay/              ← 2 JSONL replay streams
└── __init__.py                       ← MODIFY: add ~10 new exports

tests/
├── test_dossier_conformance.py       ← NEW: dual-layer validation + category tests
└── test_dossier_reducer.py           ← NEW: reducer determinism + Hypothesis properties

pyproject.toml                        ← MODIFY: add dossier/* package-data globs
CHANGELOG.md                          ← MODIFY: add v2.4.0 section
```

---

## Phase 0: Research (Inline)

No external research required. All design decisions resolved from spec review, codebase inspection,
and planning alignment. Findings recorded inline below.

### R-01: Sort key pattern

**Decision**: `(lamport_clock, timestamp, event_id)` — three-field tuple.
**Source**: `mission_next.py:252` uses `status_event_sort_key` from `status.py:327`. The reducer
imports `status_event_sort_key` directly; `dossier.py` does the same.
**Implication**: No new sort function needed; reuse `status_event_sort_key`.

### R-02: Deduplication pattern

**Decision**: Import `dedup_events()` from `status.py` (already used by `mission_next.py`).
**Source**: `mission_next.py` line 260: `from spec_kitty_events.status import dedup_events, status_event_sort_key`.
**Implication**: No new dedup logic; pipeline is filter → sort → dedup → reduce.

### R-03: Pydantic frozen model pattern

**Decision**: `model_config = ConfigDict(frozen=True)` on every new BaseModel.
**Source**: All existing payload models (e.g., `MissionRunStartedPayload`, `StatusTransitionPayload`).
**Implication**: Reducer output model `MissionDossierState` also uses `frozen=True`.

### R-04: Literal string constraints vs Enum

**Decision**: Use `Literal` string types for `artifact_class` and `drift_kind` (6 values each), not Python `Enum`.
**Source**: spec §14 Assumption 2; matches existing `Literal` usage in `status.py` for lane values.
**Implication**: `ArtifactIdentity.artifact_class: Literal["input", "workflow", "output", "evidence", "policy", "runtime"]`

### R-05: Conformance validator registration pattern

**Decision**: Add dossier event types to `_EVENT_TYPE_TO_MODEL` and `_EVENT_TYPE_TO_SCHEMA` dicts in `validators.py`.
**Source**: `validators.py` shows 29 existing registrations using string event-type keys.
**Implication**: Four new entries required; schema names follow snake_case convention.

### R-06: Fixture directory shape

**Decision**: Fixture files organized as `dossier/valid/*.json`, `dossier/invalid/*.json`, `dossier/replay/*.jsonl` — matching the pattern used by `mission_next/`.
**Source**: `pyproject.toml` lines 49-51 show `mission_next/valid/*.json`, `mission_next/invalid/*.json`, `mission_next/replay/*.jsonl`.
**Implication**: 10 valid JSON + 3 invalid JSON + 2 JSONL replay files.

### R-07: package-data globs

**Decision**: Add three new globs to `pyproject.toml [tool.setuptools.package-data]`.
**Source**: Lines 34-51 of `pyproject.toml` — one glob per subdirectory per category.
```toml
"conformance/fixtures/dossier/valid/*.json",
"conformance/fixtures/dossier/invalid/*.json",
"conformance/fixtures/dossier/replay/*.jsonl",
```

### R-08: NamespaceMixedStreamError placement

**Decision**: Define `NamespaceMixedStreamError(ValueError)` in `dossier.py`; re-export from `__init__.py`.
**Source**: No existing exceptions module. Adding one exception to the domain module is KISS-consistent.
**Implication**: Exported as a first-class public API symbol; callers can `except NamespaceMixedStreamError`.

### R-09: Fixture naming convention

**Decision**: File names mirror fixture IDs with hyphens replaced by underscores.
**Source**: Existing fixture files use snake_case filenames; manifest `id` fields use kebab-case.
**Implication**: e.g., manifest id `dossier-artifact-indexed-valid` → file `dossier/valid/dossier_artifact_indexed_valid.json`.

---

## Phase 1: Design & Contracts

### Data Model

See `kitty-specs/008-mission-dossier-parity-event-contracts/data-model.md` (generated below).

### Python Type Contracts

See `kitty-specs/008-mission-dossier-parity-event-contracts/contracts/` (generated below).

---

## Implementation Sequence (Work Packages)

### WP01 — Core domain module (`dossier.py`)

**Deliverable**: `src/spec_kitty_events/dossier.py`

Sections (follow `mission_next.py` section structure):
1. **Constants** — 4 event type string constants + `DOSSIER_EVENT_TYPES: FrozenSet[str]`
2. **Exception** — `NamespaceMixedStreamError(ValueError)`
3. **Value Objects** — `ArtifactIdentity`, `ContentHashRef`, `ProvenanceRef`, `LocalNamespaceTuple`
4. **Payload Models** — `MissionDossierArtifactIndexedPayload`, `MissionDossierArtifactMissingPayload`, `MissionDossierSnapshotComputedPayload`, `MissionDossierParityDriftDetectedPayload`
5. **Reducer Output Models** — `ArtifactEntry`, `AnomalyEntry`, `SnapshotSummary`, `DriftRecord`, `MissionDossierState`
6. **Reducer** — `reduce_mission_dossier(events: Sequence[Event]) -> MissionDossierState`

Key reducer pipeline:
```
1. Filter events to DOSSIER_EVENT_TYPES
2. Sort by status_event_sort_key  (lamport_clock, timestamp, event_id)
3. Dedup by event_id using dedup_events()
4. Validate namespace consistency: raise NamespaceMixedStreamError on mismatch
5. Fold events into mutable intermediates
6. Assemble frozen MissionDossierState
```

**Acceptance**: `mypy --strict` passes; all unit tests pass; reducer is deterministic.

### WP02 — JSON schema generation

**Deliverable**: 8 new `*.schema.json` files in `src/spec_kitty_events/schemas/`

Steps:
1. Add 8 dossier imports to `generate.py` `PYDANTIC_MODELS` list
2. Run `python -m spec_kitty_events.schemas.generate` to emit schema files
3. Run `python -m spec_kitty_events.schemas.generate --check` to verify zero drift

**Acceptance**: 8 files present; `--check` exits 0; all schemas have `$schema` + `$id` fields.

### WP03 — Conformance wiring

**Deliverable**: Modified `loader.py`, `validators.py`; `__init__.py` exports

Steps:
1. `loader.py`: add `"dossier"` to `_VALID_CATEGORIES` frozenset
2. `validators.py`: add 4 event type → model and 4 event type → schema name entries
3. `__init__.py`: add ~10 new exports (4 payload models + 4 provenance types + `MissionDossierState` + `reduce_mission_dossier` + `NamespaceMixedStreamError`)
4. `pyproject.toml`: add 3 new package-data globs

**Acceptance**: `load_fixtures("dossier")` succeeds; `validate_event(payload, "MissionDossierArtifactIndexed")` dispatches to correct model; all new exports importable.

### WP04 — Fixtures

**Deliverable**: 13 fixture JSON files + 2 JSONL replay streams in `src/spec_kitty_events/conformance/fixtures/dossier/`; updated `manifest.json`

Fixture file list:

**Valid** (`dossier/valid/`, 10 files):
- `dossier_artifact_indexed_valid.json` — spec.md indexed as input artifact
- `dossier_artifact_indexed_supersedes.json` — `supersedes` field populated
- `dossier_artifact_indexed_with_provenance.json` — full ProvenanceRef populated
- `dossier_artifact_missing_required_always.json` — `manifest_step: "required_always"`
- `dossier_artifact_missing_required_by_step.json` — `manifest_step: "plan"` (step_id)
- `dossier_snapshot_computed_clean.json` — zero anomaly count
- `dossier_snapshot_computed_with_anomalies.json` — non-zero anomaly count
- `dossier_parity_drift_artifact_added.json` — `drift_kind: "artifact_added"`
- `dossier_parity_drift_artifact_mutated.json` — `drift_kind: "artifact_mutated"`
- `dossier_namespace_collision_coverage.json` — two distinct namespace tuples

**Invalid** (`dossier/invalid/`, 3 files):
- `dossier_parity_drift_namespace_mismatch.json` — namespace missing required field
- `dossier_artifact_indexed_missing_path.json` — `artifact_id.path` absent
- `dossier_artifact_indexed_invalid_class.json` — unrecognized `artifact_class` value

**Replay** (`dossier/replay/`, 2 files):
- `dossier_happy_path.jsonl` — 6 events: Indexed×3 → Snapshot → Indexed(supersedes) → Snapshot
- `dossier_drift_scenario.jsonl` — 5 events: Indexed×2 → Snapshot → Missing → DriftDetected

**Acceptance**: All fixture files load via `load_fixtures("dossier")` and `load_replay_stream(id)`; manifest `expected_result` values match actual validation outcomes.

### WP05 — Tests

**Deliverable**: `tests/test_dossier_conformance.py`, `tests/test_dossier_reducer.py`

**`test_dossier_conformance.py`** covers:
1. Valid fixtures: all pass dual-layer validation (zero violations)
2. Invalid fixtures: all produce ≥1 model or schema violation
3. `load_fixtures("dossier")` returns 13 cases
4. Both replay streams load without error

**`test_dossier_reducer.py`** covers:
1. Empty input → empty `MissionDossierState` (no error)
2. Happy-path replay stream folds into expected artifact count + `parity_status="clean"`
3. Drift scenario replay stream folds into `parity_status="drifted"`
4. `NamespaceMixedStreamError` raised when two events carry different namespace tuples
5. Deduplication: stream with repeated `event_id` → same output as de-duplicated stream
6. Hypothesis property test: `reduce_mission_dossier` output is identical across all
   causal-order-preserving permutations of the happy-path stream (200 examples)
7. Unknown event types skipped silently
8. `supersedes` correctly marks prior artifact as superseded in state

**Acceptance**: All tests pass; coverage ≥98%; `mypy --strict` passes; Hypothesis finds no counterexample.

### WP06 — CHANGELOG + exports verification

**Deliverable**: `CHANGELOG.md` v2.4.0 section; confirmed export count in `__init__.py`

Steps:
1. Prepend v2.4.0 section to CHANGELOG.md with migration notes for `spec-kitty` and `spec-kitty-saas`
2. Count and verify all new exports are present in `__init__.py`
3. Run full test suite: `python3.11 -m pytest` — all green
4. Run schema drift check: `python -m spec_kitty_events.schemas.generate --check` — exits 0
5. Run `mypy --strict src/` — zero errors

**Acceptance**: Full CI green; CHANGELOG section present with version pins; export count correct.

---

## Dependency Graph

```
WP01 (dossier.py)
  └─→ WP02 (schemas — needs models defined)
  └─→ WP03 (wiring — needs models + constants)
  └─→ WP04 (fixtures — needs event type strings to author valid/invalid payloads)
        └─→ WP05 (tests — needs fixtures on disk + loader wired)
              └─→ WP06 (final verification — needs tests passing)
```

WP02 and WP03 can proceed in parallel after WP01.
WP04 can proceed in parallel with WP02/WP03 after WP01.

---

## Key Invariants to Verify at Each WP

| Invariant | Checked in |
|---|---|
| `mypy --strict` zero errors | WP01, WP05, WP06 |
| Schema `--check` exits 0 | WP02, WP06 |
| `load_fixtures("dossier")` returns 13 cases | WP04, WP05 |
| `NamespaceMixedStreamError` carries both namespace tuples in message | WP01, WP05 |
| Sort key is `(lamport_clock, timestamp, event_id)` | WP01, WP05 |
| `artifact_class` not at event top level (only in `ArtifactIdentity`) | WP01, WP04 |
| `manifest_version` not in event payloads (only in `LocalNamespaceTuple`) | WP01, WP04 |
| Coverage ≥98% | WP05, WP06 |
