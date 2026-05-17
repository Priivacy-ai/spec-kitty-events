# Spec: WPStatusChanged Backward Transition Contract

**Mission**: `wpstatuschanged-backward-transition-contract-01KRV7SC`
**Mission ID**: `01KRV7SC4AS4SGM7HGN93HGP0W`
**Friendly name**: WPStatusChanged Backward Transition Contract
**Target branch**: `main`
**Source brief**: `/Users/robert/spec-kitty-dev/spec-kitty-20260517-165635-WafwWc/start-here.md` (sections "Agent Prompt: Event Contract" and "Observed Evidence" Incident B), planning issue `spec-kitty-events#29`, parent epic `spec-kitty-planning#17`.

---

## Purpose (TL;DR)

Lock the canonical `WPStatusChanged` event contract for backward transitions, force, actor, `from_lane` mismatch, replay, and reconciliation so that CLI and SaaS implement one consistent interpretation and review-rejection flows do not land in `terminal_failed`.

## Background

`spec-kitty-events` is the single source of truth for the `WPStatusChanged` event shape, validation rules, and projection semantics shared between the spec-kitty CLI (producer) and the spec-kitty-saas materializer (consumer).

On 2026-05-17 the production SaaS instance accumulated 22 `terminal_failed` rows for normal review-rejection events (`in_review → planned`) that the CLI emitted with `force=False`. The SaaS materializer rejected those events as "invalid unforced backward transitions" even though the `_ALLOWED_TRANSITIONS` matrix in `src/spec_kitty_events/status.py` already lists them as sanctioned review-rollback transitions guarded only by `review_ref`.

The code is correct; the **contract documentation** is silent on three points that allowed CLI and SaaS to drift apart:

1. Whether review-rollback transitions (`for_review/in_review/approved → in_progress/planned`) require `force=True` or only `review_ref`.
2. How a consumer must behave when an event's `from_lane` does not match the consumer's current projection state (`from_lane` mismatch / reconciliation).
3. Whether `actor == "user"` modifies any rule (it does not).

This mission writes the contract down, codifies it in module docstrings and a dedicated contract document, and ships conformance fixtures and tests that every consumer can run.

## Scope (in)

- A contract document at `docs/contracts/wp-status-changed.md` covering forward, rollback, terminal-exit, force, actor, `from_lane` mismatch, replay, and reconciliation diagnostics.
- Updated module docstrings in `src/spec_kitty_events/status.py` that link to the contract document and state the rules inline.
- Conformance fixtures under `src/spec_kitty_events/conformance/fixtures/wp_status_changed/` covering the six required scenarios (see FR-007).
- Conformance manifest entries for the new fixtures, with `outcome` (accept/reject/reconcile) and `reason_code` fields.
- Tests proving the contract shape against `validate_transition` and the reducer.
- A reconciliation diagnostic event type (or reuse of an existing diagnostic shape) that consumers emit when they reconcile a `from_lane` mismatch, with a `reason_code` field that distinguishes business-rule reconciliation from infra failure.

## Scope (out / non-goals)

- NG-1: Changing the existing `_ALLOWED_TRANSITIONS` matrix or any runtime validation behaviour. The matrix is correct; only documentation, fixtures, and tests are added.
- NG-2: Changing CLI emit behaviour or SaaS materializer behaviour. Those changes happen in `spec-kitty#1090/1088/1087/1089` and `spec-kitty-saas#204/205/206` (separate missions) and must consume this contract.
- NG-3: Adding new lane states or modifying `Lane` enum values.
- NG-4: Introducing a server-side reconciliation policy beyond defining the diagnostic shape. Server policy is owned by `spec-kitty-saas#205`.
- NG-5: Backfilling or repairing existing `terminal_failed` rows in production.

## Locked decisions

