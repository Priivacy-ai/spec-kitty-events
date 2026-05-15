# Feature Specification: Executable Event Timestamp Semantics

**Feature Branch**: `executable-event-timestamp-semantics-01KRNME2`
**Created**: 2026-05-15
**Status**: Draft
**Input**: GitHub issue Priivacy-ai/spec-kitty-events#24 — Event contract enforcement. Sourced from cross-repo bug brief `start-here.md` Sections "Event contract" and "Suggested Fix Plan §7. Strengthen event contracts".

## Background

Spec Kitty's canonical event contract publishes a top-level `timestamp` field. The published English-language description says `timestamp` is the producer's wall-clock occurrence time. A bug in `spec-kitty-saas` showed that the contract is not executable enough to prevent consumer drift: SaaS persisted server receipt time into the same field name (`Event.timestamp`) and used that value as canonical occurrence time, which made old historical missions appear as "just now" or "14m ago" in Teamspace Pulse during a recent historical backfill.

The contract is technically correct today, but it is also passive. There are no committed fixtures where producer time differs from receipt time, and no conformance checks that fail loudly when a consumer reassigns the canonical timestamp at import or replay. This mission makes the producer-occurrence semantics executable, so that downstream consumers cannot silently substitute receipt/import time for canonical event time without conformance tests failing.

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Contract author defines a non-ambiguous timestamp field (Priority: P1)

A maintainer of the canonical event contract must be able to declare, in committed model and schema artifacts, that `timestamp` carries producer occurrence time and that any separate receipt/import time is a different, named concept. The artifacts must be readable both by humans and by conformance tests.

**Why this priority**: This is the irreducible core. Without an executable producer-vs-receipt distinction in the canonical contract, every downstream consumer (SaaS ingestion, CLI sync, tracker egress, reducers, dashboards) inherits the ambiguity that caused the original Teamspace Pulse bug.

**Independent Test**: Read the canonical event model docstrings and committed JSON Schemas. Confirm they state, in human-readable form and in machine-readable form, that `timestamp` is producer occurrence time and that any receipt/import time is captured as a distinct concept owned by consumers. Confirm a developer reading only the contract repo can determine which value is canonical without consulting any consumer codebase.

**Acceptance Scenarios**:

1. **Given** the canonical event envelope, **When** a contract author or consumer reads the Pydantic model docstring or generated JSON Schema description for `timestamp`, **Then** the text explicitly states "producer-assigned wall-clock occurrence time" and explicitly warns that consumer receipt/import time must be stored under a different field.
2. **Given** the canonical data-model documentation under `kitty-specs/teamspace-event-contract-foundation-01KQHDE4/data-model.md`, **When** a reader navigates to the timestamp semantics section, **Then** the doc names the producer-vs-receipt distinction, names the canonical field, and prohibits reusing the canonical field name for receipt/import time in consumer storage.

---

### User Story 2 — Conformance fixtures simulate the drift bug (Priority: P1)

The contract repo must ship at least one conformance fixture in which the producer timestamp is materially older than the time the consumer would record at receipt. This fixture is the executable artifact that proves a consumer cannot accidentally collapse the two values.

**Why this priority**: Without the fixture, the contract has nothing for consumer test suites to assert against. The Teamspace bug existed precisely because no committed test exercised "old producer time, recent receipt time" end-to-end.

**Independent Test**: Discover a committed fixture where the canonical `timestamp` is an old date (for example, the start of the current year) and a companion receipt-time annotation is the current date. Apply the fixture to the conformance harness and verify it parses, validates against schema, and exposes both values distinctly to downstream consumers.

**Acceptance Scenarios**:

1. **Given** the new conformance fixture, **When** the conformance harness loads it, **Then** the harness exposes a producer `timestamp` older than today and a separately named receipt-time annotation roughly equal to today.
2. **Given** any new event payload type added to the contract that includes a timestamp, **When** maintainers update fixtures, **Then** at least one "old producer, recent receipt" fixture exists for that event type or the conformance suite explicitly opts out with a documented rationale.

---

### User Story 3 — Consumer conformance harness catches receipt-time substitution (Priority: P1)

A downstream consumer repo (SaaS ingestion, CLI sync, etc.) must be able to use a reusable conformance helper from `spec-kitty-events` that verifies the consumer preserved producer occurrence time after its ingestion path. The harness must fail loudly when a consumer replaces the canonical timestamp with receipt or import time.

**Why this priority**: The original Teamspace bug was caused by a consumer silently using receipt time in a "timestamp" field. A reusable conformance helper turns "we promised to preserve occurrence time" into a one-line consumer test. Without it, every consumer has to invent its own assertion and the contract degrades again.

**Independent Test**: Import the new conformance helper from a fake consumer that maps incoming events to its own storage. Demonstrate that a correct consumer (preserves the producer timestamp) passes the helper, and an incorrect consumer (overwrites with receipt time) fails the helper with a clear, actionable message identifying the field, the expected producer occurrence time, and the substituted receipt-time value.

