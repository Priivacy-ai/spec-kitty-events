# Tasks — Decision Moment V1 Contract Freeze

**Mission:** `decision-moment-v1-contract-freeze-01KPWA0N` (mid8: `01KPWA0N`)
**Planning/base branch:** `main`
**Final merge target:** `main`
**Date:** 2026-04-23

This file enumerates the subtasks and work packages needed to freeze the `spec-kitty-events 4.0.0` Decision Moment V1 contract. Every subtask appears in exactly one work package. No two work packages touch the same files.

## Subtask Index

| ID   | Description                                                                                                    | WP   | Parallel |
|------|----------------------------------------------------------------------------------------------------------------|------|----------|
| T001 | Create `decision_moment.py` module with V1 enums and shared Pydantic models                                    | WP01 |          |
| T002 | Extend `collaboration.py`: add `ParticipantExternalRefs`, add optional `external_refs` to `ParticipantIdentity`| WP01 |          |
| T003 | Unit tests for V1 shared models (`tests/unit/test_decision_moment_models.py`)                                  | WP01 | [P]      |
| T004 | Unit tests for `ParticipantIdentity.external_refs` extension                                                   | WP01 | [P]      |
| T005 | Add `DECISION_POINT_WIDENED`, `WIDENED` state, update state/transition tables, bump schema version to 3.0.0    | WP02 |          |
| T006 | Refactor `DecisionPointOpenedPayload` into tagged discriminated union (ADR + interview variants)               | WP02 |          |
| T007 | Add `DecisionPointWidenedPayload` (single model) and register in `_EVENT_TO_PAYLOAD`                           | WP02 |          |
| T008 | Refactor `DecisionPointDiscussingPayload` into tagged discriminated union                                      | WP02 |          |
| T009 | Refactor `DecisionPointResolvedPayload` into tagged discriminated union with cross-field validator             | WP02 |          |
| T010 | Extend `DecisionPointOverriddenPayload` with optional `origin_surface`                                         | WP02 |          |
| T011 | Extend `ReducedDecisionPointState` with V1 projection fields + plumb `WideningProjection`                      | WP02 |          |
| T012 | Extend reducer `reduce_decision_point_events`: branch on origin, idempotent Widened, new anomaly kinds         | WP02 |          |
| T013 | Extend reducer unit tests `tests/test_decisionpoint_reducer.py` with V1 transitions and anomaly cases          | WP03 |          |
| T014 | Extend property tests `tests/property/test_decisionpoint_determinism.py` with V1 Hypothesis generators         | WP03 |          |
| T015 | Assert byte-identical replay under permuted Lamport orderings in property tests                                | WP03 |          |
| T016 | Extend `src/spec_kitty_events/schemas/generate.py` to emit V1 payloads and shared models                       | WP04 |          |
| T017 | Regenerate and commit DecisionPoint and shared JSON schemas                                                    | WP04 |          |
| T018 | Extend `tests/integration/test_schema_drift.py` for new schemas                                                | WP04 |          |
| T019 | Add valid conformance fixtures under `conformance/fixtures/decisionpoint/valid/`                               | WP05 | [P]      |
| T020 | Add invalid conformance fixtures under `conformance/fixtures/decisionpoint/invalid/`                           | WP05 | [P]      |
| T021 | Extend `tests/test_decisionpoint_conformance.py` to iterate new fixtures                                       | WP05 |          |
| T022 | Create 6 golden replay fixture pairs under `tests/fixtures/decisionpoint_golden/` (+ mirror under conformance) | WP06 |          |
| T023 | Extend `tests/integration/test_lifecycle_replay.py` to replay every golden pair byte-identically               | WP06 |          |
| T024 | Property test: golden replay is byte-identical across permuted Lamport orderings                               | WP06 |          |
| T025 | Bump package version in `pyproject.toml` from 3.3.0 to 4.0.0                                                   | WP07 | [P]      |
| T026 | Extend `src/spec_kitty_events/__init__.py` to re-export V1 types                                               | WP07 | [P]      |
| T027 | Update `CHANGELOG.md` with 4.0.0 section                                                                       | WP07 | [P]      |
| T028 | Update `COMPATIBILITY.md` with Decision Moment V1 (4.0.0) block                                                | WP07 | [P]      |

