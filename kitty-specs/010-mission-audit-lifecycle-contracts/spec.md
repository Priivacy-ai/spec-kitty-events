# Feature Specification: Mission Audit Lifecycle Contracts

**Feature Branch**: `010-mission-audit-lifecycle-contracts`
**Created**: 2026-02-25
**Status**: Draft
**Input**: Team prompt — canonical mission-audit lifecycle event contracts for post-merge audit in Spec Kitty 2.x

## User Scenarios & Testing

### User Story 1 — Emit Audit Lifecycle Events (Priority: P1)

As an event consumer (reducer, SaaS projection, dashboard), I receive a canonical sequence of mission-audit lifecycle events so that I can deterministically materialize audit state for any mission run.

**Why this priority**: Without the event types and payload contracts, no downstream consumer can build audit projections. This is the foundational contract that everything else depends on.

**Independent Test**: Instantiate each of the five payload models with valid data, serialize to JSON, and round-trip back through Pydantic validation. Each payload must survive `model_validate(model.model_dump(mode="json"))` without data loss.

**Acceptance Scenarios**:

1. **Given** a post-merge audit trigger, **When** the emitter produces events for a normal pass lifecycle (Requested → Started → Completed), **Then** each event envelope contains a valid payload that the conformance validator accepts.
2. **Given** a manual audit trigger with enforcement mode `"blocking"`, **When** the audit completes with verdict `"fail"`, **Then** the MissionAuditCompleted payload includes `verdict="fail"`, `severity="error"`, a non-zero `findings_count`, and a populated `artifact_ref`.
3. **Given** any of the five event types, **When** the payload is missing a required field, **Then** Pydantic raises `ValidationError` immediately — no fallback or default substitution.

---

### User Story 2 — Reduce Audit Events to Frozen State (Priority: P1)

As a state materializer, I call `reduce_mission_audit_events()` with a sequence of `Event` objects and receive a deterministic, frozen `ReducedMissionAuditState` snapshot.

**Why this priority**: The reducer is the canonical way consumers derive audit state. Without it, every consumer must duplicate reduction logic.

**Independent Test**: Feed the reducer a replay stream of events and assert the output matches a committed golden-file snapshot byte-for-byte.

**Acceptance Scenarios**:

1. **Given** a complete pass lifecycle stream (Requested → Started → Completed with `verdict="pass"`), **When** reduced, **Then** `audit_status` is `completed`, `verdict` is `"pass"`, `artifact_ref` is populated, and `anomalies` is empty.
2. **Given** a lifecycle with a decision checkpoint (Requested → Started → DecisionRequested → Completed), **When** reduced, **Then** `pending_decisions` contains the decision entry while `audit_status` is `awaiting_decision`. When Completed arrives, `pending_decisions` is cleared (implicitly resolved) and `audit_status` reaches `completed`. The audit reducer does NOT track answered decisions — it has no `answered_decisions` field. Decision answers are outside this event family's scope (see Assumptions).
3. **Given** a failure lifecycle (Requested → Started → Failed), **When** reduced, **Then** `audit_status` is `"failed"`, `verdict` is `None`, and `partial_artifact_ref` is preserved if present.
4. **Given** duplicate events in the stream, **When** reduced, **Then** duplicates are deduplicated and the result is identical to the deduplicated stream.
5. **Given** events in random order, **When** reduced, **Then** the result is identical regardless of input order (deterministic across permutations).

---

### User Story 3 — Validate Payloads Through Conformance Suite (Priority: P1)

As a contract consumer in another repository (spec-kitty, spec-kitty-saas), I run the conformance test suite against committed fixtures to verify my local schema copy has not drifted from the canonical contracts.

**Why this priority**: Conformance fixtures are the published API surface. Without them, consumers cannot pin a version and verify compatibility.

**Independent Test**: Run `pytest --pyargs spec_kitty_events.conformance` and all mission-audit fixtures pass validation.

**Acceptance Scenarios**:

