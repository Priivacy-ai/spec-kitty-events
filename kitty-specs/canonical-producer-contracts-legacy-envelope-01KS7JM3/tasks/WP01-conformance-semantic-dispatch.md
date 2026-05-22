---
work_package_id: WP01
title: Conformance semantic dispatch in validate_event() and seven-model registry
dependencies:
- WP02
requirement_refs:
- FR-001
- FR-002
- FR-003
- FR-004
- FR-005
- FR-011
- NFR-001
- NFR-005
- C-003
planning_base_branch: kitty/pr/1198-canonical-producer-contracts
merge_target_branch: kitty/pr/1198-canonical-producer-contracts
branch_strategy: Planning artifacts for this mission were generated on kitty/pr/1198-canonical-producer-contracts. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into kitty/pr/1198-canonical-producer-contracts unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-canonical-producer-contracts-legacy-envelope-01KS7JM3
base_commit: 18c8835265ccfeda116172ba6db02af518fc89d4
created_at: '2026-05-22T10:51:55.776444+00:00'
subtasks:
- T001
- T002
- T003
- T004
- T005
- T009
phase: Phase 2 - Semantic conformance
shell_pid: "74579"
agent: "claude:opus-4-7:reviewer-renata:reviewer"
history:
- timestamp: '2026-05-22T10:22:16Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/spec_kitty_events/conformance/
execution_mode: code_change
lane: planned
owned_files:
- src/spec_kitty_events/conformance/validators.py
- tests/unit/test_conformance_semantic.py
review_status: ''
reviewed_by: ''
role: implementer
tags: []
---

# Work Package Prompt: WP01 — Conformance semantic dispatch in `validate_event()`

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your assigned agent profile so you operate with the right governance scope and identity:

```text
/ad-hoc-profile-load python-pedro
```

If your environment does not support that slash command, run:

```bash
spec-kitty agent profile show python-pedro
```

and adopt the identity, governance scope, and boundaries it declares.

---

## ⚠️ Review Feedback Status

If `review_status` above says `has_feedback`, scroll to **Review Feedback** below and treat each item as a must-do. Update `review_status: acknowledged` when you start.

## Review Feedback

*(empty)*

---

## Objective

Two changes inside `src/spec_kitty_events/conformance/validators.py`, sharing the same file ownership:

1. **Semantic dispatch** — wire the existing `spec_kitty_events.status.validate_transition()` business-rule check into the public conformance gate `validate_event()`, so an unforced backward review-rejection transition (the rc14→rc22 drift signature) fails through the public path downstream consumers call. The wiring is additive and isolated behind a per-event-type registry so future semantic validators plug in cleanly.
2. **Seven-model registry** — add the seven `_EVENT_TYPE_TO_MODEL` entries for `WPAssigned`, `BuildRegistered`, `BuildHeartbeat`, `HistoryAdded`, `ErrorLogged`, `DependencyResolved`, `MissionOriginBound` so `validate_event()` covers them. The model classes themselves are shipped by WP02; this WP registers them.

WP01 is the sole owner of `validators.py`. WP02 (model classes) must land first; WP01 then imports them and adds the registry entries.

## Context

### The gap

`validators.py:validate_event()` validates a `WPStatusChanged` payload's shape via `StatusTransitionPayload.model_validate(...)` but never calls `status.validate_transition(model)`. As a result, this payload PASSES `validate_event` today:

```python
{
    "wp_id": "WP09",
    "from_lane": "in_review",
    "to_lane": "planned",
    "actor": "user",
    "force": False,                           # invalid: review-rejection requires force=True
    "reason": "rejected on review",
    "execution_mode": "worktree",
    "mission_slug": "demo",
    "review_ref": "feedback://demo/WP09/2026-05-18-review.md",
    "evidence": None,
}
```

But `status.validate_transition()` (in `status.py:541`) already returns a `TransitionValidationResult(valid=False, violations=("review-rejection rollback in_review -> planned requires force=True",))`. Downstream consumers route on substrings `force=True` and `review-rejection`. This WP makes `validate_event` surface that violation through its existing `ConformanceResult.model_violations` channel.

### Why a registry

The dispatch belongs in a `_SEMANTIC_VALIDATORS` table keyed by event_type so future event types with business rules (e.g. terminal-lane exit checks, force-required closure events) plug in without modifying `validate_event()` itself.

## Implementation guidance

### T001 — Add `_SEMANTIC_VALIDATORS` registry to `validators.py`