## Work Packages

### WP01 — Shared V1 foundation models

**Goal.** Land the reusable cross-channel identity and Decision-Moment shared models that every downstream WP imports. This is the only WP that extends `collaboration.py`, and it creates the new `decision_moment.py` module that holds V1 enums and shared Pydantic models (SummaryBlock, TeamspaceRef, DefaultChannelRef, ThreadRef, ClosureMessageRef, WideningProjection).

**Priority.** P0 (foundation; nothing else can compile without these).

**Independent test.** `pytest tests/unit/test_decision_moment_models.py tests/unit/test_collaboration_models.py -q` passes, `mypy --strict src/spec_kitty_events/decision_moment.py src/spec_kitty_events/collaboration.py` is clean.

**Included subtasks.**

- [ ] T001 Create `decision_moment.py` module with V1 enums and shared Pydantic models (WP01)
- [ ] T002 Extend `collaboration.py`: add `ParticipantExternalRefs`, add optional `external_refs` to `ParticipantIdentity` (WP01)
- [ ] T003 Unit tests for V1 shared models (WP01)
- [ ] T004 Unit tests for `ParticipantIdentity.external_refs` extension (WP01)

**Implementation sketch.**

1. Create `src/spec_kitty_events/decision_moment.py`. Define enums (`OriginSurface`, `OriginFlow`, `TerminalOutcome`, `SummarySource`, `WideningChannel`, `DiscussingSnapshotKind`), shared models (`SummaryBlock`, `TeamspaceRef`, `DefaultChannelRef`, `ThreadRef`, `ClosureMessageRef`, `WideningProjection`) per `data-model.md` §1, §2.1.
2. In `collaboration.py`, add `ParticipantExternalRefs` (frozen, `extra="forbid"`, all fields optional but at least one required via `model_validator`) above `ParticipantIdentity`. Add `external_refs: Optional[ParticipantExternalRefs] = None` to `ParticipantIdentity`. Preserve 3.x compatibility: existing consumers that omit `external_refs` continue validating.
3. New test file `tests/unit/test_decision_moment_models.py` covering: enum values, `SummaryBlock` with/without `extracted_at`/`candidate_answer`, ThreadRef schema, each ref model rejects empty required fields.
4. Extend `tests/unit/test_collaboration_models.py` with cases for `external_refs` with only `slack_user_id`, only `teamspace_member_id`, all three, and empty (must reject).

**Parallel opportunities.** T003 and T004 can be authored in parallel once T001 and T002 land.

**Dependencies.** None.

**Risks.** `ParticipantIdentity` is heavily used in `collaboration.py` reducers; ensure no existing usage becomes type-incompatible. The class is `frozen=True` without `extra="forbid"`, so existing consumers that pass extra kwargs would already be accepted — preserve that.

**Estimated prompt size.** ~280 lines.

---

### WP02 — DecisionPoint 4.0.0 refactor (payloads, state, reducer)

**Goal.** Execute the core 4.0.0 contract refactor inside `decisionpoint.py`: introduce the `WIDENED` state, add `DecisionPointWidenedPayload`, refactor Opened/Discussing/Resolved into Pydantic v2 discriminated unions on `origin_surface`, extend Overridden with optional `origin_surface`, extend `ReducedDecisionPointState` with V1 projection fields, and extend the reducer to branch on per-event origin, idempotently handle duplicate Widened, and detect new anomaly kinds (`origin_mismatch`, `closed_locally_without_widening`). Bump `DECISIONPOINT_SCHEMA_VERSION` to `"3.0.0"`.

**Priority.** P0 (the contract itself).

**Independent test.** `pytest tests/unit/test_decisionpoint.py -q` passes (covering all discriminated-union variants and cross-field validator) and `mypy --strict src/spec_kitty_events/decisionpoint.py` clean.

**Included subtasks.**

