# Decision Moment V1 Contract Freeze

**Mission:** `decision-moment-v1-contract-freeze-01KPWA0N`
**Mission ID:** `01KPWA0N4DX047S3NX734YRFVW`
**Mission type:** `software-dev`
**Target branch:** `main`
**Related issue:** `spec-kitty-events#13`

## Context

"Decision Moment" is the user-facing planning term for moments during a Spec Kitty interview (charter, specify, plan) when the mission owner must answer a material question. The canonical cross-channel collaboration object that represents such a moment is the **DecisionPoint**, carried by the `spec_kitty_events` contract. Today, DecisionPoint events already support charter-time decisions and ad-hoc discussion, but the contract does not yet express everything a V1 Decision Moment needs: interview origin context, a first-class "widened to Slack" moment, distinct terminal outcomes beyond "resolved," a structured summary with provenance, participant identity that survives replay without live Teamspace/Slack lookups, and the local-close-while-widened case.

This mission freezes that V1 contract as `spec-kitty-events 4.0.0` so the downstream CLI (`spec-kitty#757`, `spec-kitty#758`) and SaaS work (`spec-kitty-saas#110`, `spec-kitty-saas#111`) can build against a single honest contract boundary.

## Stakeholders / Actors

- **Mission owner** — human driving a charter/specify/plan interview in the CLI. Sees "Decision Moment" language.
- **CLI (spec-kitty)** — produces DecisionPoint events at interview time (opened, widened, resolved, …).
- **SaaS backend (spec-kitty-saas)** — consumes DecisionPoint events to project Teamspace timelines, produce Slack summaries, and write back candidate answers.
- **Slack orchestrator (spec-kitty-saas)** — opens one thread per widened Decision Moment, ingests discussion, posts closure messages.
- **Conformance consumers / replay tooling** — anyone validating or replaying the event log (tests, audits, historical missions).

## User Scenarios & Testing

### Scenario 1 — Local-only Decision Moment, resolved

1. An interview question is asked during `/spec-kitty.specify`.
2. The CLI emits `DecisionPointOpened` with interview-origin metadata.
3. The mission owner answers locally; the CLI emits `DecisionPointResolved` with `terminal_outcome=resolved`, `final_answer`, `resolved_by`, and `closed_locally_while_widened=false`.
4. Replay over the event log produces the expected reduced state (`status=closed`, `terminal_outcome=resolved`, no widening artifacts).

### Scenario 2 — Widened Decision Moment, resolved via Slack summary

1. `DecisionPointOpened` is emitted with interview-origin metadata.
2. Mission owner (via CLI) confirms widening. CLI emits `DecisionPointWidened` carrying `channel=slack`, `teamspace_ref`, `default_channel_ref`, `thread_ref`, `invited_participants`, and `widened_by`.
3. One or more `DecisionPointDiscussing` events capture synthesized contribution snapshots (not raw Slack messages).
4. `DecisionPointResolved` is emitted with `terminal_outcome=resolved`, `final_answer`, `summary={text, source=slack_extraction, extracted_at, candidate_answer}`, `actual_participants` (may have `external_refs.slack_user_id`), `resolved_by`, `closed_locally_while_widened=false`, `closure_message` ref populated.

### Scenario 3 — Widened, then closed locally while widened

1. `DecisionPointOpened` → `DecisionPointWidened` emitted as in Scenario 2.
2. Before Slack discussion produces a usable summary, mission owner answers locally.
3. `DecisionPointResolved` is emitted with `terminal_outcome=resolved`, `final_answer`, `closed_locally_while_widened=true`, `summary.source ∈ {manual, mission_owner_override}`, `actual_participants` reflecting whatever Slack activity did occur (possibly empty), `closure_message` ref pointing at the closure-post Slack message once the orchestrator posts it.

### Scenario 4 — Deferred

1. `DecisionPointOpened` (optionally followed by `DecisionPointWidened`).
2. `DecisionPointResolved` with `terminal_outcome=deferred`, no `final_answer`, `rationale` required, `closed_locally_while_widened` reflects whether widening was open.
3. `DecisionInputAnswered` is NOT emitted (deferred is not a real answer).

### Scenario 5 — Canceled

1. `DecisionPointOpened` (optionally followed by `DecisionPointWidened`).
2. `DecisionPointResolved` with `terminal_outcome=canceled`, no `final_answer`, `rationale` required, `closed_locally_while_widened` reflects whether widening was open.
3. `DecisionInputAnswered` is NOT emitted.