1. **Given** valid fixture files for all five event types, **When** validated through `validate_event()`, **Then** each returns `ConformanceResult(valid=True)` with empty violation tuples.
2. **Given** invalid fixture files (missing verdict, bad trigger mode, missing decision_id), **When** validated, **Then** each returns `ConformanceResult(valid=False)` with specific `model_violations` identifying the exact field and constraint.
3. **Given** replay stream fixtures (JSONL), **When** each line is parsed as an Event and its payload validated, **Then** the full stream passes validation and the reducer produces the expected output.

---

### User Story 4 — Compose with Dossier Contracts (Priority: P2)

As a dossier materializer, I use audit artifact references (containing `ContentHashRef` and `ProvenanceRef`) to index audit reports into the Mission Dossier alongside other artifacts.

**Why this priority**: Audit artifacts must be first-class entries in the dossier. Reusing existing dossier value objects ensures interoperability without contract duplication.

**Independent Test**: Construct an `AuditArtifactRef` with real `ContentHashRef` and `ProvenanceRef` instances from `dossier.py`, embed it in a `MissionAuditCompletedPayload`, serialize, and validate — the dossier value objects must serialize and deserialize identically.

**Acceptance Scenarios**:

1. **Given** an `AuditArtifactRef` containing `ContentHashRef(algorithm="sha256", hash="abc123...", size_bytes=4096, encoding="utf-8")` and a `ProvenanceRef`, **When** embedded in `MissionAuditCompletedPayload` and round-tripped, **Then** all nested fields survive without data loss.
2. **Given** existing `MissionDossierArtifactIndexed` events in a stream, **When** mission-audit events are added to the same stream, **Then** the dossier reducer continues to function without errors (no namespace collision, no field conflict).

---

### User Story 5 — Register in Public API Surface (Priority: P2)

As a library user importing from `spec_kitty_events`, I can access all audit event types, payload models, the reducer, and supporting types directly from the top-level `__init__.py`.

**Why this priority**: The public API is the discoverability contract. If types are not exported, consumers must reach into private modules.

**Independent Test**: `from spec_kitty_events import MissionAuditRequestedPayload, reduce_mission_audit_events, AuditVerdict, MISSION_AUDIT_REQUESTED` succeeds without `ImportError`.

**Acceptance Scenarios**:

1. **Given** the `__init__.py` exports list, **When** a consumer imports any mission-audit public name, **Then** the import succeeds and `mypy --strict` reports no errors.
2. **Given** the conformance validator's `_EVENT_TYPE_TO_MODEL` mapping, **When** any of the five event type strings is looked up, **Then** the correct payload model class is returned.

---

### Edge Cases

- What happens when `MissionAuditCompleted` arrives before `MissionAuditStarted`? The reducer records an anomaly and continues (does not crash).
- What happens when multiple `MissionAuditDecisionRequested` events share the same `decision_id`? The reducer deduplicates and records an anomaly for the duplicate.
- What happens when `MissionAuditFailed` arrives after `MissionAuditCompleted`? The reducer records a terminal-state anomaly (event after terminal).
- What happens when `enforcement_mode` in `MissionAuditRequested` has an unrecognized value? Pydantic `Literal` validation rejects it immediately.
- What happens when `findings_count` is negative? Pydantic `Field(ge=0)` constraint rejects it.
- What happens when `artifact_ref` is missing in `MissionAuditCompleted`? Pydantic rejects it — every completed audit MUST produce an artifact reference. If artifact generation is deferred, the emitter MUST emit `MissionAuditFailed` instead.

## Requirements

### Functional Requirements

