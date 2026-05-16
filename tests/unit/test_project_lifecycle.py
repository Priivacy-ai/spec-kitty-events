"""Unit tests for canonical project / artifact / WP lifecycle event contracts.

Covers payload validation, idempotency-friendly fields, and the conformance
validator wiring for the new contracts introduced for spec-kitty-events#26.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from spec_kitty_events import (
    ARTIFACT_LIFECYCLE_EVENT_TYPES,
    CANONICAL_LIFECYCLE_EVENT_TYPES,
    PLAN_COMPLETED,
    PLAN_STARTED,
    PROJECT_INITIALIZED,
    PROJECT_LIFECYCLE_EVENT_TYPES,
    SPECIFY_COMPLETED,
    SPECIFY_STARTED,
    TASKS_COMPLETED,
    TASKS_STARTED,
    WP_CREATED,
    WP_LIFECYCLE_EVENT_TYPES,
    PlanCompletedPayload,
    PlanStartedPayload,
    ProjectInitializedPayload,
    SpecifyCompletedPayload,
    SpecifyStartedPayload,
    TasksCompletedPayload,
    TasksStartedPayload,
    WPCreatedPayload,
)


class TestEventTypeConstants:
    def test_canonical_set_includes_all_new_events(self) -> None:
        assert PROJECT_LIFECYCLE_EVENT_TYPES == {PROJECT_INITIALIZED}
        assert ARTIFACT_LIFECYCLE_EVENT_TYPES == {
            SPECIFY_STARTED,
            SPECIFY_COMPLETED,
            PLAN_STARTED,
            PLAN_COMPLETED,
            TASKS_STARTED,
            TASKS_COMPLETED,
        }
        assert WP_LIFECYCLE_EVENT_TYPES == {WP_CREATED}
        assert CANONICAL_LIFECYCLE_EVENT_TYPES == (
            PROJECT_LIFECYCLE_EVENT_TYPES
            | ARTIFACT_LIFECYCLE_EVENT_TYPES
            | WP_LIFECYCLE_EVENT_TYPES
        )

    def test_event_names_are_pascal_case(self) -> None:
        # Match existing event naming convention (e.g. MissionCreated).
        for name in CANONICAL_LIFECYCLE_EVENT_TYPES:
            assert name[0].isupper(), name


class TestProjectInitializedPayload:
    def test_minimal_payload_validates(self) -> None:
        p = ProjectInitializedPayload(
            project_uuid="a1b2c3d4-e5f6-7890-abcd-ef1234567890",
            actor="cli",
        )
        assert p.project_slug is None
        assert p.runtime_version is None

    def test_full_payload_validates(self) -> None:
        p = ProjectInitializedPayload(
            project_uuid="a1b2c3d4-e5f6-7890-abcd-ef1234567890",
            project_slug="spec-kitty-events",
            actor="cli",
            runtime_version="3.2.0",
            initialized_at=datetime(2026, 5, 15, 12, 0, tzinfo=timezone.utc),
        )
        assert p.project_slug == "spec-kitty-events"
        assert p.initialized_at is not None

    def test_missing_actor_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ProjectInitializedPayload(
                project_uuid="a1b2c3d4-e5f6-7890-abcd-ef1234567890",
            )

    def test_extra_keys_forbidden(self) -> None:
        with pytest.raises(ValidationError):
            ProjectInitializedPayload(
                project_uuid="a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                actor="cli",
                stray="not allowed",
            )

    def test_frozen(self) -> None:
        p = ProjectInitializedPayload(
            project_uuid="a1b2c3d4-e5f6-7890-abcd-ef1234567890",
            actor="cli",
        )
        with pytest.raises(ValidationError):
            p.actor = "other"  # type: ignore[misc]


@pytest.mark.parametrize(
    "started_cls,completed_cls",
    [
        (SpecifyStartedPayload, SpecifyCompletedPayload),
        (PlanStartedPayload, PlanCompletedPayload),
        (TasksStartedPayload, TasksCompletedPayload),
    ],
)
class TestArtifactPhasePayloads:
    def test_started_minimal(self, started_cls, completed_cls) -> None:
        p = started_cls(mission_slug="mission-001", actor="claude")
        assert p.mission_number is None
        assert p.at is None

    def test_completed_requires_artifact_path(self, started_cls, completed_cls) -> None:
        with pytest.raises(ValidationError):
            completed_cls(mission_slug="mission-001", actor="claude")

    def test_completed_valid(self, started_cls, completed_cls) -> None:
        kwargs = {
            "mission_slug": "mission-001",
            "actor": "claude",
            "artifact_path": "kitty-specs/mission-001/artifact.md",
        }
        if completed_cls is TasksCompletedPayload:
            kwargs["wp_count"] = 3
        p = completed_cls(**kwargs)
        assert p.artifact_path.endswith(".md")

    def test_extra_keys_forbidden(self, started_cls, completed_cls) -> None:
        with pytest.raises(ValidationError):
            started_cls(mission_slug="m", actor="a", bogus=1)


class TestTasksCompletedSpecifics:
    def test_wp_count_required(self) -> None:
        with pytest.raises(ValidationError):
            TasksCompletedPayload(
                mission_slug="m",
                actor="a",
                artifact_path="tasks.md",
            )

    def test_wp_count_zero_allowed(self) -> None:
        p = TasksCompletedPayload(
            mission_slug="m",
            actor="a",
            artifact_path="tasks.md",
            wp_count=0,
        )
        assert p.wp_count == 0

    def test_negative_wp_count_rejected(self) -> None:
        with pytest.raises(ValidationError):
            TasksCompletedPayload(
                mission_slug="m",
                actor="a",
                artifact_path="tasks.md",
                wp_count=-1,
            )


class TestWPCreatedPayload:
    def test_minimal_payload(self) -> None:
        p = WPCreatedPayload(
            mission_slug="mission-001",
            wp_id="WP01",
            wp_title="Build it",
            actor="claude",
        )
        assert p.depends_on == []
        assert p.wp_path is None
        assert p.mission_number is None

    def test_depends_on_supported(self) -> None:
        p = WPCreatedPayload(
            mission_slug="m",
            wp_id="WP02",
            wp_title="Second",
            depends_on=["WP01"],
            actor="claude",
        )
        assert p.depends_on == ["WP01"]

    def test_missing_title_rejected(self) -> None:
        with pytest.raises(ValidationError):
            WPCreatedPayload(
                mission_slug="m",
                wp_id="WP01",
                actor="claude",
            )

    def test_empty_wp_id_rejected(self) -> None:
        with pytest.raises(ValidationError):
            WPCreatedPayload(
                mission_slug="m",
                wp_id="",
                wp_title="t",
                actor="claude",
            )


class TestConformanceValidatorWiring:
    """The conformance validator must accept the new event types."""

    def test_project_initialized_recognized(self) -> None:
        from spec_kitty_events.conformance.validators import validate_event

        result = validate_event(
            {
                "project_uuid": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                "actor": "cli",
            },
            event_type="ProjectInitialized",
        )
        assert result.valid

    def test_wp_created_recognized(self) -> None:
        from spec_kitty_events.conformance.validators import validate_event

        result = validate_event(
            {
                "mission_slug": "m",
                "wp_id": "WP01",
                "wp_title": "Build it",
                "actor": "claude",
            },
            event_type="WPCreated",
        )
        assert result.valid

    def test_tasks_completed_recognized(self) -> None:
        from spec_kitty_events.conformance.validators import validate_event

        result = validate_event(
            {
                "mission_slug": "m",
                "actor": "claude",
                "artifact_path": "tasks.md",
                "wp_count": 3,
            },
            event_type="TasksCompleted",
        )
        assert result.valid

    def test_invalid_wp_created_payload_rejected(self) -> None:
        from spec_kitty_events.conformance.validators import validate_event

        result = validate_event(
            {
                "mission_slug": "m",
                "wp_id": "WP01",
                "actor": "claude",
            },
            event_type="WPCreated",
        )
        assert not result.valid
        assert any(v.field == "wp_title" for v in result.model_violations)
