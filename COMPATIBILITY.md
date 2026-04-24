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