- [ ] T005 Add `DECISION_POINT_WIDENED`, `WIDENED` state, update state/transition tables, bump schema version to 3.0.0 (WP02)
- [ ] T006 Refactor `DecisionPointOpenedPayload` into tagged discriminated union (WP02)
- [ ] T007 Add `DecisionPointWidenedPayload` and register in `_EVENT_TO_PAYLOAD` (WP02)
- [ ] T008 Refactor `DecisionPointDiscussingPayload` into tagged discriminated union (WP02)
- [ ] T009 Refactor `DecisionPointResolvedPayload` into tagged discriminated union with cross-field validator (WP02)
- [ ] T010 Extend `DecisionPointOverriddenPayload` with optional `origin_surface` (WP02)
- [ ] T011 Extend `ReducedDecisionPointState` with V1 projection fields + plumb `WideningProjection` (WP02)
- [ ] T012 Extend reducer `reduce_decision_point_events`: branch on origin, idempotent Widened, new anomaly kinds (WP02)

**Implementation sketch.**

1. **T005**: Add `DECISION_POINT_WIDENED = "DecisionPointWidened"`, include in `DECISION_POINT_EVENT_TYPES`. Add `WIDENED = "widened"` to `DecisionPointState` enum. Update `_EVENT_TO_STATE[DECISION_POINT_WIDENED] = DecisionPointState.WIDENED`. Update `_ALLOWED_TRANSITIONS`: `OPEN → {WIDENED, DISCUSSING, RESOLVED}`, `WIDENED → {WIDENED (idempotent no-op), DISCUSSING, RESOLVED}`, `DISCUSSING → {DISCUSSING, RESOLVED}` unchanged, terminal states unchanged. Bump `DECISIONPOINT_SCHEMA_VERSION = "3.0.0"`.
2. **T006**: Rename existing `DecisionPointOpenedPayload` to `DecisionPointOpenedAdrPayload`. Add `origin_surface: Literal[OriginSurface.ADR]` as required field. Create `DecisionPointOpenedInterviewPayload` per `data-model.md` §2.2. Export `DecisionPointOpenedPayload` as `Annotated[Union[...], Field(discriminator="origin_surface")]`. Update `_EVENT_TO_PAYLOAD[DECISION_POINT_OPENED]` to point at the union (use `TypeAdapter` for validation if needed).
3. **T007**: Add `DecisionPointWidenedPayload` per `data-model.md` §2.3. Register `_EVENT_TO_PAYLOAD[DECISION_POINT_WIDENED] = DecisionPointWidenedPayload`.
4. **T008**: Same pattern as T006 but for Discussing (ADR + interview variants per `data-model.md` §2.4).
5. **T009**: Same pattern for Resolved per §2.5, plus a `@model_validator(mode="after")` on the interview variant enforcing the cross-field rules (terminal_outcome=resolved ⇒ final_answer required; terminal_outcome∈{deferred, canceled} ⇒ final_answer must be absent AND rationale required AND other_answer=False).
6. **T010**: Add `origin_surface: Optional[OriginSurface] = None` to `DecisionPointOverriddenPayload`. No other changes; this is a backward-compatible addition.
7. **T011**: Extend `ReducedDecisionPointState` per `data-model.md` §5 (add `origin_surface`, `origin_flow`, `question`, `options`, `input_key`, `step_id`, `widening: Optional[WideningProjection]`, `terminal_outcome`, `final_answer`, `other_answer`, `summary`, `actual_participants`, `resolved_by`, `closed_locally_while_widened`, `closure_message`). Extend `DecisionPointState` enum to include `WIDENED`.
8. **T012**: Extend `reduce_decision_point_events` to: (a) branch on each event's `payload.origin_surface` where discriminated, (b) populate V1 projection fields from each event, (c) treat second `DecisionPointWidened` for the same `decision_point_id` as idempotent no-op (log no anomaly), (d) detect `closed_locally_while_widened=true` without a prior Widened → anomaly `invalid_transition`, (e) detect per-`decision_point_id` origin mismatch → anomaly kind `origin_mismatch` (new). Extend `DecisionPointAnomaly.kind` docstring to list new valid values.

