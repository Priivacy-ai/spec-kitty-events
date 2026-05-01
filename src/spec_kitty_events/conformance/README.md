# Conformance Fixtures

This directory contains the canonical conformance fixture suite for the
`spec_kitty_events` package. Fixtures are JSON files describing inputs that
the validator must accept or reject; the conformance runner asserts each
fixture's outcome matches its declared expectation.

## Eight-class taxonomy

The conformance suite is organized into **eight named classes**, defined in
[contracts/conformance-fixture-classes.md](../../../../kitty-specs/teamspace-event-contract-foundation-01KQHDE4/contracts/conformance-fixture-classes.md).
Every class must have at least one fixture; the conformance class assertion
test fails CI if any class has zero fixtures.

All eight class directories live under `class_taxonomy/` so the new
taxonomy can coexist with the legacy fixture tree (which the existing
`conformance/loader.py` filters by event-type-category prefix).

| Class | Expected | Path | Description |
|---|---|---|---|
| `envelope_valid_canonical` | accept | `class_taxonomy/envelope_valid_canonical/` | Canonical 3.0.x envelopes covering every supported event type and every canonical lane (incl. `in_review`). |
| `envelope_valid_historical_synthesized` | accept | `class_taxonomy/envelope_valid_historical_synthesized/` | Envelopes synthesized by the CLI canonicalizer's planned dry-run output (cross-repo handshake for SC-001). |
| `envelope_invalid_unknown_lane` | reject (`UNKNOWN_LANE`) | `class_taxonomy/envelope_invalid_unknown_lane/` | Envelope claiming a lane outside the canonical vocabulary. |
| `envelope_invalid_forbidden_key` | reject (`FORBIDDEN_KEY`) | `class_taxonomy/envelope_invalid_forbidden_key/` | Forbidden key at top level, nested object, depth >= 10, and inside an array element. |
| `envelope_invalid_payload_schema` | reject (`PAYLOAD_SCHEMA_FAIL`) | `class_taxonomy/envelope_invalid_payload_schema/` | Payload fails its typed schema (extra field, missing required, wrong type). |
| `envelope_invalid_shape` | reject (`ENVELOPE_SHAPE_INVALID`) | `class_taxonomy/envelope_invalid_shape/` | Missing required envelope fields, wrong wrapper. |
| `historical_row_raw` | reject (`RAW_HISTORICAL_ROW`) | `class_taxonomy/historical_row_raw/` | Real shapes from the epic #920 historical-row survey: pre-3.0 envelopes, rows containing `feature_slug`/`feature_number`/`mission_key`/`legacy_aggregate_id`, and rows using the legacy `awaiting-review` synonym. |
| `lane_mapping_legacy` | mixed | `class_taxonomy/lane_mapping_legacy/{valid,invalid}/` | Resolutions of legacy lane strings to canonical lanes. |

Note on `historical_row_raw`: today's validator may emit
`ENVELOPE_SHAPE_INVALID`, `FORBIDDEN_KEY`, or `UNKNOWN_LANE` instead of the
ideal `RAW_HISTORICAL_ROW` for these inputs. Each historical_row fixture
documents this caveat in its `notes`. The conformance class assertion test
accepts any rejection for these fixtures while pinning the *ideal* code in
`expected_error_code`. A downstream WP can refine the validator to detect
the raw-historical-row class as a distinct rejection.

## Fixture file format

Each fixture is a JSON file with the following minimum schema:

```json
{
  "class": "<class-name from table above>",
  "expected": "valid" | "invalid",
  "expected_error_code": "<closed code from validation_errors.ValidationErrorCode>",
  "input": { ... },
  "notes": "human-readable context"
}
```

`expected_error_code` is REQUIRED when `expected = "invalid"`. This pins the
exact rejection class, preventing a fixture from "passing" because validation
rejected it for the wrong reason.

## Determinism convention (R-06)

Fixtures use repository-pinned values:

- **Timestamps**: `2026-01-01T00:00:00+00:00` only.
- **ULIDs**: 26-character Crockford-base32 IDs starting with the pinned
  prefix `01J0000000000000000000` (e.g., `01J0000000000000000000FIX1`,
  `01J0000000000000000000FIX2`, ..., or `01J0000000000000000000MIS1` for
  mission ids).
- **Hashes / digests**: precomputed and committed; never recomputed at test
  time.

The audit test `tests/test_fixture_determinism.py` walks every JSON fixture
under this directory; for each timestamp-shaped string it asserts equality
with the pinned anchor; for each ULID-shaped string it asserts the pinned
prefix. Drift fails CI with a clear pointer to the offending fixture.

## Adding a fixture (developer workflow)

1. Identify the class. (See the table above.)
2. Author a JSON file in the class's directory using the schema above.
3. Use deterministic values (R-06).
4. Register the file in `manifest.json` under the `classes.entries` array.
   Provide `id`, `class`, `path`, `expected`, and (when invalid)
   `expected_error_code`.
5. Run the conformance suite locally:
   `python -m pytest tests/test_conformance_classes.py tests/test_fixture_determinism.py -q`.
6. Commit; the CI gate keeps the suite green.

## Manifest layout

`manifest.json` has two top-level sections:

- `fixtures` — the legacy per-event-type registry (read by
  `conformance/loader.py::load_fixtures`).
- `classes.entries` — the eight-class taxonomy registry (read by
  `tests/test_conformance_classes.py`).

The two sections are independent. Adding a fixture to the new class taxonomy
does not require editing the legacy `fixtures` array.

## CI gate

The conformance suite runs as a mandatory CI step (NFR-003). Failure of any
fixture, or absence of any class, blocks merge.
