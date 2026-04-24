"""Unit tests for the schemas subpackage loader API."""
from __future__ import annotations

import json
import pytest

from spec_kitty_events.schemas import list_schemas, load_schema, schema_path


def test_list_schemas_returns_all_names() -> None:
    """Test that list_schemas enumerates every committed *.schema.json file."""
    import importlib.resources

    names = list_schemas()

    # Derive expected names directly from the filesystem so that adding new
    # schemas never breaks this test.  The invariant is structural: every
    # *.schema.json file in the schemas package must be enumerable via
    # list_schemas(), the result must be sorted, and each name must be a
    # non-empty string without the .schema.json suffix.
    schemas_path = importlib.resources.files("spec_kitty_events.schemas")
    on_disk = sorted(
        p.name.removesuffix(".schema.json")
        for p in schemas_path.iterdir()  # type: ignore[union-attr]
        if isinstance(p.name, str) and p.name.endswith(".schema.json")
    )

    assert names == on_disk, (
        f"list_schemas() returned {len(names)} names but "
        f"{len(on_disk)} *.schema.json files exist on disk.\n"
        f"  Extra in list_schemas():  {sorted(set(names) - set(on_disk))}\n"
        f"  Missing from list_schemas(): {sorted(set(on_disk) - set(names))}"
    )
    assert len(names) > 0, "list_schemas() must return at least one schema"
    assert names == sorted(names), "list_schemas() must return names in sorted order"


def test_load_schema_returns_dict() -> None:
    """Test that load_schema returns a dictionary."""
    schema = load_schema("event")
    assert isinstance(schema, dict)


def test_load_schema_has_schema_key() -> None:
    """Test that loaded schema has $schema key."""
    schema = load_schema("event")
    assert "$schema" in schema
    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"


def test_load_schema_has_id_key() -> None:
    """Test that loaded schema has $id key."""
    schema = load_schema("event")
    assert "$id" in schema
    assert schema["$id"] == "spec-kitty-events/event"


def test_load_schema_nonexistent_raises() -> None:
    """Test that loading nonexistent schema raises FileNotFoundError."""
    with pytest.raises(FileNotFoundError) as exc_info:
        load_schema("nonexistent")
    assert "No schema found for 'nonexistent'" in str(exc_info.value)
    assert "Available:" in str(exc_info.value)


def test_schema_path_returns_path() -> None:
    """Test that schema_path returns a valid Path object."""
    path = schema_path("event")
    assert path.exists()
    assert path.suffix == ".json"
    assert "event.schema.json" in str(path)


def test_all_schemas_are_valid_json() -> None:
    """Test that all schemas can be loaded and parsed as JSON."""
    names = list_schemas()
    for name in names:
        schema = load_schema(name)
        # Verify it's valid JSON by round-tripping
        json_str = json.dumps(schema)
        parsed = json.loads(json_str)
        assert isinstance(parsed, dict)
        assert "$schema" in parsed
        assert "$id" in parsed
