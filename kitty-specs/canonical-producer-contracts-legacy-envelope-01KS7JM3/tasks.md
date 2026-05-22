# Tasks: Canonical Producer Contracts and Legacy Envelope Compatibility

**Mission**: `canonical-producer-contracts-legacy-envelope-01KS7JM3`
**Mission ID**: `01KS7JM3HSNXGCWV2E9X3JGAEP`
**Planning base**: `kitty/pr/1198-canonical-producer-contracts` (mission branch on `main` track)
**Final merge target**: `main` (per orchestrator PR contract for epic Priivacy-ai/spec-kitty#1198)
**Spec**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md) | **Data model**: [data-model.md](./data-model.md) | **Quickstart**: [quickstart.md](./quickstart.md) | **Contracts**: [contracts/legacy-envelope-v1.md](./contracts/legacy-envelope-v1.md)

## Overview

Five backend-only work packages with strict file ownership to avoid `validators.py`, `__init__.py`, and `manifest.json` overlap. The dependency chain is:

- **WP02** (models only, no shared files) and **WP03** (legacy module only, no shared files) run in parallel first.
- **WP01** depends on WP02 (it imports the seven model classes to add them to the `_EVENT_TYPE_TO_MODEL` registry inside `validators.py`).
- **WP04** depends on WP01, WP02, WP03 — it's the public-surface integration hub that owns `__init__.py` and `manifest.json` (exports + all fixture registrations + pyargs fix + stale fixture fix).
- **WP05** depends on all four code WPs — ships CHANGELOG and README docs.

| WP | Title | Subtasks | Estimated lines | Dependencies | Parallel-safe |
|----|-------|----------|-----------------|--------------|---------------|
| WP01 | Conformance semantic dispatch + seven-model registry in validators.py | T001–T005, T009 | ~400 | WP02 | no (after WP02) |
| WP02 | Seven canonical event-type model classes + fixture files | T006–T008, T011, T012 | ~420 | none | yes |
| WP03 | `legacy_envelope_v1` normalizer (`spec_kitty_events.legacy`) | T013–T015, T017, T018 | ~390 | none | yes |
| WP04 | Public-surface integration, manifest registrations, pyargs entrypoint health | T010, T011b, T016, T017b, T019–T022 | ~360 | WP01, WP02, WP03 | no |
| WP05 | CHANGELOG + README docs | T023–T024 | ~190 | WP01, WP02, WP03, WP04 | no |

Total subtasks: 26. All WPs are within the 3–9 subtask range; WP04 is the largest at 8 subtasks but well under the 10-subtask cap.

## Subtask Index

