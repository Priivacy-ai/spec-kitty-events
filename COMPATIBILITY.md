# Compatibility Guide

`spec-kitty-events` `3.0.0` is a fail-closed contract cutover release.

This document is the public compatibility policy for consumers of:

- `spec-kitty-events`
- `spec-kitty-saas`
- `spec-kitty`

## Canonical On-Wire Policy

The authoritative cutover artifact ships in the package and defines the live compatibility gate.

- Signal field: `schema_version`
- Signal location: event envelope
- Required cutover value: `3.0.0`
- Accepted major: `3`

Live ingestion paths fail closed when any of the following are true:

- the envelope is missing `schema_version`
- `schema_version` has the wrong accepted major
- `schema_version` does not equal `3.0.0`
- the envelope or nested payload contains forbidden legacy keys
- the envelope uses forbidden legacy event names
- the envelope uses forbidden legacy aggregate prefixes

## Forbidden Legacy Surfaces

The `3.0.0` release rejects these legacy mission-domain surfaces on live paths:

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

- New producers must emit canonical `3.0.0` envelopes from day one.
- Consumers must reject legacy mission-domain envelopes on live paths.
- Historical `2.x` or pre-cutover data may only be read by offline migration or rewrite jobs.
- Offline rewrite workflows must convert historical data into canonical `3.0.0` form before re-ingestion.

## Cross-Repo Release Gates

`spec-kitty-events` should only be treated as released when all of the following are true:

1. `spec-kitty-events` package metadata is `3.0.0`.
2. Committed JSON Schemas are regenerated and drift-free.
3. Conformance fixtures and replay goldens pass with artifact-driven validation.
4. `spec-kitty-saas` is updated to emit canonical `3.0.0` envelopes only.
5. `spec-kitty` is updated to consume canonical mission/build terminology and fail-closed validation outcomes.

## Consumer Guidance

If you operate a producer:

- emit `schema_version="3.0.0"`
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
  "schema_version": "3.0.0",
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

`3.0.0` is the breaking release that publishes the canonical mission/build contract.

- `2.x` additive compatibility language no longer applies.
- Future breaking contract changes require a new major release.
