# Phase 0 Research: WPStatusChanged Backward Transition Contract

## Q1: Is the current `_ALLOWED_TRANSITIONS` matrix already correct for review rollbacks?

**Decision**: Yes. The matrix at `src/spec_kitty_events/status.py:342-368` already lists `(for_review, planned)`, `(in_review, planned)`, `(approved, planned)`, `(for_review, in_progress)`, `(in_review, in_progress)`, `(approved, in_progress)`, and `(in_review, for_review)` as sanctioned. Combined with the guard at lines 421-427 requiring `review_ref` for these pairs, the runtime is correct. The contract gap is purely documentation.

**Rationale**: The 2026-05-17 incident was caused by SaaS implementing a stricter rule than the matrix prescribes. Changing the matrix would break correct CLI behaviour.

**Alternatives considered**:
- Tightening the matrix to require `force=True` for any backward transition — rejected; would force CLI emitters to set `force=True` for normal review rejection, which contradicts spec FR-002.
- Loosening the matrix to drop the `review_ref` guard — rejected; would erase audit trail.

## Q2: How should `from_lane` mismatch be classified?

**Decision**: Two sub-cases via `reason_code`:
- `from_lane_mismatch_replay`: the event's `from_lane` corresponds to a state the consumer has already advanced past. The consumer SHOULD record a `ReconciliationDiagnostic` and SKIP re-application.
- `from_lane_mismatch_drift`: the event's `from_lane` does not match any prior projection state in the consumer's log for that WP. Consumer MUST record a `ReconciliationDiagnostic` and HOLD the event for operator review (do not apply, do not infra-fail).

**Rationale**: The two sub-cases have different operational consequences. Replay (a common, harmless re-delivery) should not page anyone. Drift (a real event-log inconsistency) should surface on a diagnostic dashboard.

**Alternatives considered**:
- Single `from_lane_mismatch` code — rejected; operators cannot distinguish "normal replay" from "real drift" without parsing payloads.
- Auto-rebase the event's `from_lane` to current projection — rejected; silently rewriting producer payloads destroys audit trail.

## Q3: Should `actor` modify validation?

**Decision**: No. `actor` is audit-only. The validation rules apply uniformly regardless of `actor` value. The contract document MUST state this explicitly to prevent future consumer implementations from inferring "actor=user" as a policy escape hatch.

**Rationale**: The 2026-05-17 incident-A logs show CLI emitted events with `actor="user"` for review rejection. A reasonable SaaS reviewer who saw "actor=user" might have inferred "any user action is allowed, force is implicit" — exactly the kind of drift we are locking out.

**Alternatives considered**:
- Treat `actor=user` as implicit `force=True` — rejected; conflates audit identity with policy and produces inconsistent semantics when CLI emits the same transition with `actor=claude`.

## Q4: How should replay be detected?

**Decision**: Primary key is `event_id` (a ULID present on every emitted event today). Secondary fallback is the tuple `(mission_slug, wp_id, sequence)` if `sequence` is present. Consumers MUST detect replay BEFORE invoking `validate_transition`; a replay hit is logged at debug level and produces no `ReconciliationDiagnostic` unless it is a "terminal replay" (re-applying an event that targets a terminal lane the projection is already in), in which case `reason_code = terminal_replay_skipped` may be recorded for visibility.

**Rationale**: `event_id` is already universal in current producers; sequence is the durable secondary key. Logging every replay as a diagnostic would drown the diagnostic surface.

**Alternatives considered**:
- Hash the payload to detect replay — rejected; payload hashing is fragile to field ordering and timestamp differences across producers.

## Q5: Where should the contract document live?

**Decision**: `docs/contracts/wp-status-changed.md`. Linked from `README.md` under a new "Contracts" section per NFR-004. The mission's own `contracts/wp-status-changed.contract.md` is a working copy that the implementing WP promotes (`mv` or `cp`) to `docs/contracts/wp-status-changed.md` during implementation.

**Rationale**: `docs/contracts/` is the convention for already-shipped published contracts on this repo. Keeping the planning copy under `kitty-specs/.../contracts/` keeps planning artifacts colocated.

**Alternatives considered**:
- Single canonical home under `kitty-specs/` — rejected; consumers would have to dig into mission directories to find the live contract.

## Q6: What `reason_code` enum values are needed at MVP?

**Decision**: Closed enum with four members initially:
- `from_lane_mismatch_replay`
- `from_lane_mismatch_drift`
- `terminal_replay_skipped`
- `unforced_rollback_without_review_ref` (consumer caught a producer bug: tried to roll back without `review_ref` and force=False)

The contract document MUST require any new code to be accompanied by both a doc update and at least one fixture.

**Rationale**: The four cover all known operational outcomes from the 2026-05-17 incident and from foreseeable variations. Closed enum prevents string drift (e.g. `from_lane_mismatch_replay` vs `from_lane_replay_mismatch`).

**Alternatives considered**:
- Open string field with naming convention — rejected; string drift was a contributor to the original incident.

## Q7: Schema generation and drift

**Decision**: New JSON Schema `src/spec_kitty_events/schemas/reconciliation_diagnostic.schema.json` is generated from the `ReconciliationDiagnostic` Pydantic model and committed alongside the model. A schema-drift test verifies the committed schema matches the model output (consistent with existing pattern for `status_transition_payload.schema.json`).

**Rationale**: Charter quality gate requires committed schema generation checks. Following the existing pattern keeps consumer tooling stable.

**Alternatives considered**:
- Document the diagnostic only in markdown (no JSON Schema) — rejected; downstream consumers (especially SaaS) need a machine-readable shape.

## Q8: How tightly to scope the conformance fixtures

**Decision**: Six fixtures total, one per scenario named in FR-007. Each fixture is a single JSON file containing one envelope-wrapped event (or in the from_lane_mismatch and replay cases, the projection state plus the offending event). The manifest entry declares `outcome` and `reason_code`. Tests assert that running the validator + reconciler over the fixture produces the declared outcome.

**Rationale**: Six fixtures cover the contract surface without test-suite bloat (NFR-001 < 5s).

**Alternatives considered**:
- Hypothesis-generated property-based tests — accepted as additive (test_reconciliation_diagnostic_model.py uses hypothesis on the model). Not used for the fixture suite because deterministic fixtures are the binding artefact (D-6).

## Risks (premortem)

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| Consumers ignore the contract document and re-derive rules from the code | Medium | High (would reproduce the 2026-05-17 split) | Add `from <module> import RECONCILIATION_REASON_CODES` plus a module-level docstring that names the contract path so anyone reading source lands on the doc. |
| Schema drift between the committed JSON Schema and the Pydantic model | Low | Medium | Schema-drift test (mirroring the existing pattern). |
| `reason_code` enum becomes a string dumping ground | Medium | Medium | Closed enum + fixture requirement for any new code. |
| Fixture file format becomes inconsistent with the existing manifest convention | Low | Low | New fixtures follow the same envelope shape as existing entries in `manifest.json`. |

No `[NEEDS CLARIFICATION]` markers remain.
