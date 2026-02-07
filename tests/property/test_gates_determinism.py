"""Property-based tests for gate conclusion mapping determinism."""

import pytest
from hypothesis import given, settings, strategies as st

from spec_kitty_events.gates import (
    UnknownConclusionError,
    _CONCLUSION_MAP,
    map_check_run_conclusion,
)

KNOWN_CONCLUSIONS = list(_CONCLUSION_MAP.keys())


class TestMappingDeterminism:
    """Verify mapping is deterministic via property-based testing."""

    @settings(deadline=None)
    @given(conclusion=st.sampled_from(KNOWN_CONCLUSIONS))
    def test_same_input_same_output(self, conclusion: str) -> None:
        """Same conclusion always produces same result."""
        result1 = map_check_run_conclusion(conclusion)
        result2 = map_check_run_conclusion(conclusion)
        assert result1 == result2

    @settings(deadline=None)
    @given(conclusion=st.sampled_from(KNOWN_CONCLUSIONS))
    def test_all_known_produce_valid_result(self, conclusion: str) -> None:
        """All known conclusions produce GatePassed, GateFailed, or None."""
        result = map_check_run_conclusion(conclusion)
        assert result in ("GatePassed", "GateFailed", None)

    @settings(deadline=None)
    @given(
        conclusion=st.text(min_size=1).filter(
            lambda s: s not in KNOWN_CONCLUSIONS
        )
    )
    def test_unknown_always_raises(self, conclusion: str) -> None:
        """Unknown conclusions always raise UnknownConclusionError."""
        with pytest.raises(UnknownConclusionError):
            map_check_run_conclusion(conclusion)


class TestConclusionMapCompleteness:
    """Verify the conclusion map covers all documented GitHub values."""

    def test_covers_all_github_values(self) -> None:
        expected = {
            "success", "failure", "timed_out", "cancelled",
            "action_required", "neutral", "skipped", "stale",
        }
        assert set(_CONCLUSION_MAP.keys()) == expected

    def test_exactly_eight_conclusions(self) -> None:
        assert len(_CONCLUSION_MAP) == 8

    def test_one_passed_conclusion(self) -> None:
        passed = [k for k, v in _CONCLUSION_MAP.items() if v == "GatePassed"]
        assert passed == ["success"]

    def test_four_failed_conclusions(self) -> None:
        failed = sorted(k for k, v in _CONCLUSION_MAP.items() if v == "GateFailed")
        assert failed == ["action_required", "cancelled", "failure", "timed_out"]

    def test_three_ignored_conclusions(self) -> None:
        ignored = sorted(k for k, v in _CONCLUSION_MAP.items() if v is None)
        assert ignored == ["neutral", "skipped", "stale"]
