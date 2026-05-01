---
work_package_id: WP03
title: Recursive Forbidden-Key Validator
dependencies:
- WP02
requirement_refs:
- FR-005
- NFR-002
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T008
- T009
- T010
- T011
agent: "claude:sonnet:implementer-ivan:implementer"
shell_pid: "15080"
history:
- event: created
  at: '2026-05-01T09:44:26Z'
  by: /spec-kitty.tasks
agent_profile: implementer-ivan
authoritative_surface: src/spec_kitty_events/forbidden_keys.py
execution_mode: code_change
owned_files:
- src/spec_kitty_events/forbidden_keys.py
- tests/test_forbidden_keys.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load implementer-ivan
```

---

## Objective

Ship a recursive forbidden-key validator that rejects any envelope or payload containing a forbidden legacy key (seeded with `feature_slug`, `feature_number`, `mission_key`; expanded by the audit step) at any nesting depth, including inside elements of arrays. Returns a structured `ValidationError(code=FORBIDDEN_KEY, ...)` from WP02.

The validator is **key-only**: a string *value* that happens to equal a forbidden key name MUST be accepted. Hypothesis tests prove correctness across generated nested structures.

---

## Context

- Spec: FR-005, NFR-002, C-001, SC-005.
- Contract: [contracts/forbidden-key-validation.md](../contracts/forbidden-key-validation.md).
- Research: [research.md R-01](../research.md#r-01--complete-forbidden-key-set).
- Depends on WP02's `ValidationError` and `ValidationErrorCode.FORBIDDEN_KEY`.

---

## Subtasks

### T008 — Audit and expand the forbidden-key set

**Purpose**: The seeded keys (`feature_slug`, `feature_number`, `mission_key`) are guaranteed-forbidden but not exhaustive. This audit produces the **complete, named, versioned** set the validator will use.

**Steps**:
1. Survey sources for legacy keys that must be forbidden:
   - **Epic #920 historical-row survey**: the epic reports 6,155 status event rows, 2,772 with `feature_slug`, 1,624 with `work_package_id`, 424 with `legacy_aggregate_id`, etc. Read the epic at `https://github.com/Priivacy-ai/spec-kitty/issues/920` (or the local copy if available) and enumerate every distinct legacy key name surfaced.
   - **Workspace siblings**: search `../spec-kitty-saas` for ingress rejection rules. The implementer should look for files like `.../ingress.py`, `.../validation.py`, or anything literal-string-matching `feature_slug` to find the existing rejection list.
   - **`../spec-kitty` CLI**: look for any `forbidden_keys` constant or rejection set in the CLI repo's `src/`.
2. Produce a written audit (one paragraph per source + a final union list) and place it as a docstring at the top of `src/spec_kitty_events/forbidden_keys.py`. The docstring must cite each source (file path or URL) and the keys derived from it.
3. The final union list **must include** the seeded keys: `feature_slug`, `feature_number`, `mission_key`. Add any keys discovered by the audit.
4. If the workspace siblings are not accessible during this WP, fall back to the seeded set and document the limitation in the docstring; a follow-up audit work package can expand the set later (this is acceptable as long as the seeded set is correct).

