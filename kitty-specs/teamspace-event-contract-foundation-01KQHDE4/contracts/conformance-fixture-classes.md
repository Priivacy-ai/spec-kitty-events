# Contract: Conformance Fixture Classes

**Mission**: `teamspace-event-contract-foundation-01KQHDE4`
**Source spec FRs**: FR-007, FR-008, C-006 · **Source SCs**: SC-001, SC-002, SC-005 · **Research**: [research.md R-05, R-06](../research.md#r-05--historical-shape-classes-for-conformance-fixtures)

## Rule

Conformance fixtures live under `src/spec_kitty_events/conformance/fixtures/` and are organized into eight **classes**, each labeled in `manifest.json`. Every class must have at least one fixture; the manifest fails CI on a zero-population class.

## The eight classes

| Class | Expected | Path | Description |
|---|---|---|---|
| `envelope_valid_canonical` | accept | `events/valid/` | Canonical 3.0.x envelopes covering every supported event type and every canonical lane (incl. `in_review`) |
| `envelope_valid_historical_synthesized` | accept | `events/valid/` | Envelopes synthesized by the CLI canonicalizer's planned dry-run output (cross-repo handshake for SC-001) |
| `envelope_invalid_unknown_lane` | reject (`UNKNOWN_LANE`) | `events/invalid/` | Envelope claiming a lane outside the canonical vocabulary |
| `envelope_invalid_forbidden_key` | reject (`FORBIDDEN_KEY`) | `events/invalid/` | Forbidden key at top level, nested object, depth ≥ 10, and inside an array element |
| `envelope_invalid_payload_schema` | reject (`PAYLOAD_SCHEMA_FAIL`) | `events/invalid/` | Payload fails its typed schema (extra field, missing required, wrong type) |
| `envelope_invalid_shape` | reject (`ENVELOPE_SHAPE_INVALID`) | `events/invalid/` | Missing required envelope fields, wrong wrapper |
| `historical_row_raw` | reject (`RAW_HISTORICAL_ROW`) | `historical_rows/` | Lines from real historical `status.events.jsonl` files; covers pre-3.0 shapes, `in_review`-using rows, rows containing `feature_slug`/`feature_number`/`mission_key` |
| `lane_mapping_legacy` | mixed | `lane_mapping/{valid,invalid}/` | Resolutions of legacy lane strings to canonical lanes (e.g., `awaiting-review` → `in_review`); split into valid and invalid sub-cases |

## Fixture file format

Each fixture is a JSON file. The minimum schema:

```json
{
  "class": "<class-name from table above>",
  "expected": "valid" | "invalid",
  "expected_error_code": "<code from validation-error-shape.md>",   // when expected = "invalid"
  "input": { ... },
  "notes": "human-readable context"
}
```

`expected_error_code` is REQUIRED when `expected = "invalid"`. This pins the exact rejection class, preventing a fixture from "passing" because validation rejected it for the wrong reason.

## Manifest

`src/spec_kitty_events/conformance/fixtures/manifest.json` is the authoritative index. The manifest references every fixture and surfaces:

- Per-class fixture count (with a minimum of 1, recommended ≥ 3 for first ship).
- Per-class expected-outcome consistency (no `valid` fixture in `envelope_invalid_*` directories).
- A summary of lane coverage (every canonical lane appears at least once in `envelope_valid_canonical`).

The conformance runner reads the manifest and asserts each fixture's actual outcome equals its `expected` (and, when invalid, that the error code matches `expected_error_code`).

## Determinism rules (per R-06)

Fixtures use repository-pinned values:

- Timestamps: `2026-01-01T00:00:00+00:00` unless the fixture's class specifically tests timestamp variation.
- ULIDs: `01J0000000000000000000FIX1`, `01J0000000000000000000FIX2`, … (or another committed pinned scheme).
- Hashes/digests: precomputed and committed; never recomputed at test time.

A small audit test (`tests/test_fixture_determinism.py` or equivalent) scans every fixture for forbidden patterns (recent-looking timestamps, non-pinned ULID prefixes) and fails CI on drift.

## CI gate

The conformance suite runs as a mandatory CI step (NFR-003). Failures of any kind block merge.

## Adding fixtures (developer workflow)

1. Identify the class.
2. Author a JSON file in the class's directory using the schema above.
3. Register it in `manifest.json`.
4. Run the conformance suite locally; expect the new fixture's expected outcome to be honored.
5. Commit; the CI gate keeps the suite green.

## Forbidden patterns

- Wall-clock timestamps in fixture files.
- Random or session-scoped ULIDs in fixture files.
- A fixture with `expected = "invalid"` but no `expected_error_code` field.
- A fixture in `envelope_invalid_*` that the validator accepts (CI fails by definition).

## Versioning

Adding a new class is a contract change subject to the version-bump rule. Adding fixtures within an existing class is not a contract change (no version bump required) provided the manifest's coverage rules continue to hold.
