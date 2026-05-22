---
work_package_id: WP03
title: legacy_envelope_v1 normalizer (spec_kitty_events.legacy)
dependencies: []
requirement_refs:
- FR-006
- FR-007
- FR-008
- FR-009
- NFR-003
- NFR-004
- NFR-005
- C-004
- C-007
planning_base_branch: kitty/pr/1198-canonical-producer-contracts
merge_target_branch: kitty/pr/1198-canonical-producer-contracts
branch_strategy: Planning artifacts for this mission were generated on kitty/pr/1198-canonical-producer-contracts. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into kitty/pr/1198-canonical-producer-contracts unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-canonical-producer-contracts-legacy-envelope-01KS7JM3
base_commit: 18c8835265ccfeda116172ba6db02af518fc89d4
created_at: '2026-05-22T10:49:17.422202+00:00'
subtasks:
- T013
- T014
- T015
- T017
- T018
phase: Phase 2 - Legacy compatibility contract
shell_pid: "71755"
agent: "claude:opus-4-7:python-pedro:implementer"
history:
- timestamp: '2026-05-22T10:22:16Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/spec_kitty_events/
execution_mode: code_change
lane: planned
owned_files:
- src/spec_kitty_events/legacy.py
- src/spec_kitty_events/conformance/fixtures/legacy/pre_3_0_envelope_normalizes.json
- src/spec_kitty_events/conformance/fixtures/legacy/unrecognized_legacy_diagnostic.json
- tests/unit/test_legacy_normalizer.py
review_status: ''
reviewed_by: ''
role: implementer
tags: []
---

# Work Package Prompt: WP03 — `legacy_envelope_v1` normalizer

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

Publish the named legacy-envelope compatibility contract `legacy_envelope_v1` so Phase 3 SaaS adapter can replace its silent `_should_validate_strict_envelope()` bypass with an explicit normalization step. Ship the `LegacyEnvelopeNormalizer`, the result-type union, fixtures for the happy and un-normalizable paths, and tests.

## Context

### The contract

See `kitty-specs/<mission>/contracts/legacy-envelope-v1.md` for the authoritative spec. Three named legacy shapes are recognized in v1:

1. **`pre_3_0_envelope`** — pre-3.0 envelopes missing `project_uuid` but carrying `event_type`, `payload`, `event_id`, `node_id`, `build_id`. Mint `project_uuid = uuid.uuid5(NAMESPACE_URL, f"spec-kitty-events/legacy/{node_id}/{build_id}")`; require both `node_id` and `build_id` (otherwise emit a diagnostic).
2. **`feature_keys_envelope`** — envelopes carrying retired `feature_slug` / `feature_number`. Map → `mission_slug` / `mission_number`. Strip legacy keys at top-level and inside `payload`.
3. **`awaiting_review_synonym`** — `payload.to_lane == "awaiting-review"` → canonical `"in_review"`.

Fallthrough → `UnnormalizableLegacyDiagnostic(reason="unrecognized_legacy_shape")`.

## Implementation guidance

### T013 — Create `src/spec_kitty_events/legacy.py` with constants

**File**: NEW.

