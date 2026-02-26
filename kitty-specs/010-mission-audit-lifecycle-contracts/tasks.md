# Work Packages: Mission Audit Lifecycle Contracts (010)

**Inputs**: Design documents from `/kitty-specs/010-mission-audit-lifecycle-contracts/`
**Prerequisites**: plan.md (required), spec.md (user stories), research.md, data-model.md, contracts/, quickstart.md

**Tests**: Included — spec explicitly requires unit, property, and conformance tests.

**Organization**: 22 fine-grained subtasks (`Txxx`) roll up into 4 work packages (`WPxx`). WP01 and then WP02+WP03 can run in parallel; WP04 gates on both.

**Prompt Files**: Each work package references a matching prompt file in `/tasks/`.

---

## Work Package WP01: Core Types Module (Priority: P0) 🎯 MVP Start

**Goal**: Create `src/spec_kitty_events/mission_audit.py` with all enums, event type constants, value objects, payload models, and the `ReducedMissionAuditState` output model. This is the foundational contract that every downstream WP depends on.

**Independent Test**: `from spec_kitty_events import mission_audit; mypy --strict src/spec_kitty_events/mission_audit.py` returns zero errors. Each payload model round-trips through `model_validate(model.model_dump(mode="json"))`.

**Prompt**: `/tasks/WP01-core-types-module.md`

**Estimated Prompt Size**: ~270 lines

### Included Subtasks

- [x] T001 Create enums + constants in `mission_audit.py` (AuditVerdict, AuditSeverity, AuditStatus, TERMINAL_AUDIT_STATUSES, AUDIT_SCHEMA_VERSION, 5 event type constants, MISSION_AUDIT_EVENT_TYPES)
- [x] T002 Add frozen value objects to `mission_audit.py` (AuditArtifactRef composing ContentHashRef+ProvenanceRef from dossier.py; PendingDecision; MissionAuditAnomaly)
- [x] T003 [P] Add 5 frozen payload models to `mission_audit.py` (MissionAuditRequestedPayload, MissionAuditStartedPayload, MissionAuditDecisionRequestedPayload, MissionAuditCompletedPayload, MissionAuditFailedPayload)
- [x] T004 Add `ReducedMissionAuditState` frozen output model to `mission_audit.py` (18 fields with defaults; stub `reduce_mission_audit_events()` signature)

### Implementation Notes

- Module: `src/spec_kitty_events/mission_audit.py`
- Start with `from __future__ import annotations` for mypy 3.10 compat
- Import `ContentHashRef`, `ProvenanceRef` from `spec_kitty_events.dossier` (FR-020)
- Import `status_event_sort_key`, `dedup_events` from `spec_kitty_events.status` (for Phase 2)
- Import `Event` from `spec_kitty_events.models`
- Use `ConfigDict(frozen=True)` on every model (FR-019)
- `audit_scope: List[str]` in payload (not Tuple) but store as `Optional[Tuple[str, ...]]` in reducer state
- Stub the reducer function body with `...` — WP02 implements the body

### Parallel Opportunities

- T003 (5 payloads) can be split among engineers but the file must be created first (T001).

### Dependencies

- None (starting package).

### Risks & Mitigations

- `from __future__ import annotations` changes how Pydantic resolves forward refs — always use distinct variable names per type branch to satisfy mypy strict mode.
- `AuditArtifactRef.content_hash` field name must not shadow Python builtins; use `content_hash: ContentHashRef` (not `hash`).

---

## Work Package WP02: Reducer Implementation + Unit Tests (Priority: P1) 🎯 MVP

**Goal**: Implement the `reduce_mission_audit_events()` pure function (pipeline: sort → dedup → filter → fold → freeze) with full state machine, anomaly detection, and pending_decisions management. Write unit tests and Hypothesis property tests verifying all acceptance scenarios.

**Independent Test**: `python3.11 -m pytest tests/unit/test_mission_audit.py tests/test_mission_audit_reducer.py tests/property/test_mission_audit_determinism.py -v` — all pass.

**Prompt**: `/tasks/WP02-reducer-and-unit-tests.md`

**Estimated Prompt Size**: ~520 lines