- D-1: Review-rollback transitions are NORMAL transitions that DO NOT require `force=True`. They DO require a non-empty `review_ref`. Specifically the sanctioned pairs are: `(for_review|in_review|approved) → (in_progress|planned)` and `in_review → for_review`. This matches the existing `_ALLOWED_TRANSITIONS` matrix and is now contractual.
- D-2: `force=True` is required ONLY to (a) exit a terminal lane (`done`, `canceled`) or (b) execute a transition pair that is not in the matrix and is not `to: blocked` / `to: canceled` from a non-terminal lane. A `force=True` event MUST carry a non-empty `reason`. This already matches `_check_business_rules` and is now contractual.
- D-3: `actor` is an audit-trail field. It MUST be either a non-empty string or a non-empty dict (already enforced). **`actor` does NOT modify the validation rules.** `actor == "user"`, `actor == "claude"`, and `actor == {"role": "reviewer"}` all pass through `validate_transition` identically. Consumers MUST NOT treat any actor value as a policy escape hatch.
- D-4: A consumer that receives an event whose `from_lane` does not match the consumer's current projection state MUST classify the event as a reconciliation case, not as an infra failure. Two sub-cases are distinguished by `reason_code`:
  - `from_lane_mismatch_replay`: the event's `from_lane` matches a prior projection state that already advanced past it. The consumer SHOULD record a `ReconciliationDiagnostic` with this code and skip re-application (the event has effectively already been applied).
  - `from_lane_mismatch_drift`: the event's `from_lane` does not match any prior projection state in the consumer's event log for that `wp_id`. The consumer MUST record a `ReconciliationDiagnostic` with this code and surface the drift on a dedicated diagnostics surface (not on the infra-failure surface).
- D-5: Replay of an event (same `event_id` / same `(mission_slug, wp_id, sequence)` tuple) is idempotent at the consumer. Consumers MUST detect replay before invoking `validate_transition` and MUST NOT count replays as infra failures.
- D-6: Conformance fixtures are the binding artefact. If documentation and a fixture disagree, the fixture is correct. Every reason_code introduced by D-4 MUST appear in at least one fixture with `outcome: reconcile` or `outcome: reject`.

## User scenarios

### Primary scenario: review rejection

1. A user reviewer reads a WP that is `in_review` and decides the implementation is not acceptable.
2. The CLI emits `WPStatusChanged { from_lane: in_review, to_lane: planned, actor: "user", review_ref: <review-cycle-file>, force: false }`.
3. SaaS materializer receives the event, looks up the contract: review-rollback with `review_ref` → ACCEPT.
4. Projection state for the WP advances to `planned` with `review_status: has_feedback`.
5. No `terminal_failed` row is created. No reconciliation diagnostic is emitted.

### Exception 1: replay

1. SaaS materializer crashes after partially applying an event and is restarted.
2. The drain replays a batch that includes an event already applied.
3. Consumer detects replay (same `event_id`), records a debug-level idempotency hit, and does not invoke validation. No `terminal_failed` row. No reconciliation diagnostic.

### Exception 2: from_lane drift

1. CLI emits `WPStatusChanged { from_lane: in_progress, to_lane: for_review, ... }`.
2. Consumer's current projection has the WP at `planned` because an earlier event was lost.
3. Consumer detects from_lane mismatch and writes a `ReconciliationDiagnostic { reason_code: "from_lane_mismatch_drift", expected_from_lane: in_progress, actual_projected_lane: planned, wp_id: ... }` to a diagnostics surface. The event is held for operator review (not applied, not counted as infra failure).

### Exception 3: bootstrap planned race

1. Two producers each emit the canonical bootstrap `WPStatusChanged { from_lane: null, to_lane: planned, force: true }` for the same WP.
2. Consumer applies the first, sees the second as replay-by-shape (already at `planned`), records an idempotency hit, and skips the second. No diagnostic surface noise.

## Functional Requirements

