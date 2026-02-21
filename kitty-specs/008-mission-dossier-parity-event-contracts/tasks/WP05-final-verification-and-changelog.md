---
work_package_id: WP05
title: Final Verification & Changelog
lane: "for_review"
dependencies: [WP04]
base_branch: 008-mission-dossier-parity-event-contracts-WP04
base_commit: e445fb7bb2c1dabe66f12ede35b99932ad7d8a7e
created_at: '2026-02-21T14:50:59.820723+00:00'
subtasks:
- T026
- T027
- T028
- T029
- T030
phase: Phase 2 - Release Gate
assignee: ''
agent: "coordinator"
shell_pid: "41748"
review_status: ''
reviewed_by: ''
history:
- timestamp: '2026-02-21T14:00:00Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP05 – Final Verification & Changelog

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

This is the release gate for v2.4.0. Write the CHANGELOG entry with explicit consumer migration notes, verify the full test suite is green, confirm ≥98% coverage, ensure `mypy --strict` and schema drift check pass, and bump the version.

**Acceptance gates**:
- [ ] `python3.11 -m pytest` (full suite, all modules) exits 0
- [ ] `python3.11 -m pytest --cov=src/spec_kitty_events/dossier --cov-report=term-missing` shows ≥98% for `dossier.py`
- [ ] `mypy --strict src/spec_kitty_events/` exits 0 (zero errors)
- [ ] `python -m spec_kitty_events.schemas.generate --check` exits 0 (zero drift)
- [ ] `CHANGELOG.md` contains a `## 2.4.0` section with Added and Migration subsections
- [ ] `pyproject.toml` `version` field reads `"2.4.0"`
- [ ] All new dossier exports appear in `__init__.py` with no typos

## Context & Constraints

- **Depends on**: WP04 (all tests must pass before this WP is meaningful).
- **CHANGELOG format**: Follow existing version section headings in `CHANGELOG.md`. Prepend the new section (most recent version at top).
- **Version bump location**: `pyproject.toml` line with `version = "2.3.1"` → `version = "2.4.0"`.

**Implementation command**:
```bash
spec-kitty implement WP05 --base WP04
```

## Subtasks & Detailed Guidance

### Subtask T026 – Write CHANGELOG.md v2.4.0 section

- **Purpose**: Document all new additions and provide explicit migration notes for `spec-kitty` and `spec-kitty-saas` consumer teams so they can upgrade safely and pin versions.
- **Steps**:
  1. Open `CHANGELOG.md` and prepend the following section (adjust any details to match actual implementation):

     ```markdown
     ## 2.4.0 — Mission Dossier Parity Event Contracts (2026-02-21)

     ### Added

     **Domain events (4 new event types)**:
     - `MissionDossierArtifactIndexedPayload` — emitted when an artifact is catalogued
     - `MissionDossierArtifactMissingPayload` — emitted when an expected artifact is absent
     - `MissionDossierSnapshotComputedPayload` — emitted when a dossier snapshot is computed
     - `MissionDossierParityDriftDetectedPayload` — emitted when drift vs baseline is detected

     **Provenance payload objects**:
     - `LocalNamespaceTuple` — 5-field namespace key for collision-safe parity baseline scoping
     - `ArtifactIdentity` — canonical artifact identity (path, class, run, wp scoping)
     - `ContentHashRef` — content fingerprint (hash, algorithm, size, encoding)
     - `ProvenanceRef` — source trace (event IDs, git SHA/ref, actor metadata)

     **Reducer**:
     - `MissionDossierState` — deterministic dossier projection output
     - `reduce_mission_dossier(events)` — pure reducer: filter → sort → dedup → namespace-check → fold
     - `NamespaceMixedStreamError` — raised when event stream spans multiple namespace tuples

     **Conformance infrastructure**:
     - 8 new JSON schemas in `src/spec_kitty_events/schemas/`
     - 13 fixture cases + 2 replay streams in `conformance/fixtures/dossier/`
     - `dossier` fixture category registered in `load_fixtures()`
     - 5 new conformance test categories (§7.6)

     ### Key Invariants

     - `artifact_class` is exclusively in `ArtifactIdentity` — never a top-level event payload field
     - `manifest_version` is exclusively in `LocalNamespaceTuple` — never in event payloads
     - Reducer sort key: `(lamport_clock, timestamp, event_id)` — three-field total order
     - `NamespaceMixedStreamError` carries both expected and offending namespace tuples in the message

     ### Migration: spec-kitty consumers

     **Version pin**: `spec-kitty-events>=2.4.0,<3.0.0`

     No breaking changes. All existing exports (Event envelope, WPStatusChanged,
     lifecycle, collaboration, glossary, mission-next families) are unchanged.

     To emit dossier events:
     ```python
     from spec_kitty_events import (
         MissionDossierArtifactIndexedPayload,
         LocalNamespaceTuple, ArtifactIdentity, ContentHashRef,
         MISSION_DOSSIER_ARTIFACT_INDEXED,
     )
     ```
     Always include a full `LocalNamespaceTuple` with all 5 required fields.
     Use `validate_event(payload_dict, event_type)` to validate before emitting.

     To reduce a dossier event stream:
     ```python
     from spec_kitty_events import reduce_mission_dossier, NamespaceMixedStreamError
     try:
         state = reduce_mission_dossier(events)
     except NamespaceMixedStreamError:
         # partition stream by namespace first
         ...
     ```

     ### Migration: spec-kitty-saas consumers

     **Version pin**: `spec-kitty-events>=2.4.0,<3.0.0`

     No breaking changes. Import the four dossier payload models for ingestion-side validation:
     ```python
     from spec_kitty_events import (
         MissionDossierArtifactIndexedPayload,
         MissionDossierArtifactMissingPayload,
         MissionDossierSnapshotComputedPayload,
         MissionDossierParityDriftDetectedPayload,
     )
     from spec_kitty_events.conformance import validate_event, load_replay_stream
     ```

     Use fixture replay streams for integration test baselines:
     ```python
     events = load_replay_stream("dossier-replay-happy-path")
     events = load_replay_stream("dossier-replay-drift-scenario")
     ```

     Namespace collision prevention: always include the full `LocalNamespaceTuple` when
     keying parity baselines. The reducer rejects mixed-namespace streams; callers must
     partition by namespace before calling `reduce_mission_dossier()`.
     ```

  2. Save `CHANGELOG.md`.

