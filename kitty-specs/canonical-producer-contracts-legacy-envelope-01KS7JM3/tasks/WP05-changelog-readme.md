---
work_package_id: WP05
title: CHANGELOG and README documentation
dependencies:
- WP01
- WP02
- WP03
- WP04
requirement_refs:
- FR-007
- FR-016
- FR-017
planning_base_branch: kitty/pr/1198-canonical-producer-contracts
merge_target_branch: kitty/pr/1198-canonical-producer-contracts
branch_strategy: Planning artifacts for this mission were generated on kitty/pr/1198-canonical-producer-contracts. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into kitty/pr/1198-canonical-producer-contracts unless the human explicitly redirects the landing branch.
base_branch: kitty/pr/1198-canonical-producer-contracts
base_commit: 2a0667a1131fbc9db3ff5dba4634f52521a5293c
created_at: '2026-05-22T10:22:16+00:00'
subtasks:
- T023
- T024
phase: Phase 4 - Documentation
agent: "claude:opus-4-7:reviewer-renata:reviewer"
shell_pid: "77324"
history:
- timestamp: '2026-05-22T10:22:16Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
agent_profile: curator-carla
authoritative_surface: CHANGELOG.md
execution_mode: planning_artifact
lane: planned
owned_files:
- CHANGELOG.md
- README.md
review_status: ''
reviewed_by: ''
role: implementer
tags: []
---

# Work Package Prompt: WP05 — CHANGELOG and README docs

## ⚡ Do This First: Load Agent Profile

```text
/ad-hoc-profile-load curator-carla
```

Or:

```bash
spec-kitty agent profile show curator-carla
```

---

## ⚠️ Review Feedback Status

If `review_status` above says `has_feedback`, scroll to **Review Feedback** below. Update to `acknowledged` when you start.

## Review Feedback

*(empty)*

---

## Objective

Document the four shipped surfaces in `CHANGELOG.md` and `README.md`:

1. Semantic validation enforcement on `WPStatusChanged` via `validate_event`.
2. `legacy_envelope_v1` contract via `spec_kitty_events.legacy`.
3. Seven new canonical event-type contracts + `LOCAL_ONLY_EVENT_TYPES` surface.
4. Pyargs entrypoint health restored (fixture wrapper extraction + stale fixture fix).

Per C-001, **do not** bump the version or publish to PyPI. CHANGELOG entry lands under `[Unreleased]`; orchestrator owns the actual bump in Phase 5.

## Context

The CHANGELOG voice convention used in the 5.1.0 entry is "Changed" and "Added" subsections with bullet items naming the mission and the canonical contract anchor. Match that style.

## Implementation guidance

### T023 — Add `[Unreleased]` entry to `CHANGELOG.md`

Insert under the existing `## [Unreleased]` line at the top of the file. Skeleton:

```markdown
## [Unreleased]

### Added

- **Canonical event-type contracts for seven previously-uncontracted SaaS-bound events** (additive, wire-compatible). Added pydantic payload models and `_EVENT_TYPE_TO_MODEL` entries for `WPAssigned`, `BuildRegistered`, `BuildHeartbeat`, `HistoryAdded`, `ErrorLogged`, `DependencyResolved`, `MissionOriginBound`. Each model uses `ConfigDict(frozen=True, extra="forbid")`. Field shapes are derived from the canonical producer call sites in `spec-kitty/src/specify_cli/sync/emitter.py` (commit `43305c12c`, lines 720–1431). Mission: `canonical-producer-contracts-legacy-envelope-01KS7JM3`. Canonical authority: `kitty-specs/canonical-producer-contracts-legacy-envelope-01KS7JM3/data-model.md`.

- **`LOCAL_ONLY_EVENT_TYPES` machine-readable classification surface** (additive). New `frozenset[str]` exported from the package root. Empty in this release — every CLI-emitted event audited as of spec-kitty `43305c12c` routes through `SpecKittyEventEmitter._emit()` (the SaaS-bound central path). The surface is published so downstream consumers (CLI canonical-producer lint, SaaS adapter) can import the set and adjust enforcement without re-shipping a contract.

- **`legacy_envelope_v1` named compatibility contract** (additive). New `spec_kitty_events.legacy` module exporting `LegacyEnvelopeNormalizer`, `NormalizedEnvelope`, `UnnormalizableLegacyDiagnostic`, `NormalizationResult`, `LEGACY_ENVELOPE_CONTRACT_NAME`, and `RECOGNIZED_LEGACY_SHAPES`. Three named legacy shapes are recognized in v1: `pre_3_0_envelope` (pre-3.0 envelopes missing `project_uuid`; minted via deterministic `uuid5(NAMESPACE_URL || 'spec-kitty-events/legacy', f'{node_id}/{build_id}')`), `feature_keys_envelope` (retired `feature_slug` / `feature_number` keys mapped to `mission_slug` / `mission_number`), and `awaiting_review_synonym` (payload `to_lane = "awaiting-review"` mapped to canonical `"in_review"`). Un-normalizable rows surface as structured `UnnormalizableLegacyDiagnostic` rather than silent passes. Audit-preserving: both result variants carry the original `raw` dict. Phase 3 (spec-kitty-saas#274) consumes this contract to replace the implicit `_should_validate_strict_envelope()` carve-out. Canonical authority: `kitty-specs/canonical-producer-contracts-legacy-envelope-01KS7JM3/contracts/legacy-envelope-v1.md`.

- **Legacy-envelope conformance fixtures**. Added `conformance/fixtures/legacy/pre_3_0_envelope_normalizes.json` (normalization-success) and `conformance/fixtures/legacy/unrecognized_legacy_diagnostic.json` (un-normalizable). Both registered in `manifest.json` under `event_type: "LegacyEnvelope"` with `fixture_type: "legacy_normalization"`.

### Changed

- **`validate_event()` enforces `validate_transition()` for `WPStatusChanged`** (semantically tighter, wire-compatible). When the pydantic shape layer accepts a `WPStatusChanged` payload, `validate_event()` now also runs the `status.validate_transition()` business-rule check. Unforced backward review-rejection transitions (the rc14→rc22 drift signature) now fail through the public conformance gate with `ModelViolation` entries that preserve the documented routing substrings `force=True` and `review-rejection`. The new behavior is gated behind a `_SEMANTIC_VALIDATORS` registry so future event types with business rules plug in additively. Mission: `canonical-producer-contracts-legacy-envelope-01KS7JM3`.

- **Pyargs conformance entrypoint extracts `.input` from wrapper fixtures**. Fixtures whose on-disk shape is `{class, expected, input, notes, [expected_error_code]}` (class_taxonomy, historical_row_raw, lane_mapping_legacy, legacy normalization) are now correctly routed: the test extracts `entry["input"]` before calling `validate_event`. Lane-mapping and legacy-envelope fixtures are excluded from the validate_event parametrization via `event_type` / `fixture_type` filters and exercised by dedicated tests.

- **Stale `wp-status-changed-invalid-lane` fixture corrected**. The fixture's `to_lane` value was `"in_review"`, which has been canonical since 3.0. Replaced with `"in_reveiw"` (typo) so the Lane enum genuinely rejects it. Manifest notes updated.
```

