"""Tests for validate_event() ↔ validate_transition() semantic dispatch.

Mission: canonical-producer-contracts-legacy-envelope-01KS7JM3.

Covers FR-001..FR-005, the regression for force-with-empty-reason, and
the substring-routing contract that downstream consumers rely on.
"""
from __future__ import annotations

from typing import Any, Dict

import pytest

from spec_kitty_events.conformance.validators import validate_event


_UNFORCED_BACKWARD_CASES = [
    pytest.param("in_progress", "planned", id="in_progress_to_planned"),
    pytest.param("for_review", "planned", id="for_review_to_planned"),
    pytest.param("in_review", "planned", id="in_review_to_planned"),
    pytest.param("approved", "planned", id="approved_to_planned"),
]


def _unforced_payload(from_lane: str, to_lane: str) -> Dict[str, Any]:
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
def test_validate_event_rejects_unforced_review_rejection(
    from_lane: str, to_lane: str
) -> None:
    """FR-001/FR-003: every review-rejection family transition without
    force=True fails through the public conformance gate."""
    payload = _unforced_payload(from_lane, to_lane)
    result = validate_event(payload, "WPStatusChanged")
    assert not result.valid, (
        f"Unforced {from_lane}->{to_lane} should fail; got valid=True"
    )
    assert result.model_violations
    messages = [v.message for v in result.model_violations]
    assert any("force=True" in m for m in messages), messages
    assert any("review-rejection" in m for m in messages), messages


def test_validate_event_accepts_forced_review_rejection_with_reason() -> None:
    """FR-004: the forced backward transition with non-empty reason passes."""
    payload = _unforced_payload("in_review", "planned")
    payload["force"] = True
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
    violation before semantic dispatch runs (so the dispatch never sees
    a payload with empty reason)."""
    payload = _unforced_payload("in_review", "planned")
    payload["force"] = True
    payload["reason"] = ""  # empty after strip
    result = validate_event(payload, "WPStatusChanged")
    assert not result.valid
    assert result.model_violations


def test_validate_event_violation_messages_preserve_routing_substrings() -> None:
    """FR-002: routing substrings 'force=True' and 'review-rejection'
    are preserved verbatim from validate_transition()."""
    payload = _unforced_payload("approved", "planned")
    result = validate_event(payload, "WPStatusChanged")
    assert not result.valid
    messages = [v.message for v in result.model_violations]
    assert any("force=True" in m for m in messages)
    assert any("review-rejection" in m for m in messages)


def test_validate_event_violation_field_and_type_are_documented() -> None:
    """ModelViolation entries from semantic dispatch carry field='transition'
    and violation_type='transition_rule' so downstream consumers can route
    by violation_type if they prefer that over message-substring matching."""
    payload = _unforced_payload("for_review", "planned")
    result = validate_event(payload, "WPStatusChanged")
    transition_violations = [
        v for v in result.model_violations
        if v.violation_type == "transition_rule"
    ]
    assert transition_violations
    for v in transition_violations:
        assert v.field == "transition"
