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

This module owns steps 1 and 2. Step 4 is
``conformance.validators.validate_event(..., strict=True)``.

Recognized legacy shapes (v1)
-----------------------------

- ``pre_3_0_envelope`` — top-level dict has ``event_type`` and ``payload`` but
  no ``project_uuid``. Mints ``project_uuid`` from
  ``uuid.uuid5(NAMESPACE_URL || 'spec-kitty-events/legacy', f'{node_id}/{build_id}')``
  when both fields are present. If either is missing, emits
  ``UnnormalizableLegacyDiagnostic(reason='pre_3_0_envelope_missing_identity')``.
- ``feature_keys_envelope`` — top-level dict carries retired ``feature_slug``
  and/or ``feature_number`` keys. Maps to ``mission_slug`` / ``mission_number``
  and strips the legacy keys at top level and inside ``payload``.
- ``awaiting_review_synonym`` — ``payload.to_lane == 'awaiting-review'`` →
  canonical ``Lane.IN_REVIEW.value`` (the only authoritative source for the
  canonical lane vocabulary is :mod:`spec_kitty_events.status`).

Fallthrough (no recognized markers) returns
``UnnormalizableLegacyDiagnostic(reason='unrecognized_legacy_shape')``.

Guarantees
----------

- **Audit preservation**: both result variants carry the original ``raw`` dict.
- **Determinism**: same input always yields the same output. The minted
  ``project_uuid`` is a UUID5 over ``(node_id, build_id)``.
- **No silent aliases (DIR-001)**: every field-name change is captured by the
  ``legacy_shape`` identifier on the success result. Un-normalizable rows
  surface as structured diagnostics, never silent passes.
- **Idempotency**: calling ``normalize()`` on an already-canonical envelope
  returns ``UnnormalizableLegacyDiagnostic(reason='unrecognized_legacy_shape')``.
  Callers are expected to validate canonical envelopes via ``validate_event``
  directly, and call ``normalize`` only on legacy candidates.
- **Non-mutating**: ``normalize()`` never mutates its input dict.

Shipped with mission ``canonical-producer-contracts-legacy-envelope-01KS7JM3``.
"""

from __future__ import annotations

import uuid
from typing import Any, Dict, FrozenSet, List, Union

from pydantic import BaseModel, ConfigDict, Field

from spec_kitty_events.status import Lane

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


class NormalizedEnvelope(BaseModel):
    """A canonical envelope produced by promoting a named legacy shape."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    canonical: Dict[str, Any] = Field(
        ...,
        description="Canonical-shape event ready for validate_event(strict=True).",
    )
    raw: Dict[str, Any] = Field(
        ...,
        description="Original raw input retained verbatim for audit.",
    )
    legacy_shape: str = Field(
        ...,
        min_length=1,
        description="Which named shape detector matched. Member of RECOGNIZED_LEGACY_SHAPES.",
    )


class UnnormalizableLegacyDiagnostic(BaseModel):
    """Structured diagnostic for legacy rows that cannot be promoted."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    reason: str = Field(
        ...,
        min_length=1,
        description="Machine-readable reason code (e.g. 'pre_3_0_envelope_missing_identity').",
    )
    shape_hints: List[str] = Field(
        default_factory=list,
        description="Free-form hints describing why normalization failed.",
    )
    raw: Dict[str, Any] = Field(
        ...,
        description="Original raw input retained verbatim for audit.",
    )


NormalizationResult = Union[NormalizedEnvelope, UnnormalizableLegacyDiagnostic]


class LegacyEnvelopeNormalizer:
    """Promote known legacy event envelopes to canonical 3.x shape.

    Stateless. Single public method ``normalize()``. Detectors run in a
    fixed order; first match wins. Fallthrough emits an
    ``UnnormalizableLegacyDiagnostic`` so un-normalizable rows are visible
    structured diagnostics rather than silent passes.
    """

    def normalize(self, raw_event: Dict[str, Any]) -> NormalizationResult:
        # Shallow copy so downstream mutations don't touch the caller's dict.
        raw_copy = dict(raw_event)

        # Detector 1: pre-3.0 envelope (missing project_uuid).
        if (
            isinstance(raw_copy.get("event_type"), str)
            and isinstance(raw_copy.get("payload"), dict)
            and "project_uuid" not in raw_copy
        ):
            node_id = raw_copy.get("node_id")
            build_id = raw_copy.get("build_id")
            node_id_ok = isinstance(node_id, str) and bool(node_id)
            build_id_ok = isinstance(build_id, str) and bool(build_id)
            if not (node_id_ok and build_id_ok):
                hints: List[str] = []
                if not node_id_ok:
                    hints.append("missing node_id")
                if not build_id_ok:
                    hints.append("missing build_id")
                return UnnormalizableLegacyDiagnostic(
                    reason="pre_3_0_envelope_missing_identity",
                    shape_hints=hints,
                    raw=raw_event,
                )
            canonical = dict(raw_copy)
            canonical["project_uuid"] = str(
                uuid.uuid5(_LEGACY_NAMESPACE, f"{node_id}/{build_id}")
            )
            canonical.setdefault("schema_version", "3.0.0")
            if (
                "correlation_id" not in canonical
                and isinstance(canonical.get("event_id"), str)
            ):
                canonical["correlation_id"] = canonical["event_id"]
            return NormalizedEnvelope(
                canonical=canonical,
                raw=raw_event,
                legacy_shape="pre_3_0_envelope",
            )

        # Detector 2: feature_keys envelope.
        legacy_keys = {"feature_slug", "feature_number"}
        if legacy_keys & raw_copy.keys():
            canonical = dict(raw_copy)
            if "feature_slug" in canonical:
                canonical.setdefault("mission_slug", canonical.pop("feature_slug"))
            if "feature_number" in canonical:
                canonical.setdefault("mission_number", canonical.pop("feature_number"))
            inner_payload = canonical.get("payload")
            if isinstance(inner_payload, dict) and (legacy_keys & inner_payload.keys()):
                new_payload = dict(inner_payload)
                if "feature_slug" in new_payload:
                    new_payload.setdefault("mission_slug", new_payload.pop("feature_slug"))
                if "feature_number" in new_payload:
                    new_payload.setdefault("mission_number", new_payload.pop("feature_number"))
                canonical["payload"] = new_payload
            return NormalizedEnvelope(
                canonical=canonical,
                raw=raw_event,
                legacy_shape="feature_keys_envelope",
            )

        # Detector 3: awaiting_review synonym in payload.to_lane.
        payload = raw_copy.get("payload")
        if isinstance(payload, dict) and payload.get("to_lane") == "awaiting-review":
            canonical = dict(raw_copy)
            new_payload = dict(payload)
            new_payload["to_lane"] = Lane.IN_REVIEW.value
            canonical["payload"] = new_payload
            return NormalizedEnvelope(
                canonical=canonical,
                raw=raw_event,
                legacy_shape="awaiting_review_synonym",
            )

        # Fallthrough.
        return UnnormalizableLegacyDiagnostic(
            reason="unrecognized_legacy_shape",
            shape_hints=sorted(raw_copy.keys()),
            raw=raw_event,
        )


__all__ = [
    "LEGACY_ENVELOPE_CONTRACT_NAME",
    "RECOGNIZED_LEGACY_SHAPES",
    "NormalizedEnvelope",
    "UnnormalizableLegacyDiagnostic",
    "NormalizationResult",
    "LegacyEnvelopeNormalizer",
]
