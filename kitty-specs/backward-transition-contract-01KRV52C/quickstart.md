# Quickstart: Consuming the Backward-Transition Contract

**Audience**: Implementers in `spec-kitty` (CLI emit path) and `spec-kitty-saas` (materializer / drain / readiness) writing regression tests against the planning#16 fix.

This file is a recipe — it shows how to import the new conformance fixtures and assert against them. It is not part of the published package; consumers copy the recipe into their own test files.

## 1. Pin the contract anchor in your test file

```python
# Reference the canonical contract in a docstring or comment so future
# maintainers can find it quickly.
"""
Test against the review-rejection transition family.

Contract: src/spec_kitty_events/status.py (module docstring)
Reference: docs/consumer-contract-dossier-v2.4.0.md ("Backward Transitions: The Review-Rejection Family")
Planning issue: Priivacy-ai/spec-kitty-planning#16
"""
```

## 2. Load the conformance fixtures

```python
from spec_kitty_events.conformance import load_fixtures
from spec_kitty_events.conformance.loader import load_replay_stream

# Family-level positive: the full review-rejection cycle JSONL.
cycle_events = load_replay_stream("wp-review-rejection-cycle-replay")

# Single-event positive: the approved-rewind case.
edge_cases = {fc.id: fc for fc in load_fixtures("edge_cases")}
approved_rewind = edge_cases["wp-status-changed-approved-rewind-valid"]
unforced_invalid = edge_cases["wp-status-changed-unforced-in-review-to-planned-invalid"]
```

## 3. Assert your CLI / materializer behaves correctly

### In `spec-kitty` (CLI emit path)

```python
# When a user requests `move-task WP01 --to planned` from `in_review`,
# the CLI should emit a WPStatusChanged event matching the approved_rewind
# shape (force=True, reason starting with "backward rewind: ...").
emitted = run_move_task_capture_event(wp="WP01", to="planned", from_lane="in_review")
assert emitted["payload"]["force"] is True
assert emitted["payload"]["reason"].startswith("backward rewind: in_review -> planned")
assert emitted["payload"]["to_lane"] == "planned"
```

### In `spec-kitty-saas` (materializer)

```python
from spec_kitty_events.status import WPStatusChangedPayload

# Forced backward transition materializes cleanly.
payload = WPStatusChangedPayload.model_validate(approved_rewind.payload)
assert payload.force is True
result = materialize_status_event(payload)
assert result.status == "applied"

# Unforced backward transition is classified as a business-rule rejection,
# NOT as infrastructure terminal_failed.
unforced_payload = unforced_invalid.payload  # raw dict, no model validation
result = materialize_raw(unforced_payload)
assert result.classification == "business_rule_rejection"
assert result.classification != "infra_terminal_failed"
```

### In `spec-kitty-saas` (drain / readiness)

```python
# A business-rule rejection must NOT poison /health/ready/ as infra debris.
seed_drain_with(unforced_payload)
metrics = readiness_snapshot()
assert metrics.infra_terminal_failed_count == 0
assert metrics.business_rule_rejection_count == 1
assert metrics.ready is True
```

## 4. Reduce the full cycle as a smoke test

```python
from spec_kitty_events.status import reduce_status_events

# The cycle JSONL contains the canonical happy-path with one review-rejection
# round-trip. Reducing it yields a final state of `approved`.
final_state = reduce_status_events(cycle_events)
assert final_state.wps["WP01"].lane == "approved"
```

If the reducer is internal to the consumer rather than `spec_kitty_events`, use the consumer's projection engine instead. The fixture is shape-stable — only the projection logic differs across consumers.

## 5. Cite the contract in your PR

In the PR description for the planning#16 fix in your repo, include:

```
Contract anchor:
- spec-kitty-events module docstring at `src/spec_kitty_events/status.py`
- docs/consumer-contract-dossier-v2.4.0.md § "Backward Transitions: The Review-Rejection Family"
Conformance fixture used:
- <fixture id> at <fixture path>
```

This keeps the cross-repo traceability the planning#16 fix requires.

## Out of Scope for This Quickstart

- Mutating the 22 dev evidence events in `~/spec-kitty-dev/terminal-failed-evidence-2026-05-17.json`. Use the synthetic fixtures from this mission instead.
- Introducing a new event type. The review-rejection family is expressed through existing `WPStatusChanged` events with `force=True + reason`.
