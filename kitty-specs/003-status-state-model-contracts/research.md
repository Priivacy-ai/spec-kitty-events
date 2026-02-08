# Research: Status State Model Contracts

**Feature**: 003-status-state-model-contracts
**Date**: 2026-02-08
**Status**: Complete

## R1: Lane Enum Implementation for Python 3.10

**Decision**: Use `class Lane(str, Enum)` pattern.

**Rationale**: `StrEnum` is Python 3.11+ only. The `(str, Enum)` pattern is the standard approach for string-valued enums in Python 3.10. It provides `Lane.PLANNED == "planned"` and allows direct string comparison, which is essential for consumers who may pass raw strings.

**Alternatives considered**:
- `StrEnum` — Python 3.11+ only, violates `requires-python = ">=3.10"`
- `Literal` union — no enumeration/iteration support, poor for transition matrix
- `str` constants — no type safety, no validation on construction

## R2: Transition Validation Return Type

**Decision**: Return a frozen dataclass `TransitionValidationResult(valid: bool, violations: Tuple[str, ...])` rather than raising exceptions.

**Rationale**: Consumers need to check transitions *before* attempting them (pre-flight validation). Returning a result object is idiomatic for pure validation functions and avoids exception-driven flow control. This aligns with the engineering alignment note: "Pure function, returns typed result (not exceptions for flow control)."

**Exceptions still used for**: Model-level validation (unknown lane names, missing required fields) via Pydantic validators and `normalize_lane()`, consistent with existing `ValidationError` patterns in `models.py` and `gates.py`.

**Alternatives considered**:
- Raise `TransitionError` — exception-driven flow control, poor DX for pre-flight checks
- Return `Optional[str]` (None=valid, str=error) — loses ability to report multiple violations

## R3: StatusTransitionPayload and Event.payload Relationship

**Decision**: `StatusTransitionPayload` is a standalone frozen model. Consumers serialize it into `Event.payload` (dict) when constructing events, and deserialize it back when processing.

**Rationale**: The existing `Event.payload` is `Dict[str, Any]` — an opaque bag. The library establishes the *contract* for what goes in that bag when `event_type="WPStatusChanged"`. The reducer internally deserializes `Event.payload` → `StatusTransitionPayload` during replay.

**Key implication**: The sort/dedup/reduce functions operate on `Event` objects (which carry `lamport_clock`, `timestamp`, `event_id`), not bare payloads. The reducer extracts `StatusTransitionPayload` from `Event.payload` internally.

## R4: Sort Key Design — Divergence from Existing total_order_key

**Decision**: New `status_event_sort_key(event: Event) -> Tuple[int, str, str]` returns `(lamport_clock, timestamp_isoformat, event_id)`.

**Rationale**: The PRD specifies sort by `(logical_clock, at, event_id)`. The existing `total_order_key` uses `(lamport_clock, node_id)` — a different tiebreaker. For status events, `event_id` (ULID, which embeds timestamp) provides better determinism than `node_id` because it's globally unique per event, not per node.

**Coexistence**: Both functions remain available. `total_order_key` for generic Event ordering, `status_event_sort_key` for status-specific canonical ordering. No collision.

## R5: Rollback-Aware Precedence in Reducer

**Decision**: When concurrent events exist for the same WP at the same lamport_clock, and one is a reviewer rollback (`for_review -> in_progress` with `review_ref`), the rollback wins regardless of sort position.

**Rationale**: PRD Section 9.2 states: "explicit reviewer rollback outranks concurrent forward lane progression." This is a domain rule, not a sort-order rule. The reducer applies it as a post-sort precedence check within each lamport_clock tier.

**Implementation approach**: After sorting, group events by `(wp_id, lamport_clock)`. Within each group, if any event is a reviewer rollback, apply it last (overriding concurrent forward moves).

## R6: Canceled Lane — Terminal Semantics

**Decision**: `canceled` is terminal (like `done`) unless forced. Both terminal lanes require `force=True` + `actor` + `reason` for rollback.

**Rationale**: The PRD says `done` is terminal unless forced (Section 7.2) and `any (except done) -> canceled` (Section 7.2 rule 9). By analogy, `canceled` should also be terminal — once canceled, a WP shouldn't silently un-cancel.

**Not explicitly in PRD**: The PRD doesn't state `canceled` terminality explicitly. This is documented as an assumption in the spec. If consumers need `canceled -> planned` without force, the transition matrix can be relaxed in a future release.

## R7: ForceMetadata as Separate Model

**Decision**: Define `ForceMetadata` as a standalone frozen model *in addition to* the flat fields on `StatusTransitionPayload`.

**Rationale**: `StatusTransitionPayload` carries `force`, `reason` as flat fields because they're contextual to the transition. `ForceMetadata` is a convenience type that consumers can construct and pass around independently (e.g., for audit logging, policy evaluation). The validator extracts force semantics from the payload's flat fields; `ForceMetadata` is an optional structuring aid.

## R8: New Exception Type — TransitionError

**Decision**: Add `TransitionError(SpecKittyEventsError)` for cases where code *attempts* an invalid transition (as opposed to pre-flight validation which returns `TransitionValidationResult`).

**Rationale**: Two validation surfaces exist:
1. Pre-flight: `validate_transition(payload) -> TransitionValidationResult` — returns result, no exception
2. At-construction: Pydantic model validators raise `pydantic.ValidationError` for structural issues
3. Programmatic guard: If the reducer encounters an invalid transition, it records a `TransitionAnomaly` rather than raising

`TransitionError` is available for consumers who want to raise on invalid transitions in their own code (e.g., `if not result.valid: raise TransitionError(result.violations)`). The library provides it but doesn't raise it internally in the reducer.