Also extend `tests/unit/test_decisionpoint.py` with V1 unit coverage per `data-model.md` §7 in parallel with above subtasks (colocated in same file; one test class per variant).

**Parallel opportunities.** None internal; all subtasks operate on the same module and sequence matters.

**Dependencies.** WP01 (needs `OriginSurface`, `TerminalOutcome`, `SummaryBlock`, `TeamspaceRef`, `DefaultChannelRef`, `ThreadRef`, `ClosureMessageRef`, `ParticipantIdentity.external_refs`, `WideningProjection` from `decision_moment.py` and `collaboration.py`).

**Risks.** The main risk is Pydantic v2 discriminator syntax correctness (`Annotated[Union[...], Field(discriminator=...)]` vs `Discriminator` class). Test with small examples locally before committing. Reducer branching must preserve existing ADR semantics exactly — run the 3.x reducer test suite against the new code before adding V1 tests. Idempotent Widened must not double-count via `event_count`.

**Estimated prompt size.** ~680 lines.

---

### WP03 — Reducer extension tests and property determinism

**Goal.** Prove the reducer extensions from WP02 are correct and deterministic via targeted reducer tests and Hypothesis-based property tests. Property tests must cover at least 500 generated streams per run and assert byte-identical replay output across permuted Lamport orderings.

**Priority.** P1 (blocks merge; property tests lock NFR-001/NFR-005).

**Independent test.** `pytest tests/test_decisionpoint_reducer.py tests/property/test_decisionpoint_determinism.py -q` passes with ≥500 Hypothesis runs.

**Included subtasks.**

- [ ] T013 Extend reducer unit tests `tests/test_decisionpoint_reducer.py` with V1 transitions and anomaly cases (WP03)
- [ ] T014 Extend property tests with V1 Hypothesis generators (WP03)
- [ ] T015 Assert byte-identical replay under permuted Lamport orderings (WP03)

**Implementation sketch.**

1. **T013** extends `tests/test_decisionpoint_reducer.py` with: Opened(interview)→Resolved(resolved) projection assertions; Opened→Widened→Discussing→Resolved full-path projection; Opened→Widened→Resolved(closed_locally=true) projection; duplicate Widened idempotency (second Widened is ignored for state but recorded in `event_count`); `closed_locally_while_widened=true` without prior Widened produces `invalid_transition` anomaly; origin_mismatch between Opened(adr) and Resolved(interview) produces `origin_mismatch` anomaly; terminal `RESOLVED → OVERRIDDEN` still works for interview origin; Other/free-text resolution populates `other_answer=true` and `final_answer`.
2. **T014** extends `tests/property/test_decisionpoint_determinism.py` with new strategies: `st_interview_opened()`, `st_widened()`, `st_interview_resolved(terminal_outcome)`, `st_interview_resolved_other()`. Compose a mixed-origin-safe stream generator (within a single `decision_point_id`, keep origin consistent; across ids, allow mix).
3. **T015** adds a property test `test_decisionpoint_reducer_byte_identical_under_permutation`: generate an event stream, serialize `reduce_decision_point_events(events).model_dump(mode="json", by_alias=True)` with sorted-key JSON, shuffle to any ordering that preserves Lamport precedence, re-reduce, and assert the two byte strings are equal. Hypothesis `@settings(max_examples=500, deadline=None)`.

**Parallel opportunities.** T013, T014, T015 are authored in this order but T014/T015 can be refined in parallel.

**Dependencies.** WP02 (reducer implementation).

**Risks.** Hypothesis strategy composition can hit determinism-breaking behaviors if strategies share mutable state; keep strategies pure. Use `st.builds(...)` over `st.composite` where possible. Ensure permutation generator respects Lamport ordering (the existing `status_event_sort_key` helper normalises, but strategies must not produce non-comparable events).

**Estimated prompt size.** ~300 lines.

---

### WP04 — JSON schema regeneration

