# Feature Specification: GitHub Gate Observability Contracts

**Feature Branch**: `002-github-gate-observability-contracts`
**Created**: 2026-02-07
**Status**: Draft
**Input**: User description: "Define/strengthen canonical event contracts for GitHub gate observability"

## User Scenarios & Testing

### User Story 1 - Emit Typed Gate Outcome Events (Priority: P1)

A downstream consumer (CLI or SaaS) receives a GitHub `check_run` webhook conclusion and needs to produce a well-structured, validated event that records whether the gate passed or failed. The consumer constructs a `GatePassedPayload` or `GateFailedPayload`, attaches it to a generic `Event`, and persists it. The payload is validated at construction time — malformed or incomplete data is rejected immediately.

**Why this priority**: Without validated payload models, gate outcomes are unstructured blobs that downstream systems cannot reliably interpret, correlate, or query.

**Independent Test**: Create a `GatePassedPayload` with all required fields and attach it to an `Event`. Verify the payload round-trips through serialization and that omitting any required field raises a validation error.

**Acceptance Scenarios**:

1. **Given** a valid set of gate metadata (gate_name, conclusion, check_run_id, check_run_url, delivery_id), **When** a `GatePassedPayload` is constructed, **Then** it validates successfully and all fields are accessible with correct types.
2. **Given** a payload missing a required field (e.g., no `gate_name`), **When** construction is attempted, **Then** a `ValidationError` is raised before any event is emitted.
3. **Given** a valid `GatePassedPayload`, **When** it is attached as the `payload` of a generic `Event` with `event_type="GatePassed"`, **Then** the event serializes to dict and deserializes back without data loss.

---

### User Story 2 - Map GitHub Conclusions Deterministically (Priority: P1)

A consumer receives a raw GitHub `check_run` conclusion string and needs to know which event type to emit (or whether to skip). The mapping helper accepts the conclusion string and returns a deterministic result: `"GatePassed"`, `"GateFailed"`, or `None` (for ignored conclusions). The mapping is exhaustive over all known GitHub conclusion values.

**Why this priority**: Non-deterministic or incomplete mapping leads to silent data loss or incorrect gate status, making the observability pipeline unreliable.

**Independent Test**: Call the mapping helper with each known GitHub conclusion string and verify the returned event type matches the documented contract. Call with an unknown string and verify it raises an error.

**Acceptance Scenarios**:

1. **Given** `conclusion="success"`, **When** the mapping helper is called, **Then** it returns `"GatePassed"`.
2. **Given** `conclusion="failure"`, **When** the mapping helper is called, **Then** it returns `"GateFailed"`.
3. **Given** `conclusion="cancelled"` or `conclusion="timed_out"`, **When** the mapping helper is called, **Then** it returns `"GateFailed"`.
4. **Given** `conclusion="action_required"`, **When** the mapping helper is called, **Then** it returns `"GateFailed"`.
5. **Given** `conclusion="neutral"` or `conclusion="skipped"` or `conclusion="stale"`, **When** the mapping helper is called, **Then** it returns `None` and increments/logs an ignored-conclusion counter.
6. **Given** an unrecognized conclusion string (e.g., `"unknown_value"`), **When** the mapping helper is called, **Then** it raises an explicit error rather than silently dropping the event.

---

### User Story 3 - Correlate Gate Events with External Systems (Priority: P2)

An operator investigating a failed deployment needs to trace a `GateFailed` event back to the specific GitHub check run, pull request, and webhook delivery that produced it. The payload fields (`check_run_id`, `check_run_url`, `delivery_id`, `pr_number`) provide the necessary external correlation keys.

**Why this priority**: Observability without correlation is just noise. External keys make gate events actionable for incident response and audit.

**Independent Test**: Construct a `GateFailedPayload` with all correlation fields populated (including optional `pr_number`), serialize the event, and verify all correlation fields are present and correctly typed in the output.

**Acceptance Scenarios**:

1. **Given** a `GateFailedPayload` with `check_run_id=12345`, `check_run_url`, and `delivery_id`, **When** the event is serialized, **Then** all three fields appear in the serialized output with correct values.
2. **Given** a gate event from a push (not a PR), **When** the payload is constructed with `pr_number=None`, **Then** validation passes and the field is absent or null in the serialized output.
3. **Given** a gate event from a PR, **When** the payload is constructed with `pr_number=42`, **Then** the field is present and typed as an integer.

---

### User Story 4 - Changelog and Versioning for Downstream Consumers (Priority: P3)

