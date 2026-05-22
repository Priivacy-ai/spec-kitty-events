# Contract: `legacy_envelope_v1`

**Status**: Draft (lands with this mission)
**Owner**: `spec-kitty-events` package
**Consumers**: Phase 3 SaaS legacy adapter (`spec-kitty-saas#274`); future legacy-aware tooling.

## Purpose

Replace the implicit `_should_validate_strict_envelope()` carve-out in SaaS with an explicit, named normalization step that promotes known legacy event shapes to the canonical envelope, and surfaces un-normalizable rows as structured diagnostics rather than silent passes.

## Public surface

```python
from spec_kitty_events.legacy import (
    LegacyEnvelopeNormalizer,
    NormalizedEnvelope,
    UnnormalizableLegacyDiagnostic,
    NormalizationResult,
    LEGACY_ENVELOPE_CONTRACT_NAME,        # "legacy_envelope_v1"
    RECOGNIZED_LEGACY_SHAPES,             # frozenset of named shapes
)
```

## Recognized legacy shapes

| Shape id | Detection rule | Normalization |
|----------|---------------|---------------|
| `pre_3_0_envelope` | Top-level dict has `event_type` and `payload` but no `project_uuid`. | Mint `project_uuid = uuid.uuid5(NAMESPACE_URL, f"spec-kitty-events/legacy/{node_id}/{build_id}")` when both `node_id` and `build_id` are present. If either is missing, emit `UnnormalizableLegacyDiagnostic(reason="pre_3_0_envelope_missing_identity")`. Add `schema_version="3.0.0"` and `correlation_id=event_id` if not present. |
| `feature_keys_envelope` | Top-level dict has retired `feature_slug` and/or `feature_number`. | Map `feature_slug → mission_slug`, `feature_number → mission_number`. Strip the legacy keys. Recurse into `payload` dict if it has the same legacy keys. |
| `awaiting_review_synonym` | `payload.to_lane == "awaiting-review"`. | Replace with canonical `payload.to_lane = "in_review"`. |

Detection runs in the order above; first match wins. Multiple legacy markers (e.g. a pre-3.0 envelope that also uses `feature_slug`) compose by re-entering the normalizer with the intermediate result, but the result's `legacy_shape` field reports the **first** match (the outermost legacy marker).

## Fallthrough

If none of the recognized shapes match, `normalize()` returns `UnnormalizableLegacyDiagnostic(reason="unrecognized_legacy_shape", shape_hints=<observed top-level keys>, raw=...)`. The diagnostic is the explicit, audited signal to the SaaS adapter that this row must be classified as a legacy/business-rule diagnostic rather than ingested as canonical.

## Guarantees

1. **Audit preservation**: Both `NormalizedEnvelope` and `UnnormalizableLegacyDiagnostic` carry the original `raw` dict verbatim.
2. **Determinism**: Same input always yields the same output. No process state, no clock reads, no random UUIDs (the `uuid5` is deterministic over `(node_id, build_id)`).
3. **No silent aliases (DIR-001)**: Every change to a canonical field name is captured by the `legacy_shape` identifier. Consumers can audit "what was changed and why" by reading the shape id and re-applying the documented mapping.
4. **Idempotency**: Calling `normalize()` on an already-canonical envelope returns `UnnormalizableLegacyDiagnostic(reason="unrecognized_legacy_shape", ...)` — the normalizer does not pass canonical envelopes through. This is the desired property: callers are expected to call `validate_event()` directly on canonical envelopes and `normalize()` only on legacy candidates. (Alternative API shape that returns a "canonical_passthrough" variant was considered and rejected as confusing; the boundary should be explicit.)
5. **Forward compatibility**: New legacy shapes added in a future release ship as `legacy_envelope_v2` with both contracts coexisting for a deprecation window. Consumers pin to the contract name they accept.

## Out of scope (deferred to v2 or later)

- Normalizing other legacy synonyms (e.g. `for-review` ↔ `for_review`).
- Bridging `schema_version` other than the pre-3.0 → 3.0 step.
- Normalizing batch envelopes (this contract handles single-event payloads only).
- Repairing `payload`-internal field-name drift beyond the documented `awaiting-review → in_review` case.

## Fixtures

| Fixture path | Class | Purpose |
|--------------|-------|---------|
| `conformance/fixtures/legacy/pre_3_0_envelope_normalizes.json` | Success | Pre-3.0 envelope → canonical 3.0 envelope. |
| `conformance/fixtures/legacy/unrecognized_legacy_diagnostic.json` | Failure | Envelope with no recognized legacy marker → `UnnormalizableLegacyDiagnostic`. |

Both fixtures are registered in `conformance/fixtures/manifest.json`.

## Versioning

- Contract name: `legacy_envelope_v1`.
- Lands with `spec-kitty-events` `[Unreleased]` (next minor; orchestrator owns the version bump in Phase 5).
- Any breaking change to detection or normalization rules requires bumping to `legacy_envelope_v2` and shipping both side-by-side for a deprecation window.