**File**: `src/spec_kitty_events/conformance/validators.py`

Add near the top of the module (after `_EVENT_TYPE_TO_MODEL` and `_EVENT_TYPE_TO_SCHEMA` declarations):

```python
from typing import Callable

# Registry of semantic (business-rule) validators that run AFTER pydantic
# shape validation succeeds. Each entry maps event_type -> a callable
# that takes the parsed pydantic model and the raw payload dict, and
# returns a tuple of ModelViolation instances (empty tuple if the model
# satisfies the semantic rule).
#
# Why a registry: shape validation is per-field; semantic validation is
# cross-field business rules (transition matrix, force-required families,
# guard-condition checks). Registry keeps validate_event() unchanged for
# event types without semantic rules and lets future event types plug in
# with one line.
_SEMANTIC_VALIDATORS: Dict[str, Callable[[Any, Dict[str, Any]], Tuple[ModelViolation, ...]]] = {}
```

**Files**: same module.

### T002 — Implement `_semantic_validate_wp_status_changed(model, payload)`

**File**: `src/spec_kitty_events/conformance/validators.py`

Add the validator and register it:

```python
def _semantic_validate_wp_status_changed(
    model: Any,  # StatusTransitionPayload (avoid circular import on the type)
    payload: Dict[str, Any],
) -> Tuple[ModelViolation, ...]:
    """Run status.validate_transition() and wrap violations as ModelViolation.

    The string messages from validate_transition() are preserved verbatim
    so downstream consumers can continue routing on the documented substrings
    ``force=True`` and ``review-rejection`` (see status.py module docstring,
    section 'Unforced backward transitions are contract-invalid').
    """
    from spec_kitty_events.status import validate_transition

    result = validate_transition(model)
    if result.valid:
        return ()
    return tuple(
        ModelViolation(
            field="transition",
            message=violation,
            violation_type="transition_rule",
            input_value=payload,
        )
        for violation in result.violations
    )


_SEMANTIC_VALIDATORS["WPStatusChanged"] = _semantic_validate_wp_status_changed
```

### T003 — Wire the dispatch into `validate_event()`

**File**: `src/spec_kitty_events/conformance/validators.py`

After the existing `model_violations = cutover_violations + _validate_with_model(model_payload, model_class)` line in `validate_event()`, insert the semantic dispatch:

```python
# Layer 1.5: Semantic (business-rule) validation. Run only when:
#   (a) pydantic shape validation produced no violations (so the model
#       parsed cleanly — semantic checks need a valid model instance), and
#   (b) the event type has a registered semantic validator.
# Synthesized semantic violations are appended to model_violations so they
# surface through the existing ConformanceResult.model_violations channel
# without API churn for downstream consumers.
if not model_violations and event_type in _SEMANTIC_VALIDATORS:
    parsed_model = model_class.model_validate(model_payload)
    semantic_violations = _SEMANTIC_VALIDATORS[event_type](parsed_model, model_payload)
    model_violations = model_violations + semantic_violations
```

The existing `valid = len(model_violations) == 0 and ...` line below already recomputes validity correctly after the append. No further edits to `validate_event()` are required.

**Note**: the `parsed_model = model_class.model_validate(model_payload)` re-parses the dict; this is safe because `_validate_with_model` already returned no violations (so the model construction is guaranteed to succeed) and the cost is one extra pydantic parse per `WPStatusChanged` event. NFR-001 (deterministic, side-effect-free) is preserved.

### T004 — Add `tests/unit/test_conformance_semantic.py`

**File**: `tests/unit/test_conformance_semantic.py` (NEW)

