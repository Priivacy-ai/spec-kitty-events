"""Tests for the recursive forbidden-key validator (WP03 / T010 + T011).

Covers:

* Targeted edge cases pinned by ``contracts/forbidden-key-validation.md``:
  top-level, depth-1, depth-3, depth-10, array element, value-not-key,
  clean envelope, seeded-keys-in-set.
* Hypothesis property tests:
  - validator agrees with an oracle implementation written independently;
  - determinism (the validator returns byte-identical errors across
    repeated runs of the same input);
  - any structure that contains at least one forbidden key at top level
    is rejected.

The hypothesis CI profile is pinned to ``max_examples=200`` and
``deadline=2000`` (ms) per the work package brief — fast enough on CI
under load, exhaustive enough to be meaningful.
"""

from __future__ import annotations

from typing import Any

from hypothesis import HealthCheck, given, settings, strategies as st

from spec_kitty_events.forbidden_keys import (
    FORBIDDEN_LEGACY_KEYS,
    find_forbidden_keys,
    validate_no_forbidden_keys,
)
from spec_kitty_events.validation_errors import ValidationErrorCode


# ---------------------------------------------------------------------------
# Hypothesis profile — pinned for CI per WP03 brief.
# ---------------------------------------------------------------------------

settings.register_profile(
    "ci",
    max_examples=200,
    deadline=2000,
    suppress_health_check=[HealthCheck.too_slow],
)
settings.load_profile("ci")


# ---------------------------------------------------------------------------
# T010 — Targeted unit fixtures.
# ---------------------------------------------------------------------------


def test_top_level_forbidden_key() -> None:
    err = validate_no_forbidden_keys({"feature_slug": "x"})
    assert err is not None
    assert err.code == ValidationErrorCode.FORBIDDEN_KEY
    assert err.path == ["feature_slug"]
    assert err.details == {"key": "feature_slug"}


def test_depth_1_nested_forbidden_key() -> None:
    err = validate_no_forbidden_keys({"payload": {"feature_slug": "x"}})
    assert err is not None
    assert err.code == ValidationErrorCode.FORBIDDEN_KEY
    assert err.path == ["payload", "feature_slug"]


def test_depth_3_nested_forbidden_key() -> None:
    data = {"a": {"b": {"c": {"mission_key": 1}}}}
    err = validate_no_forbidden_keys(data)
    assert err is not None
    assert err.path == ["a", "b", "c", "mission_key"]
    assert err.details == {"key": "mission_key"}


def test_depth_10_nested_forbidden_key() -> None:
    # Build a 10-deep nesting with the forbidden key at the bottom.
    data: dict[str, Any] = {"feature_number": 1}
    for level in range(10):
        data = {f"l{level}": data}
    err = validate_no_forbidden_keys(data)
    assert err is not None
    assert err.code == ValidationErrorCode.FORBIDDEN_KEY
    assert err.path[-1] == "feature_number"
    assert len(err.path) == 11  # 10 wrappers + the leaf key
    # Path uses string keys for objects.
    assert all(isinstance(segment, str) for segment in err.path)


def test_array_element_forbidden_key() -> None:
    data = {"items": [{"ok": 1}, {"feature_slug": 2}]}
    err = validate_no_forbidden_keys(data)
    assert err is not None
    assert err.path == ["items", 1, "feature_slug"]
    # Path uses int for array indices, str for object keys.
    assert isinstance(err.path[0], str)
    assert isinstance(err.path[1], int)
    assert isinstance(err.path[2], str)


def test_must_accept_when_forbidden_name_is_a_value() -> None:
    # The validator inspects KEYS only; a string VALUE that looks like a
    # forbidden key is fine.
    data = {"description": "see field feature_slug for legacy"}
    assert validate_no_forbidden_keys(data) is None


def test_must_accept_clean_envelope() -> None:
    data = {"event_type": "MissionCreated", "payload": {"name": "x"}}
    assert validate_no_forbidden_keys(data) is None


def test_seeded_keys_are_in_set() -> None:
    assert "feature_slug" in FORBIDDEN_LEGACY_KEYS
    assert "feature_number" in FORBIDDEN_LEGACY_KEYS
    assert "mission_key" in FORBIDDEN_LEGACY_KEYS


def test_legacy_aggregate_id_in_set_per_audit() -> None:
    # Promoted from epic #920 audit (424 rows).
    assert "legacy_aggregate_id" in FORBIDDEN_LEGACY_KEYS


def test_work_package_id_intentionally_not_in_set() -> None:
    # Documented in the audit docstring: still legitimate frontmatter.
    assert "work_package_id" not in FORBIDDEN_LEGACY_KEYS