| ID | Description | WP | Parallel |
|----|-------------|----|----------|
| T001 | Add `_SEMANTIC_VALIDATORS: Dict[str, Callable[[BaseModel, dict], Tuple[ModelViolation, ...]]]` registry to `validators.py`. | WP01 | |
| T002 | Implement `_semantic_validate_wp_status_changed(model, payload)` that calls `validate_transition()` and wraps each violation string as a `ModelViolation`. | WP01 | |
| T003 | Wire `_SEMANTIC_VALIDATORS` dispatch into `validate_event()` (run only when `_validate_with_model` returned no model violations AND `event_type in _SEMANTIC_VALIDATORS`). | WP01 | |
| T004 | Add `tests/unit/test_conformance_semantic.py` covering the four unforced backward fixtures, forced valid fixture, bootstrap-planned, force-with-empty-reason regression, and substring routing. | WP01 | |
| T005 | Run `uv run pytest tests/unit/test_status.py tests/unit/test_fixtures.py tests/unit/test_conformance_semantic.py -q` to verify zero regressions and ten new test cases pass. | WP01 | |
| T006 | Create `src/spec_kitty_events/build_lifecycle.py` with `BuildRegisteredPayload`, `BuildHeartbeatPayload`, event-type constants, and `__all__`. | WP02 | [P] |
| T007 | Extend `src/spec_kitty_events/project_lifecycle.py` with `WPAssignedPayload`, `HistoryAddedPayload`, `ErrorLoggedPayload`, `DependencyResolvedPayload`. Update event-type constants and `__all__`. | WP02 | |
| T008 | Extend `src/spec_kitty_events/lifecycle.py` with `MissionOriginBoundPayload`. Update event-type constants and `__all__`. | WP02 | |
| T009 | Register all seven event types in `_EVENT_TYPE_TO_MODEL` in `src/spec_kitty_events/conformance/validators.py`. | WP01 | |
| T010 | Add `LOCAL_ONLY_EVENT_TYPES: frozenset[str] = frozenset()` to `src/spec_kitty_events/__init__.py`. | WP04 | |
| T011 | Author seven canonical fixture JSON files under `src/spec_kitty_events/conformance/fixtures/events/valid/` produced by `model.model_dump(mode="json")` (manifest registration is WP04 T016). | WP02 | [P] |
| T011b | Re-export the seven payload models and the `spec_kitty_events.legacy` surface from `src/spec_kitty_events/__init__.py`. | WP04 | |
| T012 | Add `tests/unit/test_seven_event_contracts.py` with model round-trip, frozen+forbid, and extra-rejection tests per type. (Registry and LOCAL_ONLY tests are covered by WP01 T005 and a sanity import line in WP04 DoD.) | WP02 | |
| T013 | Create `src/spec_kitty_events/legacy.py` with constants `LEGACY_ENVELOPE_CONTRACT_NAME = "legacy_envelope_v1"` and `RECOGNIZED_LEGACY_SHAPES`. | WP03 | |
| T014 | Implement `NormalizedEnvelope`, `UnnormalizableLegacyDiagnostic`, and the `NormalizationResult` union in `legacy.py`. | WP03 | |
| T015 | Implement `LegacyEnvelopeNormalizer` with ordered detectors (`pre_3_0_envelope`, `feature_keys_envelope`, `awaiting_review_synonym`) and fallthrough diagnostic. | WP03 | |
| T016 | Register the seven new event-type fixtures (WP02) in `conformance/fixtures/manifest.json` with `min_version: "5.2.0"`. | WP04 | |
| T017 | Author fixtures `conformance/fixtures/legacy/pre_3_0_envelope_normalizes.json` and `conformance/fixtures/legacy/unrecognized_legacy_diagnostic.json` (manifest registration is WP04 T017b). | WP03 | [P] |
| T017b | Register the two legacy fixtures (WP03) in `conformance/fixtures/manifest.json` under `event_type: "LegacyEnvelope"`, `fixture_type: "legacy_normalization"`. | WP04 | |
| T018 | Add `tests/unit/test_legacy_normalizer.py` covering each detector branch, raw-input preservation, deterministic uuid5 minting, idempotency. | WP03 | |
| T019 | Modify `src/spec_kitty_events/conformance/test_pyargs_entrypoint.py` to detect class_taxonomy / historical_row / lane_mapping wrapper fixtures (top-level keys subset of `{class, expected, input, notes, expected_error_code}`) and extract `entry["input"]` for the `validate_event` call. | WP04 | |
| T020 | Special-case lane_mapping_legacy fixtures (where `input` is `{legacy_lane, canonical_lane}`) so they are NOT routed through `validate_event` — exclude them from `_event_fixture_entries()` or skip via a `class == "lane_mapping_legacy"` guard. | WP04 | |
| T021 | Fix the stale `src/spec_kitty_events/conformance/fixtures/events/invalid/wp_status_changed_invalid_lane.json`: change `to_lane` from canonical `"in_review"` to a genuinely invalid value (`"in_reveiw"` typo). Update manifest `notes`. | WP04 | [P] |
| T022 | Verify `uv run pytest --pyargs spec_kitty_events.conformance -q` exits 0 with all 22 pre-mission failures resolved. | WP04 | |
| T023 | Add `[Unreleased]` entry to `CHANGELOG.md` covering: semantic validation enforcement on `WPStatusChanged`, `legacy_envelope_v1` contract, seven new event-type contracts, `LOCAL_ONLY_EVENT_TYPES` surface, pyargs entrypoint fixes. | WP05 | |
| T024 | Update `README.md` to document `spec_kitty_events.legacy` and `LOCAL_ONLY_EVENT_TYPES`. | WP05 | |

## Requirement coverage