```python
"""Legacy envelope compatibility contract (``legacy_envelope_v1``).

This module publishes the named contract that Spec Kitty consumers use to
normalize known legacy event shapes to canonical 3.x envelopes. The contract
is named, version-suffixed, and frozen; any breaking change requires shipping
``legacy_envelope_v2`` alongside.

Why this contract exists
------------------------

Phase 3 of the producer-refactor program (spec-kitty-saas#274) replaces the
implicit ``_should_validate_strict_envelope()`` carve-out that today silently
accepts malformed known events. The replacement is:

1. classify incoming/stored event as canonical vs named legacy envelope,
2. normalize legacy deterministically via this module,
3. preserve raw legacy input for audit,
4. strict-validate the canonical envelope and payload,
5. materialize OR classify as legacy/business-rule diagnostic.

This module owns steps 1 and 2. Step 4 is ``conformance.validators.validate_event(...,
strict=True)``.

Guarantees
----------

- **Audit preservation**: both result variants carry the original ``raw`` dict.
- **Determinism**: same input always yields the same output. The minted
  ``project_uuid`` is a UUID5 over ``(node_id, build_id)``.
- **No silent aliases (DIR-001)**: every field-name change is captured by the
  ``legacy_shape`` identifier on the success result. Un-normalizable rows
  surface as structured diagnostics, never silent passes.
- **Idempotency**: calling ``normalize()`` on an already-canonical envelope
  returns ``UnnormalizableLegacyDiagnostic(reason="unrecognized_legacy_shape")``.
  Callers are expected to validate canonical envelopes via ``validate_event``
  directly, and call ``normalize`` only on legacy candidates.
"""

from __future__ import annotations

import uuid
from typing import Any, Dict, FrozenSet, List, Union

from pydantic import BaseModel, ConfigDict, Field

LEGACY_ENVELOPE_CONTRACT_NAME: str = "legacy_envelope_v1"

RECOGNIZED_LEGACY_SHAPES: FrozenSet[str] = frozenset({
    "pre_3_0_envelope",
    "feature_keys_envelope",
    "awaiting_review_synonym",
})

# UUID namespace used when minting deterministic project_uuid values for
# pre-3.0 envelopes that lack one. Constant so the mapping is reproducible
# across processes.
_LEGACY_NAMESPACE: uuid.UUID = uuid.uuid5(
    uuid.NAMESPACE_URL, "spec-kitty-events/legacy"
)
```

### T014 — Implement result types

Append to `legacy.py`:

```python
class NormalizedEnvelope(BaseModel):
    """A canonical envelope produced by promoting a named legacy shape."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    canonical: Dict[str, Any] = Field(
        ..., description="Canonical-shape event ready for validate_event(strict=True)."
    )
    raw: Dict[str, Any] = Field(
        ..., description="Original raw input retained verbatim for audit."
    )
    legacy_shape: str = Field(
        ..., min_length=1,
        description="Which named shape detector matched. Member of RECOGNIZED_LEGACY_SHAPES.",
    )


class UnnormalizableLegacyDiagnostic(BaseModel):
    """Structured diagnostic for legacy rows that cannot be promoted."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    reason: str = Field(
        ..., min_length=1,
        description="Machine-readable reason code (e.g. 'pre_3_0_envelope_missing_identity').",
    )
    shape_hints: List[str] = Field(
        default_factory=list,
        description="Free-form hints describing why normalization failed.",
    )
    raw: Dict[str, Any] = Field(
        ..., description="Original raw input retained verbatim for audit.",
    )


NormalizationResult = Union[NormalizedEnvelope, UnnormalizableLegacyDiagnostic]
```

### T015 — Implement `LegacyEnvelopeNormalizer`

Append to `legacy.py`:

