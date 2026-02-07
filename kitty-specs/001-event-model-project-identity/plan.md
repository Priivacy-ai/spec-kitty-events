# Implementation Plan: Event Model Project Identity

**Branch**: `001-event-model-project-identity` | **Date**: 2026-02-07 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `kitty-specs/001-event-model-project-identity/spec.md`

## Summary

Add `project_uuid: uuid.UUID` (required) and `project_slug: Optional[str]` (optional, default `None`) to the `Event` model in `src/spec_kitty_events/models.py`. Update serialization (`to_dict`, `from_dict`), all 107 `Event(` call sites across 17 files, README quickstart, and bump version to `0.1.1-alpha`. No backward compatibility — this is a coordinated release with CLI and SaaS teams.

## Technical Context

**Language/Version**: Python 3.10+
**Primary Dependencies**: Pydantic 2.x (native `uuid.UUID` support), python-ulid
**Storage**: N/A (library provides abstract adapters; in-memory for testing)
**Testing**: pytest with pytest-cov, Hypothesis for property-based tests, mypy --strict
**Target Platform**: Python library (cross-platform)
**Project Type**: Single Python package
**Performance Goals**: N/A (data model change, no runtime perf impact)
**Constraints**: Must maintain mypy --strict compliance, frozen Pydantic model
**Scale/Scope**: ~940 lines source, ~2,300 lines tests, 107 `Event(` call sites across 17 files

## Constitution Check

*No constitution file found. Skipping gate check.*

## Project Structure

### Documentation (this feature)

```
kitty-specs/001-event-model-project-identity/
├── plan.md              # This file
├── research.md          # Phase 0: Technical decisions
├── data-model.md        # Phase 1: Updated entity model
├── quickstart.md        # Phase 1: Updated usage examples
└── tasks.md             # Phase 2 output (NOT created by /spec-kitty.plan)
```

### Source Code (repository root)

```
src/spec_kitty_events/
├── __init__.py          # Version bump 0.1.0-alpha → 0.1.1-alpha
├── models.py            # Add project_uuid, project_slug to Event
├── clock.py             # No changes
├── storage.py           # No changes (Event dict serialization handles new fields)
├── conflict.py          # No changes (operates on Event objects)
├── merge.py             # No changes (operates on Event objects)
├── crdt.py              # No changes (operates on Event objects)
├── error_log.py         # No changes
├── topology.py          # No changes
└── py.typed             # No changes

tests/
├── conftest.py          # No changes
├── unit/
│   ├── test_models.py           # Add project_uuid to all Event() calls + new validation tests
│   ├── test_clock.py            # No changes (doesn't construct Events)
│   ├── test_storage.py          # Add project_uuid to all Event() calls
│   ├── test_conflict.py         # Add project_uuid to all Event() calls (25 occurrences)
│   ├── test_merge.py            # Add project_uuid to all Event() calls (17 occurrences)
│   ├── test_crdt.py             # Add project_uuid to all Event() calls (10 occurrences)
│   ├── test_error_log.py        # No changes
│   └── test_placeholder.py     # No changes
├── integration/
│   ├── test_quickstart.py       # Add project_uuid to all Event() calls (11 occurrences)
│   ├── test_conflict_resolution.py # Add project_uuid to all Event() calls (7 occurrences)
│   ├── test_event_emission.py   # Add project_uuid to all Event() calls (4 occurrences)
│   ├── test_adapters.py         # Add project_uuid to all Event() calls (2 occurrences)
│   ├── test_clock_persistence.py # No changes
│   └── test_error_retention.py  # No changes
└── property/
    ├── test_crdt_laws.py        # Add project_uuid to Hypothesis strategies (2 occurrences)
    └── test_determinism.py      # Add project_uuid to Hypothesis strategies (1 occurrence)

README.md                # Update quickstart examples + API overview
pyproject.toml           # Version bump
CHANGELOG.md             # Add 0.1.1-alpha entry
```

**Structure Decision**: Existing single-package structure. No new files needed — only modifications to `models.py`, test files, `README.md`, `pyproject.toml`, `CHANGELOG.md`, and `__init__.py`.

## Complexity Tracking

*No constitution violations. No complexity justifications needed.*

## Change Impact Analysis

| File | Event() calls | Change type |
|------|:---:|---|
| `src/spec_kitty_events/models.py` | 2 | Add fields + update to_dict/from_dict |
| `src/spec_kitty_events/__init__.py` | 0 | Version bump only |
| `tests/unit/test_conflict.py` | 25 | Add `project_uuid` param |
| `tests/unit/test_merge.py` | 17 | Add `project_uuid` param |
| `tests/integration/test_quickstart.py` | 11 | Add `project_uuid` param |
| `tests/unit/test_crdt.py` | 10 | Add `project_uuid` param |
| `tests/integration/test_conflict_resolution.py` | 7 | Add `project_uuid` param |
| `tests/unit/test_models.py` | 7 | Add `project_uuid` param + new tests |
| `tests/unit/test_storage.py` | 6 | Add `project_uuid` param |
| `tests/integration/test_event_emission.py` | 4 | Add `project_uuid` param |
| `src/spec_kitty_events/topology.py` | 3 | Type hints only (no construction) |
| `src/spec_kitty_events/conflict.py` | 3 | Type hints only (no construction) |
| `src/spec_kitty_events/crdt.py` | 4 | Type hints only (no construction) |
| `src/spec_kitty_events/merge.py` | 2 | Type hints only (no construction) |
| `tests/integration/test_adapters.py` | 2 | Add `project_uuid` param |
| `tests/property/test_crdt_laws.py` | 2 | Add `project_uuid` to strategies |
| `tests/property/test_determinism.py` | 1 | Add `project_uuid` to strategies |
| `README.md` | 1 | Update quickstart example |
| `pyproject.toml` | 0 | Version bump |
| `CHANGELOG.md` | 0 | New entry |