| Requirement | WPs |
|---|---|
| FR-001 (validate_event calls validate_transition for WPStatusChanged) | WP01 |
| FR-002 (violation messages preserve `force=True` and `review-rejection` substrings) | WP01 |
| FR-003 (unforced backward fixtures fail through validate_event) | WP01, WP04 |
| FR-004 (forced + happy-path fixtures still pass) | WP01 |
| FR-005 (bootstrap-planned events still pass) | WP01 |
| FR-006 (LegacyEnvelopeNormalizer + NormalizationResult union) | WP03 |
| FR-007 (named contract `legacy_envelope_v1`, documented) | WP03, WP05 |
| FR-008 (normalization-success fixture) | WP03 |
| FR-009 (un-normalizable fixture) | WP03 |
| FR-010 (seven canonical pydantic payload models) | WP02 |
| FR-011 (seven entries in `_EVENT_TYPE_TO_MODEL`) | WP01 (registry), WP02 (models) |
| FR-012 (seven valid fixtures + manifest entries) | WP02 (files), WP04 (manifest) |
| FR-013 (LOCAL_ONLY_EVENT_TYPES surface) | WP04 |
| FR-014 (pyargs entrypoint green; wrapper extraction) | WP04 |
| FR-015 (stale `wp-status-changed-invalid-lane` fixture fixed) | WP04 |
| FR-016 (CHANGELOG entry) | WP05 |
| FR-017 (README documents new surfaces) | WP05 |
| NFR-001 (validate_event remains deterministic and side-effect-free) | WP01 (reviewer check) |
| NFR-002 (pyargs suite ≤ 10s) | WP04 |
| NFR-003 (LegacyEnvelopeNormalizer deterministic) | WP03 |
| NFR-004 (no new pip dependencies) | WP01, WP02, WP03 (reviewer check) |
| NFR-005 (existing tests stay green) | WP01, WP02, WP03, WP04 |
| C-001 (no PyPI publish in this mission) | program-level |
| C-002 (no changes outside spec-kitty-events) | reviewer check on every WP |
| C-003 (review-rejection rules unchanged) | WP01 (reviewer check) |
| C-004 (fixtures canonical-shaped) | WP02, WP03 |
| C-005 (no SaaS DB mutation) | program-level |
| C-006 (no ingress changes) | program-level |
| C-007 (legacy contract name is `legacy_envelope_v1` and frozen) | WP03 |
| C-008 (LOCAL_ONLY_EVENT_TYPES is `frozenset[str]`) | WP02 |

## Work Packages

### WP01 — Conformance semantic dispatch in `validate_event()`

**Goal**: Wire `status.validate_transition()` into the public conformance gate via a `_SEMANTIC_VALIDATORS` registry, so invalid review-rejection transitions surface as `ModelViolation` entries on the existing `ConformanceResult` API.

**Independent test**: `uv run pytest tests/unit/test_conformance_semantic.py tests/unit/test_status.py tests/unit/test_fixtures.py -q` passes.

**Owned files**:
- `src/spec_kitty_events/conformance/validators.py`
- `tests/unit/test_conformance_semantic.py`

**Authoritative surface**: `src/spec_kitty_events/conformance/`.

**Dependencies**: **WP02** (so the seven payload model classes exist before WP01 imports them to add the `_EVENT_TYPE_TO_MODEL` entries).

**Risks**: 1) Bootstrap-planned events must still pass. Mitigated by T004. 2) The semantic validator could fire on a payload whose pydantic model layer already rejected the shape, double-faulting. Mitigated by gating the dispatch on `len(model_violations) == 0`. 3) Violation message format must be preserved exactly so downstream consumers continue to route on `force=True` and `review-rejection` substrings. Mitigated by T004 substring assertion.

**Included subtasks**:
- [ ] T001 Add `_SEMANTIC_VALIDATORS` registry (WP01)
- [ ] T002 Implement `_semantic_validate_wp_status_changed` (WP01)
- [ ] T003 Wire dispatch into `validate_event()` (WP01)
- [ ] T004 Add `tests/unit/test_conformance_semantic.py` (WP01)
- [ ] T009 Register seven event types in `_EVENT_TYPE_TO_MODEL` (WP01, imports from WP02-shipped modules)
- [ ] T005 Verify zero regressions (WP01)

### WP02 — Seven canonical event-type model classes + fixture files

**Goal**: Ship canonical pydantic payload models for the seven SaaS-bound event types currently emitted without contracts. Author the seven canonical fixture JSON files. Does NOT touch `validators.py`, `__init__.py`, or `manifest.json` — those edits are owned by WP01 (registry) and WP04 (public surface + manifest).