```python
"""Tests for validate_event() <-> validate_transition() semantic dispatch.

Covers FR-001..FR-005, the regression for force-with-empty-reason, and
the substring-routing contract that downstream consumers rely on.
"""
from __future__ import annotations

import pytest

from spec_kitty_events.conformance.validators import validate_event


_UNFORCED_BACKWARD_CASES = [
    pytest.param("in_progress", "planned", id="in_progress_to_planned"),
    pytest.param("for_review", "planned", id="for_review_to_planned"),
    pytest.param("in_review", "planned", id="in_review_to_planned"),
    pytest.param("approved", "planned", id="approved_to_planned"),
]


def _unforced_payload(from_lane: str, to_lane: str) -> dict:
    return {
        "wp_id": "WP01",
        "from_lane": from_lane,
        "to_lane": to_lane,
        "actor": "user",
        "force": False,
        "reason": "rejected on review",
        "execution_mode": "worktree",
        "mission_slug": "mission-test",
        "review_ref": "feedback://mission-test/WP01/2026-05-22-review.md",
        "evidence": None,
    }


@pytest.mark.parametrize(("from_lane", "to_lane"), _UNFORCED_BACKWARD_CASES)
def test_validate_event_rejects_unforced_review_rejection(from_lane: str, to_lane: str) -> None:
    """FR-001/FR-003: every review-rejection family transition without force=True fails."""
    payload = _unforced_payload(from_lane, to_lane)
    result = validate_event(payload, "WPStatusChanged")
    assert not result.valid
    assert result.model_violations
    messages = [v.message for v in result.model_violations]
    assert any("force=True" in m for m in messages), messages
    assert any("review-rejection" in m for m in messages), messages


def test_validate_event_accepts_forced_review_rejection_with_reason() -> None:
    """FR-004: the forced backward transition with non-empty reason passes."""
    payload = _unforced_payload("in_review", "planned")
    payload["force"] = True
    # reason already populated in _unforced_payload
    result = validate_event(payload, "WPStatusChanged")
    assert result.valid, result.model_violations


def test_validate_event_accepts_canonical_planned_to_claimed() -> None:
    """FR-004 regression: existing happy-path transition still passes."""
    payload = {
        "wp_id": "WP01",
        "from_lane": "planned",
        "to_lane": "claimed",
        "actor": "agent",
        "force": False,
        "execution_mode": "worktree",
        "mission_slug": "mission-test",
        "evidence": None,
    }
    result = validate_event(payload, "WPStatusChanged")
    assert result.valid, result.model_violations


def test_validate_event_accepts_bootstrap_planned_event() -> None:
    """FR-005: bootstrap-planned events (from_lane=None, forced *->planned) pass."""
    payload = {
        "wp_id": "WP01",
        "from_lane": None,
        "to_lane": "planned",
        "actor": "system",
        "force": True,
        "reason": "initial bootstrap of WP",
        "execution_mode": "worktree",
        "mission_slug": "mission-test",
        "evidence": None,
    }
    result = validate_event(payload, "WPStatusChanged")
    assert result.valid, result.model_violations


def test_validate_event_still_rejects_force_with_empty_reason() -> None:
    """Regression: the existing StatusTransitionPayload model validator
    rejects force=True with empty reason. This must surface as a model
    violation before semantic dispatch runs.
    """
    payload = _unforced_payload("in_review", "planned")
    payload["force"] = True
    payload["reason"] = ""  # empty after strip
    result = validate_event(payload, "WPStatusChanged")
    assert not result.valid
    assert result.model_violations


def test_validate_event_violation_messages_preserve_routing_substrings() -> None:
    """FR-002: routing substrings 'force=True' and 'review-rejection'
    are preserved verbatim from validate_transition().
    """
    payload = _unforced_payload("approved", "planned")
    result = validate_event(payload, "WPStatusChanged")
    assert not result.valid
    messages = [v.message for v in result.model_violations]
    assert any("force=True" in m for m in messages)
    assert any("review-rejection" in m for m in messages)


def test_validate_event_violation_field_and_type_are_documented() -> None:
    """ModelViolation entries from semantic dispatch carry field='transition'
    and violation_type='transition_rule' so downstream consumers can route
    by violation_type if they prefer that over message-substring matching.
    """
    payload = _unforced_payload("for_review", "planned")
    result = validate_event(payload, "WPStatusChanged")
    transition_violations = [
        v for v in result.model_violations
        if v.violation_type == "transition_rule"
    ]
    assert transition_violations
    for v in transition_violations:
        assert v.field == "transition"
```

### T009 — Register the seven new event-type models in `_EVENT_TYPE_TO_MODEL`

**File**: `src/spec_kitty_events/conformance/validators.py`

Pre-requisite: WP02 must have landed and the model classes must exist in `build_lifecycle.py`, `project_lifecycle.py`, and `lifecycle.py`.

Add imports at the top (near the existing lifecycle imports):

```python
from spec_kitty_events.build_lifecycle import (
    BuildRegisteredPayload,
    BuildHeartbeatPayload,
)
from spec_kitty_events.project_lifecycle import (
    # ... existing imports ...
    WPAssignedPayload,
    HistoryAddedPayload,
    ErrorLoggedPayload,
    DependencyResolvedPayload,
)
from spec_kitty_events.lifecycle import (
    # ... existing imports ...
    MissionOriginBoundPayload,
)
```

