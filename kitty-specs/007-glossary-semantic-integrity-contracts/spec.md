# Feature Specification: Glossary Semantic Integrity Contracts

**Feature Branch**: `007-glossary-semantic-integrity-contracts`
**Created**: 2026-02-16
**Status**: Draft
**Target Branch**: `2.x`
**Input**: Sprint S2 kickoff prompt — glossary semantic integrity event contracts for `spec-kitty-events`

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Typed Glossary Event Contracts (Priority: P1)

As a downstream consumer (CLI runtime or SaaS projection), I can import typed glossary semantic integrity events with validated payloads so that I can build glossary-aware features against well-defined contracts without ambiguity.

**Why this priority**: Without typed event contracts, no other glossary feature can be built. This is the foundation that CLI and SaaS repos depend on.

**Independent Test**: Can be fully tested by importing each event payload model, constructing valid instances, and confirming round-trip serialization — delivers typed contracts consumable by downstream repos.

**Acceptance Scenarios**:

1. **Given** the `spec-kitty-events` package is installed, **When** a consumer imports `GlossaryScopeActivatedPayload`, **Then** the payload model is available with validated fields for scope id, scope type, and glossary version id.
2. **Given** a payload model for any of the 8 glossary event types, **When** constructed with valid data, **Then** it passes validation and serializes to a dictionary that round-trips back to an identical model.
3. **Given** a payload model, **When** constructed with invalid data (missing required fields, wrong types), **Then** validation raises an error immediately — no silent fallback.
4. **Given** all 8 event type constants and their payload models, **When** inspected in the public API, **Then** they are exported from the package top-level `__init__.py`.

---

### User Story 2 — Glossary Evolution Reducer (Priority: P1)

As a system that replays event streams, I can reduce a sequence of glossary events into a deterministic glossary state snapshot so that glossary evolution is fully reconstructable from canonical events alone.

**Why this priority**: Deterministic replay is a hard invariant — without a reducer, the append-only glossary evolution guarantee cannot be verified.

**Independent Test**: Can be fully tested by feeding event sequences into `reduce_glossary_events()` and asserting the output state matches expected glossary snapshots — delivers replay determinism.

**Acceptance Scenarios**:

1. **Given** a sequence of glossary events in any causal-order-preserving permutation, **When** reduced, **Then** the resulting glossary state is identical regardless of input ordering.
2. **Given** a `GlossaryScopeActivated` event followed by `TermCandidateObserved` and `GlossarySenseUpdated` events, **When** reduced, **Then** the state contains the activated scope, observed candidates, and current sense values.
3. **Given** a `GlossaryStrictnessSet` event changing policy from `medium` to `max`, **When** reduced, **Then** the state reflects the latest strictness mode and records the policy transition in history.
4. **Given** duplicate events (same event_id), **When** reduced, **Then** duplicates are discarded and the result is the same as reducing the deduplicated set.
5. **Given** an event referencing a scope that was never activated, **When** reduced in strict mode, **Then** the reducer raises an error. **When** reduced in permissive mode, **Then** the reducer records an anomaly and continues.

---

### User Story 3 — Semantic Check and Generation Gate Contracts (Priority: P1)

As a CLI runtime enforcing glossary policy, I can emit and consume `SemanticCheckEvaluated` and `GenerationBlockedBySemanticConflict` events so that step-level generation gates are auditable and replayable.

**Why this priority**: The hard invariant — high-severity unresolved conflicts block LLM generation — requires these gate events to be well-defined and enforceable.

**Independent Test**: Can be fully tested by constructing check evaluation and block events with varying severity/strictness combinations and asserting correct payload structure — delivers gate contract clarity.

**Acceptance Scenarios**:

1. **Given** a `SemanticCheckEvaluated` event with high severity and `effective_strictness` of `medium` or `max`, **When** the conflict is unresolved, **Then** the payload includes the conflict list, recommended action of `block`, and all fields required by downstream gate enforcement.
2. **Given** a `SemanticCheckEvaluated` event with medium severity, **When** the `effective_strictness` is `medium`, **Then** the recommended action is `warn` and the mission is not blocked.
3. **Given** a `GenerationBlockedBySemanticConflict` event, **When** constructed, **Then** the payload includes the step id, unresolved conflict references, and the blocking policy mode — sufficient for a consumer to identify which term caused the block and why.
4. **Given** `effective_strictness` is `off`, **When** a semantic check runs, **Then** no `SemanticCheckEvaluated` event is emitted (checks are skipped entirely).

---

### User Story 4 — Clarification Lifecycle Contracts (Priority: P2)

As a mission participant (human or LLM), I can observe clarification request and resolution events so that the clarification lifecycle is traceable and the burst cap is enforceable.

**Why this priority**: Clarification contracts are needed for the interactive UX loop but are downstream of the core check/gate contracts.

**Independent Test**: Can be fully tested by constructing request/resolution event pairs and verifying payload completeness and burst-cap fixture behavior — delivers traceable clarification lifecycle.

**Acceptance Scenarios**:

1. **Given** a `GlossaryClarificationRequested` event, **When** constructed, **Then** the payload includes the question text, the ambiguous term, option choices, urgency level, and the step id that triggered the request.
2. **Given** a `GlossaryClarificationResolved` event, **When** constructed, **Then** the payload includes the selected or entered meaning, the resolving actor's identity, and a reference to the originating request event.
3. **Given** 5 pending clarifications ranked by severity, **When** reduced, **Then** the state shows at most 3 active clarification prompts per burst window (the burst cap is observable in reduced state).

---

### User Story 5 — Conformance Fixtures for Block/Warn/Burst Behavior (Priority: P2)

As a test author in a downstream repo (CLI or SaaS), I can import pre-built conformance fixtures that prove glossary gate behavior so that I don't need to construct complex event sequences from scratch.

**Why this priority**: Fixtures accelerate downstream testing and serve as living documentation of expected behavior. They depend on the typed events and reducer being complete first.

**Independent Test**: Can be fully tested by loading each fixture, reducing it through the glossary reducer, and asserting the documented outcome — delivers reusable test data for downstream repos.

**Acceptance Scenarios**:

1. **Given** the "high-severity unresolved conflict blocks generation" fixture, **When** reduced, **Then** the state contains a `GenerationBlockedBySemanticConflict` event and the glossary state shows an unresolved blocking conflict.
2. **Given** the "medium-severity conflict warns and continues" fixture, **When** reduced, **Then** the state contains a warning-level `SemanticCheckEvaluated` event and no generation block.
3. **Given** the "clarification burst cap at 3" fixture, **When** reduced, **Then** the state shows exactly 3 active clarification prompts despite more than 3 conflicts being present.

---

### Edge Cases

- What happens when a `GlossarySenseUpdated` event arrives for a term that was never observed via `TermCandidateObserved`? The reducer should record an anomaly (permissive mode) or raise an error (strict mode) — a sense cannot be updated for an unobserved term.
- What happens when `GlossaryStrictnessSet` changes from `max` to `off` mid-mission while unresolved high-severity conflicts exist? The strictness change is recorded; previously emitted block events remain in the log but no new checks or blocks are emitted going forward.
- What happens when two `GlossaryClarificationResolved` events arrive for the same request (concurrent resolution by different actors)? The reducer applies last-write-wins within concurrent groups using the established causal ordering (lamport clock + node_id tiebreak).
- What happens when a `GenerationBlockedBySemanticConflict` event references conflicts that have since been resolved? The block event is historical and immutable; the reducer's current state should reflect the resolved status separately from the historical block record.
- What happens when events arrive for a scope that was never activated? Strict mode raises an error; permissive mode records an orphan-scope anomaly and processes the events.

## Requirements *(mandatory)*

### Functional Requirements

**Event Type Constants and Payload Models**