**Independent test**: `uv run pytest tests/unit/test_seven_event_contracts.py tests/unit/test_fixtures.py -q` passes.

**Owned files**:
- `src/spec_kitty_events/build_lifecycle.py` (NEW)
- `src/spec_kitty_events/project_lifecycle.py` (extend existing)
- `src/spec_kitty_events/lifecycle.py` (extend existing)
- `src/spec_kitty_events/conformance/fixtures/events/valid/wp_assigned.json` (NEW)
- `src/spec_kitty_events/conformance/fixtures/events/valid/build_registered.json` (NEW)
- `src/spec_kitty_events/conformance/fixtures/events/valid/build_heartbeat.json` (NEW)
- `src/spec_kitty_events/conformance/fixtures/events/valid/history_added.json` (NEW)
- `src/spec_kitty_events/conformance/fixtures/events/valid/error_logged.json` (NEW)
- `src/spec_kitty_events/conformance/fixtures/events/valid/dependency_resolved.json` (NEW)
- `src/spec_kitty_events/conformance/fixtures/events/valid/mission_origin_bound.json` (NEW)
- `tests/unit/test_seven_event_contracts.py` (NEW)

**Authoritative surface**: `src/spec_kitty_events/`.

**Dependencies**: none (parallel-safe with WP03). WP01 depends on WP02 (imports the seven model classes); WP04 depends on WP02 (re-exports models, registers fixtures in manifest).

**Risks**: 1) Field shapes might drift from the CLI emitter. Mitigated by basing the models on the pre-mission audit. 2) `extra="forbid"` could reject benign extra fields the producer wants to add later. Mitigated by the spec's explicit decision: drift becomes a hard error at the contract boundary. 3) Fixtures must round-trip through `model.model_dump(mode="json")` to stay canonical-shaped (per C-004). T011 enforces this.

**Included subtasks**:
- [x] T006 Create `build_lifecycle.py` (WP02)
- [x] T007 Extend `project_lifecycle.py` (WP02)
- [x] T008 Extend `lifecycle.py` (WP02)
- [x] T011 Author seven canonical fixture JSON files (WP02)
- [x] T012 Add `tests/unit/test_seven_event_contracts.py` (WP02; model-only tests, no registry assertions)

### WP03 — `legacy_envelope_v1` normalizer

**Goal**: Publish the named legacy-envelope compatibility contract via `spec_kitty_events.legacy.LegacyEnvelopeNormalizer`. Ship normalization-success and un-normalizable fixtures so Phase 3 SaaS adapter has a contract to consume.

**Independent test**: `uv run pytest tests/unit/test_legacy_normalizer.py -q` passes.

**Owned files**:
- `src/spec_kitty_events/legacy.py` (NEW)
- `src/spec_kitty_events/conformance/fixtures/legacy/pre_3_0_envelope_normalizes.json` (NEW)
- `src/spec_kitty_events/conformance/fixtures/legacy/unrecognized_legacy_diagnostic.json` (NEW)
- `tests/unit/test_legacy_normalizer.py` (NEW)

**Authoritative surface**: `src/spec_kitty_events/`.

**Dependencies**: none (parallel-safe with WP02). WP04 depends on WP03 (re-exports the legacy surface from `__init__.py` and registers the two legacy fixtures in `manifest.json`).

**Risks**: 1) The detector order matters; first-match wins. T018 covers each branch independently. 2) `uuid5` minting must be deterministic. T018 asserts the same input always yields the same minted uuid. 3) The fallthrough `"unrecognized_legacy_shape"` diagnostic must surface for already-canonical envelopes (no silent passthrough). T018 asserts.

**Included subtasks**:
- [ ] T013 Create `legacy.py` with constants (WP03)
- [ ] T014 Implement `NormalizedEnvelope`, `UnnormalizableLegacyDiagnostic`, `NormalizationResult` (WP03)
- [ ] T015 Implement `LegacyEnvelopeNormalizer` with ordered detectors (WP03)
- [ ] T017 Author success and un-normalizable fixture files (WP03; manifest registration is WP04 T017b)
- [ ] T018 Add `tests/unit/test_legacy_normalizer.py` (WP03)

