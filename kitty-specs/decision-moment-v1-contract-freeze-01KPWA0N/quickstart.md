# Quickstart — Decision Moment V1 Contract Freeze

Hands-on walkthrough for anyone implementing or reviewing the `spec-kitty-events 4.0.0` Decision Moment contract. Assumes a checkout at the repo root (`spec-kitty-events/`).

## 1. Install the dev environment

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev,conformance]"
```

## 2. Run the existing test suite (baseline)

```bash
pytest
```

Expect green on 3.3.0 before any V1 changes. Record the wall time; V1 must not regress suite runtime more than ~10 percent.

## 3. Regenerate schemas after model changes

The Python Pydantic models in `src/spec_kitty_events/decisionpoint.py` and `src/spec_kitty_events/collaboration.py` are the source of truth. Regenerate committed JSON Schemas after any model change:

```bash
python -m spec_kitty_events.schemas.generate
```

Then run the drift check:

```bash
pytest tests/integration/test_schema_drift.py -q
```

Zero diff is required.

## 4. Validate a V1 Decision Moment event by hand

Once the V1 models land, you can validate payloads directly against committed schemas via the `conformance` extra:

```bash
python - <<'PY'
import json, pathlib
import jsonschema

schemas = pathlib.Path("src/spec_kitty_events/schemas")
schema = json.loads((schemas / "decision_point_opened_payload.schema.json").read_text())

interview_opened = {
    "origin_surface": "planning_interview",
    "origin_flow": "specify",
    "decision_point_id": "01JA2B3C4D5E6F7G8H9J0K1L2M",
    "mission_id": "01JA0000000000000000000000",
    "run_id": "01JA1111111111111111111111",
    "mission_slug": "my-feature-01JA0000",
    "mission_type": "software-dev",
    "phase": "P1",
    "question": "Which auth strategy should we use?",
    "options": ["session", "oauth2", "oidc", "Other"],
    "input_key": "auth_strategy",
    "step_id": "specify.q3",
    "actor_id": "participant_abc",
    "actor_type": "human",
    "state_entered_at": "2026-04-23T10:00:00+00:00",
    "recorded_at": "2026-04-23T10:00:00+00:00",
}
jsonschema.validate(interview_opened, schema)
print("OK: interview Opened validates against 4.0.0 schema.")
PY
```

## 5. Replay a golden fixture and assert byte-identical output

Assuming a golden pair `replay_interview_widened_resolved.jsonl` + `replay_interview_widened_resolved_output.json` exists:

```bash
python - <<'PY'
import json, pathlib
from spec_kitty_events import models
from spec_kitty_events.decisionpoint import reduce_decision_point_events

fixtures = pathlib.Path("tests/fixtures/decisionpoint_golden")
events_file = fixtures / "replay_interview_widened_resolved.jsonl"
expected_file = fixtures / "replay_interview_widened_resolved_output.json"

events = [models.Event.model_validate_json(line) for line in events_file.read_text().splitlines() if line.strip()]
reduced = reduce_decision_point_events(events)

actual = reduced.model_dump(mode="json", by_alias=True)
expected = json.loads(expected_file.read_text())
assert json.dumps(actual, sort_keys=True) == json.dumps(expected, sort_keys=True), "Replay output drifted"
print("OK: widened→resolved replay reproduces golden output byte-identically.")
PY
```

## 6. Run only DecisionPoint-related tests

```bash
pytest tests/unit/test_decisionpoint.py \
       tests/test_decisionpoint_conformance.py \
       tests/test_decisionpoint_reducer.py \
       tests/property/test_decisionpoint_determinism.py \
       tests/integration/test_lifecycle_replay.py \
       -q
```

## 7. Confirm type strictness

```bash
mypy --strict src/spec_kitty_events
```

Zero errors required.

## 8. Upgrading a 3.x producer to 4.0.0

If your code emits `DecisionPointOpened` today with the ADR shape, add `origin_surface="adr"` to the payload. No other changes required. Example diff:

```python
# before (3.x)
payload = DecisionPointOpenedPayload(
    decision_point_id=did,
    mission_id=mid,
    ...
)

# after (4.0.0)
payload = DecisionPointOpenedAdrPayload(
    origin_surface=OriginSurface.ADR,
    decision_point_id=did,
    mission_id=mid,
    ...
)
```

If you emit interview-origin Decision Moments (new in V1), use `DecisionPointOpenedInterviewPayload` with `origin_surface=OriginSurface.PLANNING_INTERVIEW`, `origin_flow`, `question`, `options`, `input_key`, `step_id`.

## 9. Upgrading a 3.x DecisionInput consumer

No changes required. `DecisionInputRequested` and `DecisionInputAnswered` retain 3.x-compatible shapes. Be aware: `DecisionInputAnswered` is not emitted when `terminal_outcome ∈ {deferred, canceled}`.

## 10. Release checklist (for the mission owner)

- [ ] `pytest` green locally and in CI
- [ ] `mypy --strict src/spec_kitty_events` clean
- [ ] `tests/integration/test_schema_drift.py` passes (no uncommitted regen diff)
- [ ] All six golden replay fixtures present and passing
- [ ] All four invalid conformance fixtures present and rejected
- [ ] `CHANGELOG.md` has a `## 4.0.0` section documenting the contract boundary
- [ ] `COMPATIBILITY.md` has a `Decision Moment V1 (4.0.0)` block
- [ ] `pyproject.toml` version bumped to `4.0.0`
- [ ] `DECISIONPOINT_SCHEMA_VERSION` constant bumped to `3.0.0`
