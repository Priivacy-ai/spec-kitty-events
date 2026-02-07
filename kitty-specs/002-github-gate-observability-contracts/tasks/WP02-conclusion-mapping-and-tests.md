---
work_package_id: WP02
title: Conclusion Mapping & Tests
lane: "for_review"
dependencies: [WP01]
base_branch: main
base_commit: cc3cfc9cfafbdd09c2146c5ad6003e6a3109c3b0
created_at: '2026-02-07T20:37:06.691436+00:00'
subtasks:
- T006
- T007
- T008
- T009
- T010
phase: Phase 1 - Implementation & Verification
assignee: ''
agent: ''
shell_pid: "51548"
review_status: ''
reviewed_by: ''
history:
- timestamp: '2026-02-07T00:00:00Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP02 – Conclusion Mapping & Tests

## Review Feedback

> **Populated by `/spec-kitty.review`** – Reviewers add detailed feedback here when work needs changes.

*[This section is empty initially.]*

---

## Markdown Formatting
Wrap HTML/XML tags in backticks: `<div>`, `<script>`
Use language identifiers in code blocks: `python`, `bash`

---

## Objectives & Success Criteria

Implement the `map_check_run_conclusion()` function in `gates.py` (replacing the WP01 placeholder), then write comprehensive unit tests and Hypothesis property tests covering all payload models and the mapping function.

**Success criteria**:
- `map_check_run_conclusion("success")` returns `"GatePassed"`
- `map_check_run_conclusion("failure")` returns `"GateFailed"`
- `map_check_run_conclusion("neutral")` returns `None` and logs
- `map_check_run_conclusion("bogus")` raises `UnknownConclusionError`
- `pytest tests/unit/test_gates.py tests/property/test_gates_determinism.py -v` — all tests pass
- `pytest --cov=src/spec_kitty_events/gates --cov-report=term-missing` — 100% branch coverage on `gates.py`

## Context & Constraints

**Reference documents**:
- **Spec**: `kitty-specs/002-github-gate-observability-contracts/spec.md` — FR-005 through FR-012
- **Plan**: `kitty-specs/002-github-gate-observability-contracts/plan.md` — Design decisions D3 (mapping), D4 (case sensitivity)
- **Data model**: `kitty-specs/002-github-gate-observability-contracts/data-model.md` — Conclusion Mapping Table
- **Research**: `kitty-specs/002-github-gate-observability-contracts/research.md` — R1 (conclusion values), R5 (logging strategy)

**Existing test patterns to follow**:
- `tests/unit/test_models.py` — follow the same test structure for Pydantic model tests
- `tests/property/test_determinism.py` — follow the same Hypothesis patterns, including `@settings(deadline=None)`

**Prerequisite**: WP01 must be complete. `GatePayloadBase`, `GatePassedPayload`, `GateFailedPayload`, and `UnknownConclusionError` must exist in `gates.py`.

**Implementation command**: `spec-kitty implement WP02 --base WP01`

## Subtasks & Detailed Guidance

### Subtask T006 – Implement `map_check_run_conclusion()` function

**Purpose**: Replace the WP01 placeholder with the full mapping implementation. This function is the core of the observability contract — it deterministically maps every known GitHub `check_run` conclusion to an event type or `None`.

**Steps**:

1. At module level in `gates.py`, define the logger and mapping constants:

   ```python
   logger = logging.getLogger("spec_kitty_events.gates")

   _GATE_PASSED = "GatePassed"
   _GATE_FAILED = "GateFailed"

   _CONCLUSION_MAP: dict[str, Optional[str]] = {
       "success": _GATE_PASSED,
       "failure": _GATE_FAILED,
       "timed_out": _GATE_FAILED,
       "cancelled": _GATE_FAILED,
       "action_required": _GATE_FAILED,
       "neutral": None,
       "skipped": None,
       "stale": None,
   }

   _IGNORED_CONCLUSIONS = frozenset({"neutral", "skipped", "stale"})
   ```