### Scenario 6 — Resolved with Other/free-text answer

1. `DecisionPointOpened` includes `options` (the offered choices).
2. Mission owner selects Other (or types free text).
3. `DecisionPointResolved` emits `terminal_outcome=resolved`, `final_answer` populated with the free text, `other_answer=true`. `DecisionInputAnswered` carries the same text.

### Edge cases

- **Duplicate `DecisionPointWidened` for the same `decision_id`** — reducer MUST treat the second occurrence as a no-op on widening state (idempotent). Replay determinism MUST hold.
- **Out-of-order events** — reducer MUST be deterministic given any topological order consistent with Lamport clocks; replay fixtures include one out-of-order anomaly case.
- **`DecisionPointResolved` emitted without any prior `DecisionPointOpened`** — reducer MUST reject via structured validation; invalid conformance fixture locks this.
- **Malformed `external_refs`** — schema validator MUST fail closed; invalid conformance fixture locks this.
- **`DecisionPointWidened` missing `thread_ref`** — schema validator MUST fail closed.
- **`DecisionPointResolved` missing `terminal_outcome`** — schema validator MUST fail closed (no 4.x grace period).
- **`DecisionPointOpened` missing interview-origin fields when `origin_surface=planning_interview`** — schema validator MUST fail closed.

## Functional Requirements

| ID     | Requirement                                                                                                                                                                                                                                                                     | Status   |
| ------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------- |
| FR-001 | The contract SHALL retain the existing DecisionPoint event vocabulary (`DecisionPointOpened`, `DecisionPointDiscussing`, `DecisionPointResolved`, `DecisionPointOverridden`) for semantic continuity.                                                                           | Approved |
| FR-002 | The contract SHALL introduce exactly one new event type, `DecisionPointWidened`, emitted when an interview-origin Decision Moment is widened to a Slack-backed discussion.                                                                                                      | Approved |
| FR-003 | `DecisionPointOpened` SHALL carry interview-origin metadata: `origin_surface` (enum including `planning_interview`), `origin_flow` (`charter`/`specify`/`plan`), `question`, `options`, `input_key`, `step_id`.                                                                  | Approved |
| FR-004 | When `origin_surface=planning_interview`, the interview-origin fields on `DecisionPointOpened` SHALL be required (schema-enforced).                                                                                                                                              | Approved |
| FR-005 | `DecisionPointWidened` SHALL carry `channel=slack` (enum-constrained), `teamspace_ref`, `default_channel_ref`, `thread_ref` (including thread URL when known), `invited_participants`, and `widened_by`.                                                                        | Approved |
| FR-006 | `DecisionPointDiscussing` SHALL continue to express meaningful discussion-state updates or synthesized contribution snapshots, not raw per-message Slack traffic.                                                                                                               | Approved |
| FR-007 | `DecisionPointResolved` SHALL require `terminal_outcome ∈ {resolved, deferred, canceled}` as the sole indicator of terminal state.                                                                                                                                              | Approved |
| FR-008 | `DecisionPointResolved` SHALL carry `final_answer` (required when `terminal_outcome=resolved`, forbidden when `terminal_outcome ∈ {deferred, canceled}`), `other_answer` boolean, `rationale` (required when `terminal_outcome ∈ {deferred, canceled}`), and `resolved_by`.     | Approved |
| FR-009 | `DecisionPointResolved` SHALL carry a structured `summary` object `{text, source, extracted_at?, candidate_answer?}` where `source ∈ {slack_extraction, manual, mission_owner_override}`; `summary` is required when a widening event preceded it, optional otherwise.           | Approved |
| FR-010 | `DecisionPointResolved` SHALL carry `actual_participants` (list) and a `closed_locally_while_widened` boolean. `closed_locally_while_widened=true` SHALL only be legal when the same `decision_id` has a prior `DecisionPointWidened` event.                                    | Approved |
| FR-011 | `DecisionPointResolved` MAY carry an optional `closure_message` reference (pointer to the final Slack closure post, when one exists).                                                                                                                                           | Approved |
| FR-012 | `ParticipantIdentity` SHALL be extended with an optional `external_refs` object carrying `slack_user_id?`, `slack_team_id?`, `teamspace_member_id?`. Existing `participant_id`, `display_name`, and `role?` fields are preserved.                                                | Approved |
| FR-013 | `invited_participants` (on Widened) and `actual_participants` (on Resolved) SHALL both be arrays of the same canonical `ParticipantIdentity` shape. No separate invited-vs-actual schema families.                                                                              | Approved |
| FR-014 | The reducer SHALL compute a deterministic reduced DecisionPoint state from any replay-valid event stream; duplicate `DecisionPointWidened` for the same `decision_id` SHALL be idempotent.                                                                                      | Approved |
| FR-015 | `DecisionInputRequested` and `DecisionInputAnswered` SHALL remain backward-compatible with all 3.x producers and consumers. `DecisionInputAnswered` SHALL be emitted only when a real final answer is written back (never for `deferred` or `canceled`).                         | Approved |
| FR-016 | The package SHALL ship five golden replay fixture pairs covering: local-only resolved, widened→resolved, widened→closed-locally, deferred, and canceled — plus one additional golden pair for the Other/free-text resolved path. Each pair is `.jsonl` events + `_output.json`. | Approved |
| FR-017 | The package SHALL ship invalid conformance fixtures covering at least: Resolved missing `terminal_outcome`, Widened missing `thread_ref`, Opened missing interview-origin fields under `origin_surface=planning_interview`, and malformed `external_refs`.                      | Approved |
| FR-018 | The package version SHALL be bumped to `4.0.0` as a clean breaking release; no 4.x grace path is added to the canonical validator for missing `terminal_outcome`.                                                                                                               | Approved |
| FR-019 | `CHANGELOG.md` and `COMPATIBILITY.md` SHALL be updated to document the 3.x→4.0.0 contract boundary, the Decision Moment V1 contract, and the behavior rules for `DecisionInputAnswered` suppression on deferred/canceled.                                                        | Approved |

