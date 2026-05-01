# Compatibility Guide

`spec-kitty-events` `4.0.0` is a fail-closed contract cutover release.

This document is the public compatibility policy for consumers of:

- `spec-kitty-events`
- `spec-kitty-saas`
- `spec-kitty`

## Canonical On-Wire Policy

The authoritative cutover artifact ships in the package and defines the live compatibility gate.

- Signal field: `schema_version`
- Signal location: event envelope
- Required cutover value: `4.0.0`
- Accepted major: `4`

Live ingestion paths fail closed when any of the following are true:

- the envelope is missing `schema_version`
- `schema_version` has the wrong accepted major
- `schema_version` does not equal `4.0.0`
- the envelope or nested payload contains forbidden legacy keys
- the envelope uses forbidden legacy event names
- the envelope uses forbidden legacy aggregate prefixes

## Forbidden Legacy Surfaces

The `4.0.0` release rejects these legacy mission-domain surfaces on live paths:

- keys: `feature_slug`, `feature_number`, `mission_key`
- event names: `FeatureCreated`, `FeatureClosed`
- aggregate prefixes: `feature`, `feature_catalog`

## Canonical Mission And Build Taxonomy

Public mission-domain payloads use:

- `mission_slug`: canonical mission instance identifier
- `mission_number`: canonical numeric mission identifier
- `mission_type`: canonical workflow/template identifier

Event envelopes distinguish build and node identity explicitly:

- `build_id`: emitting build identifier
- `node_id`: emitting node identifier within that build

## Rollout Policy

There are no runtime compatibility bridges in live ingestion.

- New producers must emit canonical `4.0.0` envelopes from day one.
- Consumers must reject legacy mission-domain envelopes on live paths.
- Historical `2.x` or pre-cutover data may only be read by offline migration or rewrite jobs.
- Offline rewrite workflows must convert historical data into canonical `4.0.0` form before re-ingestion.

## Cross-Repo Release Gates

`spec-kitty-events` should only be treated as released when all of the following are true:

1. `spec-kitty-events` package metadata is `4.0.0`.
2. Committed JSON Schemas are regenerated and drift-free.
3. Conformance fixtures and replay goldens pass with artifact-driven validation.
4. `spec-kitty-saas` is updated to emit canonical `4.0.0` envelopes only.
5. `spec-kitty` is updated to consume canonical mission/build terminology and fail-closed validation outcomes.

## Consumer Guidance

If you operate a producer:

- emit `schema_version="4.0.0"`
- emit `build_id`
- emit canonical mission-domain fields only

If you operate a consumer:

- validate the envelope signal before processing payload content
- reject forbidden legacy mission-domain fields and names
- treat pre-cutover data as migration input, not live traffic

## Quick Reference

Accepted live envelope:

```json
{
  "event_type": "WPStatusChanged",
  "aggregate_id": "mission/WP01",
  "schema_version": "4.0.0",
  "build_id": "build-2026-04-05",
  "node_id": "runner-01",
  "payload": {
    "mission_slug": "mission-001",
    "wp_id": "WP01",
    "from_lane": "planned",
    "to_lane": "claimed",
    "actor": "ci-bot",
    "execution_mode": "worktree"
  }
}
```

Rejected live envelope examples:

- envelope without `schema_version`
- envelope with `schema_version="2.9.0"`
- payload containing `feature_slug`
- envelope with `event_type="FeatureCreated"`
- envelope with `aggregate_id="feature/123"`

## Versioning

`4.0.0` is the breaking release that publishes the canonical mission/build contract.

- `2.x` additive compatibility language no longer applies.
- Future breaking contract changes require a new major release.

## Decision Moment V1 (4.0.0)

### Scope

- **Breaking for DecisionPoint.** The `DecisionPoint*` event family (excluding `DecisionPointOverridden`) now carries `origin_surface` and supports discriminated-union payloads. `DecisionPointResolved` (interview variant) requires `terminal_outcome`.
- **Compatible for DecisionInput.** `DecisionInputRequested` and `DecisionInputAnswered` payloads are unchanged. 3.x consumers continue to validate.

### Producer migration

