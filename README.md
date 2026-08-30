# spec-kitty-events

Canonical event contracts for Spec Kitty mission state, mission runtime, conformance, and replay.

**Package Version**: `9.1.4` | **Envelope Schema Version**: `3.0.0` | **Python**: `>=3.10`

## What Changed In 8.0.0

`8.0.0` deletes the offline sync/replay surfaces:
`spec_kitty_events.sync`, `spec_kitty_events.legacy`
(`legacy_envelope_v1`), and `spec_kitty_events.cutover`
(`CUTOVER_ARTIFACT`). Only `.sync` had no consumers left: `.cutover`
and `.legacy` are still imported by `spec-kitty-saas`'s `apps/sync`
adapters (inert today only because that repo pins `==6.1.0`;
`apps/sync` itself is deleted by epic E6) and by `spec-kitty`'s
consumer-contract test suite — both repos must drop or port those
imports before pinning `==8.0.0`. One
behaviour change rides along: `validate_event()` no longer applies the
envelope-level cutover gate (missing/wrong `schema_version`, forbidden
legacy names) — fail-closed envelope gating lives in
`spec_kitty_events.strict.validate_strict_envelope`. Pin `>=8.0.0`; see
`COMPATIBILITY.md` and `CHANGELOG.md` for the full list.

## What Changed In 7.0.0

`7.0.0` publishes `spec_kitty_events.strict.validate_strict_envelope`, an
opt-in, deterministic, structured validator (`STRICT_PROFILE_ID =
"journal/v1"`) layered over the existing envelope and lifecycle/WP
contracts, plus the new `spec_kitty_events.harness_observation` module: a
volatile `HarnessObservation` event family with exactly six payload IDs
(`ObservationKind`: `presence`, `lane_signal`, `focus_started`,
`focus_heartbeat`, `focus_paused`, `focus_ended`). Five lifecycle payloads
(`MissionStarted`, `MissionCompleted`, `MissionCancelled`, `PhaseEntered`,
`ReviewRollback`) are hardened to `extra="forbid"`; `MissionStarted`,
`MissionCompleted`, and `PhaseEntered` gain an optional `mission_slug`
field first, so the real spec-kitty producer's current output stays valid.
See `COMPATIBILITY.md` for the full skew story and migration posture.

## What Changed In 5.0.0

`5.0.0` is a fail-closed TeamSpace migration contract release. The package
major version is `5.0.0`; the on-wire envelope schema remains
`schema_version="3.0.0"`.

- Mission identity fields are canonicalized to `mission_slug`, `mission_number`, and `mission_type`.
- Event envelopes require `build_id` and use the cutover signal `schema_version="3.0.0"`.
- Live ingestion is fail-closed. There are no runtime compatibility aliases for legacy mission-domain fields.
- Legacy mission-domain keys, names, and aggregate prefixes such as `feature_slug`, `feature_number`, `mission_key`, `legacy_aggregate_id`, `FeatureCreated`, `FeatureClosed`, and `aggregate_id="feature/…"` are rejected on live paths (the strict profile; see `COMPATIBILITY.md`).
- `in_review` is part of the canonical lane vocabulary.
- The conformance package includes historical-shape fixtures for TeamSpace migration dry-runs.

See `COMPATIBILITY.md` for the exact fail-closed rollout policy.

## Installation

From PyPI:

```bash
pip install "spec-kitty-events==5.0.0"
```

With conformance validation support:

```bash
pip install "spec-kitty-events[conformance]==5.0.0"
```

Development install:

```bash
git clone https://github.com/Priivacy-ai/spec-kitty-events.git
cd spec-kitty-events
pip install -e ".[dev,conformance]"
```