```python
class LegacyEnvelopeNormalizer:
    """Promote known legacy event envelopes to canonical 3.x shape.

    Stateless. Single public method ``normalize()``. Detectors run in a
    fixed order; first match wins. Fallthrough emits an
    ``UnnormalizableLegacyDiagnostic`` so un-normalizable rows are visible
    structured diagnostics rather than silent passes.
    """

    def normalize(self, raw_event: Dict[str, Any]) -> NormalizationResult:
        raw = dict(raw_event)  # shallow copy; downstream mutations don't touch input

        # Detector 1: pre-3.0 envelope (missing project_uuid)
        if (
            isinstance(raw.get("event_type"), str)
            and isinstance(raw.get("payload"), dict)
            and "project_uuid" not in raw
        ):
            node_id = raw.get("node_id")
            build_id = raw.get("build_id")
            if not (isinstance(node_id, str) and isinstance(build_id, str)
                    and node_id and build_id):
                hints: List[str] = []
                if not (isinstance(node_id, str) and node_id):
                    hints.append("missing node_id")
                if not (isinstance(build_id, str) and build_id):
                    hints.append("missing build_id")
                return UnnormalizableLegacyDiagnostic(
                    reason="pre_3_0_envelope_missing_identity",
                    shape_hints=hints,
                    raw=raw_event,
                )
            canonical = dict(raw)
            canonical["project_uuid"] = str(uuid.uuid5(
                _LEGACY_NAMESPACE, f"{node_id}/{build_id}"
            ))
            canonical.setdefault("schema_version", "3.0.0")
            if "correlation_id" not in canonical and isinstance(canonical.get("event_id"), str):
                canonical["correlation_id"] = canonical["event_id"]
            return NormalizedEnvelope(
                canonical=canonical, raw=raw_event, legacy_shape="pre_3_0_envelope"
            )

        # Detector 2: feature_keys envelope
        legacy_keys = {"feature_slug", "feature_number"}
        if legacy_keys & raw.keys():
            canonical = dict(raw)
            if "feature_slug" in canonical:
                canonical.setdefault("mission_slug", canonical.pop("feature_slug"))
            if "feature_number" in canonical:
                canonical.setdefault("mission_number", canonical.pop("feature_number"))
            # Recurse into payload if it carries the same retired keys
            payload = canonical.get("payload")
            if isinstance(payload, dict) and (legacy_keys & payload.keys()):
                payload = dict(payload)
                if "feature_slug" in payload:
                    payload.setdefault("mission_slug", payload.pop("feature_slug"))
                if "feature_number" in payload:
                    payload.setdefault("mission_number", payload.pop("feature_number"))
                canonical["payload"] = payload
            return NormalizedEnvelope(
                canonical=canonical, raw=raw_event, legacy_shape="feature_keys_envelope"
            )

        # Detector 3: awaiting_review synonym in payload.to_lane
        payload = raw.get("payload")
        if isinstance(payload, dict) and payload.get("to_lane") == "awaiting-review":
            canonical = dict(raw)
            new_payload = dict(payload)
            new_payload["to_lane"] = "in_review"
            canonical["payload"] = new_payload
            return NormalizedEnvelope(
                canonical=canonical, raw=raw_event, legacy_shape="awaiting_review_synonym"
            )

        # Fallthrough
        return UnnormalizableLegacyDiagnostic(
            reason="unrecognized_legacy_shape",
            shape_hints=sorted(raw.keys()),
            raw=raw_event,
        )
```

Add to module `__all__`:

```python
__all__ = [
    "LEGACY_ENVELOPE_CONTRACT_NAME",
    "RECOGNIZED_LEGACY_SHAPES",
    "NormalizedEnvelope",
    "UnnormalizableLegacyDiagnostic",
    "NormalizationResult",
    "LegacyEnvelopeNormalizer",
]
```

### T017 — Add fixtures

**File**: `src/spec_kitty_events/conformance/fixtures/legacy/pre_3_0_envelope_normalizes.json` (NEW)

The fixture shape is metadata + the raw legacy envelope under `input`, matching the existing `class_taxonomy/envelope_valid_historical_synthesized/` convention but in the `legacy/` directory:

```json
{
  "class": "legacy_envelope_v1",
  "expected": "normalized",
  "legacy_shape": "pre_3_0_envelope",
  "input": {
    "event_id": "01J0000000000000000000F001",
    "event_type": "MissionCreated",
    "aggregate_id": "mission/01J0000000000000000000MS1",
    "payload": {
      "mission_slug": "fixture-mission",
      "mission_number": 1,
      "mission_type": "software-dev",
      "target_branch": "main",
      "wp_count": 3,
      "friendly_name": "Fixture Mission",
      "purpose_tldr": "Pinned canonical baseline.",
      "purpose_context": "Pre-3.0 envelope missing project_uuid."
    },
    "timestamp": "2026-01-01T00:00:00+00:00",
    "build_id": "build-2026-01-01-fixture",
    "node_id": "fixture-node",
    "lamport_clock": 1
  },
  "notes": "Pre-3.0 envelope missing project_uuid. Normalizer mints project_uuid via uuid5(NAMESPACE_URL || 'spec-kitty-events/legacy', f'{node_id}/{build_id}') and sets schema_version=3.0.0 and correlation_id=event_id."
}
```

