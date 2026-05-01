---
work_package_id: WP05
title: Conformance Fixture Suite
dependencies:
- WP01
- WP02
- WP03
- WP04
requirement_refs:
- C-001
- C-006
- FR-006
- FR-007
- FR-008
- NFR-001
- NFR-003
planning_base_branch: main
merge_target_branch: main
branch_strategy: Worktree per lane; planning base main; merge target main
subtasks:
- T017
- T018
- T019
- T020
- T021
- T022
- T023
- T024
agent: claude
history:
- event: created
  at: '2026-05-01T09:44:26Z'
  by: /spec-kitty.tasks
agent_profile: implementer-ivan
authoritative_surface: src/spec_kitty_events/conformance/fixtures/
execution_mode: code_change
owned_files:
- src/spec_kitty_events/conformance/fixtures/**
- src/spec_kitty_events/conformance/README.md
- tests/test_fixture_determinism.py
- tests/test_conformance_classes.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load implementer-ivan
```

---

## Objective

Reorganize `src/spec_kitty_events/conformance/fixtures/` into the eight named class directories from R-05; populate every class with at least one fixture; update the manifest with class registrations and `expected_error_code` values; and add the deterministic-fixture audit + the conformance-class assertion test.

This WP proves the contract end-to-end. If a fixture's expected outcome doesn't match the actual outcome, CI fails.

---

## Context

- Spec: FR-006, FR-007, FR-008, C-006, SC-001, SC-002, SC-005.
- Contract: [contracts/conformance-fixture-classes.md](../contracts/conformance-fixture-classes.md).
- Research: [research.md R-05, R-06](../research.md#r-05--historical-shape-classes-for-conformance-fixtures).
- Depends on: WP01 (lane vocabulary), WP02 (`ValidationError`), WP03 (forbidden-key validator), WP04 (reconciled payloads).

---

## Eight Fixture Classes (recap)

| Class | Expected | Path | Notes |
|---|---|---|---|
| `envelope_valid_canonical` | accept | `events/valid/canonical/` | One per event type, including `in_review`-using `WPStatusChanged` |
| `envelope_valid_historical_synthesized` | accept | `events/valid/historical_synthesized/` | CLI canonicalizer dry-run shapes (cross-repo handshake) |
| `envelope_invalid_unknown_lane` | reject (`UNKNOWN_LANE`) | `events/invalid/unknown_lane/` | Lane outside canonical vocabulary |
| `envelope_invalid_forbidden_key` | reject (`FORBIDDEN_KEY`) | `events/invalid/forbidden_key/` | Top, nested, depth ≥ 10, array element |
| `envelope_invalid_payload_schema` | reject (`PAYLOAD_SCHEMA_FAIL`) | `events/invalid/payload_schema/` | Extra field, missing required, wrong type |
| `envelope_invalid_shape` | reject (`ENVELOPE_SHAPE_INVALID`) | `events/invalid/envelope_shape/` | Missing required envelope fields |
| `historical_row_raw` | reject (`RAW_HISTORICAL_ROW`) | `historical_rows/` | Real shapes from epic survey |
| `lane_mapping_legacy` | mixed | `lane_mapping/{valid,invalid}/` | Legacy lane string resolutions |

---

## Subtasks

### T017 — Reorganize fixtures into 8 named class directories

**Purpose**: Establish the directory layout the rest of the WP populates.

**Steps**:
1. Read the current state of `src/spec_kitty_events/conformance/fixtures/` to understand what exists.
2. Create the eight class directories (use git-tracked `.gitkeep` files where empty):
   ```
   events/valid/canonical/
   events/valid/historical_synthesized/
   events/invalid/unknown_lane/
   events/invalid/forbidden_key/
   events/invalid/payload_schema/
   events/invalid/envelope_shape/
   historical_rows/
   lane_mapping/valid/
   lane_mapping/invalid/   # already exists
   ```
3. Move existing fixture files into the appropriate class directory based on their content. Update `manifest.json` paths accordingly (T022 will redo the manifest in full).
4. Do **not** delete fixtures yet; reorganize, then T022 does the manifest pass.

**Files**:
- Various (moves under `src/spec_kitty_events/conformance/fixtures/`)

**Validation**:
- [ ] Every class directory exists.
- [ ] No fixture file is orphaned (every file in `fixtures/` is in a class subdir).

---

### T018 — Author `envelope_valid_canonical` fixtures

**Purpose**: Prove that canonical 3.0.x envelopes for every event type validate.

**Steps**:
1. For each canonical event type supported by the package (`MissionCreated`, `WPStatusChanged`, `MissionClosed`, plus any other canonical types in the existing catalog), author a JSON fixture file in `events/valid/canonical/`.
2. Use the deterministic-value convention from R-06: pinned timestamps, pinned ULIDs.
3. Specifically include a `WPStatusChanged` fixture using `to_lane = "in_review"` to handshake with WP01.
4. Each fixture file follows this minimum schema:

   ```json
   {
     "class": "envelope_valid_canonical",
     "expected": "valid",
     "input": {
       "event_type": "WPStatusChanged",
       "event_version": "3.x.y",
       "event_id": "01J0000000000000000000FIX1",
       "occurred_at": "2026-01-01T00:00:00+00:00",
       "mission_id": "01J0000000000000000000MIS1",
       "payload": { ... }
     },
     "notes": "Canonical WPStatusChanged with to_lane=in_review"
   }
   ```

5. Aim for at least one fixture per canonical event type, and at least three fixtures total in this class.

**Files**:
- `events/valid/canonical/wp_status_changed_in_review.json` (new)
- `events/valid/canonical/mission_created_baseline.json` (new)
- `events/valid/canonical/mission_closed_baseline.json` (new)
- (one per other canonical event type)

**Validation**:
- [ ] Every fixture parses as valid JSON.
- [ ] Every fixture's `input` validates as a canonical envelope.
- [ ] Pinned ULIDs and timestamps are used.

---

### T019 — Author `envelope_valid_historical_synthesized` fixtures

**Purpose**: Cross-repo handshake. These fixtures simulate the CLI canonicalizer's planned dry-run synthesis output. They MUST validate, because the CLI canonicalizer will produce them.

**Steps**:
1. Read the spec's note on the CLI canonicalizer's planned output: it normalizes legacy fields (drops `feature_slug`, maps legacy lane synonyms to canonical lanes including `in_review`) and emits canonical envelopes.
2. Author at least three fixtures here, each one labeled with the originating historical shape it's the canonicalized form of:

   ```json
   {
     "class": "envelope_valid_historical_synthesized",
     "expected": "valid",
     "input": { ... canonical envelope ... },
     "notes": "Synthesized from a historical row that originally contained 'feature_slug' (now normalized away)"
   }
   ```

3. These fixtures are mostly identical in shape to `envelope_valid_canonical` but document the historical origin in `notes`. The point is the cross-repo contract: when `spec-kitty` Tranche B produces these, this package validates them.

**Files**:
- `events/valid/historical_synthesized/from_pre30_envelope.json` (new)
- `events/valid/historical_synthesized/from_in_review_legacy_synonym.json` (new)
- `events/valid/historical_synthesized/from_envelope_with_legacy_keys.json` (new)

**Validation**:
- [ ] Every fixture validates.
- [ ] Notes cite the historical origin shape.

---

### T020 — Author `envelope_invalid_*` fixtures with `expected_error_code`

**Purpose**: Cover every rejection class.

**Steps**:
1. **`envelope_invalid_unknown_lane/`**: at least one fixture per the rejection class. Use a lane string outside the canonical vocabulary (e.g., `"to_lane": "blocked"`). `expected_error_code: "UNKNOWN_LANE"`.

2. **`envelope_invalid_forbidden_key/`**: four fixtures covering depths and array placement:
   - `forbidden_key_top_level.json` — `{"feature_slug": ..., ...}` directly in envelope
   - `forbidden_key_nested.json` — inside `payload.metadata`
   - `forbidden_key_depth_10.json` — at depth ≥ 10
   - `forbidden_key_in_array.json` — inside an element of an array
   - All with `expected_error_code: "FORBIDDEN_KEY"`.

3. **`envelope_invalid_payload_schema/`**: at least three fixtures:
   - Extra field on a payload that has `extra='forbid'` (post-WP04).
   - Missing required field.
   - Wrong type for a required field.
   - All with `expected_error_code: "PAYLOAD_SCHEMA_FAIL"`.

4. **`envelope_invalid_shape/`**: at least two fixtures:
   - Missing top-level field (e.g., no `event_type`).
   - Wrong wrapper (an array instead of an object).
   - All with `expected_error_code: "ENVELOPE_SHAPE_INVALID"`.

**Files**:
- `events/invalid/unknown_lane/*.json` (new, ~1–2 fixtures)
- `events/invalid/forbidden_key/*.json` (new, 4 fixtures)
- `events/invalid/payload_schema/*.json` (new, 3 fixtures)
- `events/invalid/envelope_shape/*.json` (new, 2 fixtures)

**Validation**:
- [ ] Each fixture has `expected_error_code` matching its class's expected code.
- [ ] T024's runner confirms the expected outcome.

---

### T021 — Author `historical_row_raw` fixtures

**Purpose**: Prove that raw historical `status.events.jsonl` rows are 100% rejected (SC-002).

**Steps**:
1. Pull representative shapes from the epic #920 historical-row survey. Specifically include:
   - A pre-3.0 envelope shape (no canonical wrapper).
   - A row containing `feature_slug`, `feature_number`, or `mission_key`.
   - A row containing `legacy_aggregate_id` (referenced in the survey).
   - A row using a historical `in_review` rendering (legacy synonym, not canonical).
   - A row that is just a raw status entry (no `event_type`/`event_version`).

2. Use deterministic values: replace any real ULIDs and timestamps with the pinned variants from R-06.

3. Each fixture: `class: "historical_row_raw"`, `expected: "invalid"`, `expected_error_code: "RAW_HISTORICAL_ROW"`.

4. If the validator does not yet detect "this is a raw historical row" as a distinct rejection class (vs. just emitting `ENVELOPE_SHAPE_INVALID`), document this in fixture notes and expect the result the validator actually returns. The contract in `validation-error-shape.md` reserves `RAW_HISTORICAL_ROW`; if the implementer needs a small detection helper, add it to `validation_errors.py` (note: that file is in WP02's `owned_files`, not this WP's — coordinate by adding `validation_errors.py` to this WP's `owned_files` ONLY if WP02 hasn't merged yet, otherwise propose the helper as a follow-up WP and use `ENVELOPE_SHAPE_INVALID` in this WP's fixtures).

**Files**:
- `historical_rows/pre30_envelope_shape.json` (new)
- `historical_rows/feature_slug_top_level.json` (new)
- `historical_rows/legacy_aggregate_id.json` (new)
- `historical_rows/in_review_legacy_synonym.json` (new)
- `historical_rows/raw_status_entry.json` (new)

**Validation**:
- [ ] Every fixture is rejected by the validator.
- [ ] Pinned values used throughout.

---

### T022 — Update `manifest.json` + add fixtures README

**Purpose**: The manifest is the authoritative index; the README explains conventions.

**Steps**:
1. Rewrite `src/spec_kitty_events/conformance/fixtures/manifest.json` so every fixture file is registered with `class`, `expected`, and (when invalid) `expected_error_code`. The manifest is the runner's input.
2. Author `src/spec_kitty_events/conformance/README.md` with:
   - The eight-class taxonomy (link to `contracts/conformance-fixture-classes.md`).
   - The deterministic-value convention (R-06).
   - How to add a fixture (developer workflow from quickstart.md).
3. Add (or update) a small manifest-coverage helper that asserts each of the eight classes has at least one fixture. This helper is exercised by T024.

**Files**:
- `src/spec_kitty_events/conformance/fixtures/manifest.json` (rewritten)
- `src/spec_kitty_events/conformance/README.md` (new)

**Validation**:
- [ ] Manifest is valid JSON.
- [ ] Every fixture file in the directory tree is referenced by the manifest.
- [ ] No manifest entry references a missing file.

---

### T023 — Author `tests/test_fixture_determinism.py`

**Purpose**: Audit fixtures for forbidden patterns (recent timestamps, non-pinned ULIDs).

**Steps**:
1. Create `tests/test_fixture_determinism.py`.
2. Walk every JSON fixture under `src/spec_kitty_events/conformance/fixtures/`:
   - Parse it.
   - Walk all string values (recursively).
   - For each timestamp-shaped string, assert it equals the pinned anchor (`2026-01-01T00:00:00+00:00`) or matches an explicit allowlist for fixtures whose class specifically tests timestamp variation.
   - For each ULID-shaped string (26-char Crockford-base32-ish), assert it begins with the pinned prefix (e.g., `01J0000000000000000000FIX` or as the convention in R-06 dictates).
3. Fail with a clear message naming the offending fixture path and the offending value.

**Files**:
- `tests/test_fixture_determinism.py` (new, ~80–120 lines)

**Validation**:
- [ ] Test passes when fixtures use pinned values.
- [ ] Manually verify it fails when a fixture is mutated to use a wall-clock timestamp.

---

### T024 — Author `tests/test_conformance_classes.py`

**Purpose**: Run the validator over every fixture and assert each fixture's expected outcome (and `expected_error_code` for invalid fixtures).

**Steps**:
1. Create `tests/test_conformance_classes.py`.
2. Read `manifest.json` and parametrize a pytest test over every fixture entry:

   ```python
   @pytest.mark.parametrize("fixture_entry", load_manifest_entries(), ids=...)
   def test_fixture_outcome(fixture_entry):
       fixture = load_fixture(fixture_entry["path"])
       result = validate_envelope(fixture["input"])  # or the package's public validator
       if fixture["expected"] == "valid":
           assert result.ok
       else:
           assert not result.ok
           assert result.error.code.value == fixture["expected_error_code"]
   ```

3. Add coverage assertions:
   - Every of the eight classes has ≥ 1 fixture (T022's helper or inline).
   - Every canonical event type appears at least once in `envelope_valid_canonical`.

**Files**:
- `tests/test_conformance_classes.py` (new, ~150 lines)

**Validation**:
- [ ] All fixtures are validated; outcomes match expectations.
- [ ] Coverage assertions hold.

---

## Branch Strategy

- Planning/base branch: `main` · Merge target: `main` · Worktree allocated by `finalize-tasks`.

---

## Definition of Done

- [ ] Eight class directories exist and are populated.
- [ ] `manifest.json` registers every fixture with class + expected + (invalid) expected_error_code.
- [ ] `README.md` for fixtures exists.
- [ ] `tests/test_fixture_determinism.py` passes.
- [ ] `tests/test_conformance_classes.py` passes (every fixture's expected outcome matches).
- [ ] Existing pytest suite still green.
- [ ] No file outside `owned_files` modified.

---

## Risks

- **R-1**: Authoring 8 classes' worth of fixtures inflates the WP. Mitigation: minimum-viable coverage is one fixture per class (we aim for three); the WP is internally parallelizable (different class directories).
- **R-2**: `historical_row_raw` fixtures need real historical content but we have a deterministic-value rule. Mitigation: anonymize historical content by replacing real IDs and timestamps with pinned variants while preserving the *shape* that proves rejection.
- **R-3**: Manifest churn during multi-author parallel editing. Mitigation: this WP runs in a single worktree; manifest updates are atomic at the WP commit.

---

## Reviewer Guidance

Codex reviewer will check:

1. Every class has at least one fixture; the manifest's coverage helper would fail otherwise.
2. The `historical_row_raw` set covers the spec's edge cases: pre-3.0 envelope, forbidden keys, legacy `in_review` synonym, raw status entry.
3. Determinism audit catches non-pinned values.
4. The conformance test parametrizes over every fixture and checks `expected_error_code` (not just accept/reject).
5. The reorganization preserved the in-review fixture moves from WP01 (no orphans).
