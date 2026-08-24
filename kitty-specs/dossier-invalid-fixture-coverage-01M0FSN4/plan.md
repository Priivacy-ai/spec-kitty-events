# Implementation Plan: Dossier Invalid Fixture Coverage

**Branch**: `feat/dossier-invalid-fixture-coverage` | **Date**: 2026-08-20 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `kitty-specs/dossier-invalid-fixture-coverage-01M0FSN4/spec.md`

## Summary

Add two invalid conformance fixtures — one for `MissionDossierArtifactMissing`, one for `MissionDossierSnapshotComputed` — so all four dossier event payload types have both valid and invalid golden fixtures, closing the spec-kitty-events-owned acceptance criterion of GitHub issue #23. This is a fixtures-and-registration change only: no payload models, JSON Schemas, or `validate_event()` code change. The two fixtures are registered in `src/spec_kitty_events/conformance/fixtures/manifest.json` — the actual mechanism `load_fixtures()` reads, not directory-scanning — and two hardcoded count assertions in `tests/test_dossier_conformance.py` are bumped accordingly.

## Technical Context

**Language/Version**: Python 3.10+ (per charter; matches the rest of `spec_kitty_events`)
**Primary Dependencies**: Pydantic (existing `dossier.py` models, unchanged), pytest (existing test runner) — no new dependencies introduced
**Storage**: N/A — fixtures are static, version-controlled JSON files; no database or runtime storage involved
**Testing**: pytest, via the existing manifest-driven fixture harness (`src/spec_kitty_events/conformance/loader.py` + `tests/test_dossier_conformance.py`'s parametrized `test_valid_fixture_passes_conformance` / `test_invalid_fixture_fails_conformance`). No new test framework or hypothesis strategy needed — the existing dual-layer (Pydantic + JSON Schema) `validate_event()` path is reused as-is.
**Target Platform**: Python library (`spec_kitty_events` package), consumed by `spec-kitty` and `spec-kitty-saas`; CI runs on Linux
**Project Type**: single (Python package + test suite, no frontend/mobile split)
**Performance Goals**: N/A — static fixture data, not a runtime-perf-sensitive path; must not measurably slow the existing conformance suite (currently well under CI budget)
**Constraints**: Fixtures-only diff (spec C-001): no edits to `src/spec_kitty_events/dossier.py`, the four JSON Schema files, or `validate_event()`. PR diff must stay within `fixtures/dossier/invalid/*.json`, `fixtures/manifest.json`, and the two count literals in `tests/test_dossier_conformance.py` (spec C-003).
**Scale/Scope**: 2 new JSON fixture files (~10 fields each), 2 new `manifest.json` entries, 2 integer-literal edits in one existing test file. No new modules, no new dependencies.

## Charter Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Charter (`.kittify/charter/charter.md`) requirements relevant to this mission:

- **Testing Standards** — "pytest, hypothesis, schema drift checks, and conformance fixture validation for any event contract change." This mission is itself a conformance-fixture change; satisfied by running the existing `tests/test_dossier_conformance.py` suite (no hypothesis property tests apply — these are hand-authored golden fixtures, not property-generated).
- **Quality Gates** — "pytest, committed schema generation checks, and mypy --strict must pass before merge." Pytest applies directly. Schema-generation checks and mypy --strict are structurally inapplicable to this diff (no schema or `.py` model changes) — confirmed during the post-spec adversarial review; not re-litigated here.
- **Review Policy** — "Any change to event envelopes, payload fields, schema versioning, or conformance fixtures requires deliberate compatibility review." **Directly triggered** — conformance fixtures are explicitly named. Satisfied via spec C-003's diff-scope check (reviewer confirms no `dossier.py`/schema/`validate_event()` changes snuck in).
- **Package Boundary** — `spec_kitty_events` must stay independent of `spec-kitty`/`spec-kitty-saas`/tracker/runtime code. Not at risk: this mission touches only fixtures and one test file inside this package.

**Gate result: PASS.** No violations requiring Complexity Tracking justification.

## Project Structure

### Documentation (this mission)

```
kitty-specs/dossier-invalid-fixture-coverage-01M0FSN4/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md         # Phase 1 output
├── quickstart.md         # Phase 1 output
├── contracts/            # Phase 1 output — manifest-entry contract
└── tasks.md              # Phase 2 output (/spec-kitty.tasks — not created here)
```

### Source Code (repository root)

```
src/spec_kitty_events/
├── dossier.py                                          # UNCHANGED — payload models already ship required constraints
├── schemas/
│   ├── mission_dossier_artifact_missing_payload.schema.json    # UNCHANGED
│   └── mission_dossier_snapshot_computed_payload.schema.json   # UNCHANGED
└── conformance/
    ├── loader.py                                        # UNCHANGED — manifest-driven load_fixtures()
    ├── validators.py                                    # UNCHANGED — validate_event() already covers all 4 dossier types
    └── fixtures/
        ├── manifest.json                                # ADD 2 entries (dossier-artifact-missing-empty-step, dossier-snapshot-computed-negative-count)
        └── dossier/invalid/
            ├── dossier_artifact_missing_empty_step.json         # NEW
            └── dossier_snapshot_computed_negative_count.json    # NEW

tests/
└── test_dossier_conformance.py    # EDIT — bump 2 hardcoded literals (fixture_count 13→15, invalid_case_count 3→5)
```

**Structure Decision**: Single project (existing Python package layout). No new source directories — only two new fixture files, two new manifest entries, and two literal edits in one existing test file.

## Complexity Tracking

*No Charter Check violations — section not applicable.*

## Implementation Concern Map

### IC-01 — ArtifactMissing invalid fixture

- **Purpose**: Author `dossier_artifact_missing_empty_step.json` — a `MissionDossierArtifactMissing` payload with `manifest_step: ""`, violating the model's `min_length=1` constraint, everything else a valid sibling of the existing valid fixtures.
- **Relevant requirements**: FR-001
- **Affected surfaces**: `src/spec_kitty_events/conformance/fixtures/dossier/invalid/dossier_artifact_missing_empty_step.json` (new file only)
- **Sequencing/depends-on**: none
- **Risks**: Low. Must confirm locally via `validate_event()` that the empty string genuinely fails (Pydantic `min_length` does reject empty strings, but this must not be assumed without running it).

### IC-02 — SnapshotComputed invalid fixture

- **Purpose**: Author `dossier_snapshot_computed_negative_count.json` — a `MissionDossierSnapshotComputed` payload with `artifact_count: -1`, violating the model's `ge=0` constraint, everything else a valid sibling of the existing valid fixtures.
- **Relevant requirements**: FR-002
- **Affected surfaces**: `src/spec_kitty_events/conformance/fixtures/dossier/invalid/dossier_snapshot_computed_negative_count.json` (new file only)
- **Sequencing/depends-on**: none (independent of IC-01 — different file, different payload type)
- **Risks**: Low. Same local-validation caveat as IC-01.

### IC-03 — Manifest registration and count-gate update

- **Purpose**: Register both new fixtures in `fixtures/manifest.json` (`expected_result: "invalid"`, `notes` naming the exact field/rule broken, `min_version` matching the existing dossier entries) and bump the two hardcoded count assertions in `tests/test_dossier_conformance.py` so the existing parametrized tests pick both fixtures up with no new test function.
- **Relevant requirements**: FR-003, NFR-002 (manifest/directory consistency)
- **Affected surfaces**: `src/spec_kitty_events/conformance/fixtures/manifest.json`, `tests/test_dossier_conformance.py` (2 literal edits only)
- **Sequencing/depends-on**: IC-01, IC-02 (both fixture files must exist first — this concern's manifest entries reference their paths, and the count bump only makes sense once both are present)
- **Risks**: This is the single shared touchpoint — if IC-01 and IC-02 are worked as separate WPs in parallel, IC-03 must land after both merge to avoid two WPs racing to edit the same two lines of `manifest.json`/`test_dossier_conformance.py`.
