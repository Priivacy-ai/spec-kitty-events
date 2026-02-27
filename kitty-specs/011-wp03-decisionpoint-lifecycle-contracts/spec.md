# Feature Specification: DecisionPoint Lifecycle Contracts

**Feature Branch**: `011-wp03-decisionpoint-lifecycle-contracts`
**Created**: 2026-02-27
**Status**: Draft
**Input**: Program WP03 objective for canonical DecisionPoint lifecycle contracts

## Problem

Spec Kitty 2.x currently has decision-adjacent events (`DecisionInputRequested`, `DecisionInputAnswered`, `DecisionCaptured`) but does not provide one canonical, replay-safe lifecycle contract for DecisionPoint state transitions. Runtime and SaaS consumers therefore cannot rely on one deterministic event family for audit-grade decision tracking across open, discussing, resolved, and overridden states.

## Goals

- Define one canonical DecisionPoint lifecycle event family for `open`, `discussing`, `resolved`, and optional `overridden`.
- Make audit-critical payload fields mandatory for every DecisionPoint lifecycle event.
- Enforce authority policy in contract validation and reduction rules:
  - Mission owner is always human and has final authority.
  - LLM roles are advisory or informed only in P0.
- Guarantee deterministic and replay-safe reduction behavior for runtime and SaaS consumers.

## Non-goals

- Implement CLI workflow changes for prompting or collecting decisions.
- Rework existing mission-next decision contracts beyond explicit integration notes.
- Build SaaS UI screens or dashboard rendering for DecisionPoint timelines.
- Add 1.x compatibility behavior or legacy fallbacks.

## Locked Constraints

- Mission owner final authority cannot be delegated to LLM actors.
- `resolved` and `overridden` lifecycle transitions require human actor attribution.
- Decision audit trail fields are mandatory in every lifecycle payload.
- Contracts remain additive in 2.x with deterministic JSON schema output.

## Scope

### In scope

- Event constants and payload models for DecisionPoint lifecycle events.
- Reducer transition rules and anomaly handling for replay-safe materialization.
- Conformance fixtures, replay streams, and schema registration.
- Public export and versioning notes for downstream runtime and SaaS consumers.

### Out of scope

- Mission policy engine redesign.
- Authorization backend implementation details.
- Consumer-specific persistence schema migrations.

## Functional Requirements

- **FR-001**: The library MUST define canonical DecisionPoint lifecycle constants and event set:
  - `DECISION_POINT_OPENED` -> `"DecisionPointOpened"`
  - `DECISION_POINT_DISCUSSING` -> `"DecisionPointDiscussing"`
  - `DECISION_POINT_RESOLVED` -> `"DecisionPointResolved"`
  - `DECISION_POINT_OVERRIDDEN` -> `"DecisionPointOverridden"`
  - `DECISION_POINT_EVENT_TYPES` as a frozen set containing exactly those four types
  - `DecisionPointState` enum containing `open`, `discussing`, `resolved`, `overridden`

- **FR-002**: Each DecisionPoint lifecycle payload model MUST be frozen and MUST require these audit-critical fields: `decision_point_id`, `mission_id`, `run_id`, `feature_slug`, `phase`, `actor_id`, `actor_type`, `authority_role`, `mission_owner_authority_flag`, `mission_owner_authority_path`, `rationale`, `alternatives_considered`, `evidence_refs`, `state_entered_at`, and `recorded_at`. `alternatives_considered` and `evidence_refs` MUST be non-empty collections.

- **FR-003**: The reducer MUST implement deterministic lifecycle transitions and policy checks using sorted-plus-deduped input (`status_event_sort_key` then `dedup_events`). Allowed transitions are: `None -> open`, `open -> discussing|resolved`, `discussing -> discussing|resolved`, `resolved -> overridden` (optional), and no transitions after `overridden`. Any `resolved` or `overridden` event MUST have `actor_type="human"`, `authority_role="mission_owner"`, and `mission_owner_authority_flag=true`. Any LLM actor MUST be limited to advisory or informed roles in `phase="P0"` and MUST NOT carry mission-owner authority.

- **FR-004**: Conformance coverage MUST include DecisionPoint fixtures and tests: at least 8 valid fixtures, 6 invalid fixtures, and 3 replay streams with committed golden outputs. Invalid fixtures MUST include authority-policy failures and missing mandatory audit-trail fields.

- **FR-005**: Replay safety MUST be verified by reducer tests and property checks proving deterministic output across event permutations and duplicate-event input (idempotent dedup behavior), with no non-deterministic fields in reduced state output.

- **FR-006**: The DecisionPoint contract family MUST be exported through the public package API and documented in versioning/export notes for consumers. All new fixtures and manifest entries MUST carry `min_version: "2.6.0"`, and downstream impact notes MUST explicitly state additive 2.x adoption steps for `spec-kitty` runtime and `spec-kitty-saas`.
