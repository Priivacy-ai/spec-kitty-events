# Contract: Backward Transitions — The Review-Rejection Family

**Audience**: Implementers of `WPStatusChanged` emitters (CLI, automation, agent tooling) and consumers (SaaS materializer, durable drain, projection engine, readiness/health).

**Status**: Normative. This document is the source of truth for the wire shape of user-deliberate backward lane transitions in the canonical `WPStatusChanged` event.

This is the **draft text** that lands in two places during implementation:
1. The module docstring of `src/spec_kitty_events/status.py` (top section).
2. A new section titled "Backward Transitions: The Review-Rejection Family" in `docs/consumer-contract-dossier-v2.4.0.md`.

Both copies are kept in sync. Sibling missions in `spec-kitty` (CLI emit path) and `spec-kitty-saas` (materializer + drain) cite either anchor.

---

## Section 1 — The Family

The **review-rejection transition family** is the named set of legitimate forced backward lane transitions in `WPStatusChanged`:

| `from_lane` | `to_lane` |
|---|---|
| `in_progress` | `planned` |
| `for_review` | `planned` |
| `in_review` | `planned` |
| `approved` | `planned` |

These transitions arise from user-deliberate rewinds in the work-package lifecycle — most commonly a review rejection that returns a WP to `planned` for re-implementation. They are not infrastructure events and they are not graph errors.

## Section 2 — Wire Requirements

For every event in the family, the emitting agent MUST set:

1. `force = True` — explicit acknowledgement that the transition is a user-deliberate rewind, not a forward step.
2. `reason` — a non-empty string. Enforced by the existing `StatusTransitionPayload` model validator: `force=True requires a non-empty reason`.

Recommended canonical `reason` shape:

```
backward rewind: <from_lane> -> <to_lane>[: <feedback-ref>]
```

- `<from_lane>` / `<to_lane>` are the literal `Lane` enum values.
- `<feedback-ref>` is optional. When present, the recommended URI shape is `feedback://<mission-slug>/<wp-id>/<timestamp>-<hash>.md`.

Optional but recommended:
- `review_ref` — URI-shaped pointer to the review feedback artifact. Same value as `<feedback-ref>` above when both are populated.
- A separate `ForceMetadata` record carrying the structured `(actor, reason)` audit pair, attached at the carrying `Event` envelope level. Consumers MAY rely on payload `reason` alone; `ForceMetadata` is for structured audit pipelines.

The wire payload shape is otherwise unchanged from `StatusTransitionPayload`. No new fields, no removed fields.

## Section 3 — Unforced Backward Transitions Are Contract-Invalid

A `WPStatusChanged` event with a `from_lane → to_lane` pair drawn from the family table but `force = False` is **contract-invalid**.

- The existing `validate_transition()` validator rejects such events via the lane matrix check.
- Consumers (materializers, projection engines, drain workers) MAY reject these events as graph violations and SHOULD classify them as **business-rule rejections**, not transient infrastructure failures. See `spec-kitty-saas` for the drain/readiness implications.
- The CLI emit path in `spec-kitty` MUST NOT produce unforced backward transitions. Either fail locally with a guidance message, or auto-promote `force=True` and synthesize a canonical `reason` per the recommended shape.

## Section 4 — Relationship to `ReviewRollback`

`ReviewRollback` (declared in `src/spec_kitty_events/lifecycle.py:196`) is a **mission-level** event recording the higher-level intent of a review rejection (`mission_id`, `review_ref`, `target_phase`, `affected_wp_ids`, `actor`). It is not a substitute for the per-WP `WPStatusChanged` events in the family.

The two records are complementary:

- `ReviewRollback` = "the mission rolled back to phase X because of review Y, affecting WPs [A, B, C]".
- `WPStatusChanged(force=True, ...)` per affected WP = "WP-A moved from `in_review` to `planned` as part of that rollback".

Consumers projecting state should reduce both event streams. Emitters MAY emit only the per-WP `WPStatusChanged` events when no mission-level rollback occurred (e.g. a single reviewer rejecting a single WP).

## Section 5 — Distinction from Bootstrap-Planned Events

A forced `* → planned` transition with `from_lane = None` (or absent / initial-seeding semantics) is a **bootstrap-planned event**, not a review-rejection. The contract distinguishes them:

- Bootstrap-planned: `from_lane is None`, `to_lane = planned`, `force = True`, `reason` typically explains initial seeding. Identified by `is_bootstrap_planned_event()` (`status.py:110-131`).
- Review-rejection family member: `from_lane in {in_progress, for_review, in_review, approved}`, `to_lane = planned`, `force = True`, `reason` follows the recommended backward-rewind shape.

A consumer must not classify a bootstrap-planned event as a review rejection or vice versa.

## Section 6 — Conformance Fixtures

The conformance fixture set under `src/spec_kitty_events/conformance/fixtures/` includes:

| Fixture path | Manifest id | Purpose |
|---|---|---|
| `edge_cases/replay/wp_review_rejection_cycle.jsonl` | `wp-review-rejection-cycle-replay` | Full lifecycle replay stream including one review-rejection round-trip (`planned → claimed → in_progress → for_review → in_review → planned → claimed → in_progress → for_review → in_review → approved`). |
| `edge_cases/valid/wp_status_changed_approved_rewind.json` | `wp-status-changed-approved-rewind-valid` | Single `WPStatusChanged` payload for `approved → planned` with `force=True + reason` (synthetic minimal mirror of the planning#16 evidence-pack shape). |
| `edge_cases/invalid/wp_status_changed_unforced_in_review_to_planned.json` | `wp-status-changed-unforced-in-review-to-planned-invalid` | Single `WPStatusChanged` payload for `in_review → planned` with `force=False`. Validator MUST reject. |

Sibling missions cite these by manifest id when authoring regression tests.

## Section 7 — Forward-Transition Guards Unaffected

Forward-transition guard semantics — including but not limited to `planned → claimed`, `in_progress → for_review`, `in_review → approved` — are unchanged by this contract section. The `force=True` mechanism is reserved for documented backward families and terminal-lane exits. It MUST NOT be used to bypass forward guards or evidence requirements.

## Cross-References

- Module docstring: `src/spec_kitty_events/status.py` (mirror of this content).
- Pydantic model: `StatusTransitionPayload` (`status.py:236`).
- Validator: `validate_transition` (`status.py:392`).
- Bootstrap distinction: `is_bootstrap_planned_event` (`status.py:110`).
- Mission-level rollback event: `ReviewRollbackPayload` (`lifecycle.py:196`).
- Planning issue: `Priivacy-ai/spec-kitty-planning#16`.
