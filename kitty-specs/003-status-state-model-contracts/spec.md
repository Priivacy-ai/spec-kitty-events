# Feature Specification: Status State Model Contracts

**Feature Branch**: `003-status-state-model-contracts`
**Created**: 2026-02-08
**Status**: Draft
**Input**: PRD: Feature Status State Model Remediation (Combined v2)

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Emit a Valid Status Transition Event (Priority: P1)

A consumer (CLI agent or SaaS service) constructs a status transition event to record that a work package moved from one lane to another. The library validates the transition is legal, normalizes any legacy lane aliases, and produces an immutable event payload ready for append to a canonical log.

**Why this priority**: This is the foundational contract — every other capability (reduction, validation, ordering) depends on well-formed status events existing first.

**Independent Test**: Can be fully tested by constructing `StatusTransitionPayload` instances with various lane combinations and verifying validation accepts legal transitions and rejects illegal ones.

**Acceptance Scenarios**:

1. **Given** a work package in lane `planned`, **When** a consumer creates a transition event to `claimed` with a valid actor, **Then** the library produces a frozen, serializable payload with canonical lane values.
2. **Given** a transition from `in_progress` to `done`, **When** the event lacks required `done` evidence, **Then** the library raises a validation error before the event can be created.
3. **Given** a consumer passes `doing` as the source lane, **When** the payload is constructed, **Then** the library normalizes it to `in_progress` and emits canonical values only.
4. **Given** a forced transition that bypasses normal guards, **When** `force=True` but `reason` or `actor` is missing, **Then** the library raises a validation error.

---

### User Story 2 - Validate Transition Legality (Priority: P1)

A consumer checks whether a proposed lane transition is allowed under the state machine rules before attempting it. The library provides a reusable validator that encodes the full transition matrix, guard conditions, and force-override semantics.

**Why this priority**: Transition validation is the core safety mechanism preventing invalid state corruption — it must ship alongside the event models.

**Independent Test**: Can be tested by calling the transition validator with every combination of (from_lane, to_lane, metadata) and verifying the matrix matches the PRD specification.

**Acceptance Scenarios**:

1. **Given** the transition `planned -> claimed`, **When** an actor is provided, **Then** the validator returns success.
2. **Given** the transition `done -> planned`, **When** `force=False`, **Then** the validator rejects the transition (done is terminal without force).
3. **Given** the transition `done -> in_progress`, **When** `force=True` with actor and reason, **Then** the validator accepts the forced rollback.
4. **Given** the transition `for_review -> in_progress`, **When** no `review_ref` is provided, **Then** the validator rejects the transition (review feedback reference required).
5. **Given** any lane transitioning to `blocked`, **When** valid metadata is provided, **Then** the validator accepts (any non-terminal lane can transition to blocked).

---

### User Story 3 - Deterministic Event Ordering and Deduplication (Priority: P2)

A consumer merges status event logs from multiple sources (e.g., after a git merge of concurrent branches). The library provides sort and deduplication primitives that produce a deterministic, canonical ordering regardless of input order.

**Why this priority**: Deterministic ordering is essential for consistent state reconstruction across distributed consumers, but depends on the event models from P1.

**Independent Test**: Can be tested by shuffling event lists and verifying that sort+dedup always produces the same canonical order, and that duplicate event_ids are collapsed.

**Acceptance Scenarios**:

1. **Given** two event lists with overlapping events, **When** concatenated and passed through dedup, **Then** each `event_id` appears exactly once.
2. **Given** events with different `lamport_clock` values, **When** sorted, **Then** lower clock values appear first.
3. **Given** events with identical `lamport_clock` values, **When** sorted, **Then** ties are broken by `timestamp`, then by `event_id` (lexicographic), producing a stable total order.
4. **Given** the same set of events in any permutation, **When** sorted, **Then** the output order is identical every time.

---

### User Story 4 - Reduce Events to Current State (Priority: P2)

A consumer replays a sorted, deduplicated event log through the reference reducer to obtain the current lane state for every work package in a feature. The reducer is pure logic with no file I/O.

**Why this priority**: The reducer is the central contract for deterministic state reconstruction — consumers rely on it for canonical truth.

**Independent Test**: Can be tested by feeding known event sequences to the reducer and asserting the output state matches expectations, including rollback-aware precedence.

**Acceptance Scenarios**:

