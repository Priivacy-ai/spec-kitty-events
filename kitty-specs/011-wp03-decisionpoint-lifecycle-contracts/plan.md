# Implementation Plan: DecisionPoint Lifecycle Contracts

**Branch**: `011-wp03-decisionpoint-lifecycle-contracts` | **Date**: 2026-02-27 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/kitty-specs/011-wp03-decisionpoint-lifecycle-contracts/spec.md`

## Summary

Add a canonical DecisionPoint lifecycle contract family to `spec-kitty-events` with mandatory audit-trail payload fields, deterministic reducer transitions (`open`, `discussing`, `resolved`, optional `overridden`), conformance fixtures, and explicit versioning/export notes for downstream runtime and SaaS consumers.

## Technical Context

**Language/Version**: Python >=3.10, strict typing via mypy
**Primary Dependencies**: pydantic v2, pytest, hypothesis, jsonschema (conformance extra)
**Storage**: N/A (pure event contract package)
**Testing**: pytest unit/integration/property/conformance suites
**Target Platform**: PyPI package consumed by `spec-kitty` and `spec-kitty-saas`
**Project Type**: Single package (`src/spec_kitty_events/`)
**Current Package Version**: 2.5.0
**Planned Contract Min Version**: 2.6.0 (additive 2.x)

## Current Modules and Touchpoints

Planned source touchpoints in this repository:

- `src/spec_kitty_events/decisionpoint.py` (new): DecisionPoint constants, enums, payloads, reducer, output models.
- `src/spec_kitty_events/status.py` (reuse only): deterministic sort/dedup helpers via `status_event_sort_key` and `dedup_events`.
- `src/spec_kitty_events/conformance/validators.py`: register DecisionPoint event type -> model and schema mappings.
- `src/spec_kitty_events/conformance/loader.py`: add `decisionpoint` fixture category.
- `src/spec_kitty_events/conformance/fixtures/manifest.json`: add valid/invalid/replay and reducer-output fixture entries.
- `src/spec_kitty_events/conformance/fixtures/decisionpoint/{valid,invalid,replay}` (new): DecisionPoint fixture files.
- `src/spec_kitty_events/schemas/generate.py`: include DecisionPoint payload models in deterministic schema generation list.
- `src/spec_kitty_events/schemas/*.schema.json`: committed generated schemas for DecisionPoint payloads.
- `src/spec_kitty_events/__init__.py`: public exports for DecisionPoint constants/models/reducer.

Planned test touchpoints:

- `tests/unit/test_decisionpoint.py`
- `tests/test_decisionpoint_reducer.py`
- `tests/property/test_decisionpoint_determinism.py`
- `tests/test_decisionpoint_conformance.py`

## Schema and Versioning Touchpoints

- Add `DECISION_POINT_SCHEMA_VERSION = "2.6.0"` in the DecisionPoint module.
- Add conformance manifest entries for DecisionPoint fixtures with `min_version: "2.6.0"`.
- Ensure schema generation is deterministic (`sort_keys=True` JSON output in schema generator flow).
- Publish DecisionPoint API through `__init__.py` export list.
- Version/export notes must call out additive 2.x contract introduction and required consumer pin (`>=2.6.0`).

## Execution Plan

### Phase 1 (WP01): Contract Core and Reducer

- Define event constants, state enum, role enum, and frozen payload models with mandatory audit fields.
- Encode authority policy constraints in validation and reducer logic:
  - mission owner final authority is human-only,
  - LLM roles advisory/informed only in P0,
  - no LLM mission-owner authority.
- Implement deterministic reducer transitions and anomaly recording.

### Phase 2 (WP02): Conformance, Replay, and Release Surface

- Add conformance fixtures (valid, invalid, replay, golden outputs) and manifest entries.
- Register DecisionPoint mappings in conformance validator and loader.
- Add reducer replay tests and property determinism checks.
- Add schema generation and committed schema artifacts.
- Add export/versioning/downstream impact notes.

## Risks

| Risk | Impact | Mitigation |
|---|---|---|
| Naming overlap with existing decision-adjacent contracts (`DecisionInput*`, `DecisionCaptured`) | Consumer confusion and mapper bugs | Use a dedicated `decisionpoint` event family and explicit mapping table entries |
| Policy ambiguity around LLM and mission-owner authority | Security and governance drift | Enforce validation rule set in payload/reducer tests, include invalid fixtures for policy violations |
| Non-deterministic replay output | Broken SaaS/runtime projections | Keep strict sort+dedup pipeline and commit golden replay outputs |
| Versioning drift across fixtures/schema/exports | Partial adoption failures | Gate merge on manifest/schema/export checks and explicit min-version assertions |

## Acceptance Gate

All of the following must pass before the feature is considered complete:

1. `python3.11 -m mypy --strict src/spec_kitty_events/decisionpoint.py`
2. `python3.11 -m pytest tests/unit/test_decisionpoint.py tests/test_decisionpoint_reducer.py tests/property/test_decisionpoint_determinism.py -v`
3. `python3.11 -m pytest tests/test_decisionpoint_conformance.py -v`
4. `python3.11 -m pytest --pyargs spec_kitty_events.conformance`
5. `python3.11 -m pytest tests/ -q` (no regressions)
6. Public import smoke check succeeds for all DecisionPoint exports from `spec_kitty_events`.