**Acceptance Scenarios**:

1. **Given** a fake consumer that records the incoming envelope and exposes its persisted occurrence-time field, **When** the consumer correctly stores the producer `timestamp`, **Then** the conformance helper returns success for that fixture.
2. **Given** the same fake consumer modified to replace the canonical `timestamp` with `datetime.utcnow()`-style receipt time, **When** the conformance helper is run, **Then** the helper raises a typed failure that names the substituted value, the expected value, and the contract rule that was violated.
3. **Given** a downstream consumer that wishes to also record receipt time, **When** the consumer's metadata exposes a separately named receipt-time field, **Then** the conformance helper neither requires nor forbids the receipt-time field and only checks producer occurrence preservation.

---

### User Story 4 — Schema regeneration is verified in CI (Priority: P2)

When a contract author changes the `timestamp` description, regenerates schemas, or modifies conformance fixtures, the existing `pytest` + schema-drift + `mypy --strict` charter quality gates must catch divergence between Pydantic models, committed JSON Schemas, fixtures, and conformance helpers.

**Why this priority**: The contract repo already has a charter-required schema drift check. This story ensures the new artifacts (executable timestamp semantics text, fixtures, conformance helpers) are pulled into the same drift envelope so future edits cannot silently re-introduce drift.

**Independent Test**: Modify the timestamp description in the Pydantic model without regenerating the schemas. Confirm the schema drift check fails. Restore. Modify a conformance fixture to make producer timestamp equal receipt time. Confirm at least one committed conformance test fails.

**Acceptance Scenarios**:

1. **Given** the existing committed schema generation check, **When** the Pydantic timestamp field's description text is modified, **Then** the schema drift check reports an out-of-sync schema until regeneration.
2. **Given** the committed conformance fixtures, **When** a fixture's producer timestamp is rewritten to equal its receipt-time annotation, **Then** at least one committed conformance test fails because the "old producer, recent receipt" invariant is violated.

---

### Edge Cases

- **Legacy events without explicit receipt-time annotation**: existing committed fixtures that pre-date this mission MUST continue to validate. Receipt-time annotation is optional; producer occurrence time is mandatory.
- **Events where producer occurrence time was lost upstream**: contract MUST permit a documented, explicit fallback annotation (e.g. "occurrence_time_inferred=true") so consumers can flag degraded provenance without silently consuming receipt time as canonical.
- **Future fields with the word "timestamp" in their name**: contract docs and lint guidance MUST warn against introducing additional fields named `*timestamp*` in consumer storage layers when those fields are not producer occurrence time.
- **Receipt time identical to producer time** (live near-real-time event): MUST be valid and not falsely flagged. Conformance asserts equality-of-canonical-field, not inequality of producer vs receipt time.
- **Out-of-order or clock-skewed producer events**: contract MUST NOT use receipt time as an ordering fallback unless explicitly named and documented; ordering rules are out of scope of this mission but the contract MUST NOT regress that boundary.

## Requirements *(mandatory)*

### Functional Requirements

| ID | Requirement | Status |
|----|-------------|--------|
| FR-001 | The canonical event envelope's `timestamp` field documentation (model docstring and generated JSON Schema description) MUST state in unambiguous English that the value is producer-assigned wall-clock occurrence time. | Required |
| FR-002 | The canonical event envelope documentation MUST explicitly prohibit consumers from storing receipt/import time under any field whose name matches the canonical `timestamp` field. | Required |
| FR-003 | The contract MUST name a distinct conceptual slot for consumer-side receipt or import time (for example, `received_at`) and document that this slot belongs to the consumer, not the canonical envelope. | Required |
| FR-004 | The `kitty-specs/teamspace-event-contract-foundation-01KQHDE4/data-model.md` document MUST be updated to record the producer-vs-receipt distinction with the same wording style as the rest of that document. | Required |
| FR-005 | At least one conformance fixture MUST exist in which the canonical `timestamp` is at least 30 days older than the fixture's receipt-time annotation. | Required |
| FR-006 | A reusable conformance helper MUST be exposed from the public package surface that, given a fixture and a consumer-supplied callable returning the consumer's persisted occurrence-time value, asserts the value equals the fixture's producer `timestamp`. | Required |
| FR-007 | The reusable conformance helper MUST raise a typed, named error (not a bare assertion or string) when a consumer substitutes a different value, and the error message MUST include the field name, the expected producer occurrence time, and the substituted value. | Required |
| FR-008 | The conformance helper MUST treat the presence or absence of a separately named consumer receipt-time field as neither required nor forbidden; only producer occurrence preservation is checked. | Required |
| FR-009 | Schema regeneration scripts MUST emit JSON Schemas whose `description` for the canonical `timestamp` includes language consistent with FR-001 and FR-002. | Required |
| FR-010 | At least one committed conformance test MUST exercise a "good consumer" path (preserves producer `timestamp`) and at least one MUST exercise a "bad consumer" path (substitutes receipt time) and assert the helper distinguishes them. | Required |
| FR-011 | The `CHANGELOG.md` MUST record this mission as a non-breaking strengthening of timestamp semantics with a brief migration note for consumers that already conflated producer and receipt time. | Required |