1. **Given** a sequence of events moving WP01 through `planned -> claimed -> in_progress -> for_review -> done`, **When** reduced, **Then** the output shows WP01 in lane `done` with the done evidence attached.
2. **Given** concurrent events where one moves WP01 to `done` and another rolls it back from `for_review -> in_progress` with a `review_ref`, **When** reduced, **Then** the reviewer rollback takes precedence (rollback-aware resolution).
3. **Given** an empty event list, **When** reduced, **Then** the output is an empty state with no errors.
4. **Given** events containing an illegal transition (e.g., `planned -> done` without force), **When** reduced, **Then** the reducer flags the invalid transition in its output rather than silently accepting it.

---

### User Story 5 - Done Evidence Contracts (Priority: P2)

A consumer records completion evidence when moving a work package to `done`. The library provides typed models for repository evidence, verification results, and review verdicts that are validated on construction.

**Why this priority**: Evidence-backed completion is a key remediation goal — without it, `done` status lacks auditability.

**Independent Test**: Can be tested by constructing `DoneEvidence` payloads with various combinations of repos, verifications, and review data, verifying required fields are enforced.

**Acceptance Scenarios**:

1. **Given** a transition to `done`, **When** evidence includes at least one repo reference and a review verdict, **Then** the evidence payload validates successfully.
2. **Given** a `RepoEvidence` entry, **When** `repo`, `branch`, and `commit` are provided, **Then** construction succeeds; `files_touched` is optional.
3. **Given** a `VerificationEntry`, **When** `command` and `result` are provided, **Then** construction succeeds; `summary` is optional.
4. **Given** a `ReviewVerdict`, **When** `reviewer` and `verdict` are provided but `reference` is missing, **Then** construction succeeds (reference is optional but recommended).

---

### User Story 6 - Backward Compatibility with Existing Events (Priority: P3)

Existing consumers using `Event`, `GatePassedPayload`, `GateFailedPayload`, and all other v0.2.0 exports continue to work without any changes. The new status contracts are purely additive.

**Why this priority**: Non-regression is essential but lower priority because it's a constraint rather than new functionality.

**Independent Test**: Can be tested by running the full existing test suite unchanged and verifying zero failures.

**Acceptance Scenarios**:

1. **Given** the existing `Event` model, **When** constructed with v0.2.0 parameters, **Then** it behaves identically to before.
2. **Given** the existing 37 public exports, **When** imported from `spec_kitty_events`, **Then** all are still available and unchanged.
3. **Given** the existing gate contracts, **When** used with `map_check_run_conclusion()`, **Then** behavior is identical.

---

### Edge Cases

- What happens when a consumer passes an unrecognized lane name (not canonical, not a known alias)? The library raises a `ValidationError` immediately — no silent coercion.
- What happens when a forced transition to `done` is attempted? Force + done requires both force metadata (actor, reason) AND done evidence — both validation layers apply.
- What happens when events arrive with timestamps in the future? Timestamps are recorded as-is; ordering relies on lamport_clock as primary key, not wall-clock time.
- What happens when the reducer encounters a gap in the transition sequence (e.g., events for WP01 jump from `planned` to `for_review`)? The reducer flags this as an invalid transition in its output; it does not halt, but the reduced state indicates the anomaly.
- What happens when `from_lane` is `None` (initial event for a new WP)? The library treats `None -> planned` as the only valid initial transition. Any other initial target lane requires force.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Library MUST define a `Lane` enumeration with 7 canonical values: `planned`, `claimed`, `in_progress`, `for_review`, `done`, `blocked`, `canceled`.
- **FR-002**: Library MUST accept legacy lane aliases on input (at minimum `doing -> in_progress`) and normalize to canonical values; output MUST use canonical values only.
- **FR-003**: Library MUST raise `ValidationError` for unrecognized lane names (neither canonical nor known alias).
- **FR-004**: Library MUST define a `StatusTransitionPayload` as a frozen Pydantic v2 model containing: `feature_slug`, `wp_id`, `from_lane` (Optional[Lane]), `to_lane` (Lane), `actor` (str), `force` (bool, default False), `reason` (optional str, required when force=True), `execution_mode` (ExecutionMode), `review_ref` (optional str, required for review rollback), `evidence` (optional DoneEvidence, required for transition to done).
- **FR-005**: Library MUST define `DoneEvidence` as a frozen model containing: `repos` (list of `RepoEvidence`), `verification` (list of `VerificationEntry`), `review` (`ReviewVerdict`).
- **FR-006**: Library MUST define `RepoEvidence` containing: `repo` (str), `branch` (str), `commit` (str), `files_touched` (optional list of str).
- **FR-007**: Library MUST define `VerificationEntry` containing: `command` (str), `result` (str), `summary` (optional str).
- **FR-008**: Library MUST define `ReviewVerdict` containing: `reviewer` (str), `verdict` (str), `reference` (optional str).
- **FR-009**: Library MUST define a `ForceMetadata` model containing: `force` (bool), `actor` (str), `reason` (str) — all required when force is True.
- **FR-010**: Library MUST define an `ExecutionMode` enumeration with values `worktree` and `direct_repo`.
- **FR-011**: Library MUST provide a `validate_transition(from_lane, to_lane, payload)` function that returns success or a typed error, encoding the full PRD transition matrix.
- **FR-012**: Library MUST enforce guard conditions: `planned -> claimed` requires actor; `in_progress -> for_review` requires subtask evidence or force; `for_review -> done` requires review evidence; `for_review -> in_progress` requires review_ref; all forced transitions require actor + reason.
- **FR-013**: Library MUST treat `done` as terminal unless a forced rollback is applied.
- **FR-014**: Library MUST provide a `status_event_sort_key()` function that produces a deterministic total-order key from `(lamport_clock, timestamp, event_id)`.
- **FR-015**: Library MUST provide a `dedup_events()` function that removes duplicate events by `event_id`, preserving the first occurrence in sorted order.
- **FR-016**: Library MUST provide a pure `reduce_status_events(events) -> ReducedStatus` function that replays a sorted event list into per-WP current lane state.
- **FR-017**: The reducer MUST apply rollback-aware precedence: explicit reviewer rollback (`for_review -> in_progress` with `review_ref`) outranks concurrent forward progression.
- **FR-018**: The reducer MUST flag invalid transitions encountered during replay rather than silently accepting them.
- **FR-019**: Library MUST treat `None -> planned` as the only valid initial transition for a new WP; any other initial target requires force.
- **FR-020**: All new models MUST be frozen (immutable) using Pydantic `ConfigDict(frozen=True)`, matching existing library patterns.
- **FR-021**: All new models MUST support round-trip serialization (dict/JSON).
- **FR-022**: All new public symbols MUST be exported from `spec_kitty_events.__init__`.
- **FR-023**: Library MUST pass `mypy --strict` with Python 3.10 target.
- **FR-024**: Library MUST maintain 100% backward compatibility with all existing v0.2.0 exports and behaviors.

