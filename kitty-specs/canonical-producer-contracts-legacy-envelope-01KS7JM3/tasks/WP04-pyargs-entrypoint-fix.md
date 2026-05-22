---
work_package_id: WP04
title: Public-surface integration, manifest registrations, pyargs entrypoint health
dependencies:
- WP01
- WP02
- WP03
requirement_refs:
- FR-003
- FR-011
- FR-012
- FR-013
- FR-014
- FR-015
- NFR-002
- NFR-005
- C-008
planning_base_branch: kitty/pr/1198-canonical-producer-contracts
merge_target_branch: kitty/pr/1198-canonical-producer-contracts
branch_strategy: Planning artifacts for this mission were generated on kitty/pr/1198-canonical-producer-contracts. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into kitty/pr/1198-canonical-producer-contracts unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-canonical-producer-contracts-legacy-envelope-01KS7JM3
base_commit: 18c8835265ccfeda116172ba6db02af518fc89d4
created_at: '2026-05-22T10:56:00.145236+00:00'
subtasks:
- T010
- T011b
- T016
- T017b
- T019
- T020
- T021
- T022
phase: Phase 3 - Conformance suite health
shell_pid: '74710'
history:
- timestamp: '2026-05-22T10:22:16Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/spec_kitty_events/conformance/
execution_mode: code_change
lane: planned
owned_files:
- src/spec_kitty_events/__init__.py
- src/spec_kitty_events/conformance/test_pyargs_entrypoint.py
- src/spec_kitty_events/conformance/fixtures/events/invalid/wp_status_changed_invalid_lane.json
- src/spec_kitty_events/conformance/fixtures/manifest.json
review_status: ''
reviewed_by: ''
role: implementer
tags: []
---

# Work Package Prompt: WP04 — Pyargs entrypoint wrapper-shape extraction + stale fixture fix

## ⚡ Do This First: Load Agent Profile

```text
/ad-hoc-profile-load python-pedro
```

Or:

```bash
spec-kitty agent profile show python-pedro
```

---

## ⚠️ Review Feedback Status

If `review_status` above says `has_feedback`, scroll to **Review Feedback** below. Update to `acknowledged` when you start.

## Review Feedback

*(empty)*

---

## Objective

WP04 is the public-surface integration hub. It depends on WP01 (semantic dispatch + registry), WP02 (model classes + fixture files), and WP03 (legacy module + legacy fixture files). It performs the file edits that have to land last:

1. **Package-root exports** (`src/spec_kitty_events/__init__.py`):
   - Add `LOCAL_ONLY_EVENT_TYPES: frozenset[str] = frozenset()` (FR-013, C-008).
   - Re-export the seven new payload models from WP02.
   - Re-export the `spec_kitty_events.legacy` surface from WP03.
