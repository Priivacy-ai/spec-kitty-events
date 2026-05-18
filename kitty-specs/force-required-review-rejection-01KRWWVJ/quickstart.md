# Quickstart: Force-Required Review-Rejection Contract

This document is the operator-facing reproduction + verification guide
for the mission. Run from the repository root:
`/Users/robert/spec-kitty-dev/spec-kitty-20260518-082805-q0Lu7J/spec-kitty-events`.

## 1. Reproduce the bug (pre-fix)

Run the snippet from `start-here.md` Phase 1:

```bash
uv run python - <<'PY'
from spec_kitty_events.status import (
    StatusTransitionPayload, Lane, ExecutionMode, validate_transition
)

payload = StatusTransitionPayload(
    mission_slug="m",
    wp_id="WP01",
    from_lane=Lane.IN_REVIEW,
    to_lane=Lane.PLANNED,
    actor="user",
    execution_mode=ExecutionMode.WORKTREE,
    force=False,
    reason="review rejected",
    review_ref="feedback://m/WP01/review.md",
)
result = validate_transition(payload)
print(result.valid, result.violations)
PY
```

**Pre-fix expected output**: `True ()`.
This is the bug — an unforced rollback with `review_ref` present is
accepted.

## 2. Apply the fix (work-package execution)

Run `/spec-kitty.tasks` to materialize the work packages, then
`/spec-kitty.implement` to execute them. The fix lands in
`src/spec_kitty_events/status.py` along with fixture and doc updates
under `src/spec_kitty_events/conformance/`,
`docs/consumer-contract-dossier-v2.4.0.md`, and
`tests/unit/`.

## 3. Verify (post-fix)

Re-run the reproduction snippet from §1. Expected output:

```
False  ('review-rejection rollback in_review -> planned requires force=True', ...)
```

The exact tuple may contain additional violations from unrelated
guards depending on payload contents; the contract is that the
violation string containing both `force=True` and `review-rejection`
is present.

## 4. Run the test commands from `start-here.md`

```bash
uv run pytest \
  tests/unit/test_status.py::TestReviewRejectionFamily \
  tests/unit/test_fixtures.py::TestEdgeCaseFixtures -q

uv run pytest tests/unit/test_status.py tests/unit/test_fixtures.py -q
```

Both must exit 0.

## 5. Optional package release

This mission does not publish the package. If the operator decides to
ship `5.1.1`:

```bash
# from repository root, AFTER all tests pass on main
git tag spec-kitty-events-5.1.1
git push origin spec-kitty-events-5.1.1
# CI publishes; record version + SHA in tracker comments for #32/#29/#31.
```

## 6. Issue closure (after merge to main)

- Close `spec-kitty-events#32` with a comment quoting the violation
  string and linking the merged PR.
- Close `#29` as resolved by `#32`.
- Close `#31` as superseded by `#32`.

## 7. Coordination with downstream

The CLI (`spec-kitty`) and SaaS (`spec-kitty-saas`) are downstream
consumers that already classify unforced rollbacks as
business-rule-rejections (per spec §C-004). No change is required in
those repositories as part of this mission. Their next dependency bump
will pick up the corrected runtime behavior; that bump is part of the
operator's Phase 2/3 sequencing.
