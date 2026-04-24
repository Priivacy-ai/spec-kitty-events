# Research — Decision Moment V1 Contract Freeze

Phase 0 research for mission `decision-moment-v1-contract-freeze-01KPWA0N`.
All items below were resolved during specify/plan discovery with the mission owner; this document preserves the rationale per DIRECTIVE_003 (Decision Documentation) so future contributors can see why the path was chosen.

## R-1 — Event vocabulary shape

**Decision:** Hybrid (option C from discovery). Keep the four existing DecisionPoint event types and add exactly one new event type — `DecisionPointWidened`.

**Rationale:**

1. Widening is a real first-class moment. Slack orchestration (`spec-kitty-saas#111`) needs a dedicated event to key thread creation off, and the CLI Widen Mode (`spec-kitty#758`) needs the same event as the confirmation landing point.
2. Deferred and canceled are terminal *outcomes*, not fundamentally different lifecycles. They do not warrant separate event types; a required `terminal_outcome` enum on `DecisionPointResolved` captures them losslessly.
3. Local-close-while-widened is *provenance on the terminal event*, not its own terminal state. `closed_locally_while_widened: bool` on `Resolved` is the correct home for it.
4. Expanding the event vocabulary carries high replay and conformance cost; each new type forces a schema, a reducer branch, fixtures, and public-API surface. One addition (Widened) is the minimum viable delta.

**Alternatives considered:**

- **Extend existing events only.** Rejected: widening has no natural home on `Opened` or `Discussing`; consumers would have to scan for a side-effect payload field to detect the thread. Slack orchestration becomes brittle.
- **Four new terminal event types (Deferred, Canceled, Widened, ClosedLocally).** Rejected: over-expands the vocabulary; `terminal_outcome` + `closed_locally_while_widened` collapses three of the four into fields on `Resolved` with identical semantics and simpler downstream handling.

## R-2 — Participant identity shape

**Decision:** Reuse a single canonical `ParticipantIdentity` shape for both `invited_participants` (on `Widened`) and `actual_participants` (on `Resolved`). Extend it with an optional `external_refs: {slack_user_id?, slack_team_id?, teamspace_member_id?}` block.

**Rationale:**

1. Separate invited-vs-actual schema families would double the surface area and force consumers to convert between shapes, creating drift risk.
2. Invited participants usually have canonical `participant_id` plus `teamspace_member_id`; actual participants may have `slack_user_id`/`slack_team_id` before the canonical participant mapping is minted. Optional `external_refs` makes both cases representable without a live Teamspace lookup at replay time.
3. Preserves 3.x compatibility for all existing payloads that embed `ParticipantIdentity` (`ParticipantInvited`, `ParticipantJoined`, collaboration state snapshots). Adding one optional field does not break any 3.x consumer.

**Alternatives considered:**

- **Two separate shapes.** Rejected: breaks invariant that one canonical identity exists per participant across channels.
- **Require `external_refs`.** Rejected: most 3.x callers don't have Slack mapping, and interview-origin decisions that aren't widened never produce Slack IDs at all.

## R-3 — Conformance + replay fixture granularity

**Decision:** Ship five mandatory golden replay pairs plus a dedicated Other/free-text golden replay pair, plus a small set of invalid fixtures for schema enforcement.

**Rationale:**

1. The five mandated scenarios (`local_only_resolved`, `widened_resolved`, `widened_closed_locally`, `deferred`, `canceled`) are load-bearing for downstream consumers. Each must be a golden that downstream repos can test against.
2. Other/free-text is explicitly load-bearing for `spec-kitty#757` and `spec-kitty#758`. Burying it inside `widened_resolved` makes regressions hard to attribute; a named fixture `replay_interview_resolved_other` makes the expectation visible.
3. Invalid fixtures (Resolved missing `terminal_outcome`, Widened missing `thread_ref`, Opened missing interview-origin fields when `origin_surface=planning_interview`, malformed `external_refs`) lock the schema validator at the file system level, not just via Pydantic unit tests.
4. The repo's conformance convention already splits `valid/` and `invalid/` directories per domain; this mission mirrors that convention.

**Alternatives considered:**

