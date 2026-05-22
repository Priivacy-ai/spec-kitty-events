# Implementation Plan: Canonical Producer Contracts and Legacy Envelope Compatibility

**Branch**: `kitty/pr/1198-canonical-producer-contracts` | **Date**: 2026-05-22 | **Spec**: [spec.md](./spec.md)
**Mission ID**: `01KS7JM3HSNXGCWV2E9X3JGAEP`
**Mission Slug**: `canonical-producer-contracts-legacy-envelope-01KS7JM3`
**Input**: Brief embedded inline by the orchestrator (Phase 1 of epic Priivacy-ai/spec-kitty#1198 program).
**Parent issue**: Priivacy-ai/spec-kitty-events#38.

## Summary

Three additive contract surfaces ship in this mission:

1. **Semantic validation pass-through** in `conformance.validators.validate_event()` so the existing `status.validate_transition()` rule fires when downstream consumers call the public conformance gate.
2. **Named legacy-envelope normalization contract** (`legacy_envelope_v1`) exposed as `spec_kitty_events.legacy.LegacyEnvelopeNormalizer`, with normalization-success and un-normalizable fixtures.
3. **Canonical pydantic payload models** for the seven previously-uncontracted SaaS-bound event types emitted by spec-kitty (`WPAssigned`, `BuildRegistered`, `BuildHeartbeat`, `HistoryAdded`, `ErrorLogged`, `DependencyResolved`, `MissionOriginBound`), plus a `LOCAL_ONLY_EVENT_TYPES` machine-readable surface (empty in this mission; the seven audited events all route through `_emit()` and are SaaS-bound).

The mission also fixes the currently-red pyargs conformance entrypoint by teaching the test to extract `.input` from class_taxonomy/historical_row/lane_mapping wrapper fixtures, and corrects the stale `wp-status-changed-invalid-lane` fixture that still treats canonical `in_review` as invalid.

## Technical Context

**Language/Version**: Python 3.10+ (matches `pyproject.toml` `requires-python = ">=3.10"`).
**Primary Dependencies**: `pydantic >=2.0.0,<3.0.0`, `python-ulid >=1.1.0` (existing; no new pins). Optional `jsonschema >=4.21.0,<5.0.0` for the dual-layer schema validation already present.
**Storage**: None at runtime. Conformance fixtures are committed JSON files under `src/spec_kitty_events/conformance/fixtures/`.
**Testing**: `pytest` with `hypothesis` and `pytest-cov` (existing dev extras). Schema-drift integration tests and conformance fixture determinism tests are required to keep passing.
**Target Platform**: Python library shipped to PyPI; runtime is any Linux/macOS/Windows host with Python 3.10+.
**Project Type**: single (library package — no client/server split).
**Performance Goals**: `validate_event()` is hot in CLI emit paths and SaaS drain validation. Stay deterministic and side-effect-free. Full conformance suite < 10s wall clock (baseline ~2.1s for 323 cases).
**Constraints**: No new pip dependencies; no PyPI publish in this mission; no changes outside `spec-kitty-events`; preserve all existing public surfaces; new surfaces are additive only.
**Scale/Scope**: ~30 new fixtures, ~150 LOC of new pydantic models, ~200 LOC of new normalizer, ~150 LOC of new tests, ~30 LOC of validator changes. Targeted, additive change set.

## Charter Check

Project charter (`.kittify/charter/charter.md`) intent: "Publish canonical event envelopes, conformance fixtures, and compatibility rules consumed by Spec Kitty systems."

Doctrine gates this mission must honor:

| Gate | Charter source | This plan satisfies it because |
|------|----------------|--------------------------------|
| Pydantic event models with frozen/extra=forbid | Project charter quality gates | All seven new payload models use `ConfigDict(frozen=True, extra="forbid")`. |
| Committed JSON schemas | Project charter quality gates | Existing schemas unchanged. New event types intentionally do NOT add JSON Schemas in this mission (schema_name=None gracefully skips the schema layer); a follow-up can generate schemas without breaking compat. |
| Conformance fixture coverage for any event contract change | Project charter testing | Every new event-type contract ships with at least one valid fixture in `events/valid/`. Legacy normalizer ships with both success and un-normalizable fixtures. |
| pytest + mypy --strict pass before merge | Project charter quality gates | All existing tests stay green; new tests run under the same `pytest` invocation. mypy strictness is preserved by using existing pydantic typing idioms. |
| Compatibility review on envelope/payload/schema-version change | Project charter review policy | This mission does NOT change the `Event` envelope, existing payload field shapes, or `schema_version`. All additions are new surfaces; the `legacy_envelope_v1` contract is explicitly named and version-suffixed. |
| DIRECTIVE_003 (Decision Documentation) | Action doctrine | This `plan.md`, `spec.md`, and the CHANGELOG entry capture the why of each contract choice. |
| DIRECTIVE_010 (Specification Fidelity) | Action doctrine | Implementation will follow the file surface table below verbatim; mission-review will verify spec→code fidelity. |
| DIR-001 project (no silent compatibility aliases) | Project doctrine | The legacy normalizer is named and explicit; it does NOT silently alias canonical fields. Un-normalizable rows surface as structured diagnostics, never silent passes. |
| DIR-002 project (docs synchronized) | Project doctrine | `README.md` and `CHANGELOG.md` are in the in-scope artifacts list. |

**Verdict**: Charter check passes by construction. No charter exceptions required.

## Project Structure

### Documentation (this feature)

```
kitty-specs/canonical-producer-contracts-legacy-envelope-01KS7JM3/
├── plan.md              # This file
├── spec.md              # Functional/non-functional requirements
├── research.md          # Phase 0 output (this mission: pre-audit captured below)
├── data-model.md        # Phase 1 output (new payload models + normalizer types)
├── contracts/           # Phase 1 output (legacy_envelope_v1 contract docs)
├── quickstart.md        # Phase 1 output (consumer-facing usage examples)
└── tasks.md             # Phase 2 output (/spec-kitty.tasks)
```

### Source Code (repository root)

```
src/spec_kitty_events/
├── conformance/
│   ├── validators.py                    # MODIFY: add _SEMANTIC_VALIDATORS dispatch + 7 new _EVENT_TYPE_TO_MODEL entries
│   ├── test_pyargs_entrypoint.py        # MODIFY: detect class_taxonomy wrapper, extract .input
│   └── fixtures/
│       ├── manifest.json                # MODIFY: register new fixtures, fix stale notes
│       ├── events/valid/
│       │   ├── wp_assigned.json         # NEW (canonical fixture from model.model_dump(mode='json'))
│       │   ├── build_registered.json    # NEW
│       │   ├── build_heartbeat.json     # NEW
│       │   ├── history_added.json       # NEW
│       │   ├── error_logged.json        # NEW
│       │   ├── dependency_resolved.json # NEW
│       │   └── mission_origin_bound.json# NEW
│       ├── events/invalid/
│       │   └── wp_status_changed_invalid_lane.json  # MODIFY: replace stale "in_review" with real typo
│       └── legacy/
│           ├── pre_3_0_envelope_normalizes.json     # NEW (success case)
│           └── unrecognized_legacy_diagnostic.json  # NEW (un-normalizable)
├── legacy.py                            # NEW: LegacyEnvelopeNormalizer, contract constants
├── build_lifecycle.py                   # NEW: BuildRegisteredPayload, BuildHeartbeatPayload
├── project_lifecycle.py                 # MODIFY: add WPAssignedPayload, HistoryAddedPayload, ErrorLoggedPayload, DependencyResolvedPayload
├── lifecycle.py                         # MODIFY: add MissionOriginBoundPayload
└── __init__.py                          # MODIFY: export new surfaces (legacy, LOCAL_ONLY_EVENT_TYPES, 7 payload models)

tests/
├── unit/
│   ├── test_conformance_semantic.py     # NEW: validate_event ↔ validate_transition tests
│   ├── test_legacy_normalizer.py        # NEW: LegacyEnvelopeNormalizer tests
│   └── test_seven_event_contracts.py    # NEW: 7 new contracts + LOCAL_ONLY_EVENT_TYPES tests
└── (existing tests unchanged)

CHANGELOG.md                             # MODIFY: add [Unreleased] entry
README.md                                # MODIFY: document spec_kitty_events.legacy + LOCAL_ONLY_EVENT_TYPES
```

## Engineering Alignment

**Architecture seam #1: Validators dispatch**

- Add `_SEMANTIC_VALIDATORS: Dict[str, Callable[[BaseModel, dict], Tuple[ModelViolation, ...]]]` in `conformance/validators.py`.
- Register `"WPStatusChanged"` → `_semantic_validate_wp_status_changed`.
- The semantic validator: parses the dict into `StatusTransitionPayload.model_validate(model_payload)` (safe because we only run this when shape validation already passed), calls `validate_transition(model)`, wraps each violation string in a `ModelViolation(field="transition", violation_type="transition_rule", message=<verbatim>, input_value=model_payload)`.
- `validate_event()` calls the semantic validator only if (a) `event_type in _SEMANTIC_VALIDATORS` and (b) the prior `_validate_with_model` call returned no model violations (the pydantic model parsed cleanly). The semantic violations are concatenated onto `model_violations` and `valid` is recomputed.
- This isolates the future addition of semantic validators (e.g. for state transitions on other aggregates) behind a one-line registry entry.

**Architecture seam #2: Legacy normalizer**

- New module `src/spec_kitty_events/legacy.py`. Stateless single-method API. Detector list is ordered; first match wins.
- Detectors (initial):
  - **`pre_3_0_envelope`** — top-level dict with `event_type` and `payload`, missing `project_uuid`. Mints `project_uuid` from `uuid.uuid5(NAMESPACE_URL, f"spec-kitty-events/legacy/{node_id}/{build_id}")` when both fields are present. Otherwise emits `UnnormalizableLegacyDiagnostic(reason="pre_3_0_envelope_missing_identity", shape_hints=["missing project_uuid", "missing node_id" or "missing build_id"])`.
  - **`feature_keys_envelope`** — top-level dict with retired `feature_slug` / `feature_number`. Maps `feature_slug → mission_slug`, `feature_number → mission_number`, strips legacy keys, recurses if `payload` dict also has them.
  - **`awaiting_review_synonym`** — `payload.to_lane == "awaiting-review"` → canonical `payload.to_lane = "in_review"`.
  - **Fallthrough** — none of the above match AND canonical shape doesn't parse → `UnnormalizableLegacyDiagnostic(reason="unrecognized_legacy_shape", shape_hints=[<observed top-level keys>])`.
- Public surface: `LegacyEnvelopeNormalizer`, `NormalizedEnvelope`, `UnnormalizableLegacyDiagnostic`, `NormalizationResult` (Union), `LEGACY_ENVELOPE_CONTRACT_NAME = "legacy_envelope_v1"`, `RECOGNIZED_LEGACY_SHAPES = frozenset({"pre_3_0_envelope", "feature_keys_envelope", "awaiting_review_synonym"})`.
- Both result variants preserve `raw: dict` for audit. Pydantic models with `frozen=True, extra="forbid"`.

**Architecture seam #3: Seven event contracts**

- All seven SaaS-bound (audited against `spec-kitty/src/specify_cli/sync/emitter.py` at lines 720–1431; commit `43305c12c`).
- Models placed by aggregate type:
  - `build_lifecycle.py` (NEW) — `BuildRegisteredPayload`, `BuildHeartbeatPayload` (aggregate_type="Build").
  - `project_lifecycle.py` (extend) — `WPAssignedPayload`, `HistoryAddedPayload`, `ErrorLoggedPayload`, `DependencyResolvedPayload` (aggregate_type="WorkPackage" or "Mission" for ErrorLogged).
  - `lifecycle.py` (extend) — `MissionOriginBoundPayload` (aggregate_type="Mission", co-located with MissionCreated).
- Each payload model uses `ConfigDict(frozen=True, extra="forbid")` matching `_ArtifactPhasePayloadBase` and `MissionCreatedPayload` conventions.
- Field shapes derived from the emitter audit (captured in `research.md`).
- All seven registered in `_EVENT_TYPE_TO_MODEL` in `conformance/validators.py`. No `_EVENT_TYPE_TO_SCHEMA` entries (schema_name=None triggers graceful skip).

**Test strategy**

- Unit tests in `tests/unit/`:
  - `test_conformance_semantic.py`: 8 test functions covering the four unforced backward fixtures, the forced valid fixture, bootstrap-planned acceptance, force-with-empty-reason regression, and substring routing on violation messages.
  - `test_legacy_normalizer.py`: 6 test functions covering each detector branch + raw-input preservation invariants.
  - `test_seven_event_contracts.py`: 14 test functions (round-trip + registry per type) + 2 tests for `LOCAL_ONLY_EVENT_TYPES` properties.
- Fixtures registered in manifest with `min_version: "5.2.0"` (next-Unreleased; orchestrator owns the actual version bump).
- All existing tests stay green: `tests/unit/test_status.py`, `tests/unit/test_fixtures.py`, `tests/integration/test_schema_drift.py`, `tests/test_fixture_determinism.py`.
- Pyargs entrypoint green: `pytest --pyargs spec_kitty_events.conformance -q`.

## Phase 0: Outline & Research

The mission ships with a complete pre-audit (see `spec.md` "Assumptions" and the file surface table). Research is captured in `research.md`. Three research items:

### Research item R1: Field shapes for the seven uncontracted event types

**Decision**: Use the field shapes assembled in `spec-kitty/src/specify_cli/sync/emitter.py` (commit `43305c12c`, lines 720–1431). Field-by-field table:

| Event type | Source emit function | Required fields | Optional fields |
|------------|---------------------|-----------------|-----------------|
| `WPAssigned` | `emit_wp_assigned` (line 879) | `wp_id`, `agent_id`, `phase`, `retry_count` (defaults 0) | — |
| `BuildRegistered` | `emit_build_registered` (line 722) | (none; envelope-derivable identity) | `repo_slug`, `git_branch`, `head_commit_sha` |
| `BuildHeartbeat` | `emit_build_heartbeat` (line 738) | (none) | `remote_head`, `ahead_of_remote`, `behind_remote`, `recent_commits`, `repo_slug`, `git_branch`, `head_commit_sha` |
| `HistoryAdded` | `emit_history_added` (line 1320) | `wp_id`, `entry_type`, `entry_content`, `author` | — |
| `ErrorLogged` | `emit_error_logged` (line 1339) | `error_type`, `error_message` | `wp_id`, `stack_trace`, `agent_id` |
| `DependencyResolved` | `emit_dependency_resolved` (line 1370) | `wp_id`, `dependency_wp_id`, `resolution_type` | — |
| `MissionOriginBound` | `emit_mission_origin_bound` (line 1391) | `mission_slug`, `provider`, `external_issue_id`, `external_issue_key`, `external_issue_url`, `title` | `mission_id` |

**Rationale**: The CLI is the authoritative producer. Phase 2's job is to refactor those producers to construct via models; the model field shapes must match what the producers actually assemble today, or the refactor fails the new `_EVENT_TYPE_TO_MODEL` lookup.

**Alternatives considered**: (a) Mint richer "future-facing" shapes — rejected because Phase 2 hasn't happened yet and the producers would need to be updated in lockstep. (b) Use schema generation to derive shapes — rejected because no JSON Schemas exist for these types yet.

### Research item R2: Legacy envelope shapes to cover in `legacy_envelope_v1`

**Decision**: Three named shapes in v1:
- `pre_3_0_envelope` — pre-3.0 envelopes missing `project_uuid`.
- `feature_keys_envelope` — envelopes using retired `feature_slug`/`feature_number` at top level or in payload.
- `awaiting_review_synonym` — payloads using the `awaiting-review` legacy synonym for canonical `in_review`.

**Rationale**: These three shapes are already documented in the existing `class_taxonomy/envelope_valid_historical_synthesized/` fixtures. The Phase 3 SaaS adapter consumes them. Any additional shapes can be added under `legacy_envelope_v2` later without breaking v1 consumers.

**Alternatives considered**: A bigger initial shape catalog — rejected to keep v1 small and auditable. A discriminated tagged union for `NormalizationResult` — rejected because the isinstance pattern is simpler and Python ≥3.10 supports structural pattern matching natively.

### Research item R3: Semantic validator dispatch shape

**Decision**: A module-level `_SEMANTIC_VALIDATORS: Dict[str, Callable[..., Tuple[ModelViolation, ...]]]` keyed by `event_type`. Each callable takes the parsed pydantic model and the raw payload dict; returns a tuple of `ModelViolation`s.

**Rationale**: Mirrors the existing `_EVENT_TYPE_TO_MODEL` and `_EVENT_TYPE_TO_SCHEMA` registry pattern in the same file. Keeps the change additive and discoverable.

**Alternatives considered**: A pydantic `@model_validator(mode="after")` directly on `StatusTransitionPayload` — rejected because `validate_transition()` is intentionally a separate function so callers can decide whether to enforce business rules vs shape rules. Adding the call inside the model would couple the two and break tests that construct payloads to test transitions in isolation.

## Phase 1: Design & Contracts

### data-model.md

The data model artifact captures the public types this mission ships. See `data-model.md` for the per-type field tables. Highlights:

- **NormalizedEnvelope** — `canonical: dict`, `raw: dict`, `legacy_shape: Literal["pre_3_0_envelope","feature_keys_envelope","awaiting_review_synonym"]`.
- **UnnormalizableLegacyDiagnostic** — `reason: str`, `shape_hints: list[str]`, `raw: dict`.
- **NormalizationResult** — `Union[NormalizedEnvelope, UnnormalizableLegacyDiagnostic]`.
- **Seven payload models** — see Research item R1 table.

### contracts/

The contract artifact captures the `legacy_envelope_v1` named contract: the three recognized shapes, the canonical-output guarantee, the audit-preservation guarantee, and the un-normalizable diagnostic surface. See `contracts/legacy-envelope-v1.md`.

### quickstart.md

The quickstart artifact gives Phase 3 SaaS adapter authors a one-page recipe. See `quickstart.md`.

### Charter re-check (post-design)

All gates from the initial Charter Check above still hold:

- No envelope / payload-field-shape / schema-version change.
- No new pip dependencies.
- Fixtures committed; deterministic.
- README + CHANGELOG updated.
- DIR-001 (no silent aliases): the normalizer is named and explicit; un-normalizable rows surface, never silently pass.

**Verdict**: Charter post-design re-check passes.

## Branch contract recap (final)

- Current branch at workflow start: `kitty/pr/1198-canonical-producer-contracts`
- Planning/base branch: `kitty/pr/1198-canonical-producer-contracts` (mission branch — PRs merge from here into `main`)
- Final merge target: `main` (per orchestrator PR contract for epic #1198)
- `branch_matches_target`: true (working on the mission branch, as expected)

## Next command

`/spec-kitty.tasks` — generate the WP decomposition. The WP shape is sketched in the orchestrator brief (WP01: semantic dispatch; WP02: seven contracts + LOCAL_ONLY; WP03: legacy normalizer; WP04: pyargs entrypoint + stale fixture; WP05: docs/CHANGELOG).