- **FR-001**: System MUST define 8 event type constants: `GLOSSARY_SCOPE_ACTIVATED`, `TERM_CANDIDATE_OBSERVED`, `SEMANTIC_CHECK_EVALUATED`, `GLOSSARY_CLARIFICATION_REQUESTED`, `GLOSSARY_CLARIFICATION_RESOLVED`, `GLOSSARY_SENSE_UPDATED`, `GENERATION_BLOCKED_BY_SEMANTIC_CONFLICT`, `GLOSSARY_STRICTNESS_SET`.
- **FR-002**: System MUST provide a frozen Pydantic payload model for each event type with validated, typed fields — no opaque dictionaries for glossary event data.
- **FR-003**: All payload models MUST use `ConfigDict(frozen=True)` matching the established immutability pattern in the codebase.

**Payload Contract — Scope**

- **FR-004**: `GlossaryScopeActivatedPayload` MUST include scope id, scope type (one of `spec_kitty_core`, `team_domain`, `audience_domain`, `mission_local`), and glossary version identifier.
- **FR-005**: `GlossaryScopeActivatedPayload` MUST include the mission id linking the scope activation to its mission context.

**Payload Contract — Term Observation and Sense**

- **FR-006**: `TermCandidateObservedPayload` MUST include the term surface text, source step id, actor identity, confidence score, and scope id.
- **FR-007**: `GlossarySenseUpdatedPayload` MUST include the term surface, scope id, before-sense value, after-sense value, reason for change, and actor identity.

**Payload Contract — Semantic Check and Gate**

- **FR-008**: `SemanticCheckEvaluatedPayload` MUST include step id, scope id, severity level, confidence score, conflict list (referencing specific terms), recommended action (`block`, `warn`, or `pass`), and effective strictness mode used for the evaluation.
- **FR-009**: `SemanticCheckEvaluatedPayload` MUST carry mission primitive metadata for the step being checked — no hardcoded step-name assumptions.
- **FR-010**: `GenerationBlockedBySemanticConflictPayload` MUST include the step id, references to unresolved conflicts that caused the block, and the blocking policy mode.

**Payload Contract — Clarification**

- **FR-011**: `GlossaryClarificationRequestedPayload` MUST include the question text, the ambiguous term, available options, urgency level, step id, and scope id.
- **FR-012**: `GlossaryClarificationResolvedPayload` MUST include the selected or entered meaning, the resolving actor's identity, and a reference to the originating clarification request.

**Payload Contract — Strictness Configuration**

- **FR-013**: `GlossaryStrictnessSetPayload` MUST include the mission id, the new strictness mode (`off`, `medium`, `max`), the previous strictness mode (if any), and the actor who set it.

**Payload Contract — Actor Attribution**

- **FR-014**: All payload models that record who performed an action MUST include an actor field sufficient to identify the human or LLM participant.

**Payload Contract — Conflict Classification**

- **FR-015**: Conflict entries within `SemanticCheckEvaluatedPayload` MUST include the conflicting term, the nature of the conflict (overloaded meaning, drift from canonical sense, ambiguous usage), and severity classification.

**Reducer**

- **FR-016**: System MUST provide a `reduce_glossary_events()` function in a standalone `glossary.py` module that produces a deterministic glossary state from an event sequence.
- **FR-017**: The reducer MUST support both strict mode (raises on integrity violations) and permissive mode (records anomalies and continues), matching the dual-mode pattern in the collaboration reducer.
- **FR-018**: The reducer MUST reconstruct: active scopes, current strictness per scope, observed term candidates, current term senses, pending and resolved clarifications, semantic check history, and generation block records.
- **FR-019**: The reducer MUST enforce the clarification burst cap — the reduced state exposes at most 3 active (unresolved) clarification prompts per burst window.
- **FR-020**: The reducer MUST produce identical output for any causal-order-preserving permutation of the same event set (determinism invariant).
- **FR-021**: The reducer MUST reuse `dedup_events()` from the existing codebase for event deduplication.

**Conformance Fixtures**

- **FR-022**: System MUST provide a conformance fixture proving that an unresolved high-severity conflict produces a generation block event.
- **FR-023**: System MUST provide a conformance fixture proving that a medium-severity conflict produces a warning without blocking generation.
- **FR-024**: System MUST provide a conformance fixture proving that the clarification burst cap limits active prompts to 3.

**Exports and API Surface**

