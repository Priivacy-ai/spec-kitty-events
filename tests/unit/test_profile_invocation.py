"""Unit tests for profile_invocation module.

Covers: valid construction, field enforcement, immutability, extra-forbid,
reserved constants, schema version, roundtrip, and RuntimeActorIdentity embedding.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from spec_kitty_events.mission_next import RuntimeActorIdentity
from spec_kitty_events.profile_invocation import (
    PROFILE_INVOCATION_COMPLETED,
    PROFILE_INVOCATION_EVENT_TYPES,
    PROFILE_INVOCATION_FAILED,
    PROFILE_INVOCATION_RESERVED_TYPES,
    PROFILE_INVOCATION_SCHEMA_VERSION,
    PROFILE_INVOCATION_STARTED,
    ProfileInvocationStartedPayload,
)


# ── Helpers ──────────────────────────────────────────────────────────────────


def _make_actor(**overrides: object) -> RuntimeActorIdentity:
    defaults: dict[str, object] = {"actor_id": "test-actor", "actor_type": "llm"}
    defaults.update(overrides)
    return RuntimeActorIdentity(**defaults)


def _make_payload(**overrides: object) -> ProfileInvocationStartedPayload:
    defaults: dict[str, object] = {
        "mission_id": "test-mission",
        "run_id": "test-run",
        "step_id": "implement",
        "action": "implement WP03",
        "profile_slug": "architect-v2",
        "actor": _make_actor(),
    }
    defaults.update(overrides)
    return ProfileInvocationStartedPayload(**defaults)


# ── 1. Valid construction ────────────────────────────────────────────────────


def test_minimal_payload() -> None:
    """Construct with only required fields; verify all values."""
    p = _make_payload()
    assert p.mission_id == "test-mission"
    assert p.run_id == "test-run"
    assert p.step_id == "implement"
    assert p.action == "implement WP03"
    assert p.profile_slug == "architect-v2"
    assert p.profile_version is None
    assert p.governance_scope is None
    assert p.actor.actor_id == "test-actor"
    assert p.actor.actor_type == "llm"


def test_full_payload() -> None:
    """Construct with all fields including optional ones."""
    p = _make_payload(
        profile_version="2.1.0",
        governance_scope="org/project",
    )
    assert p.profile_version == "2.1.0"
    assert p.governance_scope == "org/project"


def test_actor_embedding() -> None:
    """Verify RuntimeActorIdentity is correctly nested and accessible."""
    actor = _make_actor(
        actor_id="custom-agent",
        actor_type="service",
        display_name="Custom Agent",
        provider="anthropic",
        model="claude-opus-4-6",
    )
    p = _make_payload(actor=actor)
    assert isinstance(p.actor, RuntimeActorIdentity)
    assert p.actor.actor_id == "custom-agent"
    assert p.actor.actor_type == "service"
    assert p.actor.display_name == "Custom Agent"
    assert p.actor.provider == "anthropic"
    assert p.actor.model == "claude-opus-4-6"


# ── 2. Field enforcement ────────────────────────────────────────────────────


def test_missing_mission_id_raises() -> None:
    """Omit mission_id; expect ValidationError."""
    with pytest.raises(ValidationError):
        ProfileInvocationStartedPayload(
            run_id="r1",
            step_id="s1",
            action="act",
            profile_slug="slug",
            actor=_make_actor(),
        )


def test_missing_profile_slug_raises() -> None:
    """Omit profile_slug; expect ValidationError."""
    with pytest.raises(ValidationError):
        ProfileInvocationStartedPayload(
            mission_id="m1",
            run_id="r1",
            step_id="s1",
            action="act",
            actor=_make_actor(),
        )


def test_empty_action_raises() -> None:
    """Pass action=''; expect ValidationError (min_length=1)."""
    with pytest.raises(ValidationError):
        _make_payload(action="")


def test_empty_step_id_raises() -> None:
    """Pass step_id=''; expect ValidationError (min_length=1)."""
    with pytest.raises(ValidationError):
        _make_payload(step_id="")


def test_empty_mission_id_raises() -> None:
    """Pass mission_id=''; expect ValidationError (min_length=1)."""
    with pytest.raises(ValidationError):
        _make_payload(mission_id="")


def test_empty_run_id_raises() -> None:
    """Pass run_id=''; expect ValidationError (min_length=1)."""
    with pytest.raises(ValidationError):
        _make_payload(run_id="")


def test_empty_profile_slug_raises() -> None:
    """Pass profile_slug=''; expect ValidationError (min_length=1)."""
    with pytest.raises(ValidationError):
        _make_payload(profile_slug="")


def test_empty_profile_version_raises() -> None:
    """Pass profile_version=''; expect ValidationError (min_length=1 when present)."""
    with pytest.raises(ValidationError):
        _make_payload(profile_version="")


def test_empty_governance_scope_raises() -> None:
    """Pass governance_scope=''; expect ValidationError (min_length=1 when present)."""
    with pytest.raises(ValidationError):
        _make_payload(governance_scope="")


# ── 3. Immutability and extra-forbid ─────────────────────────────────────────


def test_frozen_immutability() -> None:
    """Attempt attribute assignment; expect error."""
    p = _make_payload()
    with pytest.raises(ValidationError):
        p.mission_id = "changed"  # type: ignore[misc]


def test_extra_forbid() -> None:
    """Pass unknown field; expect ValidationError."""
    with pytest.raises(ValidationError):
        _make_payload(unknown_field="should-fail")


# ── 4. Reserved constants ────────────────────────────────────────────────────


def test_reserved_constants_exist() -> None:
    """Assert reserved constants are strings with expected values."""
    assert isinstance(PROFILE_INVOCATION_COMPLETED, str)
    assert PROFILE_INVOCATION_COMPLETED == "ProfileInvocationCompleted"
    assert isinstance(PROFILE_INVOCATION_FAILED, str)
    assert PROFILE_INVOCATION_FAILED == "ProfileInvocationFailed"


def test_event_types_frozenset() -> None:
    """Assert only validatable types are in PROFILE_INVOCATION_EVENT_TYPES."""
    assert len(PROFILE_INVOCATION_EVENT_TYPES) == 1
    assert PROFILE_INVOCATION_STARTED in PROFILE_INVOCATION_EVENT_TYPES
    assert PROFILE_INVOCATION_COMPLETED not in PROFILE_INVOCATION_EVENT_TYPES
    assert PROFILE_INVOCATION_FAILED not in PROFILE_INVOCATION_EVENT_TYPES
    assert isinstance(PROFILE_INVOCATION_EVENT_TYPES, frozenset)


def test_reserved_types_frozenset() -> None:
    """Assert reserved types are in a separate set, not in EVENT_TYPES."""
    assert len(PROFILE_INVOCATION_RESERVED_TYPES) == 2
    assert PROFILE_INVOCATION_COMPLETED in PROFILE_INVOCATION_RESERVED_TYPES
    assert PROFILE_INVOCATION_FAILED in PROFILE_INVOCATION_RESERVED_TYPES
    assert isinstance(PROFILE_INVOCATION_RESERVED_TYPES, frozenset)
    # No overlap
    assert PROFILE_INVOCATION_EVENT_TYPES.isdisjoint(PROFILE_INVOCATION_RESERVED_TYPES)


def test_schema_version() -> None:
    """Assert schema version is 3.1.0."""
    assert PROFILE_INVOCATION_SCHEMA_VERSION == "3.1.0"


# ── 5. Roundtrip ────────────────────────────────────────────────────────────


def test_model_dump_roundtrip() -> None:
    """Construct payload, dump to dict, reconstruct, verify equality."""
    original = _make_payload(
        profile_version="1.0.0",
        governance_scope="test-scope",
    )
    data = original.model_dump(mode="json")
    restored = ProfileInvocationStartedPayload.model_validate(data)
    assert restored == original
    assert restored.mission_id == original.mission_id
    assert restored.profile_version == original.profile_version
    assert restored.governance_scope == original.governance_scope
    assert restored.actor.actor_id == original.actor.actor_id