- **Five golden pairs, no invalid fixtures.** Rejected: schema validator regressions would only be caught by unit tests, which are easier to accidentally weaken than committed fixtures.
- **Full matrix (~20 pairs).** Rejected: not required to lock the contract; diminishing returns.

## R-4 — Version bump policy for the 4.0.0 freeze

**Decision:** Bump package version to `4.0.0`. Make `terminal_outcome` on `DecisionPointResolved` required immediately in the canonical 4.x validator (no grace period). Keep `DecisionInputRequested` / `DecisionInputAnswered` 3.x-compatible.

**Rationale:**

1. Requiring a new field on an existing canonical event payload is a breaking contract change. Calling that `3.4.0` would be semver drift; this repo is explicitly the contract source of truth and must tell the truth.
2. A clean `4.0.0` freeze gives downstream repos one honest contract boundary to migrate against, instead of a leaky "minor but actually breaking" 3.4.0 with a temporary grace path.
3. `DecisionInputRequested` / `DecisionInputAnswered` are consumed by an older set of callers. Preserving their 3.x shape (optionally adding fields) means those callers can migrate to 4.0.0 without code changes.
4. `DecisionInputAnswered` is emitted only when a real answer is written back; deferred/canceled do not fake an answer. This preserves semantic honesty for input-tracking consumers.

**Alternatives considered:**

- **3.4.0 minor with grace period.** Rejected: invites producers to stay half-migrated and obscures the contract.
- **3.4.0 minor with immediate break.** Rejected: would be dishonest semver.

## R-5 — `summary` payload shape

**Decision:** Structured `SummaryBlock` object `{text, source, extracted_at?, candidate_answer?}` where `source ∈ {slack_extraction, manual, mission_owner_override}`.

**Rationale:**

1. The `spec-kitty#758` write-back flow depends on distinguishing extracted summary from manual or owner-overridden summary. A bare string cannot express provenance without overloading.
2. A structured block future-proofs the extraction path (`candidate_answer` lets the SaaS side carry its best-guess answer alongside the narrative without a second event round-trip).
3. `extracted_at` is diagnostic — if we later need to bound staleness or audit extraction timing, the data is already there.

**Alternatives considered:**

- **Plain string `summary`.** Rejected: forces provenance into a sibling field later and increases schema churn.
- **Nested per-source variants.** Rejected: over-engineered; three enum values in `source` cover V1 needs without a discriminated sub-union.

## R-6 — Ask-time vs post-analysis payload compatibility (Opened/Discussing/Resolved)

**Decision:** Model `DecisionPointOpened`, `DecisionPointDiscussing`, and `DecisionPointResolved` payloads as Pydantic v2 **discriminated unions keyed by `origin_surface ∈ {adr, planning_interview}`**. Single event type string per event; two payload variants per event type (ADR variant preserves all 3.x required fields; interview variant carries V1 ask-time fields). `origin_surface` is required on every event in the DecisionPoint family (self-describing events are replay-safe without reducer state lookups).

**Rationale:**

1. Existing 3.x `DecisionPointOpenedPayload` requires `rationale`, `alternatives_considered` (min_length=1), `evidence_refs` (min_length=1), and ADR authority metadata. At interview ask time, the mission owner has not yet supplied any of that — they're being asked "which option?". Any scheme that stuffs placeholders into those fields would create provenance confusion downstream.
2. A single "fat" payload with conditional requirements (option A from planning discovery) reads as optional-spaghetti and invites drift; the interview payload would carry empty ADR fields and the ADR payload would carry empty interview fields. Eventually someone ships bad data.
3. Pydantic v2's `Discriminator` + tagged union gives compile-time/runtime type safety per variant with minimal code. Schema generation naturally emits two JSON Schemas per event type (via `oneOf`).
4. Self-describing events (origin on every event) mean conformance replay and downstream consumers never need to look up "what origin was this decision?" — every event answers on its own.
5. ADR semantics are preserved *exactly* under `origin_surface="adr"`. Existing ADR producers migrate by adding `origin_surface="adr"` to their payloads and bumping to 4.0.0; no other field changes.

**Alternatives considered:**

