---
affected_files: []
cycle_number: 2
mission_slug: decision-moment-v1-contract-freeze-01KPWA0N
reproduction_command:
reviewed_at: '2026-04-23T06:25:06Z'
reviewer_agent: unknown
verdict: rejected
wp_id: WP07
---

# WP07 Review — Cycle 1

**Verdict: Changes requested — send back to planned**

WP07's own deliverables (version bump, re-exports, CHANGELOG, COMPATIBILITY, test_schemas fix) are all correctly implemented and pass. However, 3 tests are failing that must be green before WP07 can be approved.

---

## Issue 1 (BLOCKER): WP06 reducer fix dropped by lane-c merge

**Test failures:**
- `tests/integration/test_lifecycle_replay.py::test_v1_golden_replay_byte_identical[replay_interview_deferred]`
- `tests/integration/test_lifecycle_replay.py::test_v1_golden_replay_byte_identical[replay_interview_canceled]`

**Root cause:** The `DecisionPointResolvedInterviewPayload` branch of the reducer in `src/spec_kitty_events/decisionpoint.py` is missing `last_rationale = payload.rationale`. This line was correctly added by WP06 in commit `fb88002` but was wiped out by the subsequent `f765e83` merge (lane-c into lane-g), which resolved a conflict by choosing the WP02 version of the reducer (without the fix) instead of the WP06-patched version.

**What to fix:** In `src/spec_kitty_events/decisionpoint.py`, inside the `elif isinstance(payload, DecisionPointResolvedInterviewPayload):` branch (currently around line 898), add after the `last_state_entered_at` line:

```python
last_rationale = payload.rationale  # may be None for terminal=resolved; required for deferred/canceled
```

This is exactly what lane-f (WP06) has at line 906. Verify with:
```
grep -n "last_rationale = payload.rationale" /Users/robert/spec-kitty-dev/spec-kitty-20260423-061619/spec-kitty-events/.worktrees/decision-moment-v1-contract-freeze-01KPWA0N-lane-f/src/spec_kitty_events/decisionpoint.py
```
Lane-f has 5 hits; lane-g currently only has 4 (missing the one in the interview-Resolved branch).

**After the fix, verify:**
```
python - <<'PY'
import json, pathlib
from spec_kitty_events.models import Event
from spec_kitty_events.decisionpoint import reduce_decision_point_events
for name in ("replay_interview_deferred", "replay_interview_canceled"):
    events = [Event.model_validate_json(l) for l in pathlib.Path(f"tests/fixtures/decisionpoint_golden/{name}.jsonl").read_text().splitlines() if l.strip()]
    reduced = reduce_decision_point_events(events)
    actual = json.dumps(reduced.model_dump(mode="json", by_alias=True), sort_keys=True, indent=2)
    expected = pathlib.Path(f"tests/fixtures/decisionpoint_golden/{name}_output.json").read_text().rstrip()
    print(name, "MATCH" if actual == expected else "MISMATCH")
PY
```

---

## Issue 2 (BLOCKER): 6 new conformance fixture files missing from manifest.json

**Test failure:**
- `tests/unit/test_fixtures.py::TestManifest::test_every_fixture_file_has_manifest_entry`

**Root cause:** WP05 and WP06 added 6 new `_output.json` files under `src/spec_kitty_events/conformance/fixtures/decisionpoint/replay/` but did not register them in `src/spec_kitty_events/conformance/fixtures/manifest.json`. These files are:
- `decisionpoint/replay/replay_interview_canceled_output.json`
- `decisionpoint/replay/replay_interview_deferred_output.json`
- `decisionpoint/replay/replay_interview_local_only_resolved_output.json`
- `decisionpoint/replay/replay_interview_resolved_other_output.json`
- `decisionpoint/replay/replay_interview_widened_closed_locally_output.json`
- `decisionpoint/replay/replay_interview_widened_resolved_output.json`

**What to fix:** Add each of these 6 files to the `fixtures` array in `src/spec_kitty_events/conformance/fixtures/manifest.json` with the correct schema category (same format as the existing `decisionpoint/replay/decisionpoint_full_lifecycle_output.json` entry).

This fix is within WP07's "full-suite smoke" responsibility and is a minor addition. The implementer may add it to the existing WP07 commit or as a separate commit.

---

## WP07's own deliverables (all passing)

- `pyproject.toml` version: `4.0.0` — correct
- All 21 V1 symbols importable from `spec_kitty_events` — correct
- All 21 V1 symbols in `__all__` — correct
- `CHANGELOG.md` has `## 4.0.0 — 2026-04-23` with all required subsections — correct
- `COMPATIBILITY.md` has `## Decision Moment V1 (4.0.0)` block — correct
- `tests/unit/test_schemas.py::test_list_schemas_returns_all_names` — passing
- WP07 commit only touches owned files plus `tests/unit/test_schemas.py` — correct

**Total test count:** 3 failed, 1777 passed (vs. pre-existing baseline of 15 failures per WP06 cycle-1 — WP07 brought it down to 3 but the 3 are all blockers).

---

## How to re-implement

1. Apply the one-line fix to `src/spec_kitty_events/decisionpoint.py` (add `last_rationale = payload.rationale` in the `DecisionPointResolvedInterviewPayload` branch).
2. Update `src/spec_kitty_events/conformance/fixtures/manifest.json` to register the 6 new `decisionpoint/replay/replay_interview_*_output.json` files.
3. Run `pytest tests/ -q` and confirm 0 failures (or confirm only pre-existing failures that are irrelevant to this mission).