**File**: `src/spec_kitty_events/conformance/fixtures/legacy/unrecognized_legacy_diagnostic.json` (NEW)

```json
{
  "class": "legacy_envelope_v1",
  "expected": "unnormalizable",
  "expected_reason": "unrecognized_legacy_shape",
  "input": {
    "some_random_field": "value",
    "another_field": 42
  },
  "notes": "Envelope with no recognized legacy markers. Normalizer must surface UnnormalizableLegacyDiagnostic(reason='unrecognized_legacy_shape')."
}
```

Register both in `conformance/fixtures/manifest.json`. The pyargs entrypoint already filters fixtures by `event_type != "LaneMapping"` and skips wrapper kinds; use `event_type: "LegacyEnvelope"` (a new value) so these fixtures are SKIPPED by the standard `validate_event` parametrization. The new test file (T018) loads them directly.

Manifest entries:

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

Note: the pyargs entrypoint already excludes fixtures whose `event_type == "LaneMapping"` and `fixture_type in {"replay_stream", "reducer_output", "timestamp_semantics"}`. WP04 will extend the exclusion to include `fixture_type == "legacy_normalization"` so these fixtures are not routed to `validate_event`.

### T018 — Add `tests/unit/test_legacy_normalizer.py`

**File**: NEW.

```python
"""Tests for spec_kitty_events.legacy.LegacyEnvelopeNormalizer.

Covers FR-006..FR-009, NFR-003 (determinism), and the idempotency guarantee.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from spec_kitty_events.legacy import (
    LEGACY_ENVELOPE_CONTRACT_NAME,
    LegacyEnvelopeNormalizer,
    NormalizedEnvelope,
    RECOGNIZED_LEGACY_SHAPES,
    UnnormalizableLegacyDiagnostic,
)

_FIXTURES = Path(__file__).resolve().parents[2] / "src/spec_kitty_events/conformance/fixtures/legacy"


def _read_fixture(name: str) -> dict:
    return json.loads((_FIXTURES / name).read_text(encoding="utf-8"))


def test_contract_name_is_legacy_envelope_v1() -> None:
    assert LEGACY_ENVELOPE_CONTRACT_NAME == "legacy_envelope_v1"


def test_recognized_shapes_is_frozenset() -> None:
    assert isinstance(RECOGNIZED_LEGACY_SHAPES, frozenset)
    assert RECOGNIZED_LEGACY_SHAPES == frozenset({
        "pre_3_0_envelope", "feature_keys_envelope", "awaiting_review_synonym",
    })


def test_normalize_pre_3_0_envelope_synthesizes_canonical() -> None:
    fixture = _read_fixture("pre_3_0_envelope_normalizes.json")
    raw = fixture["input"]
    result = LegacyEnvelopeNormalizer().normalize(raw)
    assert isinstance(result, NormalizedEnvelope)
    assert result.legacy_shape == "pre_3_0_envelope"
    assert "project_uuid" in result.canonical
    assert result.canonical["schema_version"] == "3.0.0"
    assert result.canonical["correlation_id"] == raw["event_id"]
    assert result.raw == raw


def test_normalize_pre_3_0_uuid_is_deterministic() -> None:
    """NFR-003: same input always yields the same uuid5."""
    fixture = _read_fixture("pre_3_0_envelope_normalizes.json")
    a = LegacyEnvelopeNormalizer().normalize(fixture["input"])
    b = LegacyEnvelopeNormalizer().normalize(fixture["input"])
    assert isinstance(a, NormalizedEnvelope)
    assert isinstance(b, NormalizedEnvelope)
    assert a.canonical["project_uuid"] == b.canonical["project_uuid"]


def test_normalize_pre_3_0_missing_identity_surfaces_diagnostic() -> None:
    raw = {
        "event_type": "MissionCreated",
        "payload": {"mission_slug": "demo"},
        "event_id": "01J0000000000000000000F001",
        # missing node_id and build_id
    }
    result = LegacyEnvelopeNormalizer().normalize(raw)
    assert isinstance(result, UnnormalizableLegacyDiagnostic)
    assert result.reason == "pre_3_0_envelope_missing_identity"
    assert "missing node_id" in result.shape_hints
    assert "missing build_id" in result.shape_hints
    assert result.raw == raw


def test_normalize_feature_keys_envelope_maps_to_mission_keys() -> None:
    raw = {
        "event_type": "MissionClosed",
        "feature_slug": "demo",
        "feature_number": 5,
        "payload": {
            "feature_slug": "demo",
            "feature_number": 5,
            "mission_type": "software-dev",
        },
        "project_uuid": "00000000-0000-0000-0000-000000000001",
        "event_id": "01J0000000000000000000F002",
        "build_id": "b",
        "node_id": "n",
        "lamport_clock": 1,
        "schema_version": "3.0.0",
        "correlation_id": "01J0000000000000000000C002",
        "timestamp": "2026-01-01T00:00:00+00:00",
    }
    result = LegacyEnvelopeNormalizer().normalize(raw)
    assert isinstance(result, NormalizedEnvelope)
    assert result.legacy_shape == "feature_keys_envelope"
    assert "feature_slug" not in result.canonical
    assert "feature_number" not in result.canonical
    assert result.canonical["mission_slug"] == "demo"
    assert result.canonical["mission_number"] == 5
    assert result.canonical["payload"]["mission_slug"] == "demo"
    assert result.canonical["payload"]["mission_number"] == 5
    assert "feature_slug" not in result.canonical["payload"]


def test_normalize_awaiting_review_synonym_maps_to_in_review() -> None:
    raw = {
        "event_type": "WPStatusChanged",
        "payload": {
            "wp_id": "WP01",
            "from_lane": "for_review",
            "to_lane": "awaiting-review",
            "actor": "user",
            "execution_mode": "worktree",
            "mission_slug": "demo",
        },
        "project_uuid": "00000000-0000-0000-0000-000000000001",
        "event_id": "01J0000000000000000000F003",
        "build_id": "b",
        "node_id": "n",
        "lamport_clock": 1,
        "schema_version": "3.0.0",
        "correlation_id": "01J0000000000000000000C003",
        "timestamp": "2026-01-01T00:00:00+00:00",
    }
    result = LegacyEnvelopeNormalizer().normalize(raw)
    assert isinstance(result, NormalizedEnvelope)
    assert result.legacy_shape == "awaiting_review_synonym"
    assert result.canonical["payload"]["to_lane"] == "in_review"
    # Raw input is preserved verbatim
    assert result.raw["payload"]["to_lane"] == "awaiting-review"


def test_normalize_unrecognized_surfaces_diagnostic() -> None:
    fixture = _read_fixture("unrecognized_legacy_diagnostic.json")
    raw = fixture["input"]
    result = LegacyEnvelopeNormalizer().normalize(raw)
    assert isinstance(result, UnnormalizableLegacyDiagnostic)
    assert result.reason == "unrecognized_legacy_shape"
    assert result.raw == raw


def test_normalize_canonical_envelope_is_idempotent_unrecognized() -> None:
    """Idempotency guarantee: a fully-canonical envelope is NOT silently
    passed through; the normalizer reports it as unrecognized so callers
    keep the canonical-vs-legacy boundary explicit."""
    canonical = {
        "event_id": "01J0000000000000000000F004",
        "event_type": "MissionCreated",
        "payload": {"mission_slug": "demo"},
        "project_uuid": "00000000-0000-0000-0000-000000000001",
        "build_id": "b",
        "node_id": "n",
        "lamport_clock": 1,
        "schema_version": "3.0.0",
        "correlation_id": "01J0000000000000000000C004",
        "timestamp": "2026-01-01T00:00:00+00:00",
    }
    result = LegacyEnvelopeNormalizer().normalize(canonical)
    assert isinstance(result, UnnormalizableLegacyDiagnostic)
    assert result.reason == "unrecognized_legacy_shape"


def test_normalizer_does_not_mutate_input() -> None:
    raw = {
        "event_type": "MissionCreated",
        "payload": {"mission_slug": "demo"},
        "event_id": "01J0000000000000000000F005",
        "build_id": "b",
        "node_id": "n",
    }
    raw_copy = dict(raw)
    _ = LegacyEnvelopeNormalizer().normalize(raw)
    assert raw == raw_copy
```