## Non-Functional Requirements

| ID      | Requirement                                                                                                                                                                                                                                                | Status   |
| ------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------- |
| NFR-001 | Replay of any golden `.jsonl` fixture via the reducer SHALL produce byte-identical output to its paired `_output.json` (deterministic serialization: sorted keys, stable separators).                                                                       | Approved |
| NFR-002 | Every valid conformance fixture SHALL validate against its JSON Schema with no errors; every invalid conformance fixture SHALL fail validation with a structured error pointing at the offending field path.                                              | Approved |
| NFR-003 | Reducer evaluation on any golden fixture (≤32 events) SHALL complete in under 10 ms wall time on reference hardware; larger-scale property tests (≤10,000 events) SHALL complete in under 1 s.                                                              | Approved |
| NFR-004 | `mypy --strict` SHALL pass on the full `src/spec_kitty_events` tree after the changes land.                                                                                                                                                                 | Approved |
| NFR-005 | Hypothesis-based determinism property tests for DecisionPoint SHALL cover at least 500 generated event streams per run with zero determinism failures.                                                                                                      | Approved |
| NFR-006 | Committed JSON Schemas SHALL be regenerable from Pydantic models; schema-drift check SHALL pass on CI with no diff.                                                                                                                                         | Approved |

## Constraints

| ID    | Constraint                                                                                                                                                                                                                                    | Status   |
| ----- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------- |
| C-001 | The package version MUST become `4.0.0`. Any attempt to ship these changes under `3.x` is out of scope.                                                                                                                                         | Approved |
| C-002 | No new event types beyond `DecisionPointWidened` may be introduced in this mission. Deferred, canceled, and local-close must be expressed via fields on existing events.                                                                       | Approved |
| C-003 | The contract must remain channel-agnostic for eventual multi-channel widening, but V1 only validates `channel=slack`. A future channel enum extension must not require a 5.0.0 bump.                                                            | Approved |
| C-004 | `DecisionInputRequested` and `DecisionInputAnswered` payload shapes MAY gain optional fields but MUST NOT break any 3.x required-field contract.                                                                                               | Approved |
| C-005 | All schemas, fixtures, and conformance tests live inside `spec-kitty-events`; no dependencies on `spec-kitty` or `spec-kitty-saas` packages may be introduced.                                                                                  | Approved |
| C-006 | Pydantic models remain the source of truth; committed JSON Schemas are regenerated from them, not hand-edited.                                                                                                                                 | Approved |
| C-007 | Existing 3.x conformance fixtures must continue to validate (they do not reference the new required fields).                                                                                                                                    | Approved |

## Success Criteria