- **Files**: `CHANGELOG.md`
- **Parallel?**: Yes — can be written in parallel with T027/T028/T029 (different file).

### Subtask T027 – Full test suite + coverage verification

- **Purpose**: Confirm that all existing tests continue to pass (no regressions) and that new dossier code has ≥98% line coverage.
- **Steps**:
  1. Run the full test suite:
     ```bash
     python3.11 -m pytest -x
     ```
     Must exit 0. If any test fails, fix before proceeding.

  2. Run dossier-specific coverage:
     ```bash
     python3.11 -m pytest --cov=src/spec_kitty_events/dossier --cov-report=term-missing tests/test_dossier_conformance.py tests/test_dossier_reducer.py
     ```
     Look for lines marked with `miss` in the report. Coverage must be ≥98%.

  3. If coverage is below 98%, identify the uncovered lines and add targeted micro-tests to `test_dossier_reducer.py`:
     - **Payload parse failure branches**: add a test event with `"payload": {}` for each event type and verify the reducer handles it gracefully (no exception, event is skipped or anomaly added).
     - **`_extract_namespace` with None payload**: pass an event where `payload["namespace"]` is missing.
     - **Empty stream after filtering**: pass a stream with only non-dossier events.

- **Files**: No file changes unless coverage fixes are needed.

### Subtask T028 – mypy --strict src/ verification

- **Purpose**: Ensure all new code passes strict type checking, consistent with the project's quality policy.
- **Steps**:
  1. Run:
     ```bash
     mypy --strict src/spec_kitty_events/
     ```
     Must exit 0 with zero errors.

  2. Common issues to fix:
     - **`Optional` return from `_extract_namespace`**: ensure the caller in the reducer handles `None` (if both namespaces are `None`, treat as match or skip the check).
     - **`Dict` vs `dict`**: with `from __future__ import annotations`, use `Dict` from `typing` for 3.10 compat — but mypy may accept `dict[str, Any]` as well. Match existing codebase style.
     - **`Literal` in default**: if mypy complains about `parity_status: Literal["clean", "drifted", "unknown"] = "unknown"`, use `Field(default="unknown")`.
     - **`Any` in payload access**: `event.payload` is `Dict[str, Any]` — `.get("namespace")` returns `Optional[Any]`. Cast as needed to satisfy strict.

  3. If mypy reports errors in test files (test discovery runs mypy too), check `mypy.ini` or `pyproject.toml [tool.mypy]` for `exclude` patterns for `tests/`.