2. **Manifest registrations** (`src/spec_kitty_events/conformance/fixtures/manifest.json`):
   - Register the seven new event-type fixtures shipped by WP02 (`min_version: "5.2.0"`, FR-012).
   - Register the two legacy-normalization fixtures shipped by WP03 (`event_type: "LegacyEnvelope"`, `fixture_type: "legacy_normalization"`).
   - Update notes on the fixed stale fixture (see #4 below).
3. **Pyargs entrypoint wrapper-shape extraction** (`test_pyargs_entrypoint.py`):
   - Detect wrapper-shape fixtures `{class, expected, input, notes, expected_error_code}` and extract `.input` before calling `validate_event`.
   - Special-case `LaneMapping` and `LegacyEnvelope` event_types so they are excluded from the validate_event parametrization.
4. **Stale fixture fix** (`events/invalid/wp_status_changed_invalid_lane.json`):
   - The fixture's `to_lane = "in_review"` is now a canonical lane value; the fixture passes shape validation, but the manifest still says `expected_result: "invalid"`. Replace with a genuinely invalid value (typo: `"in_reveiw"`).
5. **Verification**: `uv run pytest --pyargs spec_kitty_events.conformance -q` must exit 0 (FR-014, NFR-002).

## Context

### The 22 failures

Pre-mission baseline:

```
22 failed, 301 passed in 2.12s
```

Breakdown:
- 17 fixtures with wrapper shape `{class, expected, input, notes, [expected_error_code]}` — fail because validator sees wrapper keys as model_payload extras.
- 4 unforced-backward-transition fixtures (`unforced-{in_review,for_review,approved,in_progress}-to-planned-invalid`) — these PASS shape but should fail through `validate_transition`. **After WP01 lands**, these now fail through the new semantic dispatch — WP04 just needs to verify.
- 1 stale `wp-status-changed-invalid-lane` fixture — `to_lane: "in_review"` is now canonical.

So this WP must:
- T019/T020: extract `.input` from wrapper fixtures, skip lane-mapping `LegacyEnvelope` and `LaneMapping` fixtures.
- T021: fix the stale fixture.
- T022: re-run pyargs and verify 0 failures.

## Implementation guidance

### T010 — Add `LOCAL_ONLY_EVENT_TYPES` to package root

**File**: `src/spec_kitty_events/__init__.py`

Add a new constant export (near the existing `__version__` line):

```python
# Machine-readable classification surface for event types that are NOT
# routed through the SaaS-bound producer path. Empty in this release —
# every CLI-emitted event audited as of spec-kitty 43305c12c routes
# through SpecKittyEventEmitter._emit(). The surface is published so
# downstream consumers (CLI canonical-producer lint, SaaS adapter) can
# import the set and adjust enforcement without re-shipping a contract.
LOCAL_ONLY_EVENT_TYPES: frozenset[str] = frozenset()
```

Add `"LOCAL_ONLY_EVENT_TYPES"` to the existing `__all__` tuple.

### T011b — Re-export seven payload models and the legacy surface from `__init__.py`

**File**: `src/spec_kitty_events/__init__.py`

Add imports (near existing lifecycle/project_lifecycle import blocks):

```python
from spec_kitty_events.build_lifecycle import (
    BuildRegisteredPayload,
    BuildHeartbeatPayload,
)
from spec_kitty_events.project_lifecycle import (
    # ... existing imports ...
    WPAssignedPayload,
    HistoryAddedPayload,
    ErrorLoggedPayload,
    DependencyResolvedPayload,
)
from spec_kitty_events.lifecycle import (
    # ... existing imports ...
    MissionOriginBoundPayload,
)

from spec_kitty_events import legacy
from spec_kitty_events.legacy import (
    LEGACY_ENVELOPE_CONTRACT_NAME,
    RECOGNIZED_LEGACY_SHAPES,
    NormalizedEnvelope,
    UnnormalizableLegacyDiagnostic,
    NormalizationResult,
    LegacyEnvelopeNormalizer,
)
```

Append all the new names to `__all__`.

### T016 — Register the seven new event-type fixtures in `manifest.json`

**File**: `src/spec_kitty_events/conformance/fixtures/manifest.json`

Append seven entries to the `fixtures` array. Example for `WPAssigned`:

```json
{
  "id": "wp-assigned-valid",
  "path": "events/valid/wp_assigned.json",
  "expected_result": "valid",
  "event_type": "WPAssigned",
  "notes": "Canonical WPAssignedPayload with required fields.",
  "min_version": "5.2.0"
}
```

Add one entry for each of the seven event types (matching the seven fixture files shipped by WP02). `min_version: "5.2.0"` matches the next-Unreleased package version.

### T017b — Register the two legacy fixtures in `manifest.json`

**File**: `src/spec_kitty_events/conformance/fixtures/manifest.json`

Append two entries:

```json
{
  "id": "legacy-envelope-v1-pre30-normalizes",
  "path": "legacy/pre_3_0_envelope_normalizes.json",
  "expected_result": "valid",
  "event_type": "LegacyEnvelope",
  "fixture_type": "legacy_normalization",
  "notes": "Pre-3.0 envelope without project_uuid; normalizer promotes to canonical shape.",
  "min_version": "5.2.0"
},
{
  "id": "legacy-envelope-v1-unrecognized-diagnostic",
  "path": "legacy/unrecognized_legacy_diagnostic.json",
  "expected_result": "invalid",
  "event_type": "LegacyEnvelope",
  "fixture_type": "legacy_normalization",
  "notes": "Envelope with no recognized legacy markers; normalizer surfaces UnnormalizableLegacyDiagnostic.",
  "min_version": "5.2.0"
}
```

`event_type: "LegacyEnvelope"` is a new sentinel value used to exclude these fixtures from the standard validate_event parametrization (handled in T020).

### T019 — Detect wrapper-shape fixtures and extract `.input`

**File**: `src/spec_kitty_events/conformance/test_pyargs_entrypoint.py`

Modify `_event_fixture_params()`:

```python
_WRAPPER_KEYS = frozenset({
    "class", "expected", "input", "notes", "expected_error_code",
    "expected_reason", "legacy_shape",
})


def _is_wrapper_shape(obj: Any) -> bool:
    """Return True if obj is a class_taxonomy / historical_row / legacy /
    similar wrapper that nests the actual event envelope under .input.
    """
    return (
        isinstance(obj, dict)
        and "input" in obj
        and isinstance(obj["input"], dict)
        and obj.keys() <= _WRAPPER_KEYS
    )


def _event_fixture_params() -> List[Dict[str, Any]]:
    params: List[Dict[str, Any]] = []
    for entry in _event_fixture_entries():
        fixture_path = _FIXTURES_DIR / entry["path"]
        payload: Any = json.loads(fixture_path.read_text(encoding="utf-8"))
        if _is_wrapper_shape(payload):
            payload = payload["input"]
        params.append({**entry, "payload": payload})
    return params
```

### T020 — Special-case lane_mapping_legacy and legacy_normalization fixtures

**File**: same.

Extend the existing filter in `_event_fixture_entries()` so:
- `event_type == "LaneMapping"` continues to be excluded (handled by `_lane_mapping_fixture_entries`).
- `event_type == "LegacyEnvelope"` is excluded (handled by tests in `tests/unit/test_legacy_normalizer.py`, not by `validate_event`).
- `fixture_type in {"replay_stream", "reducer_output", "timestamp_semantics", "legacy_normalization"}` continues to be excluded.
- Additionally, exclude entries whose `event_type` does not correspond to a key in `_EVENT_TYPE_TO_MODEL` — these are taxonomy-only fixtures used by other tests.

Updated filter:

```python
def _event_fixture_entries() -> List[Dict[str, Any]]:
    return [
        f for f in _MANIFEST["fixtures"]
        if f["event_type"] not in ("LaneMapping", "LegacyEnvelope")
        and f.get("fixture_type") not in (
            "replay_stream",
            "reducer_output",
            "timestamp_semantics",
            "legacy_normalization",
        )
    ]
```

If a class_taxonomy fixture's underlying `event_type` is not registered in `_EVENT_TYPE_TO_MODEL` (e.g. some `historical_row_raw` entries declaring `event_type` strings used purely for diagnostic taxonomy), the existing `validate_event` will raise `ValueError("Unknown event type: ...")`. Audit each failing fixture's manifest entry; if the `event_type` value is not in `_EVENT_TYPE_TO_MODEL`, either:
- (a) fix the manifest entry so `event_type` is a real type, or
- (b) add a new `fixture_type: "diagnostic_taxonomy"` to the manifest entry and add it to the filter.

Run the test once after T019 + T020 are in place to see which fixtures still fail; iterate until 0.

### T021 — Fix stale `wp-status-changed-invalid-lane` fixture

**File**: `src/spec_kitty_events/conformance/fixtures/events/invalid/wp_status_changed_invalid_lane.json`

Change to a genuinely invalid lane (typo of `in_review`):

```json
{
  "actor": "test-agent",
  "execution_mode": "worktree",
  "from_lane": "planned",
  "mission_slug": "mission-001",
  "to_lane": "in_reveiw",
  "wp_id": "WP01"
}
```

Keys are sorted alphabetically to satisfy `test_fixture_determinism.py`.

Also update the manifest `notes` for this fixture entry (in `conformance/fixtures/manifest.json`) to reflect the new content:

```json
{
  "id": "wp-status-changed-invalid-lane",
  "path": "events/invalid/wp_status_changed_invalid_lane.json",
  "expected_result": "invalid",
  "event_type": "WPStatusChanged",
  "notes": "StatusTransitionPayload with invalid to_lane value 'in_reveiw' (typo); fails the Lane enum.",
  "min_version": "2.0.0"
}
```

### T022 — Verify pyargs entrypoint is green

Run:

```bash
uv run pytest --pyargs spec_kitty_events.conformance -q
```

Expected: 0 failures. Wall-clock time well under NFR-002's 10s budget.

If any fixtures still fail, iterate on T020's filter. The goal is zero red, not zero skipped — every fixture must have a clear home (event-conformance test, lane-mapping test, legacy-normalizer test, or an explicit `fixture_type` opt-out).

## Branch Strategy

- WP04 depends on WP01 and WP02. Wait for those to land on the mission branch before starting.
- Same merge target as other WPs: mission branch → orchestrator PR → `main`.

## Definition of Done

- [ ] `LOCAL_ONLY_EVENT_TYPES = frozenset()` exported from `__init__.py` and listed in `__all__`.
- [ ] Seven new payload models re-exported from `__init__.py`.
- [ ] Legacy module re-exported from `__init__.py` (`LEGACY_ENVELOPE_CONTRACT_NAME`, `RECOGNIZED_LEGACY_SHAPES`, `NormalizedEnvelope`, `UnnormalizableLegacyDiagnostic`, `NormalizationResult`, `LegacyEnvelopeNormalizer`).
- [ ] Seven new fixture manifest entries with `min_version: "5.2.0"`.
- [ ] Two legacy fixture manifest entries with `event_type: "LegacyEnvelope"` + `fixture_type: "legacy_normalization"`.
- [ ] `_is_wrapper_shape()` helper added; `_event_fixture_params()` extracts `.input` for wrapper fixtures.
- [ ] `_event_fixture_entries()` filter excludes `LegacyEnvelope` and `legacy_normalization` fixture types in addition to existing exclusions.
- [ ] `wp_status_changed_invalid_lane.json` uses a genuinely invalid lane value (typo).
- [ ] Manifest notes for the fixed fixture reflect the new content.
- [ ] `uv run pytest --pyargs spec_kitty_events.conformance -q` exits 0.
- [ ] Wall-clock time for the suite < 10s (NFR-002).
- [ ] `uv run pytest tests/test_fixture_determinism.py -q` still exits 0.
- [ ] Sanity: `python -c "from spec_kitty_events import LOCAL_ONLY_EVENT_TYPES, LegacyEnvelopeNormalizer, WPAssignedPayload"` succeeds.

## Reviewer guidance

1. Verify the wrapper-detection helper checks `obj.keys() <= _WRAPPER_KEYS` so a fixture that happens to have `input` as one of many keys does not get accidentally extracted.
2. Verify the fixture filter excludes both `event_type` and `fixture_type` correctly; no fixture should be silently skipped without rationale.
3. Verify the stale fixture's `to_lane` value is in fact rejected by the `Lane` enum (try `Lane("in_reveiw")` — must raise `ValueError`).
4. Verify the manifest is still sorted by `id` if the existing convention requires it.

## Risks

- **Risk**: An unaudited fixture type fails after the filter change. **Mitigation**: T022 explicitly re-runs the pyargs suite and iterates until 0 failures.
- **Risk**: The wrapper-detection helper is too permissive and extracts `input` from a non-wrapper fixture. **Mitigation**: the `obj.keys() <= _WRAPPER_KEYS` check is strict — only fixtures whose keys are a subset of the wrapper key set match.
- **Risk**: A reviewer-time question whether the legacy fixtures should also go through the wrapper extraction. **Mitigation**: no — legacy fixtures are exercised by `tests/unit/test_legacy_normalizer.py` (in WP03) which reads `entry["input"]` directly. Excluding them from the pyargs entrypoint is correct.
