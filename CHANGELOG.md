# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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

[Unreleased]: https://github.com/robertDouglass/spec-kitty-events/compare/v0.1.0-alpha...HEAD
[0.1.0-alpha]: https://github.com/robertDouglass/spec-kitty-events/releases/tag/v0.1.0-alpha
