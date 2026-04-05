# Feature Specification: Mission Contract Cutover

**Feature Branch**: `014-mission-contract-cutover`
**Created**: 2026-04-05
**Status**: Draft
**Input**: Breaking contract release for mission/build taxonomy in spec-kitty-events

## Problem

The public event contracts in `spec-kitty-events` still expose mission-domain `feature*` terminology, ambiguous mission event names, and an incomplete identity model for individual checkouts. This causes contract drift across repos, makes it unclear whether `MissionCompleted` refers to mission catalog closure or runtime completion, and leaves consumers without a canonical way to distinguish a project checkout identity from the causal emitter identity used for Lamport ordering.

Without a hard cutover to canonical mission/build terminology and a named published release artifact that identifies the cutover contract version plus its forbidden legacy surface set, downstream consumers can continue to emit or accept incompatible payloads, creating mixed-version operation that is difficult to detect and unsafe to roll out.

## Goals

- Publish the canonical breaking contract release for `spec-kitty-events` using mission/build terminology.
- Replace mission-domain public payload fields `feature_slug` and `feature_number` with `mission_slug` and `mission_number`.
- Replace mission-domain public `mission_key` usage with `mission_type` wherever it identifies the mission workflow/template kind.
- Define `MissionCreated` and `MissionClosed` as the canonical mission catalog record events.
- Preserve one meaning per event name by keeping `MissionCompleted` lifecycle-only and `MissionRunCompleted` runtime-only.
- Add `build_id` as the canonical checkout identity while keeping `node_id` as a separate required causal ordering field.
- Regenerate canonical schemas, fixtures, validators, and documentation for the new contract version.
- Publish a named cutover contract artifact that defines the released contract-version signal and forbidden legacy surface set for downstream rejection gates.
- Make the release explicitly non-shippable until consuming repos are ready for the same contract version and reject mixed-version operation.

## Non-goals

- Implement consumer-side contract migration work inside `spec-kitty-saas`.
- Implement CLI emission changes inside `spec-kitty`.
- Preserve long-lived compatibility aliases, bridges, or dual-write behavior between old and new mission-domain terms.
- Rename unrelated concepts that legitimately use the word `feature`, such as feature flags.
- Expand the scope beyond contract taxonomy, event identity semantics, and release-readiness requirements tied to this cutover.

## User Scenarios & Testing

### User Story 1 - Canonical Mission Catalog Contracts (Priority: P1)

A downstream consumer reads mission catalog events from `spec-kitty-events` and sees only the canonical mission-domain contract: `mission_slug`, `mission_number`, `mission_type`, `MissionCreated`, and `MissionClosed`. The consumer no longer needs to infer whether a `feature*` field or `MissionCompleted` is meant for catalog state.

**Why this priority**: The release exists to establish one canonical contract vocabulary for mission records. Without this, the cutover does not solve the naming ambiguity.

**Independent Test**: Validate mission catalog payloads and fixtures against the released schemas and confirm they accept canonical mission fields and reject legacy mission-domain `feature*` fields and catalog use of `MissionCompleted`.

**Acceptance Scenarios**:

1. **Given** a mission catalog creation payload, **When** it is validated against the released contract, **Then** it requires canonical mission identifiers and emits `MissionCreated` rather than a legacy catalog event.
2. **Given** a mission catalog closure payload, **When** it is validated against the released contract, **Then** it emits `MissionClosed` and does not reuse `MissionCompleted` for catalog state.
3. **Given** a payload containing `feature_slug`, `feature_number`, or catalog-level `mission_key`, **When** it is validated against the released contract, **Then** validation fails.

---

### User Story 2 - Explicit Build Identity in the Event Envelope (Priority: P1)

A consumer reducing or auditing events can distinguish the identity of the checkout that produced an event from the causal emitter identity used for Lamport ordering. The event envelope exposes `build_id` as the canonical checkout identity and keeps `node_id` as a separate required field for deterministic ordering and tie-breaking.

**Why this priority**: Project identity and build identity are central to the cutover. Without explicit `build_id`, the contract cannot model one concrete checkout independently from the emitter identity.

**Independent Test**: Validate canonical event envelopes and build registration or heartbeat payloads to confirm they require both `build_id` and `node_id`, and that consumers can distinguish their roles.