- **(A) Discriminator with a single fat payload, conditional requirements.** Rejected: optional-spaghetti problem.
- **(C) Separate event types per origin (`InterviewDecisionPointOpened`).** Rejected: violates the user's "exactly one new event type for V1" directive.
- **(D) Freeze Opened; put interview-origin metadata on Widened.** Rejected: Widened wouldn't exist for local-only decisions, and FR-003 explicitly puts `origin_surface`, `origin_flow`, question, options, input_key, step_id on Opened.

## R-7 — `decision_point_id` format and correlation

**Decision:** Retain the existing ULID-backed string convention for `decision_point_id`. The CLI (`spec-kitty#757`) assigns a stable `decision_point_id` at ask time that is reused for every subsequent event (Widened, Discussing, Resolved) in the same Decision Moment.

**Rationale:**

1. The current contract already uses `decision_point_id: str` with `min_length=1`. Keeping the format stable means no migration cost for existing ADR producers.
2. ULIDs are lexicographically sortable by time, which aligns with the reducer's sort step and simplifies determinism.
3. A stable ask-time ID is what lets the reducer correlate events across local-only, widened, and terminal transitions without any extra correlation field.

**Alternatives considered:**

- **New `moment_id` namespace.** Rejected: creates dual-identity ambiguity and forces every consumer to track both IDs.

## R-8 — Reducer changes (scope of V1 projection)

**Decision:** Extend `ReducedDecisionPointState` with V1 projection fields (channel/thread snapshot, invited/actual participants, terminal_outcome, closed_locally_while_widened, summary, final_answer, other_answer). Keep one reducer entry point (`reduce_decision_point_events`). Reducer branches on per-event `origin_surface` to apply variant-specific projection, and logs a `DecisionPointAnomaly(kind="origin_mismatch")` if events for the same `decision_point_id` disagree on origin. Duplicate `DecisionPointWidened` for the same decision is a no-op on widening state (idempotent); this satisfies replay safety.

**Rationale:**

1. A single reducer function keeps API surface small and aligns with how other domains in this repo already reduce (see `collaboration.reduce_collaboration_state`, `mission_next.reduce_mission_next_state`).
2. Origin-mismatch as an anomaly (not a fatal) preserves the `fail-closed-at-schema` / `fail-soft-at-reducer` split already in use — schemas reject malformed events, the reducer records anomalies for semantic oddities.
3. Idempotent Widened aligns with NFR-005 (Hypothesis-based determinism ≥500 streams per run) and is the standard behaviour elsewhere in the repo.

**Alternatives considered:**

- **Two reducers (ADR reducer + Interview reducer).** Rejected: forces callers to know origin before reducing, duplicates sort/dedup pipeline, and multiplies projection-model surface.

## R-9 — Schema generation

**Decision:** Extend `src/spec_kitty_events/schemas/generate.py` to register new V1 models (the discriminated unions, `DecisionPointWidenedPayload`, `SummaryBlock`, `ParticipantExternalRefs`, `ThreadRef`, `TeamspaceRef`, `DefaultChannelRef`, `ClosureMessageRef`). Committed JSON Schemas remain the source of truth for non-Python consumers; Pydantic models remain the source of truth for Python consumers; schema-drift check keeps them in sync.

**Rationale:**

1. The repo convention (constraint C-006) is that JSON Schemas are regenerated from Pydantic models, not hand-edited. Sticking to this avoids divergence.
2. Existing `test_schema_drift.py` integration test will catch any accidental hand-edit, reinforcing the invariant.

**Alternatives considered:**

- **Hand-maintain JSON Schemas for the new V1 shapes.** Rejected: violates C-006 and would guarantee drift.

## R-10 — CHANGELOG / COMPATIBILITY policy

**Decision:** Write a `CHANGELOG.md` `## 4.0.0` section and a new `COMPATIBILITY.md` block documenting:

- the contract boundary (3.x → 4.0.0 for DecisionPoint only)
- `DecisionInputRequested` / `DecisionInputAnswered` remain backward-compatible
- behaviour rule: `DecisionInputAnswered` is only emitted when a real final answer is written back (never on deferred/canceled)
- migration steps for existing ADR producers: add `origin_surface="adr"` to payloads

**Rationale:** Charter review policy explicitly mandates a compatibility review for any envelope/payload/versioning change. This mission *is* that review; the docs artifacts are the permanent record.