| ID | Description | Status |
|----|-------------|--------|
| FR-001 | A contract document MUST exist at `docs/contracts/wp-status-changed.md` that enumerates every transition allowed without force (matching `_ALLOWED_TRANSITIONS`), every guard (review_ref, reason, evidence), and the terminal-lane exit rule. | Approved |
| FR-002 | The contract document MUST explicitly classify review-rollback transitions (`{for_review, in_review, approved} → {in_progress, planned}` plus `in_review → for_review`) as sanctioned NORMAL transitions that DO NOT require `force=True`. | Approved |
| FR-003 | The contract document MUST state that `actor` is audit-only and does NOT modify validation; `actor == "user"` is NOT a policy escape hatch. | Approved |
| FR-004 | The contract document MUST define `from_lane` mismatch semantics with two distinct `reason_code` values (`from_lane_mismatch_replay`, `from_lane_mismatch_drift`) and a `ReconciliationDiagnostic` payload shape. | Approved |
| FR-005 | The contract document MUST define replay semantics: same `event_id` (or, if missing, same `(mission_slug, wp_id, sequence)` if a sequence is present) is idempotent; consumers MUST detect replay before invoking validation. | Approved |
| FR-006 | A `ReconciliationDiagnostic` payload type MUST be added to `src/spec_kitty_events/status.py` (or a sibling module) with fields: `mission_slug`, `wp_id`, `event_id` (the offending event), `expected_from_lane` (Optional[Lane]), `actual_projected_lane` (Optional[Lane]), `reason_code` (str, from a closed enum), `actor` (str), `detected_at` (datetime). | Approved |
| FR-007 | Conformance fixtures MUST exist under `src/spec_kitty_events/conformance/fixtures/wp_status_changed/` covering: (a) normal forward lifecycle (planned→claimed→in_progress→for_review→approved→done); (b) review rejection from in_review to planned with review_ref, force=false; (c) backward transition without force AND without review_ref → reject; (d) backward transition with force and audit reason → accept; (e) from_lane mismatch (drift) → reconcile diagnostic; (f) deterministic business-rule replay → idempotency skip. | Approved |
| FR-008 | The conformance manifest (`src/spec_kitty_events/conformance/fixtures/manifest.json`) MUST list each new fixture with `outcome` ∈ {accept, reject, reconcile, idempotency_skip} and `reason_code` (string or null). | Approved |
| FR-009 | Tests MUST prove every fixture's declared outcome matches `validate_transition` (or the appropriate reducer) output. | Approved |
| FR-010 | Module docstrings in `src/spec_kitty_events/status.py` MUST link to the contract document and restate D-1, D-2, D-3, D-4, D-5 inline. | Approved |
| FR-011 | The contract document MUST include a "Consumer responsibilities" section that names CLI, SaaS materializer, and drain worker as the three consumers and points to their respective issues for follow-up. | Approved |
| FR-012 | The contract document MUST include a "Diagnostic surface separation" subsection that explicitly states `ReconciliationDiagnostic` events are NOT infra failures and MUST be reported on a separate health surface from infra terminal failures. (This is the contract-side requirement that `spec-kitty-saas#204/#206` consume.) | Approved |
| FR-013 | The `ReconciliationDiagnostic` `reason_code` field MUST be a closed enum; at minimum it MUST include: `from_lane_mismatch_replay`, `from_lane_mismatch_drift`, `terminal_replay_skipped`, `unforced_rollback_without_review_ref`. Adding a new code MUST require updating the contract document and a fixture. | Approved |

## Non-Functional Requirements

| ID | Description | Threshold | Status |
|----|-------------|-----------|--------|
| NFR-001 | Conformance fixture suite MUST run as part of `pytest` in this repo. | Aggregate runtime for the new fixtures < 5 seconds. | Approved |
| NFR-002 | New `pytest` tests added by this mission MUST pass with `uv run pytest` on `main` checked out at HEAD. | 0 failures, 0 errors. | Approved |
| NFR-003 | Contract document MUST be ≤ 600 lines of markdown to remain reviewable in one pass. | line count ≤ 600 | Approved |
| NFR-004 | The contract document MUST be linked from `README.md` under a "Contracts" section so external consumers can discover it. | One link added; `grep "wp-status-changed.md" README.md` returns ≥ 1 hit. | Approved |

## Constraints

| ID | Description | Status |
|----|-------------|--------|
| C-001 | No change to `_ALLOWED_TRANSITIONS`, `TERMINAL_LANES`, `validate_transition`, or `StatusTransitionPayload` field set. The matrix is already correct; this mission documents it. | Approved |
| C-002 | No new dependencies (no additions to `pyproject.toml`). | Approved |
| C-003 | `ReconciliationDiagnostic` MUST be a frozen Pydantic model (`model_config = ConfigDict(frozen=True, extra="forbid")`) consistent with the rest of `status.py`. | Approved |
| C-004 | This mission MUST land before `spec-kitty#1090/1088/1087/1089` and `spec-kitty-saas#204/205/206`, which consume this contract. | Approved |
| C-005 | The contract document MUST cite the existing `_ALLOWED_TRANSITIONS` matrix verbatim (line-anchored, or reproduced as a table) so future drift is detectable. | Approved |

