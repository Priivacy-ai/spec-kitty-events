# Quickstart: TeamSpace Event Contract Foundation

**Mission**: `teamspace-event-contract-foundation-01KQHDE4`
**Audience**: developers landing this mission's work packages, and downstream tranche authors who will rely on the contract.

This is a developer onboarding doc, not a user guide. The user-facing compatibility doc lives in `COMPATIBILITY.md` (updated as part of FR-009).

---

## What this mission ships

- `src/spec_kitty_events/forbidden_keys.py` — recursive forbidden-key validator + `FORBIDDEN_LEGACY_KEYS` constant
- Updated `src/spec_kitty_events/status.py` — `Lane` enum widened to include `in_review` as canonical
- Updated `src/spec_kitty_events/lifecycle.py` — `MissionCreatedPayload`, `MissionClosedPayload` reconciled
- New conformance fixture classes under `src/spec_kitty_events/conformance/fixtures/` — eight classes, registered in `manifest.json`
- Regenerated JSON Schemas under `src/spec_kitty_events/schemas/`
- Updated `COMPATIBILITY.md` — local-CLI compatibility vs TeamSpace ingress validity section
- Updated `CHANGELOG.md` — "Breaking Changes" section for the major bump

---

## Validating an envelope (the typical downstream consumer call)

```python
from spec_kitty_events import validate_envelope, ValidationError

result = validate_envelope(candidate_dict)
if not result.ok:
    error: ValidationError = result.error
    # error.code is a stable enum: FORBIDDEN_KEY, UNKNOWN_LANE, PAYLOAD_SCHEMA_FAIL,
    # ENVELOPE_SHAPE_INVALID, RAW_HISTORICAL_ROW
    log.error("envelope rejected", code=error.code, path=error.path, details=error.details)
```

The exact public function name is finalized in the work package; this is the shape downstream consumers should expect.

---

## Adding a fixture

1. Decide the class (see [contracts/conformance-fixture-classes.md](./contracts/conformance-fixture-classes.md)).
2. Author the JSON file in the class's directory under `src/spec_kitty_events/conformance/fixtures/`.
3. Use deterministic values (per [contracts/conformance-fixture-classes.md](./contracts/conformance-fixture-classes.md) §Determinism rules).
4. Register the file in `manifest.json` with `class`, `expected`, and (when `invalid`) `expected_error_code`.
5. Run the conformance suite: `pytest tests/test_conformance.py` (path may vary; the work package commits the runner).

---

## Reading a structured error

`ValidationError(code, message, path, details)`:

- `code` — switch on this in code; it is a stable enum.
- `message` — log this; it is one line, human-readable.
- `path` — JSON-pointer-like list. `[]` means "envelope root". `["payload", "tags", 2, "feature_slug"]` means "the value of key `feature_slug` inside element 2 of the array under `tags` inside the payload".
- `details` — class-specific structured detail; see [contracts/validation-error-shape.md](./contracts/validation-error-shape.md).

---

## How downstream tranches integrate

| Tranche | What it imports / cites |
|---|---|
| `spec-kitty` Tranche A (audit) | The lane vocabulary contract; the validation error shape. |
| `spec-kitty` Tranche B (canonicalizer) | The payload reconciliation contract (it is the transformation layer); the canonical lane vocabulary. |
| `spec-kitty` Tranche D (TeamSpace dry-run) | All of the above; emits envelopes that are validated against this package's contract. |
| `spec-kitty-saas` Tranche A (ingress) | The forbidden-key validator; the validation error shape; the canonical lane vocabulary. |
| `spec-kitty-saas` Tranche B (reconciliation) | The conformance fixture classes (it builds reconciliation reports against the same shapes). |
| `spec-kitty-runtime` Tranche A | The canonical lane vocabulary; the validation error shape (for log emission). |
| `spec-kitty-tracker` Tranche A | The canonical lane vocabulary (tracker UI surfaces lanes). |

Each tranche's plan must reference the exact contract files it depends on.

---

## Codex review (mandatory per C-005)

Before mission close, Codex reviews:

1. The reconciliation log appended to [contracts/payload-reconciliation.md](./contracts/payload-reconciliation.md).
2. The bump justification in `COMPATIBILITY.md` and `CHANGELOG.md`.
3. The conformance fixture coverage (every class populated; manifest CI green).
4. The recursive forbidden-key tests, especially the depth ≥ 10 case and the "must accept when forbidden key is a value" case.
5. The `local-CLI compatibility vs TeamSpace ingress validity` doc section.

The Codex review record is attached to the mission before close.

---

## Quick sanity checks before declaring "ready for review"

- [ ] `pytest` is green
- [ ] `mypy --strict` is green for changed modules and the new `forbidden_keys.py`
- [ ] `*.schema.json` regeneration is byte-identical to committed files (schema-drift CI green)
- [ ] Conformance manifest reports at least one fixture per class
- [ ] `tests/test_lane_vocabulary.py` asserts `Lane.IN_REVIEW` is canonical
- [ ] `CHANGELOG.md` has a "Breaking Changes" section for this bump
- [ ] `COMPATIBILITY.md` has the local-vs-ingress section
- [ ] The reconciliation log in [contracts/payload-reconciliation.md](./contracts/payload-reconciliation.md) is filled in