**Goal.** Regenerate the committed JSON Schemas to match the 4.0.0 Pydantic models, add new schema files for the new shared models, and keep `tests/integration/test_schema_drift.py` green.

**Priority.** P1.

**Independent test.** `pytest tests/integration/test_schema_drift.py -q` passes; no diff between committed schemas and `schemas/generate.py` output.

**Included subtasks.**

- [ ] T016 Extend `src/spec_kitty_events/schemas/generate.py` to emit V1 payloads and shared models (WP04)
- [ ] T017 Regenerate and commit DecisionPoint and shared JSON schemas (WP04)
- [ ] T018 Extend `tests/integration/test_schema_drift.py` for new schemas (WP04)

**Implementation sketch.**

1. **T016** extends `generate.py` registration to include: `DecisionPointWidenedPayload`, the discriminated-union payload types (which emit `oneOf` schemas), `SummaryBlock`, `ParticipantExternalRefs`, `TeamspaceRef`, `DefaultChannelRef`, `ThreadRef`, `ClosureMessageRef`, and the updated `ParticipantIdentity` (with `external_refs`). Confirm Pydantic v2 `model_json_schema()` emits `oneOf` for discriminated unions.
2. **T017** runs `python -m spec_kitty_events.schemas.generate` to regenerate, commits the resulting schema files. Replace `decision_point_opened_payload.schema.json`, `decision_point_discussing_payload.schema.json`, `decision_point_resolved_payload.schema.json`. Add `decision_point_widened_payload.schema.json`, `summary_block.schema.json`, `participant_external_refs.schema.json`, `teamspace_ref.schema.json`, `default_channel_ref.schema.json`, `thread_ref.schema.json`, `closure_message_ref.schema.json`. Update `decision_point_overridden_payload.schema.json` to include the new optional `origin_surface` property.
3. **T018** ensures `tests/integration/test_schema_drift.py` iterates all regenerated files; if the test uses a hard-coded list of payload names, extend it. If it globs the schemas directory, no change required.

**Parallel opportunities.** T017 depends on T016. T018 is independent but conceptually last.

**Dependencies.** WP02 (models must be final; schemas are derived).

