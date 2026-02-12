---
work_package_id: WP07
title: Compatibility Table, Changelog, and Migration Notes
lane: "doing"
dependencies: [WP06]
base_branch: 005-event-contract-conformance-suite-WP06
base_commit: 65a647b9980d95fd0de21cefef3a99b43b9e520a
created_at: '2026-02-12T11:35:12.699714+00:00'
subtasks: [T040, T041, T042, T043, T044]
shell_pid: "22344"
history:
- date: '2026-02-12'
  action: created
  by: spec-kitty.tasks
---

# WP07 — Compatibility Table, Changelog, and Migration Notes

## Implementation Command

```bash
spec-kitty implement WP07 --base WP06
```

## Objective

Create consumer-facing documentation: `CHANGELOG.md` with migration notes, `COMPATIBILITY.md` with lane mapping table and field requirements, versioning policy, and consumer CI integration guide.

## Context

This WP fulfills FR-019 (compatibility table), FR-020 (changelog with migration notes), and FR-021 (SCHEMA_VERSION documentation). These artifacts are consumed by CLI and SaaS developers migrating from `0.4.x` to `2.0.0`.

**Key files to create**:
- `CHANGELOG.md` (repo root)
- `COMPATIBILITY.md` (repo root)

**Key files to verify**:
- All FR-001 through FR-023 are addressed across WP01–WP07

## Subtask Guidance

### T040: Create `CHANGELOG.md`

**Purpose**: Document the version history and migration path.

**Steps**:
1. Create `CHANGELOG.md` at repo root.
2. Structure:

```markdown
# Changelog

All notable changes to spec-kitty-events will be documented in this file.

This project adheres to [Semantic Versioning](https://semver.org/).

## [2.0.0-rc1] - 2026-02-XX

### Added
- **Lane Mapping Contract**: `SyncLaneV1` enum (4 values), `CANONICAL_TO_SYNC_V1` immutable mapping, `canonical_to_sync_v1()` function. Consumers import this instead of hardcoding the 7→4 lane mapping.
- **JSON Schema Artifacts**: 11 JSON Schema files generated from Pydantic v2 models, committed as canonical contract documents. Build-time generation script with CI drift detection (`python -m spec_kitty_events.schemas.generate --check`).
- **Conformance Validator API**: `validate_event()` with dual-layer validation (Pydantic + JSON Schema). Returns structured `ConformanceResult` with separate `model_violations` and `schema_violations` buckets.
- **Conformance Test Suite**: Pytest-runnable via `pytest --pyargs spec_kitty_events.conformance`. Manifest-driven fixtures covering all event types, lane mappings, and edge cases.
- **Fixture Loading API**: `load_fixtures()` and `FixtureCase` for programmatic fixture access.
- **`[conformance]` Optional Extra**: `pip install spec-kitty-events[conformance]` adds `jsonschema>=4.21.0` for JSON Schema validation layer.

### Changed
- **Version**: Graduated from `0.4.0-alpha` to `2.0.0-rc1`.
- **SCHEMA_VERSION**: Updated to `"2.0.0"` (locked for 2.x lifetime).

### Migration from 0.4.x
1. Update dependency: `spec-kitty-events>=2.0.0rc1,<3.0.0`
2. Replace hardcoded lane mappings with `canonical_to_sync_v1()`:
   ```python
   # Before (in consumer code):
   LANE_MAP = {"planned": "planned", "in_progress": "doing", ...}

   # After:
   from spec_kitty_events import Lane, canonical_to_sync_v1
   sync_lane = canonical_to_sync_v1(Lane.IN_PROGRESS)  # SyncLaneV1.DOING
   ```
3. Replace local status enum with `SyncLaneV1` import.
4. Add conformance CI step: `pytest --pyargs spec_kitty_events.conformance`

## [0.4.0-alpha] - 2026-02-XX

### Added
- Canonical Event Contract (Feature 004): `correlation_id`, `schema_version`, `data_tier` on Event model.
- Lifecycle event contracts and reducer.

## [0.3.0-alpha] - 2026-XX-XX

### Added
- Status State Model Contracts (Feature 003): 7-lane model, transition validation, reducer.

## [0.2.0-alpha] - 2026-XX-XX

### Added
- GitHub Gate Observability Contracts (Feature 002): Gate payloads, conclusion mapping.

## [0.1.0-alpha] - 2026-XX-XX

### Added
- Initial release: Event model, Lamport clock, CRDT merge, error logging.
```

3. Use real dates where known, placeholders where approximate.