- **Files**: `src/spec_kitty_events/dossier.py` (if fixes needed), `mypy.ini` or `pyproject.toml [tool.mypy]` (if test exclusion needed).

### Subtask T029 – Schema drift check exits 0

- **Purpose**: Confirm that the 8 committed schema files exactly match what the generator would produce. This is the CI gate that prevents schema drift.
- **Steps**:
  1. Run:
     ```bash
     python3.11 -m spec_kitty_events.schemas.generate --check
     ```
     Must print `All N schemas are up to date.` and exit 0.

  2. If drift is reported: re-run the generator without `--check` to regenerate, inspect the diff, and commit the corrected files:
     ```bash
     python3.11 -m spec_kitty_events.schemas.generate
     git diff src/spec_kitty_events/schemas/
     ```

  3. After confirming the schemas look correct, re-run `--check` to verify zero drift.

- **Files**: `src/spec_kitty_events/schemas/` (if regeneration needed)
- **Notes**: If WP02 T007/T008 were done correctly, this should pass immediately.

### Subtask T030 – Export count and version bump

- **Purpose**: Confirm all new dossier symbols are exported and bump the library version to 2.4.0.
- **Steps**:
  1. Count new exports in `src/spec_kitty_events/__init__.py`:
     ```bash
     python3.11 -c "
     import spec_kitty_events as m
     dossier_exports = [name for name in dir(m) if 'Dossier' in name or name in [
         'ArtifactIdentity', 'ContentHashRef', 'ProvenanceRef', 'LocalNamespaceTuple',
         'MissionDossierState', 'reduce_mission_dossier', 'NamespaceMixedStreamError',
         'DOSSIER_EVENT_TYPES',
     ]]
     print('Dossier exports:', sorted(dossier_exports))
     print('Count:', len(dossier_exports))
     "
     ```
     Expected count: ≥10 new dossier symbols.

  2. Verify each expected export is present:
     - `MissionDossierArtifactIndexedPayload`
     - `MissionDossierArtifactMissingPayload`
     - `MissionDossierSnapshotComputedPayload`
     - `MissionDossierParityDriftDetectedPayload`
     - `ArtifactIdentity`
     - `ContentHashRef`
     - `ProvenanceRef`
     - `LocalNamespaceTuple`
     - `MissionDossierState`
     - `reduce_mission_dossier`
     - `NamespaceMixedStreamError`
     - `DOSSIER_EVENT_TYPES` (and optionally the 4 event type string constants)

  3. Bump version in `pyproject.toml`:
     Change `version = "2.3.1"` to `version = "2.4.0"` in the `[project]` section.

  4. Run one final full suite to confirm:
     ```bash
     python3.11 -m pytest -q
     ```

- **Files**: `pyproject.toml`

## Risks & Mitigations

- **Regression in existing tests**: If any existing test fails after WP01-WP04, check for circular import issues (`dossier.py` importing `status.py` at module level vs function level). The lazy import pattern in `mission_next.py` (`from ... import ... inside the function body`) prevents circular imports — dossier.py must follow the same pattern.
- **mypy version sensitivity**: Some mypy strict flags behave differently across minor versions. Check `mypy --version` matches what was used in the existing CI runs (see `pyproject.toml [project.optional-dependencies] dev`).

## Review Guidance

1. `python3.11 -m pytest` — full suite, all green.
2. Coverage ≥98% for `dossier.py` — shown in coverage report.
3. `mypy --strict src/spec_kitty_events/` — zero errors.
4. `python -m spec_kitty_events.schemas.generate --check` — exits 0.
5. `CHANGELOG.md` has `## 2.4.0` section with both Migration subsections and explicit version pins.
6. `pyproject.toml version = "2.4.0"`.
7. All 10+ dossier exports verified importable from top-level package.

## Activity Log

- 2026-02-21T14:00:00Z – system – lane=planned – Prompt created.
- 2026-02-21T14:51:00Z – coordinator – shell_pid=41748 – lane=doing – Assigned agent via workflow command
- 2026-02-21T14:56:21Z – coordinator – shell_pid=41748 – lane=for_review – Full suite passes (842 tests); dossier.py at 100% coverage; CHANGELOG.md v2.4.0 with Added and Migration subsections; version bumped to 2.4.0; mypy --strict clean; schema drift check passes (36 schemas up to date)