- **FR-001**: Library MUST define five event type constants: `MISSION_AUDIT_REQUESTED`, `MISSION_AUDIT_STARTED`, `MISSION_AUDIT_DECISION_REQUESTED`, `MISSION_AUDIT_COMPLETED`, `MISSION_AUDIT_FAILED` with PascalCase string values (`"MissionAuditRequested"`, etc.).
- **FR-002**: Library MUST define frozen Pydantic payload models for each event type, all sharing common fields: `mission_id` (str), `run_id` (str), `feature_slug` (str), `actor` (str).
- **FR-003**: `MissionAuditRequestedPayload` MUST include `trigger_mode: Literal["manual", "post_merge"]`, `audit_scope: List[str]`, and `enforcement_mode: Literal["advisory", "blocking"]`.
- **FR-004**: `MissionAuditStartedPayload` MUST include `audit_scope_hash: str` representing a deterministic hash of the input artifact set.
- **FR-005**: `MissionAuditDecisionRequestedPayload` MUST include `decision_id: str`, `question: str`, `context_summary: str`, and `severity: AuditSeverity`.
- **FR-006**: `MissionAuditCompletedPayload` MUST include `verdict: AuditVerdict`, `severity: AuditSeverity`, `findings_count: int` (≥0), `artifact_ref: AuditArtifactRef` (required — every completed audit produces an artifact), and `summary: str`.
- **FR-007**: `MissionAuditFailedPayload` MUST include `error_code: str`, `error_message: str`, and `partial_artifact_ref: Optional[AuditArtifactRef]`.
- **FR-008**: Library MUST define `AuditVerdict` enum with values: `pass`, `pass_with_warnings`, `fail`, `blocked_decision_required`.
- **FR-009**: Library MUST define `AuditSeverity` enum with values: `info`, `warning`, `error`, `critical`.
- **FR-010**: Library MUST define `AuditStatus` enum with values: `pending`, `running`, `awaiting_decision`, `completed`, `failed`.
- **FR-011**: Library MUST define `AuditArtifactRef` frozen model composing `report_path: str`, `content_hash: ContentHashRef` (from dossier.py), `provenance: ProvenanceRef` (from dossier.py).
- **FR-012**: Library MUST provide `reduce_mission_audit_events()` pure function accepting `Sequence[Event]` and returning frozen `ReducedMissionAuditState`.
- **FR-013**: Reducer MUST be deterministic: identical event sets in any order produce identical output.
- **FR-014**: Reducer MUST record anomalies for: events before Requested, events after terminal state, duplicate decision_ids, unrecognized event types within the audit family.
- **FR-015**: All five event types MUST be registered in the conformance validator `_EVENT_TYPE_TO_MODEL` mapping.
- **FR-016**: Conformance fixtures MUST include at minimum 7 valid, 3 invalid, and 3 replay stream fixtures covering pass, warning, fail, and decision-checkpoint flows.
- **FR-017**: All new public types MUST be exported from `__init__.py`.
- **FR-018**: Schema version for this event family MUST be `"2.5.0"`.
- **FR-019**: All models MUST use `ConfigDict(frozen=True)` and pass `mypy --strict` with Python 3.10 target.
- **FR-020**: Library MUST NOT duplicate or redefine `ContentHashRef`, `ProvenanceRef`, or any other existing dossier value object — MUST import and compose.

### Key Entities

- **MissionAuditRequestedPayload**: Initiating event capturing trigger source, scope, and enforcement policy.
- **MissionAuditStartedPayload**: Execution-start marker with deterministic scope fingerprint.
- **MissionAuditDecisionRequestedPayload**: Human-in-control checkpoint when audit confidence is insufficient.
- **MissionAuditCompletedPayload**: Terminal success event carrying verdict, severity, findings count, artifact reference, and summary.
- **MissionAuditFailedPayload**: Terminal error event with error classification and optional partial artifact.
- **AuditArtifactRef**: Value object linking an audit report to its content hash and provenance.
- **AuditVerdict**: Constrained vocabulary for audit outcomes (pass / pass_with_warnings / fail / blocked_decision_required).
- **AuditSeverity**: Constrained vocabulary for finding severity (info / warning / error / critical).
- **AuditStatus**: Reducer state machine values (pending / running / awaiting_decision / completed / failed).
- **ReducedMissionAuditState**: Frozen output of the reducer containing full materialized audit state.
- **MissionAuditAnomaly**: Non-fatal issue recorded during reduction.