### Non-Functional Requirements

| ID | Requirement | Threshold | Status |
|----|-------------|-----------|--------|
| NFR-001 | The conformance helper MUST be deterministic and free of network or filesystem side effects beyond reading provided fixture data. | 0 network calls, 0 writes to filesystem during execution. | Required |
| NFR-002 | The conformance helper MUST complete in well under one second on a single fixture on standard developer hardware. | <250 ms per fixture in pytest. | Required |
| NFR-003 | The conformance fixture set added by this mission MUST not increase total `pytest` suite wall time on a clean checkout by more than a small, bounded amount. | <2 seconds increase in `pytest` wall time on a clean checkout. | Required |
| NFR-004 | All new code added by this mission MUST satisfy the charter-mandated quality gates. | `pytest`, schema generation drift check, and `mypy --strict` all green. | Required |

### Constraints

| ID | Constraint | Status |
|----|------------|--------|
| C-001 | Public Python import paths and existing exported names MUST NOT change as a side effect of this mission; the change is additive. | Required |
| C-002 | The wire-format identifier for the canonical producer timestamp MUST remain `timestamp` for backwards compatibility with existing consumers and persisted JSONL/log streams. | Required |
| C-003 | The mission MUST NOT introduce a runtime dependency on `spec-kitty-saas`, `spec-kitty`, or `spec-kitty-tracker`; conformance helpers MUST be importable into any consumer that already depends on `spec-kitty-events`. | Required |
| C-004 | The mission MUST NOT modify reducer ordering semantics; if reducer ordering rules are touched at all, they MUST remain at parity with current behaviour. | Required |
| C-005 | The mission MUST NOT add an "occurrence_time_inferred" or similar provenance flag to the canonical envelope; that boundary is reserved for a future, separately scoped contract change. | Required |

### Key Entities

- **Canonical event envelope**: The serialized record published by producers (CLI, tracker, internal subsystems) and consumed by SaaS, dashboards, and audit tooling. Its `timestamp` is producer occurrence time.
- **Receipt-time annotation (consumer-owned)**: A separately named concept (for example `received_at`) that lives in consumer storage and is not part of the canonical envelope wire format.
- **Conformance fixture**: A committed JSON payload (with associated metadata) used by tests in this repo and by downstream consumer repos to verify timestamp behaviour.
- **Conformance helper**: A reusable, deterministic Python callable exposed by the public package surface that asserts a consumer preserved producer occurrence time.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A new contributor reading only the canonical event model and the data-model document can correctly answer "is the canonical `timestamp` producer time or server receipt time?" without consulting any consumer codebase. Verified by reviewer sign-off.
- **SC-002**: A consumer repo that currently passes its own tests but silently substitutes receipt time fails the new reusable conformance helper on at least the "old producer, recent receipt" fixture, in 100% of runs across at least three repeat invocations.
- **SC-003**: At least one committed fixture exists where the producer timestamp is at least 30 days older than the fixture's receipt-time annotation, and that fixture is exercised by the conformance test suite.
- **SC-004**: After this mission lands, the `spec-kitty-saas` repo's planned occurrence-time work can import the conformance helper without adding a runtime dependency on any other repo beyond `spec-kitty-events`.
- **SC-005**: Charter-mandated quality gates (`pytest`, schema generation/drift check, `mypy --strict`) pass on the mission branch with the new artifacts present, and the suite wall-time increase is bounded by NFR-003.

## Assumptions

- The producer `timestamp` field already exists on the canonical envelope and stays in its current wire position; this mission strengthens its meaning, not its shape.
- Downstream consumers (SaaS, CLI, tracker, hub) will run the new conformance helper in their own test suites as part of follow-on missions. This contract mission does not modify those consumers.
- The committed JSON Schemas are regenerated via the existing schema generation workflow (not a new tool introduced here).
- The "30 days older" threshold in FR-005 is a documentation aid, not a wire-format requirement; consumers must preserve any producer timestamp regardless of age.

## Out of Scope

- Modifying any consumer repo. CLI sync, SaaS ingestion, tracker egress, and dashboard semantics are addressed by sibling missions in the relevant repos.
- Introducing a canonical receipt-time field on the wire envelope. Receipt time remains a consumer-owned concept.
- Reordering reducer or replay semantics, beyond preserving current ordering behaviour.
- Adding a provenance/inference flag to the envelope.
- Data repair tooling for SaaS or any other consumer's existing persisted rows. That belongs to consumer repos.