### Key Entities

- **Lane**: Enumeration of 7 canonical status lanes with alias normalization.
- **StatusTransitionPayload**: Immutable event payload capturing a single lane transition with all associated metadata.
- **DoneEvidence**: Composite evidence record required for `done` transitions, containing repo refs, verification results, and review verdict.
- **RepoEvidence**: A single repository's contribution to a done transition (repo, branch, commit, optional files).
- **VerificationEntry**: A single test/verification execution record (command, result, optional summary).
- **ReviewVerdict**: Reviewer identity, verdict, and optional reference to the review artifact.
- **ForceMetadata**: Actor and reason metadata required for forced transitions.
- **ExecutionMode**: Enum distinguishing `worktree` vs `direct_repo` execution contexts.
- **ReducedStatus**: Output of the reference reducer — per-WP current lane state with optional anomaly flags.
- **TransitionMatrix**: The encoded set of legal (from_lane, to_lane) pairs with guard conditions.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: All 24 functional requirements are implemented and covered by at least one passing test each.
- **SC-002**: The transition validator correctly accepts all 9 legal default transitions and rejects all illegal combinations (full matrix coverage).
- **SC-003**: The reference reducer produces identical output for any permutation of the same event set (determinism property test).
- **SC-004**: Deduplication removes 100% of duplicate `event_id` entries while preserving canonical order (property test).
- **SC-005**: Legacy alias normalization maps `doing` to `in_progress` transparently — consumers using `doing` see no validation errors.
- **SC-006**: All existing v0.2.0 tests pass without modification (zero regressions).
- **SC-007**: `mypy --strict` reports zero errors across all new and existing modules.
- **SC-008**: New modules achieve high test coverage (unit + property tests).
- **SC-009**: Consumer integration checklists are provided for both `spec-kitty` (CLI) and `spec-kitty-saas`.

## Assumptions

- The PRD's 7-lane state machine is the correct target model; no additional lanes are anticipated for this release.
- `event_id` values are ULIDs (consistent with existing `Event` model convention).
- The reference reducer does not need thread-safety guarantees — consumers handle concurrency.
- `done` evidence is only required for transitions TO `done`, not for forced rollbacks FROM `done`.
- The `canceled` lane is terminal (like `done`) unless forced.
- Guard conditions for `claimed -> in_progress` ("active workspace context established") are validated by the consumer, not the library — the library only validates that the transition itself is legal.