**Files**:
- `src/spec_kitty_events/forbidden_keys.py` (created in T009; this subtask informs the constant's content)

**Validation**:
- [ ] The audit docstring lists every source consulted.
- [ ] The seeded keys are present.
- [ ] Any expansion is justified by a citation.

---

### T009 — Create `src/spec_kitty_events/forbidden_keys.py`

**Purpose**: The validator + the named constant.

**Steps**:
1. Create `src/spec_kitty_events/forbidden_keys.py`. Top of file: the audit docstring from T008.
2. Define the constant:

   ```python
   FORBIDDEN_LEGACY_KEYS: frozenset[str] = frozenset({
       "feature_slug",
       "feature_number",
       "mission_key",
       # ... add audit-derived keys here, with a # comment citing the source
   })

   FORBIDDEN_LEGACY_KEYS_VERSION: str = "v1"  # bump on membership change
   ```

3. Implement the recursive validator:

   ```python
   from typing import Any, Iterator
   from spec_kitty_events.validation_errors import ValidationError, ValidationErrorCode

   def find_forbidden_keys(
       data: Any,
       *,
       forbidden: frozenset[str] = FORBIDDEN_LEGACY_KEYS,
       _path: list[str | int] | None = None,
   ) -> Iterator[ValidationError]:
       """Yield a ValidationError(FORBIDDEN_KEY) for each forbidden key found.

       Walks objects (dicts) by their *keys*; never inspects values.
       Recurses into nested objects and into elements of arrays.
       Visit order is deterministic: dict keys in insertion order, then
       recurse into each value; array elements in index order.
       """
       path = list(_path) if _path is not None else []

       if isinstance(data, dict):
           for key, value in data.items():
               key_path = path + [key]
               if key in forbidden:
                   yield ValidationError(
                       code=ValidationErrorCode.FORBIDDEN_KEY,
                       message=f"Forbidden legacy key '{key}' is not allowed",
                       path=key_path,
                       details={"key": key},
                   )
               yield from find_forbidden_keys(value, forbidden=forbidden, _path=key_path)
       elif isinstance(data, list):
           for index, element in enumerate(data):
               yield from find_forbidden_keys(
                   element, forbidden=forbidden, _path=path + [index]
               )
       # primitives: no-op

   def validate_no_forbidden_keys(
       data: Any,
       *,
       forbidden: frozenset[str] = FORBIDDEN_LEGACY_KEYS,
   ) -> ValidationError | None:
       """Return the first ValidationError, or None if no forbidden keys found."""
       try:
           return next(find_forbidden_keys(data, forbidden=forbidden))
       except StopIteration:
           return None
   ```

4. Add a tiny docstring example showing the value-vs-key distinction (a fixture-style accepted case where `"feature_slug"` is a *value*).

5. Type the function fully (`mypy --strict` clean). Use `Any` only for the input data type; everything else is precisely typed.

**Files**:
- `src/spec_kitty_events/forbidden_keys.py` (~80–120 lines including docstring)

**Validation**:
- [ ] `mypy --strict` clean.
- [ ] `validate_no_forbidden_keys({"feature_slug": "x"})` returns a `ValidationError` with `code=FORBIDDEN_KEY` and `path=["feature_slug"]`.
- [ ] `validate_no_forbidden_keys({"name": "feature_slug"})` returns `None` (value-not-key case).
- [ ] `validate_no_forbidden_keys([{"a": {"feature_slug": 1}}])` returns a `ValidationError` with `path=[0, "a", "feature_slug"]`.

---

### T010 — Targeted unit fixtures

**Purpose**: Lock down the specific edge cases called out in the contract.

**Steps**:
1. Create `tests/test_forbidden_keys.py` (new file).
2. Add the targeted cases:

   ```python
   import pytest
   from spec_kitty_events.forbidden_keys import (
       validate_no_forbidden_keys,
       FORBIDDEN_LEGACY_KEYS,
   )
   from spec_kitty_events.validation_errors import ValidationErrorCode

   def test_top_level_forbidden_key():
       err = validate_no_forbidden_keys({"feature_slug": "x"})
       assert err is not None
       assert err.code == ValidationErrorCode.FORBIDDEN_KEY
       assert err.path == ["feature_slug"]
       assert err.details == {"key": "feature_slug"}

   def test_depth_1_nested_forbidden_key():
       err = validate_no_forbidden_keys({"payload": {"feature_slug": "x"}})
       assert err is not None
       assert err.path == ["payload", "feature_slug"]

   def test_depth_3_nested_forbidden_key():
       data = {"a": {"b": {"c": {"mission_key": 1}}}}
       err = validate_no_forbidden_keys(data)
       assert err is not None
       assert err.path == ["a", "b", "c", "mission_key"]

   def test_depth_10_nested_forbidden_key():
       # Build a 10-deep nesting with the forbidden key at the bottom.
       data: dict = {"feature_number": 1}
       for level in range(10):
           data = {f"l{level}": data}
       err = validate_no_forbidden_keys(data)
       assert err is not None
       assert err.code == ValidationErrorCode.FORBIDDEN_KEY
       assert err.path[-1] == "feature_number"
       assert len(err.path) == 11  # 10 wrappers + the leaf key

   def test_array_element_forbidden_key():
       data = {"items": [{"ok": 1}, {"feature_slug": 2}]}
       err = validate_no_forbidden_keys(data)
       assert err is not None
       assert err.path == ["items", 1, "feature_slug"]

   def test_must_accept_when_forbidden_name_is_a_value():
       # The validator inspects KEYS only; a string VALUE that looks like
       # a forbidden key is fine.
       data = {"description": "see field feature_slug for legacy"}
       assert validate_no_forbidden_keys(data) is None

   def test_must_accept_clean_envelope():
       data = {"event_type": "MissionCreated", "payload": {"name": "x"}}
       assert validate_no_forbidden_keys(data) is None

   def test_seeded_keys_are_in_set():
       assert "feature_slug" in FORBIDDEN_LEGACY_KEYS
       assert "feature_number" in FORBIDDEN_LEGACY_KEYS
       assert "mission_key" in FORBIDDEN_LEGACY_KEYS
   ```

**Files**:
- `tests/test_forbidden_keys.py` (~150 lines so far; T011 extends it)

**Validation**:
- [ ] All cases pass.
- [ ] `path` lists use `int` for array indices and `str` for object keys.
- [ ] `details["key"]` matches the offending key.

---

### T011 — Hypothesis property tests + determinism

**Purpose**: Prove the validator's correctness across generated nested structures and across repeated runs.

**Steps**:
1. Add hypothesis to `pyproject.toml` test dependencies if not already present.
2. Extend `tests/test_forbidden_keys.py`:

   ```python
   from hypothesis import given, strategies as st

   # Strategy for arbitrary nested JSON-like structures
   json_like = st.recursive(
       st.one_of(
           st.none(),
           st.booleans(),
           st.integers(),
           st.floats(allow_nan=False, allow_infinity=False),
           st.text(),
       ),
       lambda children: st.one_of(
           st.lists(children, max_size=5),
           st.dictionaries(st.text(min_size=1, max_size=10), children, max_size=5),
       ),
       max_leaves=20,
   )

   def _contains_forbidden_key(data, forbidden=FORBIDDEN_LEGACY_KEYS):
       if isinstance(data, dict):
           if any(k in forbidden for k in data.keys()):
               return True
           return any(_contains_forbidden_key(v, forbidden) for v in data.values())
       if isinstance(data, list):
           return any(_contains_forbidden_key(e, forbidden) for e in data)
       return False

   @given(json_like)
   def test_property_validator_agrees_with_oracle(data):
       err = validate_no_forbidden_keys(data)
       expected = _contains_forbidden_key(data)
       if expected:
           assert err is not None
           assert err.code == ValidationErrorCode.FORBIDDEN_KEY
       else:
           assert err is None

   @given(json_like)
   def test_property_determinism(data):
       a = validate_no_forbidden_keys(data)
       b = validate_no_forbidden_keys(data)
       if a is None:
           assert b is None
       else:
           assert b is not None
           assert a.model_dump_json() == b.model_dump_json()

   @given(st.dictionaries(
       st.sampled_from(sorted(FORBIDDEN_LEGACY_KEYS)),
       st.text(),
       min_size=1,
   ))
   def test_property_any_forbidden_key_at_top_level_is_rejected(data):
       err = validate_no_forbidden_keys(data)
       assert err is not None
       assert err.code == ValidationErrorCode.FORBIDDEN_KEY
       assert err.path[0] in FORBIDDEN_LEGACY_KEYS
   ```

3. Pin `hypothesis` settings to keep the test fast on CI:

   ```python
   from hypothesis import settings
   settings.register_profile("ci", max_examples=200, deadline=2000)
   settings.load_profile("ci")
   ```

**Files**:
- `tests/test_forbidden_keys.py` (extended, total ~280 lines)
- `pyproject.toml` (modified to add hypothesis if absent — note that pyproject is **not** in this WP's `owned_files`; if hypothesis is missing, instead leave a TODO and add to the deps in WP06 (which owns `pyproject.toml`). Confirm hypothesis is already a test dep before assuming you must add it.)

**Validation**:
- [ ] Property tests pass with at least 200 examples each.
- [ ] Determinism property holds.
- [ ] Test runtime stays under a few seconds locally.

---

## Branch Strategy

- Planning/base branch: `main` · Merge target: `main` · Worktree allocated by `finalize-tasks`.

---

## Definition of Done

- [ ] `src/spec_kitty_events/forbidden_keys.py` exists with the audit docstring, the named constant, and the recursive validator.
- [ ] `tests/test_forbidden_keys.py` passes including all targeted cases and hypothesis property tests.
- [ ] `mypy --strict` clean for the new module.
- [ ] No file outside `owned_files` modified (modulo the noted pyproject coordination).
- [ ] `WP02`'s `ValidationError` and `ValidationErrorCode` are imported and used; no new error type invented.

---

## Risks

- **R-1**: An overly aggressive forbidden-key set rejects legitimate envelopes. Mitigation: T008's audit must justify each entry; the seeded three are the safe default.
- **R-2**: Hypothesis tests flake on CI under load. Mitigation: set deadline and max_examples conservatively; pin a CI profile.
- **R-3**: A consumer needs "collect all" mode (all errors at once). Mitigation: `find_forbidden_keys` is a generator; consumers can `list(...)` it. Short-circuit form is `validate_no_forbidden_keys`.

---

## Reviewer Guidance

Codex reviewer will check:

1. The audit docstring cites real sources, not generic prose.
2. The validator inspects keys only — there is a dedicated must-accept test for the value-as-string case.
3. The walk is depth-first and order-deterministic.
4. The `path` list uses `int` for indices and `str` for keys, matching the contract.
5. Hypothesis tests use a sound oracle (the `_contains_forbidden_key` helper is intentionally a different implementation from the validator under test).

## Activity Log

- 2026-05-01T10:38:32Z – claude:sonnet:implementer-ivan:implementer – shell_pid=15080 – Started implementation via action command