- **SC-1 — Downstream unblock.** Contracts (schemas + reducers + fixtures) are stable enough that `spec-kitty#757`, `spec-kitty#758`, `spec-kitty-saas#110`, and `spec-kitty-saas#111` can be implemented and reviewed against them without further contract changes.
- **SC-2 — Replay integrity.** 100% of golden fixtures produce their expected reduced state byte-identically on replay.
- **SC-3 — Schema validation coverage.** 100% of invalid fixtures are rejected with a structured error; 0% of valid fixtures are rejected.
- **SC-4 — No silent breakage for 3.x DecisionInput consumers.** `DecisionInputRequested` / `DecisionInputAnswered` continue to validate against their 3.x schemas for all 3.x-compatible payloads.
- **SC-5 — Determinism under load.** Hypothesis property tests (≥500 runs per CI) produce zero nondeterministic reducer outputs.
- **SC-6 — Package release readiness.** `pytest`, `mypy --strict`, and schema-drift check all pass on the 4.0.0 branch; `CHANGELOG.md` documents the contract boundary.

## Key Entities

- **DecisionPoint (aka Decision Moment in user-facing planning language)** — `{decision_id, origin_surface, origin_flow?, status, terminal_outcome?, question, options, widening?, resolution?, participants}`. `decision_id` is a stable identifier assigned at ask-time.
- **DecisionPointOpened payload** — `{decision_id, origin_surface, origin_flow?, question, options, input_key?, step_id?, created_at, created_by}`.
- **DecisionPointWidened payload** — `{decision_id, channel=slack, teamspace_ref, default_channel_ref, thread_ref, invited_participants, widened_by, widened_at}`.
- **DecisionPointDiscussing payload** — `{decision_id, snapshot_kind, contributions?, updated_at}`.
- **DecisionPointResolved payload** — `{decision_id, terminal_outcome, final_answer?, other_answer?, rationale?, summary?, actual_participants, resolved_by, closed_locally_while_widened, closure_message?, resolved_at}`.
- **DecisionPointOverridden payload** — unchanged.
- **ParticipantIdentity** — `{participant_id, display_name, role?, external_refs?}`.
- **ParticipantExternalRefs** — `{slack_user_id?, slack_team_id?, teamspace_member_id?}`.
- **SummaryBlock** — `{text, source ∈ {slack_extraction, manual, mission_owner_override}, extracted_at?, candidate_answer?}`.
- **ClosureMessageRef** — `{channel=slack, thread_ref, message_ts, url?}`.
- **ThreadRef** — `{slack_team_id?, channel_id, thread_ts, url?}`.
- **TeamspaceRef** — `{teamspace_id, name?}`.
- **DefaultChannelRef** — `{channel_id, name?}`.

## Assumptions

1. Existing `decision_id` format (ULID-backed string) is retained and used as the stable correlation key.
2. `DecisionInputRequested` / `DecisionInputAnswered` continue to be emitted by CLI for 3.x-compatibility; DecisionPoint events are the richer collaboration truth.
3. No transport, auth, or persistence concerns live in this repo; this is a pure contract package (schemas + Pydantic models + reducer + fixtures).
4. "Synthesized contribution snapshot" for `DecisionPointDiscussing` is produced by CLI or SaaS; the contract only defines the payload shape.
5. Future channels (email, MS Teams, etc.) will reuse `DecisionPointWidened` with a widened `channel` enum — not a new event type — so the 4.0.0 contract is forward-compatible for that axis.
6. Timestamps on the wire are ISO-8601 UTC strings; Lamport clocks continue to be carried by the envelope layer, not these payloads.

## Out of Scope

- CLI implementation of interview-time Decision Moment emission (`spec-kitty#757`).
- CLI Widen Mode UX and write-back loop (`spec-kitty#758`).
- SaaS Teamspace projection / audience lookup / decision APIs (`spec-kitty-saas#110`).
- SaaS Slack orchestration, summary extraction, closure posts (`spec-kitty-saas#111`).
- E2E acceptance across repos (`spec-kitty-end-to-end-testing#25`).
- Plain-English regression coverage (`spec-kitty-plain-english-tests#1`).
- Any new event types beyond `DecisionPointWidened`.
- Multi-channel widening implementation.
- Any cross-DecisionPoint relationship / grouping (e.g., bundled decisions).

## Dependencies

- **Upstream (blockers):** none. This mission freezes the contract; nothing else in the V1 program should land first.
- **Downstream (unblocks):** `spec-kitty#757`, `spec-kitty-saas#110`, `spec-kitty-saas#111`, `spec-kitty#758`, `spec-kitty-end-to-end-testing#25`, `spec-kitty-plain-english-tests#1`.

## Open Questions

None carried forward. All clarifications resolved during discovery (vocabulary shape, participant identity, fixture set, version+summary shape).