**Acceptance Scenarios**:

1. **Given** a canonical event envelope, **When** it is validated, **Then** it requires both `build_id` and `node_id` as separate fields.
2. **Given** an envelope that omits `build_id`, **When** it is validated, **Then** validation fails.
3. **Given** an envelope that treats `node_id` as the build identity, **When** it is validated or documented, **Then** the contract rejects that interpretation and describes `node_id` as causal ordering identity only.

---

### User Story 3 - Mixed-Version Rejection and Release Gating (Priority: P1)

A release manager needs confidence that the contract cutover cannot enter production while one repo still emits legacy mission-domain payloads or another repo still accepts them. This mission owns the canonical breaking contract release in `spec-kitty-events`; downstream consumer rejection behavior and lockstep rollout across consuming repos are required release gates, but not implementation scope for this repository. A client is considered pre-cutover if it emits or accepts a payload that lacks the released contract-version signal or contains any forbidden legacy mission-domain keys or catalog event names.

**Why this priority**: The cutover is explicitly a hard break. If mixed old/new producers and consumers can continue operating, the release contract is unsafe.

**Independent Test**: Review the release documentation and compatibility guidance to confirm they require downstream consumers to enforce a released contract-version gate, reject payloads containing forbidden legacy mission-domain keys or catalog event names, require producers to stop emitting legacy payloads, and block rollout until all three repos are ready for the same contract version.

**Acceptance Scenarios**:

1. **Given** the published release guidance, **When** a consuming repo accepts a payload without the released contract-version signal, **Then** the `spec-kitty-events` release is marked not shippable.
2. **Given** the published release guidance, **When** a consuming repo accepts a payload containing forbidden legacy mission-domain keys or catalog event names, **Then** the payload is classified as pre-cutover and rollout is blocked.
3. **Given** the published release guidance, **When** the CLI repo still emits legacy mission-domain payloads or omits the released contract-version signal, **Then** production rollout is blocked.
4. **Given** all three repos are ready for the same contract version and mixed-version operation is impossible, **When** release readiness is evaluated, **Then** the release may proceed.

---

### User Story 4 - Canonical Mission-Domain Projections and Docs (Priority: P2)

A maintainer using dossier, decisionpoint, mission audit, and related mission-domain projections sees one consistent taxonomy for mission identity, mission type, and build identity across payloads, fixtures, validators, and documentation.

**Why this priority**: Supporting artifacts must match the release contract. If projections or docs keep legacy names, downstream teams cannot reliably adopt the cutover.

**Independent Test**: Validate canonical fixtures, replay data, and public documentation to confirm they consistently use `mission_slug`, `mission_type`, `build_id`, and the mission catalog event names.

**Acceptance Scenarios**:

1. **Given** mission-domain projections and fixtures, **When** they are reviewed, **Then** they use canonical mission/build terminology consistently.
2. **Given** public documentation for mission identity and event semantics, **When** it is reviewed, **Then** it clearly distinguishes `mission_slug` from `mission_type` and `build_id` from `node_id`.
3. **Given** a legacy compatibility example that implies mixed old/new operation is supported, **When** the release docs are reviewed, **Then** that example is absent or explicitly rejected.

---

### Edge Cases

- What happens when a consumer submits canonical mission payload fields but still uses `MissionCompleted` as a catalog terminal event? The contract rejects the payload because the event name meaning is ambiguous and no aliasing is supported.
- What happens when a consumer emits both `build_id` and `node_id` but assigns the same operational meaning to both? The documentation and validation rules must preserve their distinct semantics and reject contracts that collapse them.
- What happens when public contract documentation describes project identity for fresh clones in different SaaS teams or orgs? The documentation must state that project identity is team-scoped rather than globally repo-scoped, while enforcement remains a downstream consumer concern.
- What happens when a release candidate passes local contract validation but a consumer repo has not yet added rejection gates for pre-cutover payloads? The release remains blocked because cross-repo readiness is a ship gate.

## Requirements

### Functional Requirements

