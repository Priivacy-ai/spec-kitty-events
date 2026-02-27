# Quickstart: Mission Audit Lifecycle Contracts

## Installation

```bash
pip install "spec-kitty-events>=2.5.0"
```

## 1. Emit a Complete Audit Lifecycle

```python
from spec_kitty_events import (
    Event,
    MISSION_AUDIT_REQUESTED,
    MISSION_AUDIT_STARTED,
    MISSION_AUDIT_COMPLETED,
    MISSION_AUDIT_FAILED,
    MissionAuditRequestedPayload,
    MissionAuditStartedPayload,
    MissionAuditCompletedPayload,
    MissionAuditFailedPayload,
    AuditArtifactRef,
    AuditVerdict,
    AuditSeverity,
)
from spec_kitty_events.dossier import ContentHashRef, ProvenanceRef

# --- Step 1: Request an audit ---
requested = MissionAuditRequestedPayload(
    mission_id="mission-42",
    run_id="run-001",
    feature_slug="010-mission-audit",
    actor="agent-claude",
    trigger_mode="post_merge",
    audit_scope=["spec.md", "plan.md", "data-model.md"],
    enforcement_mode="blocking",
)

# --- Step 2: Mark audit started ---
started = MissionAuditStartedPayload(
    mission_id="mission-42",
    run_id="run-001",
    feature_slug="010-mission-audit",
    actor="agent-claude",
    audit_scope_hash="sha256:a1b2c3d4e5f6",
)

# --- Step 3a: Complete with pass verdict (artifact_ref is REQUIRED) ---
completed = MissionAuditCompletedPayload(
    mission_id="mission-42",
    run_id="run-001",
    feature_slug="010-mission-audit",
    actor="agent-claude",
    verdict=AuditVerdict.PASS,
    severity=AuditSeverity.INFO,
    findings_count=0,
    artifact_ref=AuditArtifactRef(
        report_path="audits/mission-42/run-001/report.json",
        content_hash=ContentHashRef(
            hash="sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            algorithm="sha256",
            size_bytes=4096,
            encoding="utf-8",
        ),
        provenance=ProvenanceRef(
            source_event_ids=["evt-001", "evt-002"],
            git_sha="abc123def456",
            git_ref="refs/heads/main",
            actor_id="agent-claude",
            actor_kind="agent",
            revised_at="2026-02-25T16:30:00Z",
        ),
    ),
    summary="All checks passed. No findings.",
)

# --- Step 3b: Or fail (partial_artifact_ref is Optional) ---
failed = MissionAuditFailedPayload(
    mission_id="mission-42",
    run_id="run-001",
    feature_slug="010-mission-audit",
    actor="agent-claude",
    error_code="TIMEOUT",
    error_message="Audit timed out after 300s",
    partial_artifact_ref=None,  # Optional — may include partial report if available
)

# Wrap in Event envelopes (your event infrastructure handles this):
# event = Event(event_type=MISSION_AUDIT_COMPLETED, payload=completed.model_dump(), ...)
```

## 2. Reduce Audit Events to State

```python
from spec_kitty_events import (
    reduce_mission_audit_events,
    AuditStatus,
    AuditVerdict,
)

# Given a list of Event objects from your event store:
state = reduce_mission_audit_events(events)

# Inspect the reduced state
assert state.audit_status == AuditStatus.COMPLETED
assert state.verdict == AuditVerdict.PASS
assert state.artifact_ref is not None
assert state.artifact_ref.report_path == "audits/mission-42/run-001/report.json"
assert state.findings_count == 0
assert state.event_count == 3  # Requested + Started + Completed
assert len(state.anomalies) == 0
assert len(state.pending_decisions) == 0
```

## 3. Validate with Conformance Suite

```python
from spec_kitty_events.conformance.validators import validate_event

# Validate a raw payload dict against the canonical schema
result = validate_event(
    payload={
        "mission_id": "mission-42",
        "run_id": "run-001",
        "feature_slug": "010-mission-audit",
        "actor": "agent-claude",
        "trigger_mode": "post_merge",
        "audit_scope": ["spec.md"],
        "enforcement_mode": "blocking",
    },
    event_type="MissionAuditRequested",
)
assert result.valid

# Invalid payload: missing required artifact_ref
result = validate_event(
    payload={
        "mission_id": "mission-42",
        "run_id": "run-001",
        "feature_slug": "010-mission-audit",
        "actor": "agent-claude",
        "verdict": "pass",
        "severity": "info",
        "findings_count": 0,
        "summary": "All passed",
        # artifact_ref intentionally missing — will fail validation
    },
    event_type="MissionAuditCompleted",
)
assert not result.valid  # artifact_ref is required, not Optional
```

## 4. Run Tests

```bash
# Unit + conformance + reducer tests
python3.11 -m pytest tests/ -v

# Property tests only (reducer determinism, >=200 examples)
python3.11 -m pytest tests/property/test_mission_audit_determinism.py -v

# mypy strict check
mypy --strict src/spec_kitty_events/mission_audit.py
```
