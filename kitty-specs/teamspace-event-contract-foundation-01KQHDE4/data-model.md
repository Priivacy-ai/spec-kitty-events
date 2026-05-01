# Phase 1 Data Model: TeamSpace Event Contract Foundation

**Mission**: `teamspace-event-contract-foundation-01KQHDE4`
**Spec**: [spec.md](./spec.md) · **Plan**: [plan.md](./plan.md) · **Research**: [research.md](./research.md)

This document captures the entities, value objects, invariants, and state transitions that the Phase 1 contracts in [contracts/](./contracts/) formalize. It is technology-agnostic at the data-model layer; the implementation language and framework are stated in the plan's Technical Context.

---

## Entities

### Canonical Envelope

The TeamSpace 3.0.x event wrapper. Every event accepted by the contract package is, structurally, a `CanonicalEnvelope`.

| Field | Type | Required | Notes |
|---|---|---|---|
| `event_type` | string (enum) | yes | One of the canonical event types: `MissionCreated`, `WPStatusChanged`, `MissionClosed`, plus the existing event-type catalog |
| `event_version` | string | yes | Semantic version of the envelope contract (FR-010 / R-03) |
| `event_id` | string (ULID) | yes | Stable identity for the event |
| `occurred_at` | string (ISO-8601 UTC) | yes | Producer-assigned timestamp; never overwritten by the consumer |
| `mission_id` | string (ULID) | yes | Canonical mission identity |
| `payload` | object (Typed Payload) | yes | Per-event-type payload, validated against the corresponding typed payload schema |

**Invariants**:
- No field, anywhere within the envelope or payload, may use a key from the **Forbidden-Key Set** (recursive).
- `payload` must validate against the typed payload schema named by `event_type`.
- `event_type` must be in the canonical catalog.
- `event_version` must match the package's contract version on accept.

**Source of truth**: `src/spec_kitty_events/` (Pydantic models + committed JSON Schemas).

---

### Lane Vocabulary

The authoritative ordered list of work-package lanes used across all consumers.

| Lane | Notes |
|---|---|
| `todo` | New work, not started |
| `in_progress` | Implementation underway |
| `in_review` | Reviewer assigned, review in progress (canonical per this mission's decision) |
| `review` | Review terminal-pending state (existing) |
| `done` | Completed and accepted |
| (other existing lanes from `src/spec_kitty_events/status.py` `Lane` enum) | Preserved as canonical |

**Invariants**:
- The vocabulary is a closed set; consumers must reject anything outside it.
- `in_review` is canonical (the mission's decision; recorded in `Assumptions` of [spec.md](./spec.md)).
- The contract package, the CLI, and the SaaS projector reference the **same constant** (no duplicate definitions). This is enforced by `tests/test_lane_vocabulary.py`.

**State transitions**: Out of scope for this entity at the contract level — `WPStatusChanged` carries `from_lane` / `to_lane` and any transition rules are validated by the typed payload model, not by the lane vocabulary itself.

---

### Typed Payload (per event type)

A payload is a typed Pydantic model whose name corresponds to the event type.

| Event type | Payload model | Notes |
|---|---|---|
| `MissionCreated` | `MissionCreatedPayload` | Reconciled per [contracts/payload-reconciliation.md](./contracts/payload-reconciliation.md); single source of truth |
| `WPStatusChanged` | `StatusTransitionPayload` (existing) | Lane vocabulary now includes `in_review`; from/to lane fields validate against the canonical Lane Vocabulary |
| `MissionClosed` | `MissionClosedPayload` | Reconciled per [contracts/payload-reconciliation.md](./contracts/payload-reconciliation.md); CLI emission narrowed to match |
| (other existing event types) | (existing payload models) | Unchanged unless surfaced by R-01/R-02 |

**Invariants**:
- Producers must conform to the typed payload schema (R-02 decision).
- A payload's keys, recursively, must not include any Forbidden Key (R-01).
- Optional fields are explicit; unknown fields are rejected (Pydantic `model_config = ConfigDict(extra='forbid')` at the payload boundary).

---

### Forbidden-Key Set

A closed, named, versioned constant.

| Field | Type | Notes |
|---|---|---|
| `name` | string | `FORBIDDEN_LEGACY_KEYS_V1` (or successor) |
| `members` | `frozenset[str]` | Includes the seeded `feature_slug`, `feature_number`, `mission_key`; full set determined by the audit work package per R-01 |
| `since_version` | string | The contract version that introduced the set |

**Invariants**:
- Membership is checked **only** against keys, never against values.
- Recursive walk traverses every nested object and every element of every array.
- Depth is unbounded in principle; tests prove correctness at depth ≥ 10 (NFR-002).

---

### Conformance Fixture

A committed `(input, expected outcome, class)` record that proves a contract rule.

| Field | Type | Required | Notes |
|---|---|---|---|
| `input` | JSON | yes | The candidate envelope or raw row |
| `expected` | enum (`valid` \| `invalid`) | yes | The expected outcome of validation |
| `class` | enum | yes | One of the eight classes from R-05 |
| `expected_error_code` | enum (`code` from R-04) | yes when `expected = invalid` | The structured error code that must be returned |
| `notes` | string | no | Human context |

**Invariants**:
- All values are deterministic (R-06): no wall-clock timestamps, no random IDs.
- Each class must have at least one fixture; the manifest fails CI on a zero-population class (FR-008 / SC-005).

---

### Local Status Row

A line from a historical `status.events.jsonl` file. Distinct from a Canonical Envelope by structure.

**Invariant**: A Local Status Row **always** fails ingress validation (C-001, FR-006). The `historical_row_raw` fixture class proves this for every surveyed historical shape.

---

### Structured Validation Error

The result returned by the validator on rejection (R-04).

| Field | Type | Required | Notes |
|---|---|---|---|
| `code` | enum (closed) | yes | Stable rejection class identifier |
| `message` | string | yes | One-line human-readable summary |
| `path` | list of (string \| int) | yes (may be empty) | JSON-pointer-like path to the offending location |
| `details` | object | no | Class-specific structured detail |

**Invariants**:
- The `code` enum is part of the public contract; new codes follow the same review rule as schema bumps.
- Validation is deterministic (NFR-001): identical input produces identical `code`, `message`, `path`, and `details`.

---

## Cross-entity invariants (envelope-level acceptance criteria)

For an envelope to be accepted:

1. Envelope shape is well-formed (`event_type`, `event_version`, `event_id`, `occurred_at`, `mission_id`, `payload` all present and well-typed).
2. `event_type` is in the canonical catalog.
3. `event_version` matches the package's contract version.
4. `payload` validates against the typed payload model corresponding to `event_type`.
5. No key, anywhere in the envelope or payload, is in the Forbidden-Key Set (recursive).
6. Every lane reference in the payload is a canonical lane (per Lane Vocabulary), including `in_review`.

The validator short-circuits on the first failure but reports the structured error for *that* failure. Consumers wishing to surface multiple failures may opt into a "collect all" mode (out of scope for this mission unless surfaced by R-04 follow-up).

---

## State transitions

This mission introduces **no new state machines**. The existing `WPState` and lane-transition logic in `src/spec_kitty_events/status.py` is preserved; the only change is that the canonical lane vocabulary is widened to include `in_review` (and any transitions involving `in_review` become permitted).

---

## Determinism contract

For any input `x`:

- `validate(x)` is a pure function: `validate(x) == validate(x)` always.
- Fixtures contain no time- or random-derived fields except where the fixture's class specifically tests timestamp variation.
- Fixture audit test enforces this (R-06).
