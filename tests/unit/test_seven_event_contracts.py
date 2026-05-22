"""Tests for the seven canonical contracts shipped with WP02.

Covers FR-010 (model classes exist, round-trip, frozen+forbid).

Registry-presence tests (FR-011) and LOCAL_ONLY_EVENT_TYPES tests (FR-013)
live in WP01 and WP04 respectively — WP02's tests intentionally import payload
models directly from their source modules so this file can run before WP01
adds the seven entries to `_EVENT_TYPE_TO_MODEL` and before WP04 adds the
package-root re-exports.
"""
from __future__ import annotations

from typing import Any, Dict, Tuple, Type

import pytest
from pydantic import BaseModel, ValidationError

from spec_kitty_events.build_lifecycle import (
    BuildHeartbeatPayload,
    BuildRegisteredPayload,
)
from spec_kitty_events.lifecycle import MissionOriginBoundPayload
from spec_kitty_events.project_lifecycle import (
    DependencyResolvedPayload,
    ErrorLoggedPayload,
    HistoryAddedPayload,
    WPAssignedPayload,
)

_SEVEN: Tuple[Tuple[str, Type[BaseModel], Dict[str, Any]], ...] = (
    (
        "WPAssigned",
        WPAssignedPayload,
        {"wp_id": "WP01", "agent_id": "claude", "phase": "implement"},
    ),
    (
        "BuildRegistered",
        BuildRegisteredPayload,
        {"repo_slug": "org/repo", "git_branch": "main", "head_commit_sha": "abc123"},
    ),
    (
        "BuildHeartbeat",
        BuildHeartbeatPayload,
        {
            "repo_slug": "org/repo",
            "ahead_of_remote": 0,
            "behind_remote": 0,
        },
    ),
    (
        "HistoryAdded",
        HistoryAddedPayload,
        {
            "wp_id": "WP01",
            "entry_type": "note",
            "entry_content": "started",
            "author": "claude",
        },
    ),
    (
        "ErrorLogged",
        ErrorLoggedPayload,
        {"error_type": "ValueError", "error_message": "oops"},
    ),
    (
        "DependencyResolved",
        DependencyResolvedPayload,
        {
            "wp_id": "WP02",
            "dependency_wp_id": "WP01",
            "resolution_type": "merged",
        },
    ),
    (
        "MissionOriginBound",
        MissionOriginBoundPayload,
        {
            "mission_slug": "demo",
            "provider": "github",
            "external_issue_id": "1198",
            "external_issue_key": "spec-kitty#1198",
            "external_issue_url": "https://example.com/issues/1198",
            "title": "Epic",
        },
    ),
)

_IDS = [t[0] for t in _SEVEN]


@pytest.mark.parametrize(("event_type", "model_cls", "fields"), _SEVEN, ids=_IDS)
def test_payload_round_trip(event_type: str, model_cls: Type[BaseModel], fields: Dict[str, Any]) -> None:
    """FR-010: each model round-trips through model_dump(mode='json')."""
    model = model_cls(**fields)
    data = model.model_dump(mode="json")
    restored = model_cls.model_validate(data)
    assert restored == model


@pytest.mark.parametrize(("event_type", "model_cls", "fields"), _SEVEN, ids=_IDS)
def test_payload_is_frozen_and_forbid_extra(
    event_type: str, model_cls: Type[BaseModel], fields: Dict[str, Any]
) -> None:
    """C-004 + plan: every model uses ConfigDict(frozen=True, extra='forbid')."""
    assert model_cls.model_config.get("frozen") is True
    assert model_cls.model_config.get("extra") == "forbid"


@pytest.mark.parametrize(("event_type", "model_cls", "fields"), _SEVEN, ids=_IDS)
def test_payload_rejects_extra_fields(
    event_type: str, model_cls: Type[BaseModel], fields: Dict[str, Any]
) -> None:
    """extra='forbid' is the drift-detection mechanism — extras MUST raise."""
    polluted = {**fields, "this_field_does_not_exist": True}
    with pytest.raises(ValidationError):
        model_cls(**polluted)


@pytest.mark.parametrize(("event_type", "model_cls", "fields"), _SEVEN, ids=_IDS)
def test_payload_instance_is_immutable(
    event_type: str, model_cls: Type[BaseModel], fields: Dict[str, Any]
) -> None:
    """frozen=True ensures the instance cannot be mutated after construction."""
    model = model_cls(**fields)
    # Pick any field that's actually set; attempt to overwrite it.
    target = next(iter(fields.keys()))
    with pytest.raises(ValidationError):
        setattr(model, target, "tampered")
