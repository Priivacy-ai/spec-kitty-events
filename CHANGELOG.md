# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.3.0-alpha] - 2026-02-08

### Added

**Status State Model Contracts** — New `status.py` module establishing the library as the
shared contract authority for feature/WP status lifecycle events.

#### Enums
- `Lane` — 7 canonical status lanes: planned, claimed, in_progress, for_review, done, blocked, canceled
- `ExecutionMode` — worktree | direct_repo execution context

#### Evidence Models
- `RepoEvidence` — Repository contribution evidence (repo, branch, commit, files_touched)
- `VerificationEntry` — Test/verification execution record (command, result, summary)
- `ReviewVerdict` — Reviewer identity and verdict (reviewer, verdict, reference)
- `DoneEvidence` — Composite evidence required for done transitions

#### Transition Models
- `ForceMetadata` — Actor and reason for forced transitions
- `StatusTransitionPayload` — Immutable payload for lane transitions with cross-field validation

#### Validation
- `TransitionValidationResult` — Result type for transition validation (valid, violations)
- `validate_transition()` — Pre-flight transition legality check against PRD state machine
- `TransitionError` — Exception for consumers who want to raise on invalid transitions

#### Ordering and Reduction
- `status_event_sort_key()` — Deterministic sort key: (lamport_clock, timestamp, event_id)
- `dedup_events()` — Remove duplicate events by event_id
- `reduce_status_events()` — Pure reference reducer with rollback-aware precedence
- `WPState` — Per-WP reduced state (current_lane, last_event_id, evidence)
- `TransitionAnomaly` — Record of invalid transition encountered during reduction
- `ReducedStatus` — Reducer output (wp_states, anomalies, event_count)

#### Constants
- `TERMINAL_LANES` — frozenset of terminal lanes (done, canceled)
- `LANE_ALIASES` — Legacy alias map (doing -> in_progress)
- `WP_STATUS_CHANGED` — Canonical event_type string

### Key Features
- **Lane alias normalization**: Legacy `doing` accepted on input, normalized to `in_progress`
- **Data-driven transition matrix**: All legal transitions encoded as data, not branching logic
- **Rollback-aware reducer**: Reviewer rollback outranks concurrent forward progression
- **Pure functions**: Reducer has no I/O, no side effects, deterministic output

### Backward Compatibility
- Zero changes to existing modules or exports
- All v0.2.0 tests pass without modification
- 21 new exports added alongside existing 37 (total: 58)

### Graduation Criteria (alpha → stable)
- 2+ consumers integrated (spec-kitty CLI and spec-kitty-saas)
- All property tests green for 30+ days in CI
- No breaking API changes needed after consumer integration
- Transition matrix validated against real-world workflow data

## [0.2.0-alpha] - 2026-02-07

### Added
- `GatePayloadBase` — shared Pydantic base model for CI gate outcome event payloads (frozen, validated)
- `GatePassedPayload(GatePayloadBase)` — typed payload for successful gate conclusions (`success`)
- `GateFailedPayload(GatePayloadBase)` — typed payload for failed gate conclusions (`failure`, `timed_out`, `cancelled`, `action_required`)
- `map_check_run_conclusion(conclusion, on_ignored=None)` — deterministic mapping from GitHub `check_run` conclusion strings to event type strings (`"GatePassed"`, `"GateFailed"`, or `None` for ignored)
- `UnknownConclusionError(SpecKittyEventsError)` — raised for unrecognized conclusion values
- Ignored conclusions (`neutral`, `skipped`, `stale`) logged via `logging.getLogger("spec_kitty_events.gates")` with optional `on_ignored` callback
- All new types exported from `spec_kitty_events` package public API
- Unit tests for payload model validation, field constraints, and serialization round-trips
- Hypothesis property tests for mapping determinism and exhaustiveness

## [0.1.1-alpha] - 2026-02-07

### Added
- `project_uuid` field on `Event` model (required, `uuid.UUID` type)
- `project_slug` field on `Event` model (optional, `str` type, defaults to `None`)

### Changed
- `Event` now requires `project_uuid` in all constructors (breaking change from 0.1.0-alpha)
- `to_dict()` / `from_dict()` include project identity fields
- `__repr__()` displays truncated project UUID

### Breaking Changes
- All `Event()` constructors must now include `project_uuid` parameter
- This is a coordinated release with spec-kitty CLI and spec-kitty-saas

## [0.1.0-alpha] - 2026-01-27

### Added

**Core Features**:
- Lamport logical clocks with `LamportClock` class
  - `tick()`: Increment clock for local events
  - `update(remote_clock)`: Synchronize with remote events
  - `current()`: Get clock value without incrementing
- Immutable `Event` model with causal metadata (Pydantic frozen)
  - ULID event_id (26 characters, time-sortable)
  - lamport_clock, node_id, causation_id, timestamp
  - Opaque payload (dict)
- Conflict detection with `is_concurrent(e1, e2)`
- Deterministic total ordering with `total_order_key(event)`
- Topological sorting by causation with `topological_sort(events)`

**Merge Functions**:
- CRDT merge for grow-only sets: `merge_gset(events)`
- CRDT merge for counters: `merge_counter(events)` (with deduplication)
- State-machine merge: `state_machine_merge(events, priority_map)`
  - Priority-based winner selection
  - Deterministic tiebreaker by node_id

**Error Logging**:
- `ErrorLog` class with append-only semantics
- `ErrorEntry` model (timestamp, action_attempted, error_message, resolution, agent)
- Retention policy (configurable max entries, FIFO eviction)

**Storage Adapters**:
- Abstract base classes: `EventStore`, `ClockStorage`, `ErrorStorage`
- In-memory implementations for testing:
  - `InMemoryEventStore` (idempotent save)
  - `InMemoryClockStorage` (initial value 0)
  - `InMemoryErrorStorage` (retention policy enforced)

**Type Safety**:
- mypy --strict compliance (zero errors)
- py.typed marker for PEP 561
- Comprehensive type hints (parameters, return types, variables)

**Testing**:
- 90%+ code coverage (pytest + pytest-cov)
- Property-based testing (Hypothesis) for CRDT laws and determinism
- Integration tests for event emission, conflict resolution, adapters
- Quickstart validation tests

### Changed
- N/A (initial release)

### Deprecated
- N/A (initial release)

### Removed
- N/A (initial release)

### Fixed
- N/A (initial release)

### Security
- N/A (initial release)

---

[Unreleased]: https://github.com/Priivacy-ai/spec-kitty-events/compare/v0.3.0-alpha...HEAD
[0.3.0-alpha]: https://github.com/Priivacy-ai/spec-kitty-events/compare/v0.2.0-alpha...v0.3.0-alpha
[0.2.0-alpha]: https://github.com/Priivacy-ai/spec-kitty-events/compare/v0.1.1-alpha...v0.2.0-alpha
[0.1.1-alpha]: https://github.com/Priivacy-ai/spec-kitty-events/compare/v0.1.0-alpha...v0.1.1-alpha
[0.1.0-alpha]: https://github.com/Priivacy-ai/spec-kitty-events/releases/tag/v0.1.0-alpha