## Success Criteria

### Measurable Outcomes

- **SC-001**: All five payload models validate through conformance suite with zero violations on valid fixtures.
- **SC-002**: Invalid fixtures produce specific, field-level violations (not generic errors) for every invalid fixture.
- **SC-003**: Replay stream fixtures cover all four lifecycle outcomes (pass, warning pass, fail, decision checkpoint) and produce deterministic reducer snapshots matching committed golden files.
- **SC-004**: Hypothesis property tests (≥200 examples) confirm reducer determinism across random event orderings.
- **SC-005**: Adding audit contracts causes zero regressions in existing conformance, reducer, and dossier composition test suites.
- **SC-006**: `mypy --strict` reports zero errors for all new and existing modules after additions.
- **SC-007**: Version pin compatibility: consumers declaring `spec-kitty-events>=2.5.0` can install the package, import audit types, and call validate/reduce functions — the version pin is sufficient to guarantee all audit contract APIs are available.
- **SC-008**: Export completeness: all audit payload models, enums, constants, the reducer, and supporting types are exported from `spec_kitty_events.__init__` so consumers never need to import from private submodules.
- **SC-009**: Dossier composition non-regression: `AuditArtifactRef` round-trips through `MissionAuditCompletedPayload` and existing dossier reducers accept mixed audit+dossier event streams without error.

## Assumptions

- Feature 009 (dossier contracts) is stable and its value objects (`ContentHashRef`, `ProvenanceRef`) are final.
- The library version will be bumped to 2.5.0 as part of this feature release.
- `DecisionInputRequested` / `DecisionInputAnswered` from `mission_next.py` are separate from audit decisions — audit decisions use their own `decision_id` namespace scoped to the audit run. **Clarification**: The mission-audit event family defines only `MissionAuditDecisionRequested` (no answer event). The audit reducer tracks `pending_decisions` but has no `answered_decisions` field. Decision resolution is implicit: when `MissionAuditCompleted` or `MissionAuditFailed` arrives, all pending decisions are cleared. If a future need arises for explicit decision-answer tracking within audit, that would require a new event type and a breaking reducer change (3.x scope).
- Replay fixtures use JSONL format (one Event envelope per line) consistent with existing dossier and mission-next replay fixtures.
- The `schema_version` field in Event envelopes for this family is `"2.5.0"`.

## Scope Boundaries

**In scope**:
- Five event type constants and PascalCase string values
- Five frozen Pydantic payload models
- Three enum types (AuditVerdict, AuditSeverity, AuditStatus)
- One value object (AuditArtifactRef) composing existing dossier types
- One pure reducer function with frozen output model
- Conformance validator registration (5 new entries)
- Conformance fixtures (7 valid + 3 invalid + 3 replay)
- Public API exports in `__init__.py`
- Unit tests, property tests, and conformance tests

**Out of scope**:
- CLI command implementation (`spec-kitty verify`)
- Merge hook integration
- SaaS view/dashboard implementation
- Runtime mission policy evaluation
- 1.x compatibility

## Dependencies

- `spec-kitty-events` v2.4.0 (current baseline)
- `pydantic>=2.0.0,<3.0.0` (existing)
- `python-ulid>=1.1.0` (existing)
- `hypothesis>=6.0.0` (existing dev dependency)
- Existing dossier contracts: `ContentHashRef`, `ProvenanceRef` from `dossier.py`

## Migration Notes

- Consumers of `spec-kitty-events` pinned to `>=2.4.0` MUST update to `>=2.5.0` to access audit contracts.
- No breaking changes to existing contracts — this is a purely additive feature.
- `spec-kitty` CLI and `spec-kitty-saas` can adopt audit event types by importing from `spec_kitty_events>=2.5.0`.
- Version bump guidance: `spec-kitty` should declare `spec-kitty-events>=2.5.0` once it implements the merge-audit hook; `spec-kitty-saas` should declare `spec-kitty-events>=2.5.0` once it implements dashboard/dossier projection for audit events.