### Included Subtasks

- [x] T005 Implement `reduce_mission_audit_events()` pipeline in `mission_audit.py` (sort via `status_event_sort_key`, dedup via `dedup_events`, filter to MISSION_AUDIT_EVENT_TYPES, fold via match/dispatch, return frozen `ReducedMissionAuditState`)
- [x] T006 Implement state machine transitions in reducer fold (pending→running on Started; running→awaiting_decision on DecisionRequested; running/awaiting_decision→completed on Completed; running/awaiting_decision→failed on Failed)
- [x] T007 Implement anomaly detection in reducer (`event_before_requested`, `event_after_terminal`, `duplicate_decision_id`, `unrecognized_event_type`)
- [x] T008 Implement pending_decisions management (append PendingDecision on DecisionRequested, dedup by decision_id, clear on terminal event Completed/Failed)
- [x] T009 [P] Write unit tests — `tests/unit/test_mission_audit.py` (5 payload round-trips, required field rejection x5, Literal constraint rejection x2, Field constraint rejection x2, enum validation x3, AuditArtifactRef composition, frozen immutability x5, PendingDecision construction)
- [x] T010 [P] Write reducer unit tests — `tests/test_mission_audit_reducer.py` (happy-path pass, happy-path fail, decision checkpoint, empty stream, dedup, 4 anomaly scenarios, terminal clears pending, partial artifact, 3 golden-file replay)
- [x] T011 [P] Write Hypothesis property tests — `tests/property/test_mission_audit_determinism.py` (order independence ≥200 examples, idempotent dedup ≥200 examples, monotonic event_count ≥200 examples)

### Implementation Notes

- Reducer fold pattern: parse payload by event_type, update mutable local state dict, convert to frozen `ReducedMissionAuditState` at end
- Golden-file replay: write golden files as JSON to `tests/fixtures/mission_audit_golden/` — commit them so future runs are byte-for-byte deterministic
- Use `model_dump(mode="json", sort_keys=True)` for golden-file comparison to avoid field-ordering brittleness
- Anomaly order: append in processing order; the tuple is stable across same-ordered input
- `event_count` = number of events after dedup (not after filter)

### Parallel Opportunities

- T009, T010, T011 are parallel-safe once T005-T008 are complete.

### Dependencies

- Depends on WP01.

### Risks & Mitigations

- Golden-file brittleness on field ordering → use `sort_keys=True` in `json.dumps` comparisons.
- Hypothesis strategy complexity → use `st.lists(st.sampled_from(events), min_size=1)` for permutation tests.
- State machine edge case: `DecisionRequested` can arrive multiple times → dedup by `decision_id`; second occurrence with same ID is an anomaly.

---

## Work Package WP03: Conformance Integration (Priority: P1)

**Goal**: Register 5 new audit event types in the conformance system: generate JSON schemas, update validators.py and loader.py, create all 14 fixture files (7 valid + 4 invalid + 3 replay JSONL + 3 golden snapshots) and update manifest.json with 17 entries.

**Independent Test**: `pytest --pyargs spec_kitty_events.conformance` passes (all mission_audit fixtures load and validate). `python -c "from spec_kitty_events.conformance.loader import load_fixtures; load_fixtures('mission_audit')"` succeeds.

**Prompt**: `/tasks/WP03-conformance-integration.md`

**Estimated Prompt Size**: ~420 lines

### Included Subtasks

- [x] T012 Generate 5 JSON schema files in `src/spec_kitty_events/schemas/` via `TypeAdapter(...).json_schema()` (mission_audit_requested_payload.json, mission_audit_started_payload.json, mission_audit_decision_requested_payload.json, mission_audit_completed_payload.json, mission_audit_failed_payload.json)
- [x] T013 Update `src/spec_kitty_events/conformance/validators.py` — add 5 imports from `mission_audit`, 5 entries to `_EVENT_TYPE_TO_MODEL`, 5 entries to `_EVENT_TYPE_TO_SCHEMA`
- [x] T014 Update `src/spec_kitty_events/conformance/loader.py` — add `"mission_audit"` to `_VALID_CATEGORIES` frozenset
- [x] T015 [P] Create 7 valid fixture JSON files in `src/spec_kitty_events/conformance/fixtures/mission_audit/valid/`
- [x] T016 [P] Create 4 invalid fixture JSON files in `src/spec_kitty_events/conformance/fixtures/mission_audit/invalid/`
- [x] T017 [P] Create 3 replay JSONL files + 3 golden reducer output JSON files in `src/spec_kitty_events/conformance/fixtures/mission_audit/replay/`
- [x] T018 Update `src/spec_kitty_events/conformance/fixtures/manifest.json` with 17 new entries (7 valid + 4 invalid + 3 replay_stream + 3 reducer_output), all `min_version: "2.5.0"`