| ID | Title | User Story | Priority | Status |
|----|-------|------------|----------|--------|
| FR-001 | Canonical mission identifiers | As a consumer, I want public mission payloads to use `mission_slug` and `mission_number` so that mission records have one canonical identifier vocabulary. | High | Open |
| FR-002 | Canonical mission type field | As a consumer, I want public workflow/template identifiers to use `mission_type` so that mission classification is unambiguous. | High | Open |
| FR-003 | Canonical catalog event names | As a consumer, I want mission catalog record events to use `MissionCreated` and `MissionClosed` so that catalog state is distinct from lifecycle and runtime completion. | High | Open |
| FR-004 | Single meaning per completion event | As a consumer, I want `MissionCompleted` to remain lifecycle-only and `MissionRunCompleted` to remain runtime-only so that each event name has exactly one meaning. | High | Open |
| FR-005 | Canonical build identity | As a consumer, I want every canonical event envelope and build-related contract to include `build_id` so that checkout identity is explicit. | High | Open |
| FR-006 | Separate causal node identity | As a consumer, I want `node_id` to remain a required causal ordering field distinct from `build_id` so that deterministic ordering semantics remain intact. | High | Open |
| FR-007 | Canonical mission-domain projections | As a consumer, I want dossier, decisionpoint, mission audit, and related mission-domain contracts to use canonical mission/build terminology so that downstream projections stay consistent with the released contract. | High | Open |
| FR-008 | Legacy surface removal | As a consumer, I want legacy mission-domain `feature*` and public `mission_key` contract surfaces removed from canonical schemas, fixtures, validators, and docs so that no supported public contract remains ambiguous. | High | Open |
| FR-009 | Major contract release | As a release manager, I want the package version advanced as a breaking release so that consumers can detect the incompatible contract cutover. | High | Open |
| FR-010 | Explicit unsupported mixed-version operation | As a release manager, I want documentation and compatibility guidance to state that mixed old/new clients are unsupported so that teams do not attempt to bridge incompatible contracts. | High | Open |
| FR-011 | External release gate definition | As a release manager, I want the spec to define downstream rejection behavior and lockstep rollout across `spec-kitty-events`, `spec-kitty-saas`, and `spec-kitty` as release gates so that the release cannot ship until all repos are aligned. | High | Open |
| FR-012 | Machine-checkable cutover signal | As a release manager, I want the released contract to define a machine-checkable contract-version signal and a forbidden legacy-key set so that downstream repos can deterministically classify and reject pre-cutover payloads. | High | Open |
| FR-013 | Contract-semantics documentation | As a consumer, I want the published contract documentation to describe team-scoped `Project` identity semantics so that downstream repos can implement consistent reconciliation behavior without this repository claiming ownership of that enforcement. | Medium | Open |

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
|----|-------|-------------|----------|----------|--------|
| NFR-001 | Public contract completeness | 100% of canonical public schemas, fixtures, validators, and docs released by this repository must use canonical mission/build terminology with no remaining public `feature_slug`, `feature_number`, or mission-domain `mission_key` where `mission_type` is intended. | Correctness | High | Open |
| NFR-002 | Event-name exclusivity | 100% of released mission catalog examples, fixtures, and validators must reserve `MissionCompleted` for lifecycle meaning only and reserve `MissionRunCompleted` for runtime meaning only. | Correctness | High | Open |
| NFR-003 | Envelope identity clarity | 100% of released canonical event envelope examples and validators must require both `build_id` and `node_id`, and all public docs must describe their distinct meanings with no conflicting examples. | Correctness | High | Open |
| NFR-004 | Release readiness evidence | Before the release is marked shippable, documented release gates must verify readiness across exactly three repos: `spec-kitty-events`, `spec-kitty-saas`, and `spec-kitty`, with zero allowed mixed-version production paths and 100% rejection of payloads that fail the cutover contract-version gate or contain forbidden legacy mission-domain keys or catalog event names. | Release Governance | High | Open |
| NFR-005 | Regression-free validation | The complete conformance validation, replay-fixture validation, and repository test suite must finish successfully for the release candidate with zero failing checks. | Quality | High | Open |

### Constraints