2. Replace the placeholder function with the full implementation:

   ```python
   def map_check_run_conclusion(
       conclusion: str,
       on_ignored: Optional[Callable[[str, str], None]] = None,
   ) -> Optional[str]:
       """Map a GitHub check_run conclusion to an event type string.

       Args:
           conclusion: The raw conclusion string from GitHub's check_run API.
               Must be lowercase. GitHub always sends lowercase values;
               non-lowercase input is treated as unknown.
           on_ignored: Optional callback invoked when a conclusion is ignored.
               Receives (conclusion, reason) where reason is "non_blocking".

       Returns:
           "GatePassed" for success.
           "GateFailed" for failure, timed_out, cancelled, action_required.
           None for neutral, skipped, stale (ignored).

       Raises:
           UnknownConclusionError: If conclusion is not in the known set.
       """
       if conclusion not in _CONCLUSION_MAP:
           raise UnknownConclusionError(conclusion)

       event_type = _CONCLUSION_MAP[conclusion]

       if conclusion in _IGNORED_CONCLUSIONS:
           logger.info(
               "Ignored non-blocking check_run conclusion: %s", conclusion
           )
           if on_ignored is not None:
               on_ignored(conclusion, "non_blocking")

       return event_type
   ```

3. **Key design points**:
   - **Lowercase only**: `"SUCCESS"` is not in `_CONCLUSION_MAP` → raises `UnknownConclusionError`. This is intentional (D4).
   - **Logging**: Uses `logger.info()` with the named logger `"spec_kitty_events.gates"`. Consumers can configure this logger's level independently.
   - **Callback**: `on_ignored` is called with `(conclusion, "non_blocking")` — the reason string is always `"non_blocking"` for now but the signature allows future extension.
   - **No fallback**: Unknown conclusions raise — never silently return `None`.

**Files**: `src/spec_kitty_events/gates.py` (modify existing file from WP01)
**Parallel?**: No — must be complete before T007, T008, T009.

### Subtask T007 – Write unit tests for payload model validation and serialization

**Purpose**: Verify that `GatePassedPayload` and `GateFailedPayload` enforce all field constraints, are frozen, and round-trip through serialization correctly. Covers FR-001 through FR-004, FR-010.

**Steps**:

1. Create `tests/unit/test_gates.py`.

2. **Test valid construction** — both `GatePassedPayload` and `GateFailedPayload`:
   ```python
   def test_gate_passed_payload_valid_construction():
       payload = GatePassedPayload(
           gate_name="ci/build",
           gate_type="ci",
           conclusion="success",
           external_provider="github",
           check_run_id=123456,
           check_run_url="https://github.com/org/repo/runs/123456",
           delivery_id="delivery-abc-123",
       )
       assert payload.gate_name == "ci/build"
       assert payload.gate_type == "ci"
       assert payload.check_run_id == 123456
       assert payload.pr_number is None  # default
   ```

3. **Test each required field missing** — parametrize over field names:
   ```python
   @pytest.mark.parametrize("omitted_field", [
       "gate_name", "gate_type", "conclusion", "external_provider",
       "check_run_id", "check_run_url", "delivery_id",
   ])
   def test_gate_payload_missing_required_field(omitted_field):
       valid_data = { ... }  # all fields present
       del valid_data[omitted_field]
       with pytest.raises(pydantic.ValidationError):
           GatePassedPayload(**valid_data)
   ```

4. **Test `pr_number` optional field**:
   - `pr_number=None` → valid
   - `pr_number=42` → valid
   - `pr_number=0` → `ValidationError` (gt=0 constraint)
   - `pr_number=-1` → `ValidationError`

5. **Test frozen immutability**:
   ```python
   def test_gate_payload_is_frozen():
       payload = GatePassedPayload(...)
       with pytest.raises(pydantic.ValidationError):
           payload.gate_name = "changed"
   ```

6. **Test `Literal` constraints**:
   - `gate_type="not_ci"` → `ValidationError`
   - `external_provider="gitlab"` → `ValidationError`

7. **Test URL validation**:
   - `check_run_url="not-a-url"` → `ValidationError`
   - `check_run_url="https://github.com/org/repo/runs/123"` → valid