Place this content immediately under the existing `## [Unreleased]` heading at the top of `CHANGELOG.md`. Do not bump the version. Do not modify the existing 5.1.0 entry.

### T024 — Update `README.md`

Add two new sections (placement: near the existing "Conformance" or "Public API" sections; if no such section exists, add them near the top after the package summary).

**Section: Legacy envelope normalization (`legacy_envelope_v1`)**

Brief markdown section (~30 lines) describing:
- What `LegacyEnvelopeNormalizer` is for.
- The three recognized shapes.
- The two result variants and their `raw` audit-preservation guarantee.
- A one-paragraph code example matching `quickstart.md`'s usage pattern.
- A link to the canonical contract document: `kitty-specs/canonical-producer-contracts-legacy-envelope-01KS7JM3/contracts/legacy-envelope-v1.md`.

**Section: Local-only event classification (`LOCAL_ONLY_EVENT_TYPES`)**

Brief markdown section (~15 lines) describing:
- The purpose of the `frozenset[str]` surface.
- That it is currently empty.
- That downstream consumers (CLI lint, SaaS adapter) may import it.
- The classification rule: events that DO NOT route through `SpecKittyEventEmitter._emit()` belong here.

Suggested example for the legacy section:

```markdown
## Legacy envelope normalization (`legacy_envelope_v1`)

Spec Kitty publishes a named, frozen contract for promoting known legacy
event shapes to canonical 3.x envelopes:

```python
from spec_kitty_events.legacy import (
    LegacyEnvelopeNormalizer,
    NormalizedEnvelope,
    UnnormalizableLegacyDiagnostic,
)
from spec_kitty_events.conformance.validators import validate_event

result = LegacyEnvelopeNormalizer().normalize(stored_legacy_row)

match result:
    case NormalizedEnvelope(canonical=canonical, raw=raw, legacy_shape=shape):
        conformance = validate_event(canonical, canonical["event_type"], strict=True)
        # ship to materializer, retain raw for audit
    case UnnormalizableLegacyDiagnostic(reason=reason, shape_hints=hints, raw=raw):
        # classify as legacy/business-rule diagnostic; never silent
```

See [the contract](kitty-specs/canonical-producer-contracts-legacy-envelope-01KS7JM3/contracts/legacy-envelope-v1.md)
for the recognized shapes and guarantees.
```

## Branch Strategy

Same as other WPs. Land last.

## Definition of Done

- [ ] `CHANGELOG.md` `[Unreleased]` section contains the Added and Changed bullets listed above.
- [ ] `README.md` has new sections for `spec_kitty_events.legacy` and `LOCAL_ONLY_EVENT_TYPES`.
- [ ] Version number NOT bumped (orchestrator owns Phase 5 publish).
- [ ] CHANGELOG entry references the mission slug and canonical authority paths.
- [ ] README sections include working code examples.

## Reviewer guidance

1. Verify the CHANGELOG entry is under `[Unreleased]`, not under a new version heading.
2. Verify no version number changes in `pyproject.toml` or `src/spec_kitty_events/__init__.py`.
3. Verify the CHANGELOG voice matches the existing 5.1.0 entry (Added/Changed subsections; per-bullet anchoring to the mission and canonical authority).
4. Verify the README sections do not restructure existing sections; they're additive.
5. Verify markdown links resolve (path-relative to repo root).

## Risks

- **Risk**: README restructure conflicts with concurrent edits. **Mitigation**: WP05 lands last and only edits two files; no conflict surface.
- **Risk**: Future PyPI release inadvertently picks up `[Unreleased]` content. **Mitigation**: orchestrator's Phase 5 process re-titles `[Unreleased]` to the actual version at release time; this is the standard CHANGELOG convention.

## Activity Log

- 2026-05-22T11:00:52Z – claude:opus-4-7:curator-carla:implementer – shell_pid=77089 – Started implementation via action command
- 2026-05-22T11:02:18Z – claude:opus-4-7:curator-carla:implementer – shell_pid=77089 – WP05 ready
- 2026-05-22T11:02:25Z – claude:opus-4-7:reviewer-renata:reviewer – shell_pid=77324 – Started review via action command
