---
work_package_id: WP07
title: Performance Benchmark and Codex Review Handoff
dependencies:
- WP01
- WP06
requirement_refs:
- C-005
- NFR-004
- NFR-005
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T028
- T029
- T030
agent: claude
history:
- event: created
  at: '2026-05-01T09:44:26Z'
  by: /spec-kitty.tasks
agent_profile: implementer-ivan
authoritative_surface: tests/test_validation_benchmark.py
execution_mode: code_change
owned_files:
- tests/test_validation_benchmark.py
- kitty-specs/teamspace-event-contract-foundation-01KQHDE4/contracts/.review-handoff.md
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load implementer-ivan
```

---

## Objective

Land the final mission-close gate: a per-envelope validation performance benchmark proving NFR-005's < 5 ms p95 budget, and a `review-handoff.md` document that maps every spec SC-### to its evidence so Codex can review efficiently.

---

## Context

- Spec: NFR-005, C-005, SC-007.
- Plan: Test Strategy section names this benchmark explicitly.
- Mission close gate: Codex review per C-005.

---

## Subtasks

### T028 — Author `tests/test_validation_benchmark.py`

**Purpose**: Prove NFR-005's < 5 ms p95 envelope validation budget.

**Steps**:
1. Create `tests/test_validation_benchmark.py`.
2. Build a representative fixture sample by reading the conformance fixture suite (e.g., 50 fixtures across classes, biased toward `envelope_valid_canonical` and `envelope_valid_historical_synthesized`).
3. Time validation per fixture using a high-resolution clock; collect 100 samples per fixture.
4. Compute the 95th percentile across all samples.
5. Assert p95 < 5 ms.

   ```python
   import time
   import pytest
   from spec_kitty_events.conformance import load_manifest_entries, load_fixture
   from spec_kitty_events import validate_envelope  # adjust to actual public API

   def measure_one(envelope, iterations=100):
       times = []
       for _ in range(iterations):
           t0 = time.perf_counter_ns()
           validate_envelope(envelope)
           t1 = time.perf_counter_ns()
           times.append(t1 - t0)
       return times

   def percentile(values, p):
       values_sorted = sorted(values)
       k = int(round((p / 100.0) * (len(values_sorted) - 1)))
       return values_sorted[k]

   def test_validation_p95_under_5ms():
       all_times_ns = []
       sample_classes = ["envelope_valid_canonical", "envelope_valid_historical_synthesized"]
       for entry in load_manifest_entries():
           if entry["class"] not in sample_classes:
               continue
           fixture = load_fixture(entry["path"])
           all_times_ns.extend(measure_one(fixture["input"]))
       assert all_times_ns, "no fixtures sampled"
       p95_ns = percentile(all_times_ns, 95)
       p95_ms = p95_ns / 1_000_000
       assert p95_ms < 5.0, f"p95 envelope validation = {p95_ms:.3f}ms (>= 5.0)"
   ```

6. Mark the test with `@pytest.mark.benchmark` (or similar) so it can be run separately if needed.

7. If the benchmark is flaky on heavily-loaded CI, set the threshold with a small buffer (e.g., 5.0 ms) and document the choice; keep the test in the standard pytest run unless a CI signal proves it must be moved.

**Files**:
- `tests/test_validation_benchmark.py` (new, ~80–120 lines)

**Validation**:
- [ ] Test passes locally with comfortable margin.
- [ ] Test fails (deliberately) when seeded with a 50 ms sleep inside the validator (manually verify, then revert).

---

### T029 — Run full pytest + mypy --strict + schema-drift; document results

**Purpose**: Final all-green check before review.

**Steps**:
1. Run the full local test pipeline:
   ```
   pytest -q
   mypy --strict src/spec_kitty_events
   python -m spec_kitty_events.schemas.generate  # confirm zero diff
   ```
2. Capture the output of each command.
3. Append a "Verification Results" subsection to the review-handoff doc (see T030) with the captured outputs (or summaries).
4. If any command fails, **stop** and surface the failure to the orchestrator. Do not proceed to T030.

**Files**:
- (no file edits; results inform T030)

**Validation**:
- [ ] All three commands return success exit codes.
- [ ] Schema regeneration produces zero diff against committed schemas.

---

### T030 — Author `kitty-specs/.../contracts/.review-handoff.md`

**Purpose**: A single document Codex can read to verify mission completeness, with each SC-### mapped to its evidence.

**Steps**:
1. Create `kitty-specs/teamspace-event-contract-foundation-01KQHDE4/contracts/.review-handoff.md`.
2. Structure:

   ```markdown
   # Codex Review Handoff: TeamSpace Event Contract Foundation

   **Mission**: `teamspace-event-contract-foundation-01KQHDE4`
   **Reviewer**: Codex (mandatory per C-005)
   **Branch**: main → main
   **Date**: 2026-05-01

   ## Summary of Changes

   <one-paragraph summary>

   ## Spec → Evidence Mapping

   | Spec ID | Description | Evidence | Status |
   |---|---|---|---|
   | FR-001 | Single canonical lane vocabulary | `src/spec_kitty_events/status.py`, `tests/test_lane_vocabulary.py`, `contracts/lane-vocabulary.md` | ✓ |
   | FR-002 | `in_review` accepted as canonical | `Lane.IN_REVIEW`, conformance fixtures in `events/valid/canonical/wp_status_changed_in_review.json` | ✓ |
   | FR-003 | `MissionClosed` payload reconciled | `contracts/payload-reconciliation.md` reconciliation log; `tests/test_payload_reconciliation.py` | ✓ |
   | FR-004 | `MissionCreated` and `WPStatusChanged` reconciled | (same) | ✓ |
   | FR-005 | Recursive forbidden-key validator | `src/spec_kitty_events/forbidden_keys.py`, `tests/test_forbidden_keys.py` | ✓ |
   | FR-006 | Raw rows rejected | `historical_rows/*.json` fixtures + conformance runner | ✓ |
   | FR-007 | Synthesized envelopes accepted | `events/valid/historical_synthesized/*.json` | ✓ |
   | FR-008 | Conformance fixtures cover all classes | `manifest.json` + `tests/test_conformance_classes.py` | ✓ |
   | FR-009 | Local vs ingress doc | `COMPATIBILITY.md` new section | ✓ |
   | FR-010 | Schema version bump | `pyproject.toml` major bump; `CHANGELOG.md` Breaking Changes; regenerated `*.schema.json` | ✓ |
   | NFR-001 | Determinism | `tests/test_fixture_determinism.py` + per-test determinism asserts | ✓ |
   | NFR-002 | Depth ≥ 10 | `tests/test_forbidden_keys.py::test_depth_10_nested_forbidden_key` | ✓ |
   | NFR-003 | CI gate | conformance suite in pytest | ✓ |
   | NFR-004 | mypy --strict + pytest + schema gen | T029 verification results | ✓ |
   | NFR-005 | < 5 ms p95 | `tests/test_validation_benchmark.py` | ✓ |
   | NFR-006 | Structured + human errors | `validation_errors.py` | ✓ |
   | C-001 | No raw row validates | `historical_rows/` fixtures all rejected | ✓ |
   | C-002 | One vocabulary | `tests/test_lane_vocabulary.py::test_lane_vocabulary_is_single_source_of_truth` | ✓ |
   | C-003 | Schema bump + review | T026, T027, this doc | ✓ |
   | C-004 | No silent break | `tests/test_payload_reconciliation.py` covers historical shape acceptance | ✓ |
   | C-005 | Codex review | this doc is the input | open |
   | C-006 | Determinism | T023 audit | ✓ |
   | SC-001 | 100% acceptance for dry-run | `events/valid/historical_synthesized/` + conformance runner | ✓ |
   | SC-002 | 100% rejection of raw rows | `historical_rows/` fixtures + conformance runner | ✓ |
   | SC-003 | Single source-of-truth | `tests/test_lane_vocabulary.py` | ✓ |
   | SC-004 | `MissionClosed` resolved | reconciliation log + `tests/test_payload_reconciliation.py` | ✓ |
   | SC-005 | Recursive coverage | `tests/test_forbidden_keys.py` (depth + array) | ✓ |
   | SC-006 | Local vs ingress doc | `COMPATIBILITY.md` | ✓ |
   | SC-007 | Codex review complete | (open until reviewer signs off) | open |

   ## Verification Results (from T029)

   <pasted output or summary>

   ## Open items / known issues

   <if any; expected to be empty>

   ## Reviewer notes

   <space for Codex to leave inline notes>
   ```

3. Fill in every cell with concrete file paths and test names. Do not leave generic prose.

**Files**:
- `kitty-specs/teamspace-event-contract-foundation-01KQHDE4/contracts/.review-handoff.md` (new)

**Validation**:
- [ ] Every spec ID has an evidence cell with a real file path or test name.
- [ ] No "TBD" or "..." placeholders remain.

---

## Branch Strategy

- Planning/base branch: `main` · Merge target: `main` · Worktree allocated by `finalize-tasks`.

---

## Definition of Done

- [ ] `tests/test_validation_benchmark.py` passes (p95 < 5 ms).
- [ ] T029 verification: pytest green, mypy --strict green, schema regen zero diff.
- [ ] `review-handoff.md` exists with full spec-to-evidence mapping.
- [ ] No file outside `owned_files` modified.

---

## Risks

- **R-1**: Benchmark flakiness on shared CI. Mitigation: p95 (not p100), generous threshold buffer, mark with a tag if needed for retry policy.
- **R-2**: A late discovery that a previous WP's validation is missing. Mitigation: T029 catches it via mypy/pytest; surface to orchestrator before T030.

---

## Reviewer Guidance

Codex reviewer will read this WP's review-handoff doc as the entry point to the mission. Specifically:

1. Verify that every SC-### maps to a real test or artifact.
2. Spot-check a few mappings (e.g., open the `historical_row_raw` fixtures and confirm they are rejected by manual reading).
3. Inspect the reconciliation log in `contracts/payload-reconciliation.md` for completeness.
4. Confirm the Breaking Changes language in CHANGELOG matches reality.
5. Sign off in the "Reviewer notes" section of the handoff doc to close C-005 and SC-007.