## Branch Strategy

Same as WP01.

## Definition of Done

- [ ] `src/spec_kitty_events/legacy.py` exists with constants, two result models, `NormalizationResult` union, and `LegacyEnvelopeNormalizer`.
- [ ] Two new fixture files exist under `conformance/fixtures/legacy/`.
- [ ] `tests/unit/test_legacy_normalizer.py` exists with 10 test functions; imports directly from `spec_kitty_events.legacy` (not via package root, since WP04 ships the re-exports).
- [ ] `uv run pytest tests/unit/test_legacy_normalizer.py -q` exits 0.
- [ ] No new pip dependencies (NFR-004).
- [ ] `uv run pytest tests/test_fixture_determinism.py -q` exits 0 (fixtures use sorted-keys formatting).
- [ ] WP03 does NOT touch `__init__.py` or `manifest.json` (those are WP04 territory).

## Reviewer guidance

1. Verify the contract name string is literally `"legacy_envelope_v1"`.
2. Verify both result types use `ConfigDict(frozen=True, extra="forbid")`.
3. Verify `LegacyEnvelopeNormalizer.normalize()` does not mutate its input (deep-test in T018's `test_normalizer_does_not_mutate_input`).
4. Verify the detector order matches the contract document: `pre_3_0_envelope`, `feature_keys_envelope`, `awaiting_review_synonym`. First match wins.
5. Verify the `uuid5` namespace is computed once at module load and the minted value is reproducible across processes.
6. Verify the fallthrough does not silently pass canonical envelopes — it MUST surface as `UnnormalizableLegacyDiagnostic` (T018's `test_normalize_canonical_envelope_is_idempotent_unrecognized`).
7. Verify the fixture JSON files use sorted keys (`json.dumps(..., sort_keys=True, indent=2)`) so `test_fixture_determinism.py` stays green.

## Risks

- **Risk**: Manifest concurrent edit collision with WP02. **Mitigation**: WP02 appends to `fixtures` array, WP03 appends to the same array — lane merge handles textually disjoint entries.
- **Risk**: `__init__.py` concurrent edit collision with WP02. **Mitigation**: same — distinct import blocks.
- **Risk**: A future Phase 3 SaaS adapter assumes idempotent passthrough for canonical envelopes. **Mitigation**: contract explicitly documents that canonical envelopes surface as unrecognized; the quickstart shows the correct usage pattern (call `normalize` only on legacy candidates).

## Activity Log

- 2026-05-22T10:49:19Z – claude:opus-4-7:python-pedro:implementer – shell_pid=71755 – Assigned agent via action command
- 2026-05-22T10:51:21Z – claude:opus-4-7:python-pedro:implementer – shell_pid=71755 – WP03 ready
