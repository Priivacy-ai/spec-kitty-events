# Research: Canonical Event Contract Consolidation

**Feature**: 004-canonical-event-contract
**Date**: 2026-02-09

## R1: Event Envelope Extension — Required vs Optional Fields

**Decision**: `correlation_id` is required (no default), `schema_version` defaults to "1.0.0", `data_tier` defaults to 0.

**Rationale**: Every event belongs to a mission execution context, so correlation_id must always be present. Making it optional would create events that can't be traced to their mission, defeating the purpose of the convergence architecture. Since this is pre-1.0 (alpha), breaking changes are acceptable.

**Alternatives considered**:
- Make correlation_id optional with None default — rejected because it undermines the single-source-of-truth guarantee
- Make all three fields required — rejected because schema_version and data_tier have sensible defaults

## R2: Lifecycle Reducer Composition vs Standalone

**Decision**: The lifecycle reducer delegates WP-level reduction to the existing `reduce_status_events()` from Feature 003 rather than reimplementing WP reduction.

**Rationale**: Feature 003's reducer is battle-tested with property tests proving determinism across permutations. Reimplementing would duplicate ~200 LOC of complex concurrent-group handling logic and risk subtle inconsistencies.

**Alternatives considered**:
- Standalone reducer that handles both mission and WP events — rejected due to duplication
- Inheritance-based reducer hierarchy — rejected due to unnecessary complexity for two levels

## R3: Cancel-Beats-Re-Open Implementation Strategy

**Decision**: Within concurrent event groups (same Lamport clock), apply MissionCancelled events last so they overwrite any concurrent re-activation.

**Rationale**: This mirrors the rollback-aware precedence already implemented in Feature 003's reducer (where reviewer rollbacks apply last within concurrent groups). Using the same pattern ensures consistency.

**Alternatives considered**:
- Priority field on events — rejected as over-engineering; only one precedence rule exists at mission level
- Pre-filter before grouping — rejected because it would require two passes through the event list

## R4: Mission Terminal States

**Decision**: COMPLETED and CANCELLED are terminal. Events targeting a mission in terminal state are flagged as anomalies but do not halt the reducer.

**Rationale**: Matches the terminal-lane pattern from Feature 003 (DONE and CANCELED are terminal lanes). Non-fatal anomaly flagging allows audit trail analysis without crashing consumers.

**Alternatives considered**:
- Raise exception on terminal state violation — rejected because reducers should never halt on bad data
- Silently ignore — rejected because anomaly tracking is essential for observability

## R5: Event Type Constants

**Decision**: Define string constants for all lifecycle event types (MISSION_STARTED, MISSION_COMPLETED, MISSION_CANCELLED, PHASE_ENTERED, REVIEW_ROLLBACK) alongside the existing WP_STATUS_CHANGED from Feature 003.

**Rationale**: String constants prevent typos and enable IDE autocompletion. The existing WP_STATUS_CHANGED constant from Feature 003 established this pattern.

**Alternatives considered**:
- Enum for event types — rejected because event_type is a str field on Event; string constants are simpler
- No constants (raw strings) — rejected because this is error-prone and inconsistent with Feature 003
