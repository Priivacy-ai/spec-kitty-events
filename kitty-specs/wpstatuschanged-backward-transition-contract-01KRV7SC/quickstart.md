# Quickstart: WPStatusChanged Contract Consumer

This quickstart is for consumer engineers (spec-kitty CLI, spec-kitty-saas materializer, durable drain worker) wiring `WPStatusChanged` handling against the canonical contract.

## 1. Read the contract

Start at [`docs/contracts/wp-status-changed.md`](../../../../docs/contracts/wp-status-changed.md). The contract is short (~300 lines) and includes the allowed-transition matrix and the two reconciliation reason codes (`from_lane_mismatch_replay`, `from_lane_mismatch_drift`).

## 2. Validate transitions with `validate_transition`

```python
from spec_kitty_events.status import StatusTransitionPayload, validate_transition

payload = StatusTransitionPayload(
    mission_slug="demo",
    wp_id="WP05",
    from_lane="in_review",
    to_lane="planned",
    actor="user",
    force=False,
    review_ref="kitty-specs/demo/tasks/WP05/review-cycle-1.md",
    execution_mode="interactive",
)
result = validate_transition(payload)
assert result.valid, result.violations
```

A consumer that rejects this case as "invalid backward transition without force" is non-conformant. See contract §3.3.

## 3. Emit a `ReconciliationDiagnostic` on drift

```python
from datetime import datetime, timezone
from spec_kitty_events.status import ReconciliationDiagnostic, ReconciliationReasonCode

diag = ReconciliationDiagnostic(
    mission_slug="demo",
    wp_id="WP05",
    event_id="01J6XW9KQT7M0YB3N4R5CQZ2EX",
    expected_from_lane="in_progress",
    actual_projected_lane="planned",
    reason_code=ReconciliationReasonCode.FROM_LANE_MISMATCH_DRIFT,
    actor="saas-materializer",
    detected_at=datetime.now(timezone.utc),
)
```

Route `diag` to the drift surface, NOT to the infra-failure surface (contract §9).

## 4. Detect replay before validation

Maintain a set of seen `event_id` values per `wp_id`. On receipt:

```python
if event.event_id in seen_event_ids[event.payload.wp_id]:
    debug_log("replay", event_id=event.event_id)
    return  # idempotent skip
```

Do not emit a diagnostic for normal replay.

## 5. Run the conformance suite in CI

```bash
uv run pytest tests/test_wp_status_changed_contract_fixtures.py
```

Every fixture must pass. The fixtures live at `src/spec_kitty_events/conformance/fixtures/wp_status_changed/` and the manifest entries record the expected outcome and reason_code.

## 6. When in doubt, the fixtures win

If documentation and a fixture disagree, the fixture is canonical (contract D-6). File an issue against `spec-kitty-events` to bring documentation back in line; do not patch the consumer to match the documentation against the fixture.
