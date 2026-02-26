# Implementation Plan: Mission Audit Lifecycle Contracts

**Branch**: `010-mission-audit-lifecycle-contracts` | **Date**: 2026-02-25 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/kitty-specs/010-mission-audit-lifecycle-contracts/spec.md`

## Summary

Add five canonical mission-audit lifecycle event contracts (`MissionAuditRequested`, `Started`, `DecisionRequested`, `Completed`, `Failed`) with a deterministic reducer, conformance fixtures, and full public API export. Targets `spec-kitty-events` 2.5.0 as a purely additive minor release — zero breaking changes to 2.x consumers.

## Technical Context

**Language/Version**: Python ≥3.10, mypy strict target 3.10, tests run on 3.11
**Primary Dependencies**: pydantic ≥2.0.0 (frozen models), python-ulid (event IDs), hypothesis (property tests)
**Optional**: jsonschema ≥4.21.0 (conformance `[conformance]` extra)
**Storage**: N/A — pure event contract library, no database
**Testing**: pytest + pytest-cov (98% baseline) + hypothesis (determinism) + mypy --strict
**Target Platform**: PyPI package consumed by spec-kitty CLI and spec-kitty-saas
**Project Type**: Single Python package (`src/spec_kitty_events/`)
**Constraints**: Additive-only (2.5.0 minor bump), no 1.x work, no breaking changes

## Constitution Check

- Single package, single language — within bounds.
- No new external dependencies — reuses existing pydantic, hypothesis stack.
- Follows established event-family pattern (lifecycle → status → collaboration → glossary → mission_next → dossier → **mission_audit**).

## Project Structure

### Documentation (this feature)

```
kitty-specs/010-mission-audit-lifecycle-contracts/
├── plan.md              # This file
├── spec.md              # Feature requirements and acceptance scenarios
├── research.md          # 10 design decisions (R-001 through R-010)
├── data-model.md        # Enum, value object, payload, reducer field definitions
├── quickstart.md        # Usage examples for emit, reduce, validate
├── contracts/
│   ├── mission_audit_events.py       # Type signatures (design artifact)
│   └── conformance_registration.py   # Conformance integration spec
├── checklists/
│   └── requirements.md               # Spec quality checklist
└── tasks/
    └── README.md                      # WP file format reference
```

### Source Code (repository root)

```
src/spec_kitty_events/
├── mission_audit.py                   # NEW: enums, payloads, reducer, value objects
├── __init__.py                        # MODIFIED: +23 exports (→ ~111 total)
├── conformance/
│   ├── validators.py                  # MODIFIED: 5 new _EVENT_TYPE_TO_MODEL entries
│   ├── loader.py                      # MODIFIED: add "mission_audit" category
│   └── fixtures/mission_audit/
│       ├── valid/    (7 JSON files)
│       ├── invalid/  (4 JSON files)
│       └── replay/   (3 JSONL + 3 golden JSON)
├── schemas/                           # MODIFIED: 5 new JSON schema files
└── dossier.py                         # UNMODIFIED: provides ContentHashRef, ProvenanceRef

