---
work_package_id: WP02
title: Conformance Helper, Fixtures, and Tests
dependencies:
- WP01
requirement_refs:
- FR-005
- FR-006
- FR-007
- FR-008
- FR-010
- NFR-001
- NFR-002
- NFR-003
- NFR-004
- C-001
- C-003
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this mission were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T005
- T006
- T007
- T008
- T009
phase: Phase 2 - Conformance
assignee: ''
agent: "claude:opus-4-7:implementer-ivan:implementer"
shell_pid: "36118"
history:
- timestamp: '2026-05-15T11:00:00Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
agent_profile: implementer-ivan
authoritative_surface: src/spec_kitty_events/conformance/
execution_mode: code_change
lane: planned
owned_files:
- src/spec_kitty_events/conformance/timestamp_semantics.py
- src/spec_kitty_events/conformance/__init__.py
- src/spec_kitty_events/conformance/fixtures/timestamp_semantics/**
- src/spec_kitty_events/conformance/fixtures/manifest.json
- src/spec_kitty_events/conformance/tests/test_timestamp_semantics.py
review_status: ''
reviewed_by: ''
role: implementer
tags: []
---

# Work Package Prompt: WP02 – Conformance Helper, Fixtures, and Tests

## ⚡ Do This First: Load Agent Profile

```text
/ad-hoc-profile-load implementer-ivan
```

If your environment does not support that slash command, run `spec-kitty profiles show implementer-ivan` and adopt the identity it declares.

---

## ⚠️ IMPORTANT: Review Feedback Status

Check the `review_status` frontmatter field. If `has_feedback`, read the **Review Feedback** section below. Set `review_status: acknowledged` when you start.

---

## Review Feedback

*(empty)*

---

## Objectives & Success Criteria

Deliver the executable surface that prevents consumer drift: a reusable conformance helper, a typed substitution error, three committed fixtures, and pytest cases that exercise good-consumer, equality-edge, and bad-consumer paths.

Done means:

- `src/spec_kitty_events/conformance/timestamp_semantics.py` defines:
  - `class TimestampSubstitutionError(Exception)` with attributes `field_name: str`, `expected: datetime`, `actual: datetime` and a human-readable `__str__`.
  - `def assert_producer_occurrence_preserved(envelope: Mapping[str, Any] | Event, persisted_occurrence_time: datetime, *, field_name: str = "persisted_occurrence_time") -> None` that raises `TimestampSubstitutionError` when the consumer's persisted value does not equal the canonical envelope `timestamp`. Both values are normalised to timezone-aware UTC datetimes for comparison.
- `src/spec_kitty_events/conformance/__init__.py` re-exports the helper and the error. `__all__` includes both symbols.
- Three committed fixtures live under `src/spec_kitty_events/conformance/fixtures/timestamp_semantics/`:
  - `valid/old_producer_recent_receipt.json` (producer 2026-01-01, receipt 2026-05-15, persisted = producer)
  - `valid/live_event_producer_equals_receipt.json` (producer = receipt = persisted)
  - `invalid/consumer_substituted_receipt_time.json` (persisted equals receipt time, NOT producer)
- The conformance fixture manifest under `src/spec_kitty_events/conformance/fixtures/manifest.json` registers the new fixture kind if the loader's contract requires it (verify by reading `src/spec_kitty_events/conformance/loader.py`).
- `src/spec_kitty_events/conformance/tests/test_timestamp_semantics.py` (or whichever pytest discovery location the existing conformance tests use) verifies:
  - Helper passes for both valid fixtures.
  - Helper raises `TimestampSubstitutionError` for the invalid fixture, and the raised exception's `expected`/`actual` match the fixture's `envelope.timestamp` and `consumer_simulation.persisted_occurrence_time`.
  - Helper accepts an `Event` instance or a plain `dict` envelope.
  - Helper accepts both timezone-aware and naive datetimes for `persisted_occurrence_time` (naive treated as UTC).
  - Constructing `TimestampSubstitutionError(field_name="x", expected=..., actual=...)` directly preserves all three attributes and produces a usable `__str__`.
- Charter quality gates green: `pytest`, schema drift check, `mypy --strict`.

Mission requirements covered: FR-005, FR-006, FR-007, FR-008, FR-010, NFR-001, NFR-002, NFR-003, NFR-004, C-001, C-003.

## Context & Constraints

- Helper goes in the existing `src/spec_kitty_events/conformance/` subpackage (research R-02). Public surface stays additive (C-001).
- No runtime dependency added (C-003). The helper uses only stdlib + Pydantic (already required).
- Deterministic, no IO beyond the caller's fixture loading (NFR-001).
- Per fixture <250 ms (NFR-002), suite delta <2 s (NFR-003).
- Read `src/spec_kitty_events/conformance/loader.py` to understand how fixtures are discovered; the new fixture kind may need a `manifest.json` entry or may be auto-discovered by directory glob — match the existing convention.

## Subtasks & Detailed Guidance

### Subtask T005 – Add `timestamp_semantics.py`

- **Purpose**: Ship the reusable assertion + typed error.
- **Steps**:
  1. Create `src/spec_kitty_events/conformance/timestamp_semantics.py`.
  2. Implement `TimestampSubstitutionError`:
     ```python
     class TimestampSubstitutionError(Exception):
         """Raised when a consumer substituted receipt/import time for the canonical producer timestamp."""

         def __init__(self, *, field_name: str, expected: datetime, actual: datetime) -> None:
             self.field_name = field_name
             self.expected = expected
             self.actual = actual
             super().__init__(
                 f"Canonical producer occurrence time was not preserved. "
                 f"Field {field_name!r}: expected={expected.isoformat()} actual={actual.isoformat()}. "
                 f"See contracts/timestamp-semantics.md."
             )
     ```
  3. Implement `assert_producer_occurrence_preserved`:
     - Accept `envelope: Mapping[str, Any] | Event` and `persisted_occurrence_time: datetime`.
     - Extract the canonical `timestamp` from the envelope. If `envelope` is an `Event`, use `envelope.timestamp`; otherwise read `envelope["timestamp"]` and parse via `datetime.fromisoformat` (handle the `Z` suffix; canonicalise to UTC).
     - Canonicalise both `expected` and `actual` to timezone-aware UTC `datetime`. Naive datetimes are treated as UTC (per requirements; document that contract in the docstring).
     - If `expected != actual`, raise `TimestampSubstitutionError(field_name=field_name, expected=expected_utc, actual=actual_utc)`.
     - Otherwise return `None`.
  4. Use `from __future__ import annotations` and full type hints to satisfy `mypy --strict`.
- **Files**: `src/spec_kitty_events/conformance/timestamp_semantics.py` (new, ~80 lines).
- **Parallel?**: no.
- **Notes**: `datetime.fromisoformat` in Python 3.10 does not accept trailing `Z`; replace `Z` with `+00:00` before parsing.

### Subtask T006 – Re-export from `conformance/__init__.py`

- **Purpose**: Make the helper importable as `from spec_kitty_events.conformance import assert_producer_occurrence_preserved, TimestampSubstitutionError`.
- **Steps**:
  1. Open `src/spec_kitty_events/conformance/__init__.py`.
  2. Add an import: `from spec_kitty_events.conformance.timestamp_semantics import TimestampSubstitutionError, assert_producer_occurrence_preserved`.
  3. Extend `__all__` to include both names (alphabetical sort).
- **Files**: `src/spec_kitty_events/conformance/__init__.py`
- **Parallel?**: no (small dependent edit).

### Subtask T007 – Add fixtures

- **Purpose**: Provide the executable "old producer / recent receipt" test vectors.
- **Steps**:
  1. Create directory `src/spec_kitty_events/conformance/fixtures/timestamp_semantics/`.
  2. Create three JSON files following the shape documented in `kitty-specs/executable-event-timestamp-semantics-01KRNME2/data-model.md` (Fixture Shape section):
     - `valid/old_producer_recent_receipt.json` — producer `2026-01-01T00:00:00+00:00`, `received_at` `2026-05-15T10:00:00+00:00`, `persisted_occurrence_time` = producer.
     - `valid/live_event_producer_equals_receipt.json` — producer = `2026-05-15T10:00:00+00:00`, `received_at` = same, `persisted_occurrence_time` = same.
     - `invalid/consumer_substituted_receipt_time.json` — producer `2026-01-01T00:00:00+00:00`, `received_at` `2026-05-15T10:00:00+00:00`, `persisted_occurrence_time` = `received_at`.
  3. Use synthesised but contract-valid `event_id`, `correlation_id`, `build_id`, `node_id`, `project_uuid`, etc. (use stable ULID/UUID strings — do not generate at runtime).
  4. If the existing `src/spec_kitty_events/conformance/fixtures/manifest.json` lists fixture kinds explicitly, add a `timestamp_semantics` entry referencing the three files. If the loader auto-discovers by glob, only add files.
- **Files**: three JSON fixtures + optional manifest update.
- **Parallel?**: yes (with T005/T006 once shape is locked).

### Subtask T008 – Add conformance tests

- **Purpose**: Lock in good/equality/bad behaviour.
- **Steps**:
  1. Create `src/spec_kitty_events/conformance/tests/test_timestamp_semantics.py` (if a `tests/` dir does not exist under `conformance/`, use the existing test pattern — e.g. add to whichever pytest-collected path the package already uses for conformance tests; check `pyproject.toml` `[tool.pytest.ini_options]`).
  2. Write tests:
     - `test_old_producer_recent_receipt_helper_passes`: load fixture, call helper with `persisted_occurrence_time` parsed from fixture, expect no exception.
     - `test_live_event_producer_equals_receipt_helper_passes`: same.
     - `test_consumer_substituted_receipt_time_helper_raises`: load fixture, call helper, expect `TimestampSubstitutionError`, assert `expected` matches envelope `timestamp` and `actual` matches `received_at`.
     - `test_helper_accepts_naive_datetime_as_utc`: build a one-off envelope dict with `timestamp = "2026-01-01T00:00:00+00:00"`, call helper with naive `datetime(2026,1,1,0,0,0)`; expect no exception.
     - `test_helper_accepts_event_instance`: build an `Event` Pydantic instance (with all required fields), call helper, expect pass.
     - `test_error_attributes_round_trip`: construct `TimestampSubstitutionError(field_name="last_event_at", expected=..., actual=...)`, assert attributes and `str(err)` contains both isoformat values and the field name.
- **Files**: `src/spec_kitty_events/conformance/tests/test_timestamp_semantics.py` (new, ~120 lines).
- **Parallel?**: depends on T005/T006/T007.
- **Notes**: Use `pytest.raises(TimestampSubstitutionError) as exc_info` so attributes can be asserted.

### Subtask T009 – Run charter quality gates

- **Purpose**: Confirm pytest, schema drift, and mypy --strict are all green on the resulting tree.
- **Steps**:
  1. `pytest` (full suite) — must be green; suite wall time should not grow by more than ~2 seconds (NFR-003).
  2. Schema drift check — already exercised by pytest if integrated; otherwise run the project's explicit drift command.
  3. `mypy --strict src/spec_kitty_events` — must be green.
  4. If any gate fails, fix and re-run before declaring the WP done. Do NOT mask failures.
- **Files**: none.
- **Parallel?**: no — final gate.

## Test Strategy

The mission is contract enforcement, so tests ARE the deliverable. WP02 specifically produces:

- 6 pytest cases as listed in T008.
- Existing pytest suite continues to pass.
- Existing schema drift check continues to pass (WP01 already regenerated schemas; WP02 doesn't change models).
- `mypy --strict` clean for new code.

Commands:

```bash
pytest
mypy --strict src/spec_kitty_events
```

## Risks & Mitigations

- **Risk**: Helper too strict and rejects legitimate timezone variations (e.g. `+00:00` vs `Z`). **Mitigation**: parse and canonicalise to UTC `datetime` before equality.
- **Risk**: Fixture loader doesn't discover the new fixture kind. **Mitigation**: read `loader.py` and follow the existing convention (manifest entry or directory glob).
- **Risk**: Conformance `tests/` directory does not exist; ad-hoc placement breaks pytest discovery. **Mitigation**: place tests where the existing conformance suite already lives (the package exposes `pytest --pyargs spec_kitty_events.conformance` — tests must be discoverable through that entrypoint).
- **Risk**: `mypy --strict` complains about `datetime | None` or `Mapping[str, Any]`. **Mitigation**: use full annotations; `from __future__ import annotations` keeps signatures readable.
- **Risk**: Helper signature drifts from the contract document. **Mitigation**: match `contracts/timestamp-semantics.md` exactly.

## Review Guidance

Reviewer checks:

- [ ] `TimestampSubstitutionError` has the three documented attributes and a useful `__str__`.
- [ ] Helper handles `Event` instance and dict envelopes; canonicalises timezone before comparing.
- [ ] Helper raises the typed error (not a bare `AssertionError`).
- [ ] Three fixtures present at the documented paths with the documented values.
- [ ] All six pytest cases present and green.
- [ ] `__init__.py` re-exports both helper and error.
- [ ] `mypy --strict` clean; pytest fast (`<2s` added).
- [ ] No change to model wire format; C-001..C-005 honoured.

## Activity Log

- 2026-05-15T11:00:00Z – system – lane=planned – Prompt created
- 2026-05-15T11:11:54Z – claude:opus-4-7:implementer-ivan:implementer – shell_pid=36118 – Started implementation via action command
- 2026-05-15T11:17:16Z – claude:opus-4-7:implementer-ivan:implementer – shell_pid=36118 – WP02 complete: timestamp_semantics.py (helper + TimestampSubstitutionError), conformance package __init__ re-exports, 3 fixtures (old_producer_recent_receipt, live_event_producer_equals_receipt, consumer_substituted_receipt_time), manifest entries, loader/entrypoint filters updated, 10 pytest cases. Charter gates: pytest 1922 passed, mypy --strict clean, schema drift check passes.
