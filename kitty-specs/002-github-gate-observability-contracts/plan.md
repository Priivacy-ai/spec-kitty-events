# Implementation Plan: GitHub Gate Observability Contracts
*Path: kitty-specs/002-github-gate-observability-contracts/plan.md*

**Branch**: `002-github-gate-observability-contracts` | **Date**: 2026-02-07 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `kitty-specs/002-github-gate-observability-contracts/spec.md`

## Summary

Add typed Pydantic payload models (`GatePassedPayload`, `GateFailedPayload`) and a deterministic GitHub `check_run` conclusion mapping helper to the `spec-kitty-events` library. All new code lives in a new `gates.py` module, preserving the existing generic `Event` architecture. Ignored conclusions (`neutral`, `skipped`, `stale`) emit no event but are logged via stdlib and an optional callback. Unknown conclusions raise an explicit error.

## Technical Context

**Language/Version**: Python 3.10+ (matches existing `pyproject.toml`)
**Primary Dependencies**: Pydantic >=2.0.0,<3.0.0 (existing), python-ulid >=1.1.0 (existing). No new dependencies.
**Storage**: N/A — payload models are pure data contracts, no persistence logic added.
**Testing**: pytest + pytest-cov (existing), Hypothesis (existing for property tests), mypy --strict (existing)
**Target Platform**: Library (PyPI package), consumed by CLI and SaaS
**Project Type**: Single Python library with src/ layout
**Performance Goals**: N/A — validation and mapping are synchronous, sub-millisecond operations
**Constraints**: Must maintain mypy --strict compliance. Must not break existing `Event` model or public API. Additive-only changes (minor version bump).
**Scale/Scope**: 8 known GitHub conclusion values. 2 payload models. 1 mapping function. ~150-200 lines of production code + ~200 lines of tests.

## Constitution Check

*No constitution file found (`.kittify/memory/constitution.md` absent). Section skipped.*

## Project Structure

### Documentation (this feature)

```
kitty-specs/002-github-gate-observability-contracts/
├── plan.md              # This file
├── spec.md              # Feature specification
├── meta.json            # Feature metadata
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   └── gates-api.md     # API contract for gates module
├── quickstart.md        # Phase 1 output
└── checklists/
    └── requirements.md  # Spec quality checklist
```

### Source Code (repository root)

```
src/spec_kitty_events/
├── __init__.py          # Add exports: GatePassedPayload, GateFailedPayload,
│                        #   GatePayloadBase, map_check_run_conclusion,
│                        #   UnknownConclusionError
├── models.py            # UNCHANGED — generic Event, ErrorEntry, exceptions
└── gates.py             # NEW — payload models + mapping helper

tests/
├── unit/
│   └── test_gates.py    # NEW — payload validation, field enforcement,
│                        #   serialization round-trips
├── property/
│   └── test_gates_determinism.py  # NEW — mapping determinism property tests
└── conftest.py          # UNCHANGED (no new fixtures needed)
```

**Structure Decision**: Single new module `src/spec_kitty_events/gates.py` co-locates payload models and mapping logic. This avoids over-engineering (no subpackage) while keeping gate concerns separate from the generic event envelope in `models.py`.

## Design Decisions

### D1: Shared Base Payload Model

`GatePassedPayload` and `GateFailedPayload` share a common `GatePayloadBase` that holds all required fields (FR-001, FR-002). The two subclasses exist primarily for type discrimination — they enable consumers to use `isinstance()` checks and type narrowing. The base class is also exported for consumers who want to accept either payload type.

### D2: Literal Type Constraints

`gate_type` is typed as `Literal["ci"]` and `external_provider` as `Literal["github"]`. This makes the contract self-documenting and extensible — future gate types or providers add new literal values without breaking the base structure.

### D3: Conclusion Mapping as Pure Function + Logging

`map_check_run_conclusion(conclusion, on_ignored=None)` is a pure mapping function that:
- Returns `"GatePassed"` for `success`
- Returns `"GateFailed"` for `failure`, `timed_out`, `cancelled`, `action_required`
- Returns `None` for `neutral`, `skipped`, `stale` (and logs via `logging.getLogger("spec_kitty_events.gates")`)
- Raises `UnknownConclusionError` for any other value

The optional `on_ignored` callback has signature `Callable[[str, str], None]` → `(conclusion, reason)`.

### D4: Case Sensitivity

The mapping function accepts lowercase only and raises `UnknownConclusionError` for non-lowercase input (e.g., `"SUCCESS"`). GitHub's API returns lowercase values; accepting mixed case would mask upstream bugs.

### D5: URL Validation

`check_run_url` uses Pydantic's `AnyHttpUrl` type for structural validation. This ensures the field contains a well-formed HTTP/HTTPS URL without requiring network access.

### D6: Version Bump

This is an additive, non-breaking change → bump to `0.2.0-alpha` (minor version bump per semver).

## Complexity Tracking

*No constitution violations to justify. Feature adds one module with straightforward models and a lookup function.*
