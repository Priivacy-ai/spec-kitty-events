# Phase 1: Data Model

**Mission**: backward-transition-contract-01KRV52C
**Scope**: Recap of the existing contract surface this mission documents. No new types, no wire-shape changes (C-003, C-006).

## Existing Entities (Unchanged)

### `StatusTransitionPayload`

**Source**: `src/spec_kitty_events/status.py:236`

Public Pydantic model describing a lane transition for one work package. Frozen, schema-versioned via the canonical `Event` envelope.

| Field | Type | Required | Notes for backward-transition family |
|---|---|---|---|
| `wp_id` | `str` | Yes | The work package being moved. |
| `from_lane` | `Lane \| None` | Optional | The lane before the transition. For review-rejection family members, this is one of `in_review`, `approved`, `for_review`, `in_progress`. |
| `to_lane` | `Lane` | Yes | The lane after the transition. For review-rejection family members, always `planned`. |
| `actor` | `str` | Yes | Who triggered the move. For user-deliberate rewinds, typically `user`. |
| `force` | `bool` | No (default False) | **MUST be `True` for any review-rejection family member.** Unforced backward transition is contract-invalid. |
| `reason` | `str \| None` | Conditional | **Required when `force=True`** per existing model validator (`force=True requires a non-empty reason`). For the family, the recommended shape is `"backward rewind: <from> -> <to>[: <feedback-ref>]"` per FR-010. |
| `execution_mode` | `str` | Yes | `worktree` or equivalent. |
| `review_ref` | `str \| None` | Optional | URI-shaped pointer to a review feedback artifact. Recommended for review-rejection family members. |
| `evidence` | `Any \| None` | Optional | Pass-through. |
| `mission_slug` | `str` | Yes | Mission selector. |

Invariants enforced by the model validator (`status.py:318-321`):
- `force=True ⇒ reason ≠ None and reason.strip() ≠ ""`

Invariants enforced by `validate_transition()` (`status.py:392-420`):
- Terminal-lane exit requires `force=True`.
- Matrix-listed backward transitions require `force=True`.
- `force=True` bypasses the matrix check (audit trail is provided by `force_metadata` / `reason`).
- Guard conditions (e.g. `in_progress -> planned requires reason`) run regardless of `force`.

### `ForceMetadata`

**Source**: `src/spec_kitty_events/status.py:226`

| Field | Type | Required | Notes |
|---|---|---|---|
| `force` | `Literal[True]` | Yes | Always literal `True`. |
| `actor` | `str` (min_length=1) | Yes | Who forced the transition. |
| `reason` | `str` (min_length=1) | Yes | Why. |

When present alongside a `StatusTransitionPayload` (the canonical attachment site is the carrying `Event` envelope's metadata block), this carries the audit trail. The plan does not require `ForceMetadata` to be attached to every family-member event — the carrying envelope's `force=True + reason` in the payload is sufficient. `ForceMetadata` remains the canonical place for structured audit context when consumers want to record it separately.

### `Lane`

**Source**: `src/spec_kitty_events/status.py:20-` (enum)

Members relevant to the review-rejection family: `planned`, `claimed`, `in_progress`, `for_review`, `in_review`, `approved`. (Other members like `done`, `blocked`, `canceled` are not part of this mission's contract surface.)

### `ReviewRollbackPayload`

**Source**: `src/spec_kitty_events/lifecycle.py:196`

Pre-existing **mission-level** event. Records the higher-level intent of a review rejection (which phase, which WPs are affected, who triggered it). Distinct from `WPStatusChanged` — the rollback says "the mission rolled back"; the status-changes say "WP-N moved back in lane". The contract documentation cross-links both as complementary records, not substitutes.

| Field | Type | Required |
|---|---|---|
| `mission_id` | `str` | Yes |
| `review_ref` | `str` | Yes |
| `target_phase` | `str` | Yes |
| `affected_wp_ids` | `List[str]` | Default empty |
| `actor` | `str` | Yes |

## New Conceptual Set (Documented Only — Not a New Type)

### Review-Rejection Transition Family

| Member | `from_lane` | `to_lane` | Required `force` | Required `reason` shape |
|---|---|---|---|---|
| Implementer rewind | `in_progress` | `planned` | `True` | `"backward rewind: in_progress -> planned[: <feedback-ref>]"` |
| Pre-review rewind | `for_review` | `planned` | `True` | `"backward rewind: for_review -> planned[: <feedback-ref>]"` |
| Reviewer rejection (in-flight) | `in_review` | `planned` | `True` | `"backward rewind: in_review -> planned[: <feedback-ref>]"` |
| Post-approval rewind | `approved` | `planned` | `True` | `"backward rewind: approved -> planned[: <feedback-ref>]"` |

All four members are documented in the `status.py` module docstring and in `docs/consumer-contract-dossier-v2.4.0.md`. No code change to the enum or to the payload model.

## Out-of-Family (Documented as Distinct)

- **Bootstrap-planned** (`* → planned` when forced AND `from_lane` is empty/initial): governed by `is_bootstrap_planned_event()` (status.py:110-131). Distinct semantic — it represents initial seeding, not a user-deliberate rewind. Documentation will name this distinction explicitly to avoid downstream confusion.
- **Forward transitions**: all guard semantics preserved. This mission does not touch forward transitions.
