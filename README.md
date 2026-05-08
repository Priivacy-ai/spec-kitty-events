# spec-kitty-events

Canonical event contracts for Spec Kitty mission state, mission runtime, conformance, and replay.

**Package Version**: `5.0.0` | **Cutover Contract**: `3.0.0` | **Python**: `>=3.10`

## What Changed In 5.0.0

`5.0.0` is a fail-closed TeamSpace migration contract release. The package
major version is `5.0.0`; the on-wire envelope schema remains
`schema_version="3.0.0"`.

- Mission identity fields are canonicalized to `mission_slug`, `mission_number`, and `mission_type`.
- Event envelopes require `build_id` and use the cutover signal `schema_version="3.0.0"`.
- Live ingestion is fail-closed. There are no runtime compatibility aliases for legacy mission-domain fields.
- Legacy mission-domain keys and names such as `feature_slug`, `feature_number`, `mission_key`, `legacy_aggregate_id`, `FeatureCreated`, and `FeatureClosed` are rejected on live paths.
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

### Validate a Full Envelope With Fail-Closed Cutover Checks

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
    "correlation_id": "01ARZ3NDEKTSV4RRFFQ69G5FAV",
    "schema_version": "3.0.0",
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

## Schemas And Conformance

- Committed JSON Schemas are generated from the canonical Pydantic models.
- Replay streams and golden reducer outputs ship in the package.
- Conformance validation combines Pydantic validation, committed JSON Schemas, and cutover artifact checks.

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

## Versioning

This package now publishes the TeamSpace migration release as package `5.0.0`.

- `2.x` documentation and mixed-field operation are no longer the public contract.
- Consumers should treat the cutover artifact, recursive forbidden-key helper, and committed fixtures as the authoritative compatibility surface.
- The envelope schema version intentionally remains `3.0.0`.

## License

All rights reserved. This repository is owned by Priivacy AI.