In `_EVENT_TYPE_TO_MODEL` add seven entries:

```python
"WPAssigned": WPAssignedPayload,
"BuildRegistered": BuildRegisteredPayload,
"BuildHeartbeat": BuildHeartbeatPayload,
"HistoryAdded": HistoryAddedPayload,
"ErrorLogged": ErrorLoggedPayload,
"DependencyResolved": DependencyResolvedPayload,
"MissionOriginBound": MissionOriginBoundPayload,
```

No entries in `_EVENT_TYPE_TO_SCHEMA` — the schema layer gracefully skips when `schema_name is None`.

### T005 — Verify zero regressions

Run:

```bash
uv run pytest tests/unit/test_status.py tests/unit/test_fixtures.py tests/unit/test_conformance_semantic.py tests/unit/test_seven_event_contracts.py -q
```

Expected: all existing tests still pass, ten new tests in `test_conformance_semantic.py` pass, and the WP02-shipped `test_seven_event_contracts.py` continues to pass (it asserts the seven-model registry entries are present).

## Branch Strategy

- Planning base: `kitty/pr/1198-canonical-producer-contracts` (mission branch)
- Final merge target: `main` (orchestrator PR contract)
- Execution worktree: `.worktrees/<mission-slug>-<mid8>-lane-a` (computed by `lanes.json` after `finalize-tasks`)
- This WP merges back to the mission branch via the implement-review loop; the orchestrator opens the PR to `main`.

## Definition of Done

- [ ] `_SEMANTIC_VALIDATORS` registry exists in `validators.py`.
- [ ] `_semantic_validate_wp_status_changed` implemented and registered.
- [ ] `validate_event()` invokes the dispatch only when shape validation passed.
- [ ] Seven `_EVENT_TYPE_TO_MODEL` entries added (T009) so `validate_event` covers `WPAssigned`, `BuildRegistered`, `BuildHeartbeat`, `HistoryAdded`, `ErrorLogged`, `DependencyResolved`, `MissionOriginBound`.
- [ ] `tests/unit/test_conformance_semantic.py` exists with 7 test functions (10 parametrized cases) covering FR-001..FR-005 and the regression.
- [ ] `uv run pytest tests/unit/test_status.py tests/unit/test_fixtures.py tests/unit/test_conformance_semantic.py tests/unit/test_seven_event_contracts.py -q` exits 0.
- [ ] No new top-of-module pip imports beyond `Callable` and the seven payload model classes (NFR-004).
- [ ] `validate_event()` remains deterministic and side-effect-free (NFR-001).

## Reviewer guidance

Verify the diff contains:
1. A new `_SEMANTIC_VALIDATORS` dict with exactly one registered entry for `"WPStatusChanged"`.
2. The dispatch call in `validate_event()` is gated on `not model_violations and event_type in _SEMANTIC_VALIDATORS`.
3. Violation messages are NOT reformatted — they pass through verbatim from `validate_transition()`.
4. No changes to `status.py`, `models.py`, or the existing `StatusTransitionPayload` model body. (C-003: review-rejection rules unchanged.)
5. No new pip dependencies in `pyproject.toml` (NFR-004).
6. The new test file follows the pytest conventions used in the existing `tests/unit/` tree.

## Risks

- **Risk**: A future producer changes the `StatusTransitionPayload` shape so `validate_transition()` raises rather than returning a violation. **Mitigation**: `validate_transition` is documented to never raise on business-rule violations (status.py docstring). If it ever did, the test suite would catch the unexpected exception.
- **Risk**: Re-parsing the model inside `validate_event()` adds latency. **Mitigation**: only fires for `WPStatusChanged` events that already passed shape validation; one extra pydantic parse per event is well under the 10s NFR-002 budget.
- **Risk**: The local `from spec_kitty_events.status import validate_transition` inside the validator function avoids a top-of-module circular-import problem. **Mitigation**: tested via T005.

## Activity Log

- 2026-05-22T10:51:57Z – claude:opus-4-7:python-pedro:implementer – shell_pid=73578 – Assigned agent via action command
- 2026-05-22T10:55:32Z – claude:opus-4-7:python-pedro:implementer – shell_pid=73578 – WP01 ready
- 2026-05-22T10:55:39Z – claude:opus-4-7:reviewer-renata:reviewer – shell_pid=74579 – Started review via action command