- **FR-025**: All 8 event type constants, all payload models, the reducer function, and the reduced state model MUST be exported from the package `__init__.py`.

**Hard Invariants**

- **FR-026**: High-severity unresolved semantic conflicts MUST result in a `GenerationBlockedBySemanticConflict` event in the canonical event path — there is no alternative logging or side-channel mechanism.
- **FR-027**: All glossary state MUST be reconstructable from the canonical event stream using `reduce_glossary_events()` — no parallel logging subsystem.
- **FR-028**: Event payload contracts MUST reference mission steps via primitive metadata fields, not hardcoded step-name strings.

### Key Entities

- **GlossaryScope**: A bounded semantic context (e.g., `spec_kitty_core`, `mission_local`) within which terms have authoritative meanings. Identified by scope id and type. Has an associated glossary version and strictness mode.
- **TermCandidate**: A raw term surface observed in mission input, linked to a scope, step, and actor. Carries a confidence score indicating certainty of relevance.
- **TermSense**: The context-specific meaning of a term within a scope. Tracks before/after values when updated, with reason and actor attribution.
- **SemanticConflict**: A mismatch or ambiguity detected during a semantic check. Classified by conflict nature (overloaded, drift, ambiguous), severity, and the specific term involved.
- **ClarificationPrompt**: A targeted question emitted when conflict severity and confidence policy require human input. Linked to a specific term, scope, and step. Subject to a burst cap of 3 per evaluation window.
- **GlossaryStrictness**: Policy mode (`off`, `medium`, `max`) controlling the warning/block behavior threshold for a scope within a mission.
- **GlossaryAnomalyRecord**: A non-fatal integrity issue recorded by the reducer in permissive mode (e.g., sense update for unobserved term, event for unactivated scope).
- **ReducedGlossaryState**: The projected glossary state produced by the reducer — containing active scopes, strictness settings, term senses, pending clarifications, check history, and block records.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Replaying any valid glossary event sequence through the reducer produces identical state regardless of causal-order-preserving input permutation (100% determinism across all test orderings).
- **SC-002**: All 8 event types have typed payload contracts that reject invalid data on construction — no event can be created with missing or wrongly-typed required fields.
- **SC-003**: Downstream consumers (CLI and SaaS) can import and use glossary event contracts without ambiguity — every payload field has a clear type, every event type has a named constant.
- **SC-004**: Conformance fixtures prove all three gate behaviors: high-severity block, medium-severity warn, and clarification burst cap at 3 — each fixture is self-contained and passes when reduced.
- **SC-005**: The reducer correctly reconstructs the full glossary evolution timeline from events alone — no external state or side-channel data is required.
- **SC-006**: Strictness modes (`off`, `medium`, `max`) are cleanly represented in event payloads and the reducer differentiates behavior based on effective strictness.

## Assumptions

- Mission primitives in 2.x carry configurable metadata that step-level events can reference without hardcoding step names.
- The `2.x` branch will be cut from the current `main` baseline before feature work begins.
- The existing `dedup_events()` function from `status.py` is reusable for glossary event deduplication without modification.
- Actor identity fields in glossary payloads follow the same `str` pattern used in lifecycle and collaboration payloads (not the full `ParticipantIdentity` model, which belongs to the collaboration domain).
- Confidence scores are numeric (float, 0.0–1.0 range) and severity levels use a constrained string or enum (`low`, `medium`, `high`).
- The clarification burst cap of 3 is a per-evaluation-window limit, not a global lifetime cap.

## Dependencies

- Existing `spec-kitty-events` infrastructure: `Event` model, `dedup_events()`, causal ordering utilities, storage abstractions.
- Branch `2.x` must be established before implementation begins.
- No external package dependencies beyond what `spec-kitty-events` already declares.

## Non-Goals

- Cross-tool glossary synchronization (Jira/Confluence/Figma connectors).
- Approval workflow contracts.
- External glossary import/export.
- CLI runtime implementation of glossary checking (belongs to `spec-kitty` repo).
- SaaS projection of glossary dashboards (belongs to `spec-kitty-saas` repo).
