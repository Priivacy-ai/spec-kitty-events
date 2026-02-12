"""Tests for canonical fixtures, manifest, and load_fixtures API (WP04)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

import pytest
from pydantic import ValidationError as PydanticValidationError

from spec_kitty_events.conformance import FixtureCase, load_fixtures
from spec_kitty_events.conformance.loader import _FIXTURES_DIR, _MANIFEST_PATH
from spec_kitty_events.conformance.validators import (
    _EVENT_TYPE_TO_MODEL,
    validate_event,
)
from spec_kitty_events.status import Lane, canonical_to_sync_v1

# ---------------------------------------------------------------------------
# T021: Directory structure
# ---------------------------------------------------------------------------


class TestFixtureDirectoryStructure:
    """Verify that all fixture directories exist."""

    EXPECTED_DIRS = [
        "events/valid",
        "events/invalid",
        "lane_mapping/valid",
        "lane_mapping/invalid",
        "edge_cases/valid",
        "edge_cases/invalid",
    ]

    @pytest.mark.parametrize("subdir", EXPECTED_DIRS)
    def test_directory_exists(self, subdir: str) -> None:
        path = _FIXTURES_DIR / subdir
        assert path.is_dir(), f"Expected directory does not exist: {path}"

    def test_fixtures_init_exists(self) -> None:
        init = _FIXTURES_DIR / "__init__.py"
        assert init.is_file(), f"__init__.py missing from fixtures package: {init}"


# ---------------------------------------------------------------------------
# T022: Valid event fixtures
# ---------------------------------------------------------------------------


VALID_EVENT_FILES = [
    ("events/valid/event.json", "Event"),
    ("events/valid/wp_status_changed.json", "WPStatusChanged"),
    ("events/valid/gate_passed.json", "GatePassed"),
    ("events/valid/gate_failed.json", "GateFailed"),
    ("events/valid/mission_started.json", "MissionStarted"),
    ("events/valid/mission_completed.json", "MissionCompleted"),
    ("events/valid/mission_cancelled.json", "MissionCancelled"),
    ("events/valid/phase_entered.json", "PhaseEntered"),
    ("events/valid/review_rollback.json", "ReviewRollback"),
]


class TestValidEventFixtures:
    """Verify each valid event fixture passes model validation."""

    @pytest.mark.parametrize("path,event_type", VALID_EVENT_FILES)
    def test_valid_fixture_is_valid_json(self, path: str, event_type: str) -> None:
        full = _FIXTURES_DIR / path
        assert full.is_file(), f"Missing fixture: {full}"
        with open(full, encoding="utf-8") as f:
            data = json.load(f)
        assert isinstance(data, dict)

    @pytest.mark.parametrize("path,event_type", VALID_EVENT_FILES)
    def test_valid_fixture_passes_model(self, path: str, event_type: str) -> None:
        full = _FIXTURES_DIR / path
        with open(full, encoding="utf-8") as f:
            data = json.load(f)
        model_class = _EVENT_TYPE_TO_MODEL[event_type]
        instance = model_class.model_validate(data)
        assert instance is not None

    @pytest.mark.parametrize("path,event_type", VALID_EVENT_FILES)
    def test_valid_fixture_passes_conformance(
        self, path: str, event_type: str
    ) -> None:
        full = _FIXTURES_DIR / path
        with open(full, encoding="utf-8") as f:
            data = json.load(f)
        result = validate_event(data, event_type)
        assert result.valid is True, (
            f"Conformance failure for {path}: {result.model_violations}"
        )

    def test_nine_valid_event_fixtures_exist(self) -> None:
        valid_dir = _FIXTURES_DIR / "events" / "valid"
        files = sorted(valid_dir.glob("*.json"))
        assert len(files) == 9, f"Expected 9 valid event fixtures, got {len(files)}"


# ---------------------------------------------------------------------------
# T023: Invalid event fixtures
# ---------------------------------------------------------------------------


INVALID_EVENT_FILES = [
    ("events/invalid/event_missing_correlation_id.json", "Event"),
    ("events/invalid/event_invalid_lamport_clock.json", "Event"),
    ("events/invalid/wp_status_changed_invalid_lane.json", "WPStatusChanged"),
    ("events/invalid/wp_status_changed_force_no_reason.json", "WPStatusChanged"),
    ("events/invalid/gate_failed_invalid_conclusion.json", "GateFailed"),
]


class TestInvalidEventFixtures:
    """Verify each invalid event fixture fails model validation."""

    @pytest.mark.parametrize("path,event_type", INVALID_EVENT_FILES)
    def test_invalid_fixture_fails_model(self, path: str, event_type: str) -> None:
        full = _FIXTURES_DIR / path
        with open(full, encoding="utf-8") as f:
            data = json.load(f)
        model_class = _EVENT_TYPE_TO_MODEL[event_type]
        with pytest.raises(PydanticValidationError):
            model_class.model_validate(data)

    @pytest.mark.parametrize("path,event_type", INVALID_EVENT_FILES)
    def test_invalid_fixture_fails_conformance(
        self, path: str, event_type: str
    ) -> None:
        full = _FIXTURES_DIR / path
        with open(full, encoding="utf-8") as f:
            data = json.load(f)
        result = validate_event(data, event_type)
        assert result.valid is False, f"Expected invalid for {path}"
        assert len(result.model_violations) > 0

    def test_missing_correlation_id_error_field(self) -> None:
        full = _FIXTURES_DIR / "events/invalid/event_missing_correlation_id.json"
        with open(full, encoding="utf-8") as f:
            data = json.load(f)
        result = validate_event(data, "Event")
        fields = [v.field for v in result.model_violations]
        assert "correlation_id" in fields

    def test_invalid_lamport_clock_error_field(self) -> None:
        full = _FIXTURES_DIR / "events/invalid/event_invalid_lamport_clock.json"
        with open(full, encoding="utf-8") as f:
            data = json.load(f)
        result = validate_event(data, "Event")
        fields = [v.field for v in result.model_violations]
        assert "lamport_clock" in fields

    def test_force_no_reason_error_message(self) -> None:
        full = _FIXTURES_DIR / "events/invalid/wp_status_changed_force_no_reason.json"
        with open(full, encoding="utf-8") as f:
            data = json.load(f)
        result = validate_event(data, "WPStatusChanged")
        messages = [v.message for v in result.model_violations]
        assert any("reason" in m.lower() for m in messages)


# ---------------------------------------------------------------------------
# T024: Lane mapping fixtures
# ---------------------------------------------------------------------------


class TestLaneMappingFixtures:
    """Verify lane mapping fixtures cover all 7 canonical lanes."""

    def test_valid_mapping_has_seven_entries(self) -> None:
        full = _FIXTURES_DIR / "lane_mapping/valid/all_canonical_to_sync_v1.json"
        with open(full, encoding="utf-8") as f:
            entries: List[Dict[str, str]] = json.load(f)
        assert len(entries) == 7

    def test_valid_mapping_covers_all_lanes(self) -> None:
        full = _FIXTURES_DIR / "lane_mapping/valid/all_canonical_to_sync_v1.json"
        with open(full, encoding="utf-8") as f:
            entries: List[Dict[str, str]] = json.load(f)
        canonical_values = {e["canonical"] for e in entries}
        expected = {lane.value for lane in Lane}
        assert canonical_values == expected

    def test_valid_mapping_expected_sync_values(self) -> None:
        full = _FIXTURES_DIR / "lane_mapping/valid/all_canonical_to_sync_v1.json"
        with open(full, encoding="utf-8") as f:
            entries: List[Dict[str, str]] = json.load(f)
        for entry in entries:
            lane = Lane(entry["canonical"])
            expected_sync = canonical_to_sync_v1(lane)
            assert expected_sync.value == entry["expected_sync"], (
                f"Mismatch for {entry['canonical']}: "
                f"expected {entry['expected_sync']}, got {expected_sync.value}"
            )

    def test_invalid_lanes_fail_construction(self) -> None:
        full = _FIXTURES_DIR / "lane_mapping/invalid/unknown_lanes.json"
        with open(full, encoding="utf-8") as f:
            entries: List[Dict[str, str]] = json.load(f)
        for entry in entries:
            with pytest.raises(ValueError):
                Lane(entry["canonical"])


# ---------------------------------------------------------------------------
# T025: Edge case fixtures
# ---------------------------------------------------------------------------


class TestEdgeCaseFixtures:
    """Verify edge case fixtures for alias normalization and optional fields."""

    def test_alias_doing_normalizes(self) -> None:
        """Alias 'doing' normalises to in_progress at the Pydantic layer.

        JSON Schema may still flag the alias because the enum only lists
        canonical values. The important contract is that Pydantic accepts it.
        """
        full = _FIXTURES_DIR / "edge_cases/valid/alias_doing_normalized.json"
        with open(full, encoding="utf-8") as f:
            data = json.load(f)
        result = validate_event(data, "WPStatusChanged")
        # Pydantic normalisation must succeed (no model violations)
        assert len(result.model_violations) == 0
        # The model itself should resolve the alias
        from spec_kitty_events.status import StatusTransitionPayload, Lane
        model = StatusTransitionPayload.model_validate(data)
        assert model.to_lane == Lane.IN_PROGRESS

    def test_optional_fields_omitted_valid(self) -> None:
        full = _FIXTURES_DIR / "edge_cases/valid/optional_fields_omitted.json"
        with open(full, encoding="utf-8") as f:
            data = json.load(f)
        result = validate_event(data, "WPStatusChanged")
        assert result.valid is True

    def test_event_all_optional_fields_valid(self) -> None:
        full = _FIXTURES_DIR / "edge_cases/valid/event_with_all_optional_fields.json"
        with open(full, encoding="utf-8") as f:
            data = json.load(f)
        result = validate_event(data, "Event")
        assert result.valid is True

    def test_unsupported_schema_version_invalid(self) -> None:
        full = _FIXTURES_DIR / "edge_cases/invalid/unsupported_schema_version.json"
        with open(full, encoding="utf-8") as f:
            data = json.load(f)
        result = validate_event(data, "Event")
        assert result.valid is False

    def test_empty_event_type_invalid(self) -> None:
        full = _FIXTURES_DIR / "edge_cases/invalid/empty_event_type.json"
        with open(full, encoding="utf-8") as f:
            data = json.load(f)
        result = validate_event(data, "Event")
        assert result.valid is False


# ---------------------------------------------------------------------------
# T026: Manifest
# ---------------------------------------------------------------------------


class TestManifest:
    """Verify manifest.json integrity and completeness."""

    def test_manifest_is_valid_json(self) -> None:
        with open(_MANIFEST_PATH, encoding="utf-8") as f:
            manifest = json.load(f)
        assert "version" in manifest
        assert "fixtures" in manifest

    def test_manifest_has_version(self) -> None:
        with open(_MANIFEST_PATH, encoding="utf-8") as f:
            manifest = json.load(f)
        assert manifest["version"] == "2.0.0"

    def test_every_fixture_file_has_manifest_entry(self) -> None:
        """Every .json fixture file in the tree has a manifest entry."""
        with open(_MANIFEST_PATH, encoding="utf-8") as f:
            manifest = json.load(f)
        manifest_paths = {e["path"] for e in manifest["fixtures"]}

        # Find all .json files under fixtures/ (excluding manifest.json itself)
        all_json = set()
        for p in _FIXTURES_DIR.rglob("*.json"):
            if p.name == "manifest.json":
                continue
            rel = str(p.relative_to(_FIXTURES_DIR))
            all_json.add(rel)

        missing = all_json - manifest_paths
        assert not missing, f"Fixture files without manifest entry: {missing}"

    def test_every_manifest_entry_resolves(self) -> None:
        """Every manifest entry points to an existing file."""
        with open(_MANIFEST_PATH, encoding="utf-8") as f:
            manifest = json.load(f)
        for entry in manifest["fixtures"]:
            full = _FIXTURES_DIR / entry["path"]
            assert full.is_file(), f"Manifest entry {entry['id']} -> {full} not found"

    def test_no_orphan_manifest_entries(self) -> None:
        """Manifest entries should not have duplicate ids."""
        with open(_MANIFEST_PATH, encoding="utf-8") as f:
            manifest = json.load(f)
        ids = [e["id"] for e in manifest["fixtures"]]
        assert len(ids) == len(set(ids)), f"Duplicate ids in manifest: {ids}"

    def test_manifest_entry_fields(self) -> None:
        """Each manifest entry has all required fields."""
        with open(_MANIFEST_PATH, encoding="utf-8") as f:
            manifest = json.load(f)
        required_fields = {"id", "path", "expected_result", "event_type", "notes", "min_version"}
        for entry in manifest["fixtures"]:
            missing = required_fields - set(entry.keys())
            assert not missing, (
                f"Entry {entry.get('id', '?')} missing fields: {missing}"
            )


# ---------------------------------------------------------------------------
# T027: load_fixtures() and FixtureCase
# ---------------------------------------------------------------------------


class TestLoadFixtures:
    """Verify load_fixtures() API contract."""

    def test_load_events_returns_cases(self) -> None:
        cases = load_fixtures("events")
        assert len(cases) > 0
        assert all(isinstance(c, FixtureCase) for c in cases)

    def test_load_lane_mapping_returns_cases(self) -> None:
        cases = load_fixtures("lane_mapping")
        assert len(cases) == 2

    def test_load_edge_cases_returns_cases(self) -> None:
        cases = load_fixtures("edge_cases")
        assert len(cases) > 0

    def test_invalid_category_raises(self) -> None:
        with pytest.raises(ValueError, match="Unknown fixture category"):
            load_fixtures("nonexistent")

    def test_fixture_case_is_frozen(self) -> None:
        cases = load_fixtures("events")
        case = cases[0]
        with pytest.raises(AttributeError):
            case.id = "mutated"  # type: ignore[misc]

    def test_events_valid_cases_expected_valid_true(self) -> None:
        cases = load_fixtures("events")
        valid_cases = [c for c in cases if c.expected_valid]
        assert len(valid_cases) == 9

    def test_events_invalid_cases_expected_valid_false(self) -> None:
        cases = load_fixtures("events")
        invalid_cases = [c for c in cases if not c.expected_valid]
        assert len(invalid_cases) == 5

    def test_fixture_case_has_payload(self) -> None:
        cases = load_fixtures("events")
        for case in cases:
            assert case.payload is not None
            assert isinstance(case.payload, (dict, list))

    def test_fixture_case_has_notes(self) -> None:
        cases = load_fixtures("events")
        for case in cases:
            assert isinstance(case.notes, str)
            assert len(case.notes) > 0

    def test_valid_event_fixtures_pass_model(self) -> None:
        """Verify that all valid event fixtures actually pass validation."""
        cases = load_fixtures("events")
        for case in cases:
            if not case.expected_valid:
                continue
            if case.event_type not in _EVENT_TYPE_TO_MODEL:
                continue
            result = validate_event(case.payload, case.event_type)
            assert result.valid is True, (
                f"Fixture {case.id} expected valid but failed: "
                f"{result.model_violations}"
            )

    def test_invalid_event_fixtures_fail_model(self) -> None:
        """Verify that all invalid event fixtures actually fail validation."""
        cases = load_fixtures("events")
        for case in cases:
            if case.expected_valid:
                continue
            if case.event_type not in _EVENT_TYPE_TO_MODEL:
                continue
            result = validate_event(case.payload, case.event_type)
            assert result.valid is False, (
                f"Fixture {case.id} expected invalid but passed"
            )


# ---------------------------------------------------------------------------
# T028: Package data accessible
# ---------------------------------------------------------------------------


class TestPackageData:
    """Verify that fixtures are accessible from the installed package."""

    def test_manifest_accessible(self) -> None:
        assert _MANIFEST_PATH.is_file()

    def test_load_fixtures_after_install(self) -> None:
        """load_fixtures works after pip install -e ."""
        cases = load_fixtures("events")
        assert len(cases) > 0