A downstream library consumer needs to know what changed, whether the new version is backward-compatible, and what new types are available. The changelog entry and version bump communicate this clearly.

**Why this priority**: Downstream consumers cannot safely adopt new contracts without explicit versioning and documented changes.

**Independent Test**: Read the changelog and verify it documents the new payload models, mapping helper, and any new public API exports.

**Acceptance Scenarios**:

1. **Given** the new version is released, **When** a consumer reads the changelog, **Then** they find an entry describing the new `GatePassedPayload`, `GateFailedPayload`, and mapping helper.
2. **Given** the library version, **When** compared to the previous version, **Then** the version bump follows semver rules (minor bump for additive, non-breaking changes).

---

### Edge Cases

- What happens when a GitHub conclusion string has unexpected casing (e.g., `"SUCCESS"` vs `"success"`)? The mapping helper must define whether it normalizes or rejects non-lowercase input.
- What happens when `check_run_url` is not a valid URL format? The payload model should validate URL structure.
- What happens when `delivery_id` is empty string vs `None`? The contract must distinguish between "not provided" and "provided but empty."
- How does the system handle a `check_run` conclusion of `"stale"`? It is explicitly treated as ignored (`None`) and counted/logged as ignored.

## Requirements

### Functional Requirements

- **FR-001**: Library MUST provide a `GatePassedPayload` Pydantic model with required fields: `gate_name` (str), `gate_type` (literal `"ci"`), `conclusion` (str), `external_provider` (literal `"github"`), `check_run_id` (int), `check_run_url` (str, URL format), `delivery_id` (str, idempotency key).
- **FR-002**: Library MUST provide a `GateFailedPayload` Pydantic model with the same required fields as `GatePassedPayload` plus identical structure (shared base or identical definition).
- **FR-003**: Both payload models MUST include an optional `pr_number` field (int or None) for pull-request correlation.
- **FR-004**: Both payload models MUST be frozen (immutable after construction), consistent with the existing `Event` model.
- **FR-005**: Library MUST provide a mapping function that accepts a GitHub `check_run` conclusion string and returns the corresponding event type string (`"GatePassed"` or `"GateFailed"`) or `None` for ignored conclusions.
- **FR-006**: The mapping function MUST map `"success"` to `"GatePassed"`.
- **FR-007**: The mapping function MUST map `"failure"`, `"timed_out"`, `"cancelled"`, and `"action_required"` to `"GateFailed"`.
- **FR-008**: The mapping function MUST return `None` for `"neutral"`, `"skipped"`, and `"stale"` conclusions and log/count the ignored conclusion.
- **FR-009**: The mapping function MUST raise an explicit error for any conclusion string not in the known set.
- **FR-010**: Library MUST export the new payload models and mapping function from the package's public API.
- **FR-011**: Library MUST include unit tests validating schema construction, required field enforcement, and serialization round-trips.
- **FR-012**: Library MUST include tests verifying deterministic mapping for every known GitHub conclusion value.
- **FR-013**: Library MUST update the changelog with a new version entry documenting the added contracts and mapping helper.

### Key Entities

- **GatePassedPayload**: Validated payload model representing a CI gate that concluded successfully. Attached to a generic `Event` with `event_type="GatePassed"`.
- **GateFailedPayload**: Validated payload model representing a CI gate that concluded with a failure condition. Attached to a generic `Event` with `event_type="GateFailed"`.
- **GitHub Check Run Conclusion**: A string value from the GitHub API (`success`, `failure`, `timed_out`, `cancelled`, `action_required`, `neutral`, `skipped`, `stale`) that determines which event type to emit or whether to ignore.
- **Delivery ID**: A unique identifier from the GitHub webhook delivery, used as an idempotency key to prevent duplicate event emission.

## Success Criteria

### Measurable Outcomes

- **SC-001**: All known GitHub `check_run` conclusion values (8 values) are covered by the mapping function with zero ambiguity — each maps to exactly one outcome.
- **SC-002**: Constructing a payload model with any required field missing raises a validation error 100% of the time.
- **SC-003**: Payload models round-trip through `to_dict()` / `from_dict()` (or equivalent serialization) without data loss for all field types.
- **SC-004**: Test suite achieves 100% branch coverage for the mapping function and payload validation logic.
- **SC-005**: An unrecognized conclusion string produces an explicit, catchable error — never silent data loss.
- **SC-006**: Changelog entry is present and documents all new public API additions before the version is published.
