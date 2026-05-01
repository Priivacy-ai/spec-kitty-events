"""Performance benchmark for envelope validation (NFR-005).

Asserts that the p95 wall-clock cost of validating a representative envelope
sits comfortably under 5.0 ms on a developer laptop. The benchmark composes
the same public-surface validators that the conformance class taxonomy test
(``tests/test_conformance_classes.py``) uses, so the budget covers the
real cost a downstream caller pays:

* envelope shape check (object + required fields)
* recursive forbidden-key walk
  (``spec_kitty_events.forbidden_keys.find_forbidden_keys``)
* canonical lane vocabulary check
  (``spec_kitty_events.Lane`` + ``LANE_ALIASES``)
* typed payload-model validation
  (``MissionCreatedPayload``, ``MissionClosedPayload``,
  ``StatusTransitionPayload``)

Why compose vs. import a single ``validate_envelope`` entry point?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
The package does not yet expose a single ``validate_envelope`` symbol that
folds all of the layered checks together — each layer is its own public
helper. WP07 explicitly authorises composing the existing helpers so the
benchmark exercises the full validation cost end-to-end. If a future WP
adds a single envelope-level entry point, swap ``_validate_envelope`` for
the public function without changing the threshold.

Fixture sample
~~~~~~~~~~~~~~
The benchmark reads the WP05 class taxonomy fixture suite under
``src/spec_kitty_events/conformance/fixtures/class_taxonomy/`` and pulls
every fixture from the two ``valid`` classes:

* ``envelope_valid_canonical/``
* ``envelope_valid_historical_synthesized/``

These are the shapes that successfully traverse all validation layers (the
worst case for a *successful* validation) and therefore give an honest p95
of "validate-and-accept" cost.

Threshold
~~~~~~~~~
NFR-005 budget: < 5.0 ms p95. In practice, on a developer laptop the p95
runs about an order of magnitude under the budget, leaving comfortable
headroom for shared CI. We deliberately keep the threshold generous so
this is a regression-detector, not a flaky timing test.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Iterable, List

import pytest

from pydantic import ValidationError as PydanticValidationError

from spec_kitty_events import (
    LANE_ALIASES,
    MISSION_CLOSED,
    MISSION_CREATED,
    MissionClosedPayload,
    MissionCreatedPayload,
    StatusTransitionPayload,
    WP_STATUS_CHANGED,
    Lane,
)
from spec_kitty_events.forbidden_keys import (
    FORBIDDEN_LEGACY_KEYS,
    find_forbidden_keys,
)
from spec_kitty_events.models import Event


_FIXTURES_ROOT = (
    Path(__file__).resolve().parents[1]
    / "src"
    / "spec_kitty_events"
    / "conformance"
    / "fixtures"
)
_CLASS_TAXONOMY_ROOT = _FIXTURES_ROOT / "class_taxonomy"

_BENCHMARK_CLASSES: tuple[str, ...] = (
    "envelope_valid_canonical",
    "envelope_valid_historical_synthesized",
)

_PAYLOAD_MODELS: dict[str, type] = {
    MISSION_CREATED: MissionCreatedPayload,
    MISSION_CLOSED: MissionClosedPayload,
    WP_STATUS_CHANGED: StatusTransitionPayload,
}

_REQUIRED_ENVELOPE_FIELDS: tuple[str, ...] = (
    "event_id",
    "event_type",
    "aggregate_id",
    "payload",
    "timestamp",
    "build_id",
    "node_id",
    "lamport_clock",
    "correlation_id",
    "project_uuid",
)

_CANONICAL_LANE_VALUES: frozenset[str] = frozenset(member.value for member in Lane)

_ITERATIONS_PER_FIXTURE: int = 100

# Generous laptop-friendly p95 budget (NFR-005 calls for < 5 ms).
_P95_BUDGET_MS: float = 5.0


def _validate_envelope(envelope: Any) -> bool:
    """Compose package-public validators and return ``True`` on success.

    Returns ``False`` (without raising) on any layered failure, matching the
    contract that ``test_conformance_classes.py`` exercises in detail. The
    benchmark only cares about wall-clock cost; it doesn't introspect the
    error path.
    """

    if not isinstance(envelope, dict):
        return False

    for field in _REQUIRED_ENVELOPE_FIELDS:
        if field not in envelope:
            return False

    if next(
        find_forbidden_keys(envelope, forbidden=FORBIDDEN_LEGACY_KEYS),
        None,
    ) is not None:
        return False

    payload = envelope["payload"]
    if not isinstance(payload, dict):
        return False

    event_type = envelope["event_type"]
    if event_type == WP_STATUS_CHANGED:
        for lane_field in ("from_lane", "to_lane"):
            value = payload.get(lane_field)
            if value is None:
                continue
            if not isinstance(value, str):
                return False
            if (
                value not in _CANONICAL_LANE_VALUES
                and value not in LANE_ALIASES
            ):
                return False

    # Real Event model validation — the public envelope SSOT.
    try:
        Event.model_validate(envelope)
    except PydanticValidationError:
        return False

    model = _PAYLOAD_MODELS.get(event_type)
    if model is not None:
        try:
            model(**payload)
        except Exception:
            return False

    return True


def _iter_benchmark_envelopes() -> Iterable[dict[str, Any]]:
    """Yield ``input`` envelopes from the class-taxonomy valid fixtures."""

    for cls in _BENCHMARK_CLASSES:
        cls_dir = _CLASS_TAXONOMY_ROOT / cls
        if not cls_dir.is_dir():
            continue
        for fixture_path in sorted(cls_dir.glob("*.json")):
            with fixture_path.open("r", encoding="utf-8") as fh:
                fixture = json.load(fh)
            if not isinstance(fixture, dict):
                continue
            envelope = fixture.get("input")
            if isinstance(envelope, dict):
                yield envelope


def _percentile(values: List[int], p: float) -> int:
    """Return the *p*-th percentile (linear nearest-rank) of *values*."""

    if not values:
        raise ValueError("percentile of empty sequence is undefined")
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    k = int(round((p / 100.0) * (len(ordered) - 1)))
    return ordered[k]


def _measure(envelope: dict[str, Any], iterations: int) -> List[int]:
    """Return per-iteration wall-clock costs in nanoseconds."""

    samples: List[int] = []
    for _ in range(iterations):
        t0 = time.perf_counter_ns()
        _validate_envelope(envelope)
        t1 = time.perf_counter_ns()
        samples.append(t1 - t0)
    return samples


@pytest.mark.benchmark
def test_envelope_validation_p95_under_5_ms() -> None:
    """NFR-005: composed envelope validation p95 < 5.0 ms on a dev laptop."""

    envelopes = list(_iter_benchmark_envelopes())
    assert envelopes, (
        "No benchmark envelopes loaded — expected fixtures under "
        f"{_CLASS_TAXONOMY_ROOT} for classes {_BENCHMARK_CLASSES!r}."
    )

    # Sanity-check that every benchmarked envelope actually validates. If a
    # fixture regresses to "invalid" the timings would no longer represent
    # the success path that NFR-005 budgets for.
    for envelope in envelopes:
        assert _validate_envelope(envelope), (
            f"Benchmark fixture failed validation: "
            f"event_type={envelope.get('event_type')!r}, "
            f"event_id={envelope.get('event_id')!r}"
        )

    # Warm-up: pay the model-class import / first-validation costs once
    # before measurement so they don't pollute p95.
    for envelope in envelopes:
        _validate_envelope(envelope)

    all_samples_ns: List[int] = []
    for envelope in envelopes:
        all_samples_ns.extend(_measure(envelope, _ITERATIONS_PER_FIXTURE))

    assert all_samples_ns, "no timing samples collected"

    p95_ns = _percentile(all_samples_ns, 95.0)
    p50_ns = _percentile(all_samples_ns, 50.0)
    p99_ns = _percentile(all_samples_ns, 99.0)

    p95_ms = p95_ns / 1_000_000
    p50_ms = p50_ns / 1_000_000
    p99_ms = p99_ns / 1_000_000

    assert p95_ms < _P95_BUDGET_MS, (
        f"NFR-005 envelope validation p95 budget violated: "
        f"p50={p50_ms:.4f}ms p95={p95_ms:.4f}ms p99={p99_ms:.4f}ms "
        f"(budget {_P95_BUDGET_MS:.1f}ms, "
        f"{len(envelopes)} fixtures × {_ITERATIONS_PER_FIXTURE} iters)"
    )