| Producer                | 3.x action                         | 4.0.0 action                                                   |
|-------------------------|------------------------------------|----------------------------------------------------------------|
| ADR DecisionPoint       | Emit 3.x payload                   | Add `origin_surface: "adr"` to every payload                    |
| Interview DecisionPoint | (n/a — didn't exist)               | Use `origin_surface: "planning_interview"` + V1 fields          |
| DecisionInput* events   | Emit as-is                         | No change                                                       |

### Consumer migration

| Consumer                              | 3.x action                                       | 4.0.0 action                                                                 |
|---------------------------------------|--------------------------------------------------|------------------------------------------------------------------------------|
| DecisionPoint replay / reducer        | Reduce 3.x ADR payloads                          | Reduce ADR + V1 interview events via the single reducer (discriminated by `origin_surface`) |
| DecisionInput* consumers              | Consume as-is                                    | No change                                                                    |
| Slack orchestrator                    | (n/a)                                            | Subscribe to `DecisionPointWidened`; post closure message on `DecisionPointResolved` |
| Teamspace projection                  | (n/a)                                            | Project V1 fields from `DecisionPointResolved` interview variant             |

### Terminal outcome / write-back rules

- `DecisionInputAnswered` is emitted ONLY when `DecisionPointResolved.terminal_outcome == "resolved"` AND `final_answer` is populated. Deferred and canceled outcomes do NOT emit a `DecisionInputAnswered` (no answer exists).
- `DecisionPointResolved.closed_locally_while_widened=true` is legal only when a prior `DecisionPointWidened` exists for the same `decision_point_id`. Reducers raise an anomaly (`kind="invalid_transition"`) and project the field as `false` if the precondition is not met.

### No grace period

4.x validators fail closed on missing `terminal_outcome` or missing `origin_surface`. There is no temporary permissive path. Downstream consumers must migrate deliberately against this contract boundary.

## Local-CLI compatibility vs TeamSpace ingress validity (added 2026-05-01)

The `5.0.0` major release sharpens a distinction that has always been implicit in
`spec-kitty-events`: there are two distinct validity domains, and a row that is
acceptable in one is not necessarily acceptable in the other. This section is the
authoritative explanation. Consumers and producers must read it before assuming
that "valid" is a single global property.

### The two validity domains

- **Local-CLI compatibility.** The `spec-kitty` CLI continues to read historical
  `status.events.jsonl` rows on local disk for users' own bookkeeping —
  reconstructing a mission's history, rendering local dashboards, replaying
  status, computing diff summaries, etc. The CLI's local reader is deliberately
  permissive: it tolerates pre-cutover envelope shapes (including legacy keys
  such as `feature_slug`, `mission_key`, raw rows missing `schema_version`, and
  pre-canonical lane vocabularies) so that users do not lose access to their own
  historical data after this bump. Local compatibility is **not** weakened by
  the `5.0.0` release.

- **TeamSpace ingress validity.** Only canonical envelopes pass TeamSpace
  ingress. The ingress path runs the full fail-closed contract gate from
  `4.0.0` plus the additions landed in this mission (canonical lane vocabulary
  including `in_review`, reconciled `MissionCreated`/`WPStatusChanged`/
  `MissionClosed` payloads, and the recursive forbidden-key validator that
  rejects legacy keys at any depth, including inside array elements). A row
  that the local CLI happily reads off disk will be rejected at TeamSpace
  ingress unless it has been canonicalized first.

### Concrete examples

A historical row that is **valid for the local CLI** but **invalid for
TeamSpace ingress** (legacy `feature_slug` key, missing `schema_version`):

```json
{"event_type":"FeatureCreated","aggregate_id":"feature/123","payload":{"feature_slug":"my-feature","feature_number":7}}
```

A canonical envelope that is **valid for both** the local CLI and TeamSpace
ingress (canonical mission-domain fields, canonical lane vocabulary including
`in_review`, `schema_version="5.0.0"`, no forbidden legacy keys at any depth):

```json
{"event_type":"WPStatusChanged","aggregate_id":"mission/WP01","schema_version":"5.0.0","build_id":"build-2026-05-01","node_id":"runner-01","payload":{"mission_slug":"mission-001","wp_id":"WP01","from_lane":"claimed","to_lane":"in_review","actor":"implementer-ivan","execution_mode":"worktree"}}
```

### The documented bridge

The bridge between these two domains is the **CLI canonicalizer** that ships in
`spec-kitty` Tranche B. The canonicalizer reads historical `status.events.jsonl`
rows and produces canonical `5.0.0` envelopes suitable for ingress. Producers
that need to forward historical data into TeamSpace MUST run it through the
canonicalizer first; ingress will not accept raw historical rows. Consumers
that read locally MUST NOT assume their local-disk rows have already been
canonicalized.

### Cross-references

- [`kitty-specs/teamspace-event-contract-foundation-01KQHDE4/contracts/lane-vocabulary.md`](kitty-specs/teamspace-event-contract-foundation-01KQHDE4/contracts/lane-vocabulary.md) — the canonical lane vocabulary including `in_review`.
- [`kitty-specs/teamspace-event-contract-foundation-01KQHDE4/contracts/payload-reconciliation.md`](kitty-specs/teamspace-event-contract-foundation-01KQHDE4/contracts/payload-reconciliation.md) — the reconciliation log for `MissionCreated`, `WPStatusChanged`, and `MissionClosed` payloads.

### Bump rationale (per R-03)

The `5.0.0` bump is a genuine major bump under semantic versioning. Per
research item R-03 (schema version bump semantic), each of the following is a
behavior change for at least one role and therefore each independently
justifies a major:

1. **Lane vocabulary widens.** `in_review` is now a canonical lane (FR-001,
   FR-002). Consumers that previously rejected `in_review` as unknown now
   accept it; consumers that switch on exact lane-set membership are
   behaviorally affected.
2. **Payload reconciliation.** `MissionCreatedPayload`,
   `WPStatusChangedPayload`, and `MissionClosedPayload` are now the single
   source of truth (FR-003, FR-004). CLI emission and library models have been
   reconciled; pre-bump producers of disagreeing shapes are now invalid.
3. **Recursive forbidden-key validator.** Legacy keys (`feature_slug`,
   `feature_number`, `mission_key`, plus the audit-derived expansion) are now
   rejected at any depth, including inside array elements (FR-005). Envelopes
   that previously slipped through with a deeply nested legacy key are now
   rejected.

These three changes compound: any one of them is a contract change for at
least one role, and together they require a major bump rather than a minor or
patch.
