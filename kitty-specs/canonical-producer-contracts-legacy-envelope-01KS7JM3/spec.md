# Feature Specification: Canonical Producer Contracts and Legacy Envelope Compatibility

**Feature Branch**: `kitty/pr/1198-canonical-producer-contracts`
**Mission ID**: `01KS7JM3HSNXGCWV2E9X3JGAEP`
**Mission Slug**: `canonical-producer-contracts-legacy-envelope-01KS7JM3`
**Created**: 2026-05-22
**Status**: Draft
**Parent issues**: Priivacy-ai/spec-kitty-events#38 (epic Priivacy-ai/spec-kitty#1198)
**Input**: Brief embedded inline by the orchestrator (Phase 1 of the producer-refactor program).

## Overview

The `spec-kitty-events` package is the canonical source of truth for the event contracts that flow from the Spec Kitty CLI to the SaaS materializer. Two structural gaps block the next two phases of the epic-#1198 program:

1. **Semantic conformance gap.** `conformance.validators.validate_event()` validates the shape of a `WPStatusChanged` payload but does not call `status.validate_transition()`. As a result, an unforced backward review-rejection transition — exactly the rc14→rc22 drift signature — passes conformance through the public downstream consumer path. The contract reads valid; the lane rule it advertises is not enforced where downstream consumers (SaaS, end-to-end harness) check it.

2. **Legacy-envelope contract gap.** The SaaS-side `_should_validate_strict_envelope()` carve-out today silently accepts malformed known events that are missing identity fields (`timestamp`, `project_uuid`, `correlation_id`). Phase 3 needs to replace that bypass with explicit, audited normalization. There is no named legacy-envelope compatibility contract in `spec-kitty-events` for Phase 3 to consume.

Separately, seven event types are emitted by the CLI today through the SaaS-bound `_emit()` central path but have no entries in `_EVENT_TYPE_TO_MODEL` and no canonical pydantic payload models:

- `WPAssigned`
- `BuildRegistered`
- `BuildHeartbeat`
- `HistoryAdded`
- `ErrorLogged`
- `DependencyResolved`
- `MissionOriginBound`

A pre-mission audit of `spec-kitty/src/specify_cli/sync/emitter.py` (lines 720–1431) confirmed all seven route through `SpecKittyEventEmitter._emit()`, which is the SaaS-bound central emit path. By the brief's classification rule, all seven are SaaS-bound and need canonical models + builders + fixtures + `_EVENT_TYPE_TO_MODEL` entries. A new `LOCAL_ONLY_EVENT_TYPES` machine-readable surface is also introduced so future ambiguous events can be classified without re-shipping a contract.

The pyargs conformance entrypoint (`conformance/test_pyargs_entrypoint.py`) is currently red on 22 fixtures; this mission fixes all three failure classes (wrapper-shape, stale `in_review` fixture, unforced-backward-transition fixtures) so the conformance suite enforces semantic validity going forward.

## Domain Language

- **Canonical event** — A payload that conforms to a published `spec_kitty_events` pydantic model and Event envelope, including identity fields (`timestamp`, `project_uuid`, `correlation_id`).
- **Legacy envelope** — An on-the-wire or on-disk event row that predates the current canonical Event envelope, missing one or more identity fields or carrying retired keys (e.g. `feature_slug`, `feature_number`). Legacy envelopes are *named* (have a known historical shape) and *deterministically normalizable* to the canonical envelope.
- **Un-normalizable legacy row** — A row that cannot be safely promoted to canonical shape because required identity is missing and not synthesizable. Surfaces as a structured diagnostic, never a silent pass.
- **Review-rejection family** — The four canonical backward transitions (`in_progress → planned`, `for_review → planned`, `in_review → planned`, `approved → planned`) that require `force=True` with a non-empty `reason`. Defined in `status.py` and already enforced by `validate_transition()`.
- **Conformance gate** — The public `validate_event()` function. Downstream consumers call this to assert a payload meets contract.
- **SaaS-bound event** — An event type emitted via `SpecKittyEventEmitter._emit()` in spec-kitty, which durably appends to the outbox and is eligible for drain to SaaS.
- **Local-only event** — An event type that is durably appended to a local log but never routed through `_emit()` and therefore never crosses the SaaS boundary. (None of the seven event types in scope are local-only as of pre-mission audit.)

