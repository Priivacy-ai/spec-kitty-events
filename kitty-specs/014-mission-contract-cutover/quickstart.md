# Quickstart: Mission Contract Cutover

## Objective

Implement the `spec-kitty-events` breaking contract release with one authoritative cutover artifact, canonical mission/build terminology, explicit `build_id`, and strict fail-closed compatibility gating.

## Implementation order

1. Inspect the existing release-authority surfaces:
   - `/private/tmp/mission/spec-kitty-events/src/spec_kitty_events/conformance/fixtures/manifest.json`
   - `/private/tmp/mission/spec-kitty-events/src/spec_kitty_events/schemas/generate.py`
   - `/private/tmp/mission/spec-kitty-events/src/spec_kitty_events/conformance/validators.py`
2. Decide whether the existing manifest can fully encode the cutover policy. If not, add a dedicated packaged cutover artifact.
3. Update the canonical event envelope in `/private/tmp/mission/spec-kitty-events/src/spec_kitty_events/models.py` to require `build_id` while keeping `node_id` separate.
4. Rename mission-domain public fields across:
   - `/private/tmp/mission/spec-kitty-events/src/spec_kitty_events/lifecycle.py`
   - `/private/tmp/mission/spec-kitty-events/src/spec_kitty_events/mission_next.py`
   - `/private/tmp/mission/spec-kitty-events/src/spec_kitty_events/dossier.py`
   - `/private/tmp/mission/spec-kitty-events/src/spec_kitty_events/decisionpoint.py`
   - `/private/tmp/mission/spec-kitty-events/src/spec_kitty_events/mission_audit.py`
   - `/private/tmp/mission/spec-kitty-events/src/spec_kitty_events/status.py`
5. Introduce catalog `MissionCreated` and `MissionClosed`, and remove the runtime `MissionCompleted` alias path from mission-next.
6. Wire validators/helpers so `spec-kitty-events` enforces the cutover artifact for schema validation, conformance fixtures, and replay validation.
7. Regenerate schemas and fixtures, update `/private/tmp/mission/spec-kitty-events/README.md` and `/private/tmp/mission/spec-kitty-events/COMPATIBILITY.md`, and bump `/private/tmp/mission/spec-kitty-events/pyproject.toml` from `2.9.0` to `3.0.0`.

## Validation checklist

Run these during implementation before handoff:

```bash
pytest
mypy src/spec_kitty_events
python -m spec_kitty_events.schemas.generate
```

Required release validation beyond the commands above:

- Run the repo's conformance fixture validation and confirm the cutover artifact is enforced across valid and invalid fixtures.
- Run the repo's replay fixture validation and confirm canonical mission/build terminology plus fail-closed rejection rules hold for replay streams.
- If these validations are not already covered by `pytest`, invoke their dedicated entrypoints explicitly before considering the release candidate green.

## Release gate reminder

- `spec-kitty-events` owns the artifact and helper implementation.
- `spec-kitty-saas` and `spec-kitty` must enforce the same artifact semantics in their own runtime paths.
- No production rollout until all three repos are ready for the same contract version.

## Non-goals during implementation

- Do not add compatibility shims for legacy mission-domain payloads.
- Do not implement runtime consumer gates for `spec-kitty-saas` or `spec-kitty` in this repo.
- Do not treat local/dev as a special interoperability exception.