tests/
├── unit/
│   └── test_mission_audit.py          # NEW: payload validation, round-trip, edge cases
├── property/
│   └── test_mission_audit_determinism.py  # NEW: Hypothesis reducer determinism
├── test_mission_audit_reducer.py      # NEW: golden-file replay, state machine, anomalies
└── test_mission_audit_conformance.py  # NEW: valid/invalid fixture validation
```

## Implementation Phases

### Phase 1: Core Types (enums + value objects + payloads)
- `AuditVerdict`, `AuditSeverity`, `AuditStatus` enums
- `AuditArtifactRef` composing `ContentHashRef` + `ProvenanceRef` from dossier.py
- `PendingDecision` value object for reducer state
- `MissionAuditAnomaly` following established anomaly pattern
- 5 frozen payload models with Pydantic Field constraints
- Constants: 5 event types + `MISSION_AUDIT_EVENT_TYPES` frozenset + `TERMINAL_AUDIT_STATUSES` + `AUDIT_SCHEMA_VERSION`

### Phase 2: Reducer
- `reduce_mission_audit_events()` pure function
- Pipeline: sort (`status_event_sort_key`) → dedup (`dedup_events`) → filter → fold → freeze
- State machine: pending → running → {awaiting_decision, completed, failed}
- Anomaly detection: event_before_requested, event_after_terminal, duplicate_decision_id, unrecognized_event_type
- `pending_decisions: Tuple[PendingDecision, ...]` cleared on terminal event
- `ReducedMissionAuditState` frozen output

### Phase 3: Conformance Integration
- 5 JSON schemas generated via `TypeAdapter(...).json_schema()`
- validators.py: 5 `_EVENT_TYPE_TO_MODEL` entries + 5 `_EVENT_TYPE_TO_SCHEMA` entries
- loader.py: `"mission_audit"` added to `_VALID_CATEGORIES`
- Fixtures: 7 valid + 4 invalid + 3 replay JSONL + 3 golden-file snapshots
- Manifest entries (17 total, all `min_version: "2.5.0"`)

### Phase 4: Public API + Version Bump
- ~23 exports added to `__init__.py`
- pyproject.toml version: 2.4.0 → 2.5.0
- `__version__` in `__init__.py`: 2.4.0 → 2.5.0
- Package-data globs for `conformance/fixtures/mission_audit/`

## Test Strategy

### Unit Tests (`tests/unit/test_mission_audit.py`)

| Category | Count | Description |
|---|---|---|
| Payload round-trip | 5 | `model_validate(model.model_dump(mode="json"))` per payload |
| Required field rejection | 5+ | Missing required fields → `ValidationError` (no fallback) |
| Literal constraint rejection | 2 | Bad `trigger_mode`, bad `enforcement_mode` |
| Field constraint rejection | 2 | Negative `findings_count`, empty `mission_id` |
| Enum validation | 3 | Invalid enum values for verdict, severity, status |
| AuditArtifactRef composition | 1 | ContentHashRef + ProvenanceRef round-trip |
| Frozen immutability | 5 | Assignment to frozen model raises TypeError |
| PendingDecision construction | 1 | Valid construction and frozen immutability |

### Reducer Tests (`tests/test_mission_audit_reducer.py`)

| Category | Count | Description |
|---|---|---|
| Happy-path pass | 1 | Requested→Started→Completed(pass) → golden snapshot |
| Happy-path fail | 1 | Requested→Started→Failed → golden snapshot |
| Decision checkpoint | 1 | Requested→Started→DecisionRequested→Completed → pending_decisions lifecycle |
| Empty stream | 1 | No events → default ReducedMissionAuditState |
| Deduplication | 1 | Duplicate events → identical to deduped stream |
| Anomaly: before_requested | 1 | Started before Requested → anomaly recorded |
| Anomaly: after_terminal | 1 | Event after Completed/Failed → anomaly recorded |
| Anomaly: duplicate_decision_id | 1 | Same decision_id twice → anomaly + dedup |
| Anomaly: unrecognized_type | 1 | Unknown event_type in audit family → anomaly |
| Terminal clears pending | 1 | Completed/Failed clears pending_decisions |
| Partial artifact on failure | 1 | Failed with partial_artifact_ref preserved |
| Golden-file replay (3 streams) | 3 | JSONL replay → output matches committed snapshot |

### Property Tests (`tests/property/test_mission_audit_determinism.py`)

| Test | Examples | Property |
|---|---|---|
| Order independence | ≥200 | Any permutation of valid events → identical ReducedMissionAuditState |
| Idempotent dedup | ≥200 | Doubling every event → same result as single copy |
| Monotonic event_count | ≥200 | event_count ≤ len(input) after dedup |

### Conformance Tests (`tests/test_mission_audit_conformance.py`)

| Category | Count | Description |
|---|---|---|
| Valid fixture validation | 7 | Each valid fixture → `ConformanceResult(valid=True)` |
| Invalid fixture rejection | 4 | Each invalid fixture → `ConformanceResult(valid=False)` with field-level violations |
| Replay stream validation | 3 | Each JSONL line validates + reducer output matches golden file |
| Schema drift check | 5 | Generated schema matches committed schema file |

### Quality Gates (CI)

1. `pytest tests/ -v` — all pass, ≥98% coverage
2. `mypy --strict src/spec_kitty_events/mission_audit.py` — zero errors
3. `mypy --strict src/spec_kitty_events/__init__.py` — zero errors (after export additions)
4. `pytest --pyargs spec_kitty_events.conformance` — all mission_audit fixtures pass
5. Existing test suite: zero regressions (collaboration, glossary, dossier, mission_next reducers unaffected)

## Locked Decisions

- **2.x only**: No 1.x compatibility work or fallbacks.
- **artifact_ref required**: `MissionAuditCompletedPayload.artifact_ref` is `AuditArtifactRef` (not Optional). If artifact generation fails, emitter MUST emit `MissionAuditFailed` instead.
- **No answered_decisions**: Audit reducer tracks `pending_decisions` only. Decision resolution is implicit on terminal event. Explicit answer tracking is 3.x scope.
- **SC-007/SC-008 de-overlapped**: SC-007 (version pin) covers installability + import + API availability. SC-008 (export completeness) covers `__init__.py` export surface. No overlap.
- **Composition not duplication**: `AuditArtifactRef` imports `ContentHashRef`/`ProvenanceRef` from `dossier.py` (FR-020).

## Risks

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Dossier value object API change before release | Low | High | Feature 009 declared stable; pin import test |
| Conformance manifest format drift | Low | Medium | Schema drift CI check (SC-005) |
| Reducer golden-file brittleness on field ordering | Medium | Low | Use `model_dump(mode="json")` with sorted keys |
| PendingDecision tuple growth in long-running audits | Low | Low | Cleared on terminal; no unbounded accumulation |