## User Scenarios & Testing

### Primary scenario: SaaS consumer rejects an unforced review-rejection

**Actor**: SaaS materializer (downstream consumer).
**Trigger**: A CLI emits a `WPStatusChanged` event with `from_lane=in_review`, `to_lane=planned`, `force=false`, populated `review_ref` and `reason`. (This is the rc14→rc22 historical drift signature.)
**Pre-mission outcome**: `validate_event()` returns `valid=True` because the payload parses as `StatusTransitionPayload`. The lane-rule violation is invisible at the conformance gate.
**Post-mission outcome**: `validate_event()` returns `valid=False` with a model violation whose message contains `force=True` and `review-rejection`, exactly matching the surface that `validate_transition()` already emits. The downstream consumer's existing conformance check flags the drift at emit time, not after silent materialization.

### Secondary scenario: Phase 3 SaaS normalizes a legacy envelope

**Actor**: Phase 3 SaaS legacy adapter (downstream consumer of this mission's output).
**Trigger**: A stored event row arrives in the SaaS drain queue with a known legacy shape (e.g. a 2.x envelope using `feature_slug`/`feature_number`, missing canonical `project_uuid`).
**Outcome**: The adapter calls `spec_kitty_events.legacy.LegacyEnvelopeNormalizer.normalize(raw_event)` and receives one of two structured results:
1. `NormalizedEnvelope(canonical=..., raw=..., legacy_shape="<name>")` — the canonical event is then passed through `validate_event(..., strict=True)`. Raw input is retained for audit.
2. `UnnormalizableLegacyDiagnostic(reason=..., shape_hints=..., raw=...)` — the SaaS classifies this as a legacy/business-rule diagnostic, never as an infra-failed terminal.

The contract is named (`legacy_envelope_v1`) and frozen in this mission. Fixtures cover at least one normalization-success case and at least one un-normalizable case.

### Tertiary scenario: CLI emits one of the seven previously uncontracted events

**Actor**: Spec Kitty CLI producer (the Phase 2 refactor will consume this).
**Trigger**: The CLI calls `emit_wp_assigned()` (or any of the other six builders).
**Pre-mission outcome**: No canonical model exists. Phase 2 cannot wire the producer to a pydantic builder; the canonical-producer lint baseline remains.
**Post-mission outcome**: For each of the seven event types, a canonical pydantic payload model + `_EVENT_TYPE_TO_MODEL` entry + at least one valid fixture exists. Phase 2 can refactor the producer to construct the payload through the model. Out of scope: the actual Phase 2 producer-refactor PR. In scope: shipping the contracts so Phase 2 has something to refactor against.

### Edge cases

- **Bootstrap-planned events** (forced `*→planned` with `from_lane=None`) MUST continue to pass conformance. The existing `is_bootstrap_planned_event()` guard already handles this; the new conformance gate must not regress it.
- **Forced backward transitions with empty `reason`** MUST continue to fail. The existing `validate_transition()` rejection (`force=True requires a non-empty reason`) must surface through `validate_event()` after this mission.
- **JSON Schema layer absent (jsonschema not installed)** — `validate_event(strict=False)` must continue to fall back gracefully on the schema layer; the new semantic check is part of the model layer (pydantic-driven) and must not require jsonschema.
- **Pyargs fixture wrappers (`{class, expected, input, notes}`)** — these are taxonomy meta-fixtures, not raw envelopes. The pyargs test must extract `.input` for those, or skip them with a documented `fixture_type` opt-out.
- **Stale `wp-status-changed-invalid-lane` fixture** — the on-disk fixture treats canonical `in_review` as an invalid `to_lane`; this is wrong. Fix the fixture (or its registration) so the conformance suite reflects the current canonical lane taxonomy.

## Functional Requirements

| ID | Description | Status |
|----|-------------|--------|
| FR-001 | `conformance.validators.validate_event()` MUST invoke `status.validate_transition()` when `event_type == "WPStatusChanged"`. Violations from `validate_transition()` MUST be surfaced as `ModelViolation` entries on the returned `ConformanceResult` (so existing consumers that already inspect `model_violations` see them without API churn). | Required |
| FR-002 | Each `ModelViolation` synthesized from a `validate_transition()` violation MUST preserve the violation message verbatim, so downstream consumers can continue routing on the existing substrings `force=True` and `review-rejection`. | Required |
| FR-003 | `validate_event(payload, "WPStatusChanged")` MUST return `valid=False` for the existing fixture `edge_cases/invalid/wp_status_changed_unforced_in_review_to_planned.json` (and the parallel `unforced-for-review-to-planned`, `unforced-approved-to-planned`, `unforced-in-progress-to-planned` fixtures). | Required |
| FR-004 | `validate_event(payload, "WPStatusChanged")` MUST return `valid=True` for the existing fixture `edge_cases/valid/wp_status_changed_forced_in_review_to_planned.json` and for the canonical happy-path fixtures (`events/valid/wp_status_changed.json`, `class_taxonomy/envelope_valid_canonical/wp_status_changed_*.json`). | Required |
| FR-005 | `validate_event(payload, "WPStatusChanged")` MUST return `valid=True` for the canonical bootstrap-planned event shape (forced `to_lane=planned` with `from_lane in {None, "planned"}`). | Required |
| FR-006 | A new public surface `spec_kitty_events.legacy` MUST expose `LegacyEnvelopeNormalizer` with a stable method `normalize(raw_event: dict) -> NormalizationResult`, where `NormalizationResult` is a discriminated union of `NormalizedEnvelope` (success) and `UnnormalizableLegacyDiagnostic` (structured failure). Both result variants MUST preserve the raw input for audit. | Required |
| FR-007 | The legacy envelope contract MUST be named (`legacy_envelope_v1`) and documented in `README.md`, `CHANGELOG.md`, and an in-package docstring. The contract MUST list the legacy shapes it accepts (at minimum: pre-3.0 envelopes missing `project_uuid`, envelopes using retired `feature_slug`/`feature_number` keys). | Required |
| FR-008 | At least one normalization-success fixture MUST be added under `conformance/fixtures/legacy/` (or equivalent) showing a legacy envelope → canonical envelope mapping. The fixture MUST be registered in `conformance/fixtures/manifest.json`. | Required |
| FR-009 | At least one un-normalizable fixture MUST be added showing a legacy envelope that surfaces an `UnnormalizableLegacyDiagnostic` rather than silently passing. The fixture MUST be registered in `conformance/fixtures/manifest.json`. | Required |
| FR-010 | A canonical pydantic payload model MUST be added for each of: `WPAssigned`, `BuildRegistered`, `BuildHeartbeat`, `HistoryAdded`, `ErrorLogged`, `DependencyResolved`, `MissionOriginBound`. Each model uses `ConfigDict(frozen=True, extra="forbid")` matching the convention of `project_lifecycle.py`. | Required |
| FR-011 | Each new payload model MUST be registered in `_EVENT_TYPE_TO_MODEL` so `validate_event()` can validate it. | Required |
| FR-012 | At least one valid fixture MUST be added for each of the seven event types under `conformance/fixtures/events/valid/` and registered in the manifest. | Required |
| FR-013 | A new machine-readable surface `spec_kitty_events.LOCAL_ONLY_EVENT_TYPES: frozenset[str]` MUST be exported from the package. The set is empty in this mission (all seven audited events are SaaS-bound), but the surface is published so Phase 2 / Phase 3 can consume it and future ambiguous events can be classified without re-shipping a contract. | Required |
| FR-014 | The pyargs conformance entrypoint (`pytest --pyargs spec_kitty_events.conformance`) MUST run green. Class-taxonomy / historical-row / lane-mapping fixtures using the `{class, expected, input, notes}` wrapper shape MUST be loaded via `.input` extraction (or skipped via a documented `fixture_type` opt-out) so the validator never sees wrapper keys as extras. | Required |
| FR-015 | The stale `wp-status-changed-invalid-lane` fixture treating canonical `in_review` as invalid MUST be fixed: either remove the fixture or change its `to_lane` to a genuinely invalid value, and update notes/manifest accordingly. | Required |
| FR-016 | A `CHANGELOG.md` entry MUST be added under `[Unreleased]` describing the new conformance semantics, the legacy envelope contract, and the seven new event-type contracts. | Required |
| FR-017 | `README.md` MUST document the new `spec_kitty_events.legacy` surface and the `LOCAL_ONLY_EVENT_TYPES` surface so downstream consumers know what to import. | Required |

## Non-Functional Requirements

| ID | Description | Threshold | Status |
|----|-------------|-----------|--------|
| NFR-001 | The conformance pass-through MUST remain deterministic and side-effect-free. `validate_event()` MUST NOT mutate its input or perform I/O. | 0 mutations, 0 file/network operations per call. | Required |
| NFR-002 | The full pyargs conformance suite MUST complete in ≤ 10 seconds on a developer laptop with cold caches. Baseline pre-mission is ~2.1 seconds for 323 cases; new fixtures add ≤ 30 cases. | ≤ 10 s wall clock for `uv run pytest --pyargs spec_kitty_events.conformance -q`. | Required |
| NFR-003 | The new `LegacyEnvelopeNormalizer.normalize()` API MUST be deterministic: same input dict always yields the same `NormalizationResult` regardless of process state. | 100% deterministic across repeated calls on the same input. | Required |
| NFR-004 | No new pip dependencies MUST be added to `pyproject.toml`. The mission ships purely as additive contracts using existing pydantic + jsonschema (optional) infrastructure. | 0 new entries in `[project] dependencies` or `[project.optional-dependencies]`. | Required |
| NFR-005 | All existing tests MUST stay green: `tests/unit/test_status.py`, `tests/unit/test_fixtures.py`, `tests/integration/test_schema_drift.py`, `tests/test_fixture_determinism.py`. | 100% pass. | Required |

## Constraints

| ID | Description | Status |
|----|-------------|--------|
| C-001 | Do NOT publish to PyPI in this mission. Phase 5 (orchestrator-owned cross-repo integration) coordinates the version bump and publish. | Required |
| C-002 | Do NOT modify code in other repos (`spec-kitty`, `spec-kitty-saas`, `spec-kitty-end-to-end-testing`). The classification of the seven event types is based on a pre-mission read of those repos; the mission's diff stays inside `spec-kitty-events`. | Required |
| C-003 | Do NOT loosen the review-rejection family rules. Forced backward transitions still require `force=True` AND a non-empty `reason`. | Required |
| C-004 | All event examples in fixtures MUST be canonical-shaped. Construct fixture payloads from the published pydantic models where possible (round-trip `.model_dump(mode="json")`). | Required |
| C-005 | Do NOT mutate any SaaS DB, queue, or readiness counters to make any test pass. The mission is purely contract-side. | Required |
| C-006 | Do NOT modify ingress limits or any SaaS-side authentication boundary. | Required |
| C-007 | The legacy envelope contract is *named and frozen* in this mission. The contract name (`legacy_envelope_v1`) MUST be referenced by Phase 3 SaaS adapter PR; do not rename without a coordinated cross-repo cutover. | Required |
| C-008 | The `LOCAL_ONLY_EVENT_TYPES` surface MUST be an immutable `frozenset[str]`. The empty value in this mission is intentional. | Required |

## Success Criteria

1. The four `wp-status-changed-unforced-*-to-planned-invalid` fixtures fail `validate_event()` exactly the same way `validate_transition()` already fails them, with the violation messages containing both `force=True` and `review-rejection`.
2. The `pytest --pyargs spec_kitty_events.conformance` command exits with code 0; no fixture is skipped without a documented `fixture_type` opt-out.
3. A downstream consumer (Phase 3 SaaS) can import `from spec_kitty_events.legacy import LegacyEnvelopeNormalizer` and exercise the contract against at least one legacy and one un-normalizable fixture without writing any new normalization logic of its own.
4. A downstream consumer (Phase 2 CLI) can import canonical builders/models for all seven previously-uncontracted event types and construct payloads that pass `validate_event(strict=True)` (when jsonschema is available) or `validate_event(strict=False)` (when it is not).
5. The mission ships zero changes to other repos in this workspace.
6. The CHANGELOG entry under `[Unreleased]` is reviewable as the source of truth for what changed in this release-candidate window.

## Key Entities

- **`ConformanceResult`** (existing) — Result type returned by `validate_event()`. Gains `model_violations` entries synthesized from `validate_transition()` failures; structure unchanged.
- **`StatusTransitionPayload`** (existing) — The pydantic model already provides `force=True requires non-empty reason` via `model_validator(mode="after")`. This mission does not modify it. The new behavior calls `validate_transition()` on a successfully-parsed instance.
- **`LegacyEnvelopeNormalizer`** (new) — A class with one public method, `normalize(raw_event: dict) -> NormalizationResult`. Stateless. Implements the named `legacy_envelope_v1` contract.
- **`NormalizationResult`** (new) — Discriminated union of `NormalizedEnvelope` (success) and `UnnormalizableLegacyDiagnostic` (failure). Both variants retain `raw` for audit.
- **`NormalizedEnvelope`** (new) — Wraps a canonical `Event` plus the original raw input and a `legacy_shape` identifier.
- **`UnnormalizableLegacyDiagnostic`** (new) — Structured diagnostic carrying `reason: str`, `shape_hints: list[str]`, and the original raw input.
- **`LOCAL_ONLY_EVENT_TYPES`** (new) — `frozenset[str]` exported from the package root. Empty in this mission.
- **`WPAssignedPayload`**, **`BuildRegisteredPayload`**, **`BuildHeartbeatPayload`**, **`HistoryAddedPayload`**, **`ErrorLoggedPayload`**, **`DependencyResolvedPayload`**, **`MissionOriginBoundPayload`** (new) — Canonical pydantic models for the seven previously-uncontracted SaaS-bound events.

## Assumptions

- The pre-mission audit of `spec-kitty/src/specify_cli/sync/emitter.py` (lines 720–1431) is current. All seven event types route through `_emit()` as of `spec-kitty` at commit `43305c12c`. If a future change moves any of them off `_emit()`, the affected event type's classification needs to be re-evaluated against `LOCAL_ONLY_EVENT_TYPES`; that re-evaluation is out of scope for this mission.
- The legacy envelope shapes documented in `class_taxonomy/envelope_valid_historical_synthesized/*` (pre-3.0 envelopes, envelopes with retired `feature_slug`/`feature_number` keys, envelopes using `awaiting-review` legacy synonym) are an authoritative starting set for the `legacy_envelope_v1` contract.
- The pyargs entrypoint failures are stable across `uv` and `pip` resolvers — the failures are purely fixture-shape and semantic-validation gaps, not environment-dependent.
- The existing `_EVENT_TYPE_TO_MODEL` registration pattern is the canonical way to plug new event types into `validate_event()`. No alternative dispatch mechanism is needed.
- The package's existing test infrastructure (`pytest`, `hypothesis`, schema drift checks, fixture determinism) is sufficient to validate this mission's deliverables; no new test infrastructure is required.

## Out of Scope

- The CLI producer refactor that consumes these contracts (Phase 2 of epic #1198, tracked in spec-kitty repo).
- The SaaS legacy-envelope adapter that consumes `LegacyEnvelopeNormalizer` (Phase 3, tracked in spec-kitty-saas repo).
- The deployed-dev canary that verifies end-to-end legacy normalization (Phase 4, tracked in spec-kitty-end-to-end-testing repo).
- The version bump and PyPI publish (Phase 5, orchestrator-owned).
- Closing parent issues (#1198, #38, #1200, #1203, etc.). Evidence-only comments on issues happen later; closures wait for the full cross-repo program to land.
- Adding new transition rules to `status.py`. The existing `validate_transition()` already covers the required cases; this mission only routes its output through the public conformance gate.

## Dependencies

- Existing `spec_kitty_events.status.validate_transition()` (read-only consumer; no changes required to its API).
- Existing `spec_kitty_events.conformance.validators._EVENT_TYPE_TO_MODEL` (extended, not restructured).
- Existing `spec_kitty_events.cutover.assert_canonical_cutover_signal()` (no changes).
- Existing fixture loader pipeline (`conformance.loader`, `conformance.pytest_helpers`).
- pydantic 2.x, python-ulid (already in `[project.dependencies]`; no new pins).

## Acceptance Verification Commands

```bash
cd /Users/robert/spec-kitty-dev/spec-kitty-20260522-114105-jmsHua/spec-kitty-events
uv run pytest tests/unit/test_status.py tests/unit/test_fixtures.py -q
uv run pytest --pyargs spec_kitty_events.conformance -q
uv run pytest tests/integration/test_schema_drift.py tests/test_fixture_determinism.py -q
```

All three commands MUST exit 0 before the mission is closed.
