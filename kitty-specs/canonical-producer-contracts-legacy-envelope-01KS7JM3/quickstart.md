# Quickstart: New `spec-kitty-events` surfaces

## Audience

Authors of:

- The Phase 2 CLI producer refactor (`spec-kitty#1200`).
- The Phase 3 SaaS legacy-envelope adapter (`spec-kitty-saas#274`).
- Future tooling that needs to validate or normalize Spec Kitty events.

## 1. Validating a `WPStatusChanged` event now enforces transition rules

Before this mission:

```python
from spec_kitty_events.conformance.validators import validate_event

payload = {
    "wp_id": "WP09",
    "from_lane": "in_review",
    "to_lane": "planned",
    "actor": "user",
    "force": False,                                 # invalid: review-rejection requires force=True
    "reason": "rejected on review",
    "execution_mode": "worktree",
    "mission_slug": "demo",
    "review_ref": "feedback://demo/WP09/2026-05-18-review.md",
    "evidence": None,
}
result = validate_event(payload, "WPStatusChanged")
result.valid  # → True (the shape parses, but the lane rule wasn't enforced)
```

After this mission:

```python
result = validate_event(payload, "WPStatusChanged")
result.valid  # → False
# result.model_violations contains a ModelViolation whose message reads:
# "review-rejection rollback in_review -> planned requires force=True"
# Consumers can route on substrings "force=True" and "review-rejection".
```

The forced, valid form continues to pass:

```python
payload["force"] = True
payload["reason"] = "rejected on review"
result = validate_event(payload, "WPStatusChanged")
result.valid  # → True
```

## 2. Normalizing a legacy envelope

```python
from spec_kitty_events.legacy import LegacyEnvelopeNormalizer, NormalizedEnvelope, UnnormalizableLegacyDiagnostic
from spec_kitty_events.conformance.validators import validate_event

raw = {
    "event_id": "01J0000000000000000000F001",
    "event_type": "MissionCreated",
    "aggregate_id": "mission/01J0000000000000000000MS1",
    "payload": {
        "mission_slug": "fixture-mission",
        "mission_number": 1,
        "mission_type": "software-dev",
        "target_branch": "main",
        "wp_count": 3,
        "friendly_name": "Fixture Mission",
        "purpose_tldr": "Pinned canonical baseline.",
        "purpose_context": "Pre-3.0 envelope missing project_uuid.",
    },
    "timestamp": "2026-01-01T00:00:00+00:00",
    "build_id": "build-2026-01-01-fixture",
    "node_id": "fixture-node",
    "lamport_clock": 1,
    "correlation_id": "01J0000000000000000000CR01",
    # NOTE: no project_uuid, no schema_version — pre-3.0 envelope shape
}

normalizer = LegacyEnvelopeNormalizer()
result = normalizer.normalize(raw)

match result:
    case NormalizedEnvelope(canonical=canonical, raw=raw_dict, legacy_shape=shape):
        # shape == "pre_3_0_envelope"
        # canonical has project_uuid minted via uuid5 over (node_id, build_id)
        # canonical has schema_version="3.0.0"
        conformance = validate_event(canonical, canonical["event_type"], strict=True)
        if conformance.valid:
            materialize(canonical)
            retain_raw_for_audit(raw_dict, shape)
        else:
            classify_as_legacy_business_rule(conformance, raw_dict)

    case UnnormalizableLegacyDiagnostic(reason=reason, shape_hints=hints, raw=raw_dict):
        # reason ∈ {"pre_3_0_envelope_missing_identity", "unrecognized_legacy_shape", ...}
        # Classify as legacy/business-rule diagnostic, never as infra-failed.
        emit_legacy_diagnostic(reason, hints, raw_dict)
```

## 3. Constructing the seven previously-uncontracted events via canonical models

Phase 2 producer refactor target:

```python
from spec_kitty_events.project_lifecycle import (
    WPAssignedPayload,
    HistoryAddedPayload,
    ErrorLoggedPayload,
    DependencyResolvedPayload,
)
from spec_kitty_events.build_lifecycle import (
    BuildRegisteredPayload,
    BuildHeartbeatPayload,
)
from spec_kitty_events.lifecycle import MissionOriginBoundPayload

# Build the payload through the canonical model — extra="forbid" catches field drift at construction time.
payload = WPAssignedPayload(
    wp_id="WP01",
    agent_id="claude",
    phase="implement",
    retry_count=0,
).model_dump(mode="json")

self._emit(
    event_type="WPAssigned",
    aggregate_id="WP01",
    aggregate_type="WorkPackage",
    payload=payload,
)
```

`extra="forbid"` ensures the producer cannot accidentally pass legacy fields; `frozen=True` ensures the payload is immutable after construction. The `_EVENT_TYPE_TO_MODEL` entry means `validate_event("WPAssigned", payload)` works against the wire envelope.

## 4. Inspecting `LOCAL_ONLY_EVENT_TYPES`

```python
from spec_kitty_events import LOCAL_ONLY_EVENT_TYPES

# In this mission: empty. All seven previously-uncontracted events are SaaS-bound.
assert LOCAL_ONLY_EVENT_TYPES == frozenset()

# Phase 2/3 may add entries when a future event type is classified as local-only.
# The CLI canonical-producer lint will consult this set to know which event types
# do not require canonical-builder construction at the SaaS boundary.
```