### Implementation Notes

- Schema generation script pattern: `TypeAdapter(MissionAuditRequestedPayload).json_schema()` — run once, commit the output
- Fixture naming (follow existing convention exactly — underscores in filenames):
  - valid/: `mission_audit_requested_manual.json`, `mission_audit_requested_post_merge.json`, `mission_audit_started_valid.json`, `mission_audit_decision_requested_valid.json`, `mission_audit_completed_pass.json`, `mission_audit_completed_fail.json`, `mission_audit_failed_valid.json`
  - invalid/: `mission_audit_completed_missing_verdict.json`, `mission_audit_completed_missing_artifact_ref.json`, `mission_audit_requested_bad_trigger.json`, `mission_audit_decision_missing_id.json`
  - replay/: `mission_audit_replay_pass.jsonl`, `mission_audit_replay_fail.jsonl`, `mission_audit_replay_decision_checkpoint.jsonl`, `mission_audit_replay_pass_output.json`, `mission_audit_replay_fail_output.json`, `mission_audit_replay_decision_checkpoint_output.json`
- Replay JSONL: each line is a full Event envelope (JSON), not just payload
- Golden output files: produce by running `reduce_mission_audit_events()` on the replay stream; serialize with `model_dump(mode="json")`; commit; future CI compares against committed file

### Parallel Opportunities

- T015, T016, T017 can proceed in parallel once the fixture directory structure exists.

### Dependencies

- Depends on WP01 (payload models needed for schema gen and validator imports).
- Can run in parallel with WP02.

### Risks & Mitigations

- Manifest format drift → check existing manifest.json structure before adding entries; follow exact field names.
- Replay golden files must match WP02 golden files exactly → generate both from the same reducer call; do not hand-write.

---

## Work Package WP04: Conformance Tests + Public API + Release (Priority: P2)

**Goal**: Write conformance tests, add 21 exports to `__init__.py`, bump version 2.4.0 → 2.5.0, update package-data globs, and verify all quality gates pass.

**Independent Test**: `python3.11 -m pytest tests/ -v --tb=short` — all pass with ≥98% coverage. `mypy --strict src/spec_kitty_events/__init__.py src/spec_kitty_events/mission_audit.py` — zero errors.

**Prompt**: `/tasks/WP04-conformance-tests-public-api-release.md`

**Estimated Prompt Size**: ~310 lines

### Included Subtasks

- [x] T019 [P] Write conformance tests — `tests/test_mission_audit_conformance.py` (7 valid fixture validation, 4 invalid fixture rejection with field-level violations, 3 replay stream validation + reducer golden comparison, 5 schema drift checks)
- [x] T020 Update `src/spec_kitty_events/__init__.py` — add 21 new exports: 5 event type constants, MISSION_AUDIT_EVENT_TYPES, 3 enums, 2 value objects, 5 payload models, MissionAuditAnomaly, ReducedMissionAuditState, reduce_mission_audit_events, AUDIT_SCHEMA_VERSION, TERMINAL_AUDIT_STATUSES
- [x] T021 Bump version 2.4.0 → 2.5.0 in `pyproject.toml` (version field) and `__init__.py` (__version__)
- [x] T022 Update `pyproject.toml` package-data globs to include `conformance/fixtures/mission_audit/**` so fixtures are shipped with the package

### Implementation Notes