**Risks.** Pydantic v2's tagged-union schema output uses `discriminator` + `oneOf`. Earlier `jsonschema` validators without `draft-2020-12` support may not understand `discriminator`; confirm the repo's conformance validators use draft 2020-12 (it's already set on our planning contracts; the committed schemas already target 2020-12 elsewhere in the repo).

**Estimated prompt size.** ~260 lines.

---

### WP05 — Conformance fixtures (valid + invalid) and conformance tests

**Goal.** Ship committed valid and invalid conformance fixtures under `src/spec_kitty_events/conformance/fixtures/decisionpoint/{valid,invalid}/` for each V1 payload shape, and wire the existing `tests/test_decisionpoint_conformance.py` to iterate them.

**Priority.** P1.

**Independent test.** `pytest tests/test_decisionpoint_conformance.py -q` passes; every valid fixture validates against its JSON Schema AND its Pydantic model; every invalid fixture fails both validations with structured errors.

**Included subtasks.**

- [ ] T019 Add valid conformance fixtures under `conformance/fixtures/decisionpoint/valid/` (WP05)
- [ ] T020 Add invalid conformance fixtures under `conformance/fixtures/decisionpoint/invalid/` (WP05)
- [ ] T021 Extend `tests/test_decisionpoint_conformance.py` to iterate new fixtures (WP05)

**Implementation sketch.**

1. **T019** writes the 10 valid fixtures enumerated in `data-model.md` §8.1. Each fixture is a single-event JSON document matching the event envelope shape used elsewhere in the repo (`tests/test_decisionpoint_conformance.py` shows the existing format). Use deterministic ULIDs for `decision_point_id` so fixtures stay byte-stable.
2. **T020** writes the 5 invalid fixtures enumerated in `data-model.md` §8.2. Each fixture is minimally invalid (omit one required field or set a forbidden combination) so the assertion is clear.
3. **T021** extends `tests/test_decisionpoint_conformance.py` to iterate the new fixtures. Parametrize over `valid/*.json` and `invalid/*.json`. Use `jsonschema.validate` (schema path) and `payload_cls.model_validate` (Pydantic path). Assert valid fixtures validate against both; invalid fixtures fail both with a matching error path (e.g., `/terminal_outcome` for the missing-terminal-outcome case).

**Parallel opportunities.** T019 and T020 can be authored in parallel.

**Dependencies.** WP02 (needs payload classes), WP04 (needs committed schemas).

**Risks.** Envelope shape for conformance fixtures must match the existing convention in the repo (`event_id`, `event_type`, `payload`, timestamps). Copy the shape from one existing valid fixture under `conformance/fixtures/decisionpoint/valid/` before writing V1 fixtures.

**Estimated prompt size.** ~340 lines.

---

### WP06 — Golden replay fixtures and integration replay tests

**Goal.** Ship 6 golden replay fixture pairs (`.jsonl` + paired `_output.json`) covering: local_only_resolved, widened_resolved, widened_closed_locally, deferred, canceled, and resolved_other. Wire `tests/integration/test_lifecycle_replay.py` to replay each pair and assert byte-identical output from `reduce_decision_point_events`. Add permutation property test for golden fixtures.

**Priority.** P1.

**Independent test.** `pytest tests/integration/test_lifecycle_replay.py -q` passes; every golden pair reproduces its `_output.json` byte-identically.

**Included subtasks.**

- [ ] T022 Create 6 golden replay fixture pairs (WP06)
- [ ] T023 Extend `tests/integration/test_lifecycle_replay.py` to replay every golden pair byte-identically (WP06)
- [ ] T024 Property test: golden replay is byte-identical across permuted Lamport orderings (WP06)

**Implementation sketch.**

1. **T022** writes 6 pairs into `tests/fixtures/decisionpoint_golden/` per `data-model.md` §8.3. Also mirror each pair into `src/spec_kitty_events/conformance/fixtures/decisionpoint/replay/` (same file names) so downstream consumers can use the package as the authoritative replay source. Use stable ULIDs and timestamps so bytes are reproducible.
2. **T023** extends `tests/integration/test_lifecycle_replay.py` to iterate the 6 pairs, load each `.jsonl`, reduce, dump with sorted-key JSON, and compare to the paired `_output.json` (also dumped with sorted-key JSON). Use byte-string comparison, not semantic equality.
3. **T024** adds a property test that, for each golden stream, permutes the events in any ordering consistent with Lamport precedence and asserts the reduced output is byte-identical.

**Parallel opportunities.** T023 and T024 can be authored in parallel after T022.

**Dependencies.** WP02 (reducer extensions), WP04 (schema regeneration for envelope validation). Runs after WP05 conceptually but doesn't share files with it.

**Risks.** Byte-identical output requires deterministic JSON serialization settings (sorted keys, no whitespace unless documented, UTC ISO timestamps). Pydantic v2 `model_dump(mode="json", by_alias=True)` plus `json.dumps(..., sort_keys=True, separators=(",", ":"))` is the standard. Any drift breaks the golden. Ensure both fixture output and test output use the same settings.

**Estimated prompt size.** ~300 lines.

---

### WP07 — Release docs, version bump, and re-exports

**Goal.** Complete the 4.0.0 release: bump `pyproject.toml` version, re-export all new V1 types from `src/spec_kitty_events/__init__.py`, update `CHANGELOG.md`, and update `COMPATIBILITY.md`. Close the contract-freeze loop.

**Priority.** P2 (runs last; blocks publish).

**Independent test.** `pyproject.toml` version field reads `"4.0.0"`; `from spec_kitty_events import OriginSurface, DecisionPointWidenedPayload, SummaryBlock, ...` succeeds; `CHANGELOG.md` and `COMPATIBILITY.md` diff is coherent.

**Included subtasks.**

- [ ] T025 Bump package version in `pyproject.toml` from 3.3.0 to 4.0.0 (WP07)
- [ ] T026 Extend `src/spec_kitty_events/__init__.py` to re-export V1 types (WP07)
- [ ] T027 Update `CHANGELOG.md` with 4.0.0 section (WP07)
- [ ] T028 Update `COMPATIBILITY.md` with Decision Moment V1 (4.0.0) block (WP07)

**Implementation sketch.**

1. **T025** edits `pyproject.toml` line `version = "3.3.0"` → `version = "4.0.0"`.
2. **T026** adds to `src/spec_kitty_events/__init__.py`: import and re-export `OriginSurface`, `OriginFlow`, `TerminalOutcome`, `SummarySource`, `WideningChannel`, `DiscussingSnapshotKind`, `SummaryBlock`, `TeamspaceRef`, `DefaultChannelRef`, `ThreadRef`, `ClosureMessageRef`, `WideningProjection`, `ParticipantExternalRefs`, `DecisionPointWidenedPayload`, `DecisionPointOpenedAdrPayload`, `DecisionPointOpenedInterviewPayload`, `DecisionPointDiscussingAdrPayload`, `DecisionPointDiscussingInterviewPayload`, `DecisionPointResolvedAdrPayload`, `DecisionPointResolvedInterviewPayload`, `DECISION_POINT_WIDENED`. Add them to `__all__`.
3. **T027** prepends a `## 4.0.0` section to `CHANGELOG.md` documenting: breaking change for DecisionPoint (new required `origin_surface`, new required `terminal_outcome` on Resolved interview variant, new `DecisionPointWidened` event), preserved 3.x compatibility for `DecisionInputRequested`/`DecisionInputAnswered`, migration steps for existing ADR producers (add `origin_surface="adr"`), new shared models and `external_refs` extension.
4. **T028** adds a `## Decision Moment V1 (4.0.0)` block to `COMPATIBILITY.md` restating the same compatibility posture in more formal terms, and notes the behavior rule that `DecisionInputAnswered` is only emitted when a real answer is written back.

**Parallel opportunities.** All 4 subtasks are independent files; all [P].

**Dependencies.** All other WPs (WP01–WP06).

**Risks.** `__init__.py` re-export naming collisions (double-check no existing symbol shares a name with new V1 types). `CHANGELOG.md` voice must match the repo's existing voice (see previous entries).

**Estimated prompt size.** ~250 lines.

## MVP Scope

If time forces a cut, the minimum viable contract freeze is **WP01 + WP02 + WP04 + WP07**:

- WP01: foundation shared models
- WP02: the actual DecisionPoint 4.0.0 refactor
- WP04: committed JSON Schemas
- WP07: version bump + changelog

This yields a functional 4.0.0 contract, but NFR-001/NFR-002/NFR-005 are not locked in. Recommend all seven WPs.

## Dependencies graph

```
WP01 ────┐
         ├──► WP02 ────┬──► WP03
         │             ├──► WP04 ──► WP05
         │             │         └──► WP06
         │             │
         └─────────────┴──► WP07 (waits for all)
```

## Parallelization notes

- WP01 is a foundation sequence (nothing upstream).
- WP02 is a dense sequence; cannot be parallelized internally.
- WP03, WP04 can run in parallel after WP02.
- WP05 can run in parallel with WP06 after WP02 and WP04.
- WP07 is last; runs after all others.

## Size validation

| WP   | Subtasks | Est. prompt lines | Status     |
|------|----------|-------------------|------------|
| WP01 | 4        | ~280              | ✓ ideal    |
| WP02 | 8        | ~680              | ⚠ near max (intentional — core refactor is inherently tight) |
| WP03 | 3        | ~300              | ✓ ideal    |
| WP04 | 3        | ~260              | ✓ ideal    |
| WP05 | 3        | ~340              | ✓ ideal    |
| WP06 | 3        | ~300              | ✓ ideal    |
| WP07 | 4        | ~250              | ✓ ideal    |

WP02 size is ~680 estimated lines, within the 700-line ceiling. The subtasks are tightly coupled (same file, same refactor) and splitting them would fragment the mental model of the discriminated-union change. Proceed as-is.