### WP04 — Public-surface integration, manifest registrations, pyargs entrypoint health

**Goal**: Land the file edits that must come last — `__init__.py` re-exports, `manifest.json` registrations (seven event fixtures + two legacy fixtures), the pyargs entrypoint wrapper-shape extraction, and the stale `wp-status-changed-invalid-lane` fixture fix. After this WP, `pytest --pyargs spec_kitty_events.conformance -q` is green.

**Independent test**: `uv run pytest --pyargs spec_kitty_events.conformance -q` exits 0.

**Owned files**:
- `src/spec_kitty_events/__init__.py`
- `src/spec_kitty_events/conformance/test_pyargs_entrypoint.py`
- `src/spec_kitty_events/conformance/fixtures/events/invalid/wp_status_changed_invalid_lane.json`
- `src/spec_kitty_events/conformance/fixtures/manifest.json`

**Authoritative surface**: `src/spec_kitty_events/conformance/`.

**Dependencies**: **WP01** (semantic dispatch must be live so unforced-backward fixtures fail through `validate_event`), **WP02** (seven model classes and fixture files must exist), **WP03** (legacy module and fixture files must exist).

**Risks**: 1) The lane_mapping fixtures embed `{legacy_lane, canonical_lane}` inside `.input` — they must be skipped, not routed to `validate_event`. T020 ensures this. 2) The fix to the stale `in_review` fixture must produce a value that still fails the existing pydantic Lane enum validation; T021 uses a typo (`in_reveiw`). 3) The 22-failure baseline is the pre-mission gold; after this WP all 22 should be resolved.

**Included subtasks**:
- [ ] T010 Add `LOCAL_ONLY_EVENT_TYPES = frozenset()` to `__init__.py` (WP04)
- [ ] T011b Re-export seven payload models and the `spec_kitty_events.legacy` surface from `__init__.py` (WP04)
- [ ] T016 Register seven new event-type fixtures in `manifest.json` (WP04)
- [ ] T017b Register two legacy fixtures in `manifest.json` (WP04)
- [ ] T019 Detect wrapper-shape fixtures; extract `.input` (WP04)
- [ ] T020 Special-case lane_mapping + LegacyEnvelope fixtures (WP04)
- [ ] T021 Fix stale `wp_status_changed_invalid_lane.json` (WP04)
- [ ] T022 Verify pyargs entrypoint is green (WP04)

### WP05 — CHANGELOG + README docs

**Goal**: Document the new conformance semantics, legacy-envelope contract, seven new event-type contracts, `LOCAL_ONLY_EVENT_TYPES` surface, and pyargs entrypoint fixes. CHANGELOG entry lands under `[Unreleased]` (orchestrator owns the version bump in Phase 5).

**Independent test**: `git diff main --name-only` includes `CHANGELOG.md` and `README.md`; manual review confirms the entries describe what shipped.

**Owned files**:
- `CHANGELOG.md`
- `README.md`

**Authoritative surface**: project root docs.

**Dependencies**: WP01, WP02, WP03, WP04 (docs reflect the final shipped surfaces).

**Risks**: 1) README structure changes are sometimes contentious. Mitigated by inserting a minimal "Legacy normalization" subsection without restructuring existing sections. 2) CHANGELOG voice — match existing entries (e.g. the 5.1.0 entry uses "Changed" and "Added" subsections; this entry follows the same convention).

**Included subtasks**:
- [ ] T023 Add `[Unreleased]` CHANGELOG entry (WP05)
- [ ] T024 Update README with `spec_kitty_events.legacy` and `LOCAL_ONLY_EVENT_TYPES` sections (WP05)

## Parallelization

- **Wave 1 (parallel)**: WP01, WP02, WP03. All three work on disjoint authoritative surfaces and own different test files. Concurrent edits to `validators.py`, `__init__.py`, and `manifest.json` are textually distant and merge cleanly via the lane merge step.
- **Wave 2 (sequential)**: WP04 (depends on WP01 + WP02).
- **Wave 3 (sequential)**: WP05 (depends on all code WPs).

MVP scope: WP01 + WP02 + WP03 together establish the contract surfaces; WP04 finalizes conformance test health; WP05 documents.

## Next command

After `finalize-tasks` succeeds: `/spec-kitty.analyze` for cross-artifact consistency check, then Renata review.