def test_find_forbidden_keys_yields_all_hits_in_visit_order() -> None:
    # Two forbidden keys: top-level feature_slug, then nested mission_key.
    # Deterministic order is dict insertion order, depth-first.
    data: dict[str, Any] = {
        "feature_slug": "a",
        "child": {"mission_key": "b"},
    }
    errors = list(find_forbidden_keys(data))
    assert len(errors) == 2
    assert errors[0].path == ["feature_slug"]
    assert errors[1].path == ["child", "mission_key"]


def test_find_forbidden_keys_walks_arrays_in_index_order() -> None:
    data = [
        {"feature_slug": 1},
        {"deep": [{"mission_key": 2}]},
    ]
    errors = list(find_forbidden_keys(data))
    assert [e.path for e in errors] == [
        [0, "feature_slug"],
        [1, "deep", 0, "mission_key"],
    ]


def test_empty_root_path_is_empty_list() -> None:
    # Per contract: [] denotes the envelope root.
    err = validate_no_forbidden_keys({})
    assert err is None
    # And on a hit, the path starts at the root level.
    err = validate_no_forbidden_keys({"feature_slug": 1})
    assert err is not None
    assert err.path == ["feature_slug"]


# ---------------------------------------------------------------------------
# T011 — Hypothesis property tests.
# ---------------------------------------------------------------------------


# Strategy for arbitrary nested JSON-like structures. Bounded by
# ``max_leaves=20`` to keep generation fast; depth is implicitly bounded
# by hypothesis's recursive draw heuristics.
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
        st.dictionaries(
            st.text(min_size=1, max_size=10), children, max_size=5
        ),
    ),
    max_leaves=20,
)


def _oracle_contains_forbidden_key(
    data: Any,
    forbidden: frozenset[str] = FORBIDDEN_LEGACY_KEYS,
) -> bool:
    """Independent oracle: True iff any forbidden key is present anywhere.

    Intentionally written as a *different* implementation from the
    validator under test (uses ``any(...)`` over comprehensions instead
    of an explicit yielding walk) so that agreement is meaningful.
    """

    if isinstance(data, dict):
        if any(isinstance(k, str) and k in forbidden for k in data.keys()):
            return True
        return any(
            _oracle_contains_forbidden_key(v, forbidden) for v in data.values()
        )
    if isinstance(data, list):
        return any(
            _oracle_contains_forbidden_key(e, forbidden) for e in data
        )
    return False


@given(json_like)
def test_property_validator_agrees_with_oracle(data: Any) -> None:
    err = validate_no_forbidden_keys(data)
    expected = _oracle_contains_forbidden_key(data)
    if expected:
        assert err is not None
        assert err.code == ValidationErrorCode.FORBIDDEN_KEY
        # The terminal path segment is the offending key.
        assert err.path[-1] in FORBIDDEN_LEGACY_KEYS
        assert err.details.get("key") == err.path[-1]
    else:
        assert err is None


@given(json_like)
def test_property_determinism(data: Any) -> None:
    a = validate_no_forbidden_keys(data)
    b = validate_no_forbidden_keys(data)
    if a is None:
        assert b is None
    else:
        assert b is not None
        assert a.model_dump_json() == b.model_dump_json()


@given(
    st.dictionaries(
        st.sampled_from(sorted(FORBIDDEN_LEGACY_KEYS)),
        st.text(),
        min_size=1,
    )
)
def test_property_any_forbidden_key_at_top_level_is_rejected(
    data: dict[str, str],
) -> None:
    err = validate_no_forbidden_keys(data)
    assert err is not None
    assert err.code == ValidationErrorCode.FORBIDDEN_KEY
    assert isinstance(err.path[0], str)
    assert err.path[0] in FORBIDDEN_LEGACY_KEYS


@given(json_like, st.text(min_size=1, max_size=20))
def test_property_value_equal_to_forbidden_name_does_not_trip(
    inner: Any, key_name: str
) -> None:
    """A string VALUE equal to a forbidden key name MUST be accepted.

    We construct an envelope whose key is *not* forbidden but whose value
    is one of the forbidden key names verbatim; the validator must
    accept it (assuming ``inner`` itself is clean).
    """

    if _oracle_contains_forbidden_key(inner):
        # Skip cases where the random inner already contains a forbidden
        # key; this property is about value-vs-key only.
        return

    # Use a non-forbidden outer key name. ``key_name`` itself might be
    # one of the forbidden names — in that case skip; we want a clean
    # outer key paired with a forbidden-name VALUE.
    if key_name in FORBIDDEN_LEGACY_KEYS:
        return

    for forbidden_name in sorted(FORBIDDEN_LEGACY_KEYS):
        envelope = {key_name: forbidden_name, "nested": inner}
        assert validate_no_forbidden_keys(envelope) is None