Or, with [uv](https://docs.astral.sh/uv/), install the exact versions pinned by the committed `uv.lock` — what CI and `make test-fast`/`make test-full` resolve against. If `pyproject.toml` changes, re-run `uv lock` and commit the updated file (`uv sync --locked` fails on a stale lock):

```bash
uv sync --locked --extra dev --extra conformance
```

## Contract Highlights

- `Event` is the canonical top-level envelope.
- `build_id` identifies the build that emitted the envelope.
- `node_id` identifies the emitting node within that build.
- `schema_version` is the on-wire compatibility signal. Live envelopes must use `3.0.0` for this release.
- `StatusTransitionPayload` uses `mission_slug` for mission identity and accepts `in_review`.
- Mission catalog payloads use `mission_slug`, `mission_number`, and `mission_type`.
- Mission runtime payloads use `mission_type`; they do not accept `mission_key`.

## Quick Start

### Emit a Canonical Event Envelope

```python
import uuid
from datetime import datetime

from spec_kitty_events import Event

event = Event(
    event_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
    event_type="WPStatusChanged",
    aggregate_id="mission/WP01",
    payload={
        "mission_slug": "mission-001",
        "wp_id": "WP01",
        "from_lane": "planned",
        "to_lane": "claimed",
        "actor": "ci-bot",
        "execution_mode": "worktree",
    },
    timestamp=datetime.now(),
    build_id="build-2026-04-05",
    node_id="runner-01",
    lamport_clock=1,
    project_uuid=uuid.uuid4(),
    correlation_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
    schema_version="3.0.0",
)
```

### Validate a Payload Against the Canonical Contract

```python
from spec_kitty_events.conformance import validate_event

payload = {
    "mission_slug": "mission-001",
    "wp_id": "WP01",
    "from_lane": "planned",
    "to_lane": "claimed",
    "actor": "ci-bot",
    "execution_mode": "worktree",
}

result = validate_event(payload, "WPStatusChanged")
assert result.valid
```

### Validate a Full Envelope

Build the envelope, then validate it:

```python
from spec_kitty_events.conformance import validate_event

envelope = {
    "event_id": "01ARZ3NDEKTSV4RRFFQ69G5FAV",
    "event_type": "WPStatusChanged",
    "aggregate_id": "mission/WP01",
    "timestamp": "2026-04-05T12:00:00Z",
    "build_id": "build-2026-04-05",
    "node_id": "runner-01",
    "lamport_clock": 1,
    "project_uuid": "12345678-1234-5678-1234-567812345678",
    "project_slug": None,
    "correlation_id": "01ARZ3NDEKTSV4RRFFQ69G5FAV",
    "causation_id": None,
    "schema_version": "3.0.0",
    "data_tier": 0,
    "payload": {
        "mission_slug": "mission-001",
        "wp_id": "WP01",
        "from_lane": "planned",
        "to_lane": "claimed",
        "actor": "ci-bot",
        "execution_mode": "worktree",
    },
}

result = validate_event(envelope, "WPStatusChanged", strict=True)
assert result.valid
```

For fail-closed envelope gating (`schema_version == "3.0.0"`, full key
set, recursive forbidden-key walk), use the strict profile —
`validate_event` does not enforce it itself (the example above carries
all 14 `STRICT_ENVELOPE_KEYS`, so the strict-profile check below also
passes):

```python
from spec_kitty_events.strict import validate_strict_envelope

errors = validate_strict_envelope(envelope)
assert not errors
```

## Schemas And Conformance

- Committed JSON Schemas are generated from the canonical Pydantic models.
- Replay streams and golden reducer outputs ship in the package.
- Conformance validation combines Pydantic validation and committed JSON Schemas; the opt-in strict profile adds fail-closed envelope gating.

Run the drift and conformance gates:

```bash
python -m spec_kitty_events.schemas.generate --check
pytest --pyargs spec_kitty_events.conformance -v
```

## Public Guidance

- Use `mission_slug`, `mission_number`, and `mission_type` in public mission-domain payloads.
- Use `build_id` to identify the emitting build and `node_id` to identify the emitting node.
- Do not rely on runtime translation of legacy mission-domain fields.
- Use offline rewrite or migration jobs if you need to transform historical pre-cutover data.

## Local-Only Event Classification (`LOCAL_ONLY_EVENT_TYPES`)

`spec_kitty_events.LOCAL_ONLY_EVENT_TYPES` is a machine-readable
`frozenset[str]` published so downstream consumers (CLI canonical-producer
lint, SaaS adapter) can identify event types that are NOT routed through
the SaaS-bound producer path.

```python
from spec_kitty_events import LOCAL_ONLY_EVENT_TYPES

# Currently empty: every CLI-emitted event audited as of spec-kitty 43305c12c
# routes through SpecKittyEventEmitter._emit() (the SaaS-bound central path).
assert LOCAL_ONLY_EVENT_TYPES == frozenset()
```

Future event types that don't cross the SaaS boundary can be classified by
adding them to this set; consumers do not need to re-ship a contract or
update their lint exemption files.

Mission: `canonical-producer-contracts-legacy-envelope-01KS7JM3`.

## Versioning

This package now publishes the TeamSpace migration release as package `5.0.0`.

- `2.x` documentation and mixed-field operation are no longer the public contract.
- Consumers should treat the strict profile, recursive forbidden-key helper, and committed fixtures as the authoritative compatibility surface.
- The envelope schema version intentionally remains `3.0.0`.

## License

All rights reserved. This repository is owned by Priivacy AI.
