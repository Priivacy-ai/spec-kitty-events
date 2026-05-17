# Data Model: WPStatusChanged Backward Transition Contract

## Existing entities (unchanged — locked by C-001)

### `Lane` enum
File: `src/spec_kitty_events/status.py`
Values: `PLANNED`, `CLAIMED`, `IN_PROGRESS`, `FOR_REVIEW`, `IN_REVIEW`, `APPROVED`, `DONE`, `BLOCKED`, `CANCELED`.

### `TERMINAL_LANES`
`frozenset({Lane.DONE, Lane.CANCELED})`. Exit requires `force=True`.

### `_ALLOWED_TRANSITIONS`
The transition matrix. Lines 342-368 of `status.py`. This mission documents but does NOT modify.

### `StatusTransitionPayload`
Pydantic frozen model wrapping the `WPStatusChanged` event payload. Fields: `mission_slug`, `wp_id`, `from_lane`, `to_lane`, `actor` (str|dict), `force`, `reason`, `execution_mode`, `review_ref`, `evidence`. Field set is locked by C-001.

### `validate_transition(payload) -> TransitionValidationResult`
Pure function that never raises. Returns `valid: bool` + `violations: tuple[str, ...]`. Locked by C-001.

## New entities

### `ReconciliationReasonCode` (StrEnum)

File: `src/spec_kitty_events/status.py` (appended near the bottom of the file, after the existing public API).

```python
class ReconciliationReasonCode(StrEnum):
    """Closed enum of reasons a consumer may emit a ReconciliationDiagnostic."""

    FROM_LANE_MISMATCH_REPLAY = "from_lane_mismatch_replay"
    FROM_LANE_MISMATCH_DRIFT = "from_lane_mismatch_drift"
    TERMINAL_REPLAY_SKIPPED = "terminal_replay_skipped"
    UNFORCED_ROLLBACK_WITHOUT_REVIEW_REF = "unforced_rollback_without_review_ref"
```

**Invariants**:
- Closed set; adding a value requires updating the contract document and at least one conformance fixture (D-6, FR-013).
- String value is the wire form. Consumers serialize and compare by string value.

### `ReconciliationDiagnostic`

File: `src/spec_kitty_events/status.py` (appended after `ReconciliationReasonCode`).

```python
class ReconciliationDiagnostic(BaseModel):
    """A consumer-emitted diagnostic recording a deterministic business-rule outcome.

    Emitted when a consumer refuses to apply, or chooses to skip, a WPStatusChanged
    event under a known rule (replay, drift, terminal replay, unforced rollback
    without review_ref). MUST NOT be counted toward infra-failure metrics.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    mission_slug: str = Field(..., min_length=1)
    wp_id: str = Field(..., min_length=1)
    event_id: str = Field(..., min_length=1, description="event_id of the WPStatusChanged event that triggered the diagnostic")
    expected_from_lane: Optional[Lane] = Field(None, description="from_lane on the offending event")
    actual_projected_lane: Optional[Lane] = Field(None, description="Lane the consumer's projection had for this WP at receipt")
    reason_code: ReconciliationReasonCode = Field(..., description="Closed-enum reason")
    actor: str = Field(..., min_length=1, description="Audit identity of the consumer that produced the diagnostic")
    detected_at: datetime = Field(..., description="UTC timestamp the consumer made the determination")
```

**Invariants**:
- Frozen + `extra="forbid"` (C-003).
- `event_id` is required so operators can trace the diagnostic to the offending event.
- `actor` here is the CONSUMER identity, not the producer's `actor` from `StatusTransitionPayload`.
- `detected_at` is UTC-naive `datetime` (consistent with this codebase's existing time handling).

### `RECONCILIATION_REASON_CODES`

A module-level tuple of the enum values, re-exported for downstream consumers that want a constant to iterate over without depending on the enum class:

```python
RECONCILIATION_REASON_CODES: Tuple[str, ...] = tuple(c.value for c in ReconciliationReasonCode)
```

## Relationships

- A `WPStatusChanged` event flowing into a consumer can produce zero or one `ReconciliationDiagnostic`. Replay-by-event_id at the consumer boundary is detected BEFORE this step and does not produce a diagnostic (except `terminal_replay_skipped`).
- A `ReconciliationDiagnostic` does NOT modify the consumer's projection state. It is observational.

## JSON Schema (committed)

`src/spec_kitty_events/schemas/reconciliation_diagnostic.schema.json` is generated from `ReconciliationDiagnostic` via the same pattern used for `status_transition_payload.schema.json`. A drift test asserts the committed file matches the model output.

## Conformance fixture format

Each fixture is a single JSON file under `src/spec_kitty_events/conformance/fixtures/wp_status_changed/` with this shape:

```json
{
  "fixture_id": "wp_status_changed.review_rejection_in_review_to_planned",
  "description": "User reviewer rejects WP from in_review back to planned.",
  "input": {
    "current_projection_lane": "in_review",
    "event": {
      "event_id": "01J6XW9KQT7M0YB3N4R5CQZ2EX",
      "event_type": "WPStatusChanged",
      "payload": {
        "mission_slug": "demo",
        "wp_id": "WP05",
        "from_lane": "in_review",
        "to_lane": "planned",
        "actor": "user",
        "force": false,
        "reason": null,
        "execution_mode": "interactive",
        "review_ref": "kitty-specs/demo/tasks/WP05/review-cycle-1.md",
        "evidence": null
      }
    }
  },
  "expected": {
    "outcome": "accept",
    "reason_code": null,
    "post_projection_lane": "planned",
    "violations": []
  }
}
```

The `outcome` field is one of: `accept`, `reject`, `reconcile`, `idempotency_skip`. The `reason_code` field is required when `outcome` is `reconcile` or `idempotency_skip`; otherwise `null`.

## Manifest entry shape

Each fixture is appended to `src/spec_kitty_events/conformance/fixtures/manifest.json` with:

```json
{
  "fixture_id": "wp_status_changed.review_rejection_in_review_to_planned",
  "fixture_file": "wp_status_changed/review_rejection_in_review_to_planned.json",
  "event_type": "WPStatusChanged",
  "outcome": "accept",
  "reason_code": null,
  "notes": "FR-007(b): review rejection from in_review to planned without force."
}
```