## Success Criteria (measurable, technology-agnostic)

- SC-1: A reviewer can read `docs/contracts/wp-status-changed.md` and, without reading `status.py`, correctly answer "does `in_review → planned` with `actor: user` and `review_ref: <ref>` require force?" → NO.
- SC-2: Every entry in `_ALLOWED_TRANSITIONS` has a corresponding accept-fixture (or is named in a rollback-fixture).
- SC-3: A consumer implementor can construct a `ReconciliationDiagnostic` payload using only the contract document and have it pass schema validation.
- SC-4: Every `reason_code` defined in D-4 / FR-013 appears in at least one fixture in the conformance manifest.
- SC-5: A SaaS materializer that follows the contract document classifies the 22 historical `in_review → planned` events from the 2026-05-17 incident as ACCEPT, not as `terminal_failed`. (This is verified later by `spec-kitty-saas#205` against the fixture set; the fixture set is the testable artefact owned by this mission.)

## Key Entities

- **WPStatusChanged event**: producer-emitted event describing a lane transition. Wraps `StatusTransitionPayload`.
- **StatusTransitionPayload**: existing frozen Pydantic model in `src/spec_kitty_events/status.py`. Field set is locked by C-001.
- **ReconciliationDiagnostic**: NEW frozen Pydantic model introduced by FR-006. Emitted by consumers when they refuse to apply or replay a `WPStatusChanged` event under a known business rule.
- **Conformance fixture**: a JSON file under `src/spec_kitty_events/conformance/fixtures/wp_status_changed/` paired with a manifest entry that declares its expected outcome. Binding per D-6.

## Domain Language

- **Review rollback** — a transition from `for_review`, `in_review`, or `approved` back to `in_progress`, `planned`, or `for_review`. Sanctioned in the matrix; requires `review_ref`; does NOT require `force`.
- **Terminal exit** — a transition out of `done` or `canceled`. Requires `force=True` with a non-empty `reason`.
- **Force** — a producer-side override for transitions not in the matrix and for terminal exit. Requires `reason`. Not a substitute for `review_ref` on review rollback.
- **Replay** — a consumer re-applying an event it has already applied. Detected by `event_id` (preferred) or `(mission_slug, wp_id, sequence)`. Idempotent.
- **Reconciliation** — a consumer's deterministic response to a `from_lane` mismatch or terminal replay. Produces a `ReconciliationDiagnostic`, never an infra failure.
- **Diagnostic surface** — the health/metrics endpoint that surfaces `ReconciliationDiagnostic` events. Distinct from the infra-failure surface owned by SaaS readiness.

## Assumptions

- A-1: `event_id` is present and unique on every emitted `WPStatusChanged` event in current producer code. If a future producer drops `event_id`, this contract's replay rule degrades to `(mission_slug, wp_id, sequence)` matching.
- A-2: `review_ref` is opaque to this repo — it can be a file path, a URL, or a structured identifier. The contract only requires non-empty.
- A-3: Consumers are responsible for persisting their projection state. This contract does not specify a projection storage shape.

## Out of scope clarifications (deferred to downstream missions)

- The exact infra-failure vs reconciliation health-bucket split lives in `spec-kitty-saas#204/#206`. This contract defines the diagnostic shape; downstream missions wire it up.
- The CLI's force-emission policy (when CLI should set `force=True` itself) lives in `spec-kitty#1089/#1087`. This contract defines what consumers must accept.
- E2E canary coverage for the full path lives in `spec-kitty-end-to-end-testing#41`.

## Dependencies

- Upstream: none. This mission is the dependency root for the MVP launch blocker program.
- Downstream consumers: `spec-kitty#1090`, `spec-kitty#1088`, `spec-kitty#1087`, `spec-kitty#1089`, `spec-kitty-saas#205`, `spec-kitty-saas#204`, `spec-kitty-saas#206`, `spec-kitty-end-to-end-testing#41`.