| ID | Title | Constraint | Category | Priority | Status |
|----|-------|------------|----------|----------|--------|
| C-001 | Repository implementation boundary | Implementation work for this mission is limited to `spec-kitty-events`. Consumer changes in `spec-kitty-saas` and producer changes in `spec-kitty` are release dependencies, not implementation scope for this repository. | Scope | High | Open |
| C-002 | Hard cutover only | The cutover must not introduce long-lived compatibility aliases, bridge behavior, or mixed-contract support. Old and new mission-domain clients must be treated as incompatible. | Contract Policy | High | Open |
| C-003 | Unrelated terminology preserved | The release must not rename unrelated concepts that happen to use the word `feature`, including feature flags. | Scope | Medium | Open |
| C-004 | Planning metadata exemption | `kitty-specs/*/meta.json` and other spec-generation workflow metadata are out of scope for this contract cutover unless they are separately promoted to a public runtime or integration surface. | Scope | Medium | Open |
| C-005 | Historical migration rule | Authoritative published contract artifacts in this repository must be migrated to canonical mission/build terminology, while replayable or generated artifacts may be destructively regenerated if their intended semantics are preserved. | Data Policy | High | Open |

### Key Entities

- **Mission Record**: The canonical catalog representation of a mission identified by `mission_slug`, `mission_number`, and `mission_type`, with lifecycle tracked through mission catalog events.
- **Project**: The documented team-scoped repository identity. Fresh clones of the same GitHub repository resolve to the same `Project` only within the current SaaS team or org boundary, with enforcement owned by downstream consumers rather than this repository.
- **Build**: One concrete checkout or worktree of a `Project`, identified canonically by `build_id`.
- **Canonical Event Envelope**: The public event wrapper that carries both `build_id` as checkout identity and `node_id` as causal emitter identity for Lamport ordering and deterministic tie-breaking.
- **Mission Catalog Event**: A canonical mission record event, specifically `MissionCreated` or `MissionClosed`, used to represent mission catalog state.
- **Cutover Contract-Version Signal**: The released version marker used by downstream repos to classify whether a payload belongs to the canonical cutover contract.
- **Forbidden Legacy Surface Set**: The legacy mission-domain keys and catalog event names that, if present in a payload or example, classify it as pre-cutover and therefore invalid for mixed-version rollout.
- **Cutover Contract Artifact**: The published release artifact from `spec-kitty-events` that declares the cutover contract-version signal and forbidden legacy surface set that downstream repos must enforce.

## Assumptions

- The contract cutover applies to public mission-domain surfaces in this repository, including schemas, fixtures, validators, and docs, rather than to unrelated internal implementation details that are not part of the released contract.
- Consumers and producers are expected to adopt the same released contract version in lockstep rather than rely on transitional bridging behavior.
- Historical examples and replay fixtures can be updated or regenerated where doing so preserves their intended semantics, while authoritative published contract artifacts must be rewritten to canonical terminology rather than left as legacy snapshots.
- The spec-generation metadata under `kitty-specs/*/meta.json` is treated as workflow metadata rather than a released event-contract surface for this mission.

## Dependencies

- `spec-kitty-saas` must reject pre-cutover mission/build payloads and contracts before production rollout.
- `spec-kitty` must stop emitting legacy mission-domain payloads and contracts before production rollout.
- No production rollout may occur until `spec-kitty-events`, `spec-kitty-saas`, and `spec-kitty` are all ready for the same contract version.
- The release package from `spec-kitty-events` must publish the cutover contract-version signal and the forbidden legacy surface set that downstream repos are required to enforce.

## Success Criteria

### Measurable Outcomes

- **SC-001**: All released public mission-domain schemas, fixtures, validators, and docs in `spec-kitty-events` use canonical `mission_slug`, `mission_number`, and `mission_type`, with zero remaining supported public `feature*` mission fields.
- **SC-002**: Mission catalog validation accepts `MissionCreated` and `MissionClosed` and rejects catalog use of `MissionCompleted` in 100% of released examples and fixtures.
- **SC-003**: All released canonical event envelope contracts require both `build_id` and `node_id`, and all public documentation distinguishes checkout identity from causal ordering identity without contradiction.
- **SC-004**: The release publishes a machine-checkable cutover contract-version signal and a forbidden legacy surface set that lets downstream repos deterministically reject 100% of pre-cutover payloads.
- **SC-005**: The `spec-kitty-events` release is not considered shippable until consuming repos have matching contract-version gates and no mixed-version operation is possible.
- **SC-006**: The full conformance suite, replay-fixture validation, and repository test suite complete with zero failures for the release candidate.