**Validation**:
- [ ] CHANGELOG.md exists at repo root
- [ ] Migration section has concrete before/after code examples
- [ ] All new features from 2.0.0 are listed

### T041: Create `COMPATIBILITY.md`

**Purpose**: The definitive reference for lane mapping and field requirements.

**Steps**:
1. Create `COMPATIBILITY.md` at repo root.
2. Include:

**Lane Mapping Table**:

| Canonical Lane | SyncLaneV1 | Rationale |
|---|---|---|
| `planned` | `planned` | Direct mapping |
| `claimed` | `planned` | Pre-work, collapses to planned |
| `in_progress` | `doing` | Consumer-facing alias |
| `for_review` | `for_review` | Direct mapping |
| `done` | `done` | Direct mapping |
| `blocked` | `doing` | Mid-work, collapses to doing |
| `canceled` | `planned` | Resets to planned in sync model |

**Required/Optional Fields Per Event Type**: Table listing each event type, required fields, optional fields.

**Consumer CI Setup**: Step-by-step for adding conformance to CI.

**Validation**:
- [ ] All 7 canonical lanes documented
- [ ] All 4 sync lanes documented
- [ ] Every event type's required/optional fields listed

### T042: Document versioning policy

**Purpose**: Clear SemVer rules for the 2.x series.

**Steps**:
1. In `COMPATIBILITY.md`, add a "Versioning Policy" section:
   - `2.x.y`: Bug fixes and patch releases (no API changes)
   - `2.(x+1).0`: Additive, backward-compatible changes (new optional fields, new event types, new mapping versions like `SyncLaneV2`)
   - `3.0.0`: Any breaking change (removing fields, changing mapping behavior, removing event types)
   - `SyncLaneV1` mapping is locked: changing output for any input = `3.0.0`
   - New mapping versions are additive: `SyncLaneV2` can ship in `2.x`

**Validation**:
- [ ] Versioning policy is clear and unambiguous
- [ ] Examples of breaking vs non-breaking changes included

### T043: Document consumer CI integration

**Purpose**: Step-by-step guide for CLI and SaaS teams.

**Steps**:
1. In `COMPATIBILITY.md`, add "Consumer CI Integration" section:
   ```yaml
   # Step 1: Add dependency
   pip install "spec-kitty-events[conformance]>=2.0.0rc1,<3.0.0"

   # Step 2: Run upstream conformance
   pytest --pyargs spec_kitty_events.conformance -v

   # Step 3: Validate local payloads (optional)
   python -c "
   from spec_kitty_events.conformance import validate_event
   result = validate_event(your_payload, 'WPStatusChanged', strict=True)
   assert result.valid
   "

   # Step 4: Schema drift check (for spec-kitty-events repo only)
   python -m spec_kitty_events.schemas.generate --check
   ```

**Validation**:
- [ ] Steps are copy-pasteable
- [ ] Both consumers (CLI and SaaS) are addressed

### T044: Final review — all FRs addressed

**Purpose**: Verify every functional requirement from the spec is covered.

**Steps**:
1. Go through FR-001 to FR-023 and verify each is addressed:
   - FR-001 to FR-005: Lane mapping (WP01)
   - FR-006 to FR-009: JSON Schema (WP02)
   - FR-010 to FR-011: Fixtures (WP04)
   - FR-012 to FR-014: Validator (WP03)
   - FR-015 to FR-017: Pytest suite (WP05)
   - FR-018 to FR-021: Versioning (WP06)
   - FR-022 to FR-023: Package structure (WP02 + WP06)
2. If any FR is not addressed, flag it in a comment in the commit message.

**Validation**:
- [ ] All 23 FRs checked off
- [ ] No gaps identified (or gaps documented with justification)

## Definition of Done

- [ ] `CHANGELOG.md` exists with migration notes and feature list
- [ ] `COMPATIBILITY.md` exists with lane mapping table, field requirements, versioning policy, CI integration
- [ ] All FR-001 through FR-023 verified as addressed
- [ ] Full test suite still passes: `python3.11 -m pytest`
- [ ] `mypy --strict` still passes

## Risks

- **Documentation drift**: If code changes after docs are written, docs may be stale. This WP should be the last to merge.
- **Date placeholders**: Use actual dates for 2.0.0-rc1, approximate dates for historical versions.

## Reviewer Guidance

- Verify lane mapping table matches the locked V1 contract exactly.
- Verify migration guide code examples actually work (paste into a Python REPL and test).
- Verify every FR from the spec has a traceable implementation in one of WP01–WP07.
- Verify CI integration steps are complete and actionable.