8. **Test serialization round-trip**:
   ```python
   def test_gate_payload_serialization_roundtrip():
       payload = GatePassedPayload(...)
       dumped = payload.model_dump()
       assert isinstance(dumped, dict)
       reconstructed = GatePassedPayload.model_validate(dumped)
       assert reconstructed == payload
   ```

   **Important**: If `AnyHttpUrl` causes the round-trip to fail (serializes as `Url` object that can't be fed back), you need to add a serializer to the model. Fix this in `gates.py`:
   ```python
   from pydantic import field_serializer

   @field_serializer("check_run_url")
   @classmethod
   def serialize_url(cls, v: AnyHttpUrl) -> str:
       return str(v)
   ```

9. **Test `isinstance` discrimination**:
   ```python
   def test_gate_payload_type_discrimination():
       passed = GatePassedPayload(...)
       failed = GateFailedPayload(...)
       assert isinstance(passed, GatePayloadBase)
       assert isinstance(failed, GatePayloadBase)
       assert isinstance(passed, GatePassedPayload)
       assert not isinstance(passed, GateFailedPayload)
   ```

10. **Test `model_dump()` output used with `Event.payload`**:
    ```python
    def test_gate_payload_as_event_payload():
        gate_payload = GatePassedPayload(...)
        event = Event(
            event_id="01HXYZ" + "A" * 20,  # 26 chars
            event_type="GatePassed",
            aggregate_id="project-1",
            payload=gate_payload.model_dump(),
            timestamp=datetime.now(),
            node_id="worker-1",
            lamport_clock=1,
            project_uuid=uuid.uuid4(),
        )
        assert event.payload["gate_name"] == "ci/build"
        assert event.event_type == "GatePassed"
    ```

**Files**: `tests/unit/test_gates.py` (new file)
**Parallel?**: Yes — can be written in parallel with T008, T009 (different test classes/sections in the same file).

### Subtask T008 – Write unit tests for conclusion mapping

**Purpose**: Verify `map_check_run_conclusion()` returns correct results for all 8 known conclusions, raises for unknown values, respects case sensitivity, and invokes callbacks. Covers FR-005 through FR-009.

**Steps**:

1. **Test each known conclusion** — parametrize:
   ```python
   @pytest.mark.parametrize("conclusion,expected", [
       ("success", "GatePassed"),
       ("failure", "GateFailed"),
       ("timed_out", "GateFailed"),
       ("cancelled", "GateFailed"),
       ("action_required", "GateFailed"),
       ("neutral", None),
       ("skipped", None),
       ("stale", None),
   ])
   def test_map_check_run_conclusion_known_values(conclusion, expected):
       result = map_check_run_conclusion(conclusion)
       assert result == expected
   ```

2. **Test unknown conclusion raises**:
   ```python
   def test_map_check_run_conclusion_unknown_raises():
       with pytest.raises(UnknownConclusionError) as exc_info:
           map_check_run_conclusion("bogus_value")
       assert exc_info.value.conclusion == "bogus_value"
       assert "bogus_value" in str(exc_info.value)
   ```

3. **Test case sensitivity** (D4 — lowercase only):
   ```python
   @pytest.mark.parametrize("bad_case", ["SUCCESS", "Failure", "TIMED_OUT", "Neutral"])
   def test_map_check_run_conclusion_rejects_non_lowercase(bad_case):
       with pytest.raises(UnknownConclusionError):
           map_check_run_conclusion(bad_case)
   ```

4. **Test empty string raises**:
   ```python
   def test_map_check_run_conclusion_empty_string_raises():
       with pytest.raises(UnknownConclusionError):
           map_check_run_conclusion("")
   ```

5. **Test `on_ignored` callback invoked for ignored conclusions**:
   ```python
   @pytest.mark.parametrize("conclusion", ["neutral", "skipped", "stale"])
   def test_map_check_run_conclusion_calls_on_ignored(conclusion):
       calls = []
       def callback(c: str, reason: str) -> None:
           calls.append((c, reason))

       result = map_check_run_conclusion(conclusion, on_ignored=callback)
       assert result is None
       assert len(calls) == 1
       assert calls[0] == (conclusion, "non_blocking")
   ```

6. **Test `on_ignored` NOT invoked for non-ignored conclusions**:
   ```python
   @pytest.mark.parametrize("conclusion", ["success", "failure", "timed_out"])
   def test_map_check_run_conclusion_no_callback_for_blocking(conclusion):
       calls = []
       result = map_check_run_conclusion(conclusion, on_ignored=lambda c, r: calls.append((c, r)))
       assert result is not None
       assert len(calls) == 0
   ```

7. **Test logging output** for ignored conclusions:
   ```python
   def test_map_check_run_conclusion_logs_ignored(caplog):
       import logging
       with caplog.at_level(logging.INFO, logger="spec_kitty_events.gates"):
           map_check_run_conclusion("neutral")
       assert "neutral" in caplog.text
       assert "Ignored" in caplog.text or "ignored" in caplog.text
   ```

8. **Test `on_ignored=None` (default) doesn't error for ignored conclusions**:
   ```python
   def test_map_check_run_conclusion_no_callback_ok():
       result = map_check_run_conclusion("skipped")
       assert result is None  # no error, just None
   ```

**Files**: `tests/unit/test_gates.py` (same file as T007, different test class or section)
**Parallel?**: Yes — can be written in parallel with T007, T009.

### Subtask T009 – Write Hypothesis property tests for mapping determinism

**Purpose**: Use property-based testing to verify that the mapping function is deterministic (same input always produces same output) and that all known values are handled. Covers FR-012 and SC-001.

**Steps**:

1. Create `tests/property/test_gates_determinism.py`.

2. **Import and strategy setup**:
   ```python
   import pytest
   from hypothesis import given, settings, strategies as st

   from spec_kitty_events.gates import (
       map_check_run_conclusion,
       UnknownConclusionError,
       _CONCLUSION_MAP,
   )

   KNOWN_CONCLUSIONS = list(_CONCLUSION_MAP.keys())
   ```

3. **Test determinism** — same input always produces same output:
   ```python
   @settings(deadline=None)
   @given(conclusion=st.sampled_from(KNOWN_CONCLUSIONS))
   def test_mapping_is_deterministic(conclusion):
       result1 = map_check_run_conclusion(conclusion)
       result2 = map_check_run_conclusion(conclusion)
       assert result1 == result2
   ```

4. **Test exhaustiveness** — all known values produce a result (not an exception):
   ```python
   @settings(deadline=None)
   @given(conclusion=st.sampled_from(KNOWN_CONCLUSIONS))
   def test_all_known_conclusions_handled(conclusion):
       result = map_check_run_conclusion(conclusion)
       assert result in ("GatePassed", "GateFailed", None)
   ```

5. **Test unknown values always raise**:
   ```python
   @settings(deadline=None)
   @given(conclusion=st.text(min_size=1).filter(lambda s: s not in KNOWN_CONCLUSIONS))
   def test_unknown_conclusions_always_raise(conclusion):
       with pytest.raises(UnknownConclusionError):
           map_check_run_conclusion(conclusion)
   ```

6. **Test partition completeness** — every known conclusion maps to exactly one category:
   ```python
   def test_conclusion_map_covers_all_github_values():
       expected_conclusions = {
           "success", "failure", "timed_out", "cancelled",
           "action_required", "neutral", "skipped", "stale",
       }
       assert set(_CONCLUSION_MAP.keys()) == expected_conclusions
   ```

**Files**: `tests/property/test_gates_determinism.py` (new file)
**Parallel?**: Yes — can be written in parallel with T007, T008.

**Notes**:
- Always use `@settings(deadline=None)` — matches existing project convention (see `tests/property/test_determinism.py`).
- Import `_CONCLUSION_MAP` from `gates` — it's a module-level constant, not private API for testing purposes.

### Subtask T010 – Run full test suite and verify coverage

**Purpose**: Ensure all new and existing tests pass, and `gates.py` achieves 100% branch coverage.

**Steps**:
1. Run full test suite: `pytest tests/ -v`
2. Run coverage for gates module: `pytest tests/unit/test_gates.py tests/property/test_gates_determinism.py --cov=src/spec_kitty_events/gates --cov-report=term-missing`
3. Verify 100% coverage on `gates.py`. If any lines are uncovered, add tests to cover them.
4. Run mypy: `mypy --strict src/spec_kitty_events/gates.py`
5. Verify no regressions in existing tests.

**Files**: No file changes expected — verification only.
**Parallel?**: No — depends on T006–T009 being complete.

## Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| `AnyHttpUrl` round-trip failure | Medium | Medium | If `model_dump()` produces a `Url` object, add `@field_serializer("check_run_url")` in gates.py to serialize as string. |
| Hypothesis generates extremely slow test cases | Low | Low | Use `@settings(deadline=None, max_examples=200)` to bound execution. |
| Logging tests fragile with `caplog` | Low | Low | Match on substring, not exact message. Use logger name filtering. |

## Review Guidance

- Verify all 8 conclusions are tested parametrically (not just a subset).
- Verify `on_ignored` callback is tested for all 3 ignored conclusions.
- Verify case sensitivity tests cover at least 3 uppercase/mixed-case variants.
- Verify Hypothesis tests use `@settings(deadline=None)`.
- Verify coverage report shows 100% on `gates.py`.
- Check that the `_CONCLUSION_MAP` keys exactly match the 8 values from the spec.

## Activity Log

- 2026-02-07T00:00:00Z – system – lane=planned – Prompt created.
- 2026-02-07T20:39:24Z – unknown – shell_pid=51548 – lane=for_review – 69 tests passing, 100% coverage on gates.py