- Conformance test pattern: load fixture via `load_fixtures("mission_audit")`, call `validate_event(payload, event_type)`, assert `result.valid` and check `result.model_violations` for invalid cases
- Schema drift check: call `TypeAdapter(PayloadModel).json_schema()`, load committed JSON schema file, assert equal
- `__init__.py` exports: follow existing grouping pattern — add a `# Mission Audit Lifecycle Contracts (2.5.0)` comment block before the 21 new names
- `__version__` check: `from spec_kitty_events import __version__; assert __version__ == "2.5.0"`
- Run full test suite before finalizing: `python3.11 -m pytest tests/ -v` — ensure zero regressions on existing collaboration, glossary, dossier, mission_next test suites

### Parallel Opportunities

- T019 is parallel-safe with T020-T022.

### Dependencies

- Depends on WP02 (reducer needed for conformance tests to exercise replay → reduce flow).
- Depends on WP03 (fixtures needed for conformance tests).

### Risks & Mitigations

- Export completeness: `from spec_kitty_events import MissionAuditRequestedPayload, reduce_mission_audit_events, AuditVerdict, MISSION_AUDIT_REQUESTED` — verify this import block succeeds.
- mypy strict on `__init__.py`: re-exported names need `__all__` or explicit `from ... import X as X` syntax to satisfy mypy's implicit re-export rules.
- Package-data glob: test that `pip install -e .` installs the fixture files under `site-packages/spec_kitty_events/conformance/fixtures/mission_audit/`.

---

## Dependency & Execution Summary

- **Sequence**: WP01 → (WP02 ‖ WP03) → WP04
- **Parallelization**: After WP01 lands, WP02 (reducer + unit tests) and WP03 (conformance integration) can proceed independently in parallel; WP04 waits for both.
- **MVP Scope**: WP01 + WP02 deliver the core event contracts and reducer (User Stories 1 & 2). WP03 + WP04 complete the conformance suite and public API (User Stories 3-5).

---

## Subtask Index (Reference)

| Subtask ID | Summary | Work Package | Priority | Parallel? |
|------------|---------|--------------|----------|-----------|
| T001 | Enums + constants in mission_audit.py | WP01 | P0 | No |
| T002 | Value objects (AuditArtifactRef, PendingDecision, MissionAuditAnomaly) | WP01 | P0 | No |
| T003 | 5 frozen payload models | WP01 | P0 | Yes |
| T004 | ReducedMissionAuditState + reducer stub | WP01 | P0 | No |
| T005 | Reducer pipeline (sort→dedup→filter→fold→freeze) | WP02 | P1 | No |
| T006 | State machine transitions | WP02 | P1 | No |
| T007 | Anomaly detection | WP02 | P1 | No |
| T008 | pending_decisions management | WP02 | P1 | No |
| T009 | Unit tests — payload validation | WP02 | P1 | Yes |
| T010 | Reducer unit tests (12 scenarios + 3 golden-file) | WP02 | P1 | Yes |
| T011 | Hypothesis property tests (3 properties, ≥200 examples) | WP02 | P1 | Yes |
| T012 | Generate 5 JSON schema files | WP03 | P1 | No |
| T013 | Update validators.py (5 model + 5 schema entries) | WP03 | P1 | No |
| T014 | Update loader.py (add "mission_audit" category) | WP03 | P1 | No |
| T015 | Create 7 valid fixture JSON files | WP03 | P1 | Yes |
| T016 | Create 4 invalid fixture JSON files | WP03 | P1 | Yes |
| T017 | Create 3 replay JSONL + 3 golden output files | WP03 | P1 | Yes |
| T018 | Update manifest.json (17 new entries) | WP03 | P1 | No |
| T019 | Conformance tests (valid, invalid, replay, schema drift) | WP04 | P2 | Yes |
| T020 | Add 21 exports to __init__.py | WP04 | P2 | Yes |
| T021 | Bump version 2.4.0 → 2.5.0 | WP04 | P2 | Yes |
| T022 | Update pyproject.toml package-data globs | WP04 | P2 | Yes |

<!-- status-model:start -->
## Canonical Status (Generated)
- WP01: done
- WP02: done
- WP03: done
- WP04: for_review
<!-- status-model:end -->
