"""Unit tests for mission_audit module — payload validation, round-trip, edge cases.

Covers T009: payload validation (round-trip, required fields, Literal constraints,
Field constraints, enum validation, AuditArtifactRef composition, frozen immutability,
PendingDecision construction).
"""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from spec_kitty_events.dossier import ContentHashRef, ProvenanceRef
from spec_kitty_events.mission_audit import (
    AUDIT_SCHEMA_VERSION,
    MISSION_AUDIT_EVENT_TYPES,
    TERMINAL_AUDIT_STATUSES,
    AuditArtifactRef,
    AuditSeverity,
    AuditStatus,
    AuditVerdict,
    MissionAuditCompletedPayload,
    MissionAuditDecisionRequestedPayload,
    MissionAuditFailedPayload,
    MissionAuditRequestedPayload,
    MissionAuditStartedPayload,
    PendingDecision,
    ReducedMissionAuditState,
)


# ── Shared fixtures ────────────────────────────────────────────────────────────

def _make_content_hash_ref() -> ContentHashRef:
    return ContentHashRef(hash="abcdef1234567890", algorithm="sha256")


def _make_provenance_ref() -> ProvenanceRef:
    return ProvenanceRef(git_sha="deadbeef", actor_id="agent-1", actor_kind="llm")


def _make_artifact_ref() -> AuditArtifactRef:
    return AuditArtifactRef(
        report_path="/reports/audit-001.json",
        content_hash=_make_content_hash_ref(),
        provenance=_make_provenance_ref(),
    )


# ── 1. Payload round-trips ─────────────────────────────────────────────────────

def test_requested_payload_round_trip() -> None:
    original = MissionAuditRequestedPayload(
        mission_id="m-001",
        run_id="run-001",
        feature_slug="my-feature",
        actor="agent-1",
        trigger_mode="manual",
        audit_scope=["file1.py", "file2.py"],
        enforcement_mode="advisory",
    )
    data = original.model_dump(mode="json")
    restored = MissionAuditRequestedPayload.model_validate(data)
    assert restored.mission_id == original.mission_id
    assert restored.run_id == original.run_id
    assert restored.trigger_mode == original.trigger_mode
    assert restored.audit_scope == original.audit_scope
    assert restored.enforcement_mode == original.enforcement_mode


def test_started_payload_round_trip() -> None:
    original = MissionAuditStartedPayload(
        mission_id="m-001",
        run_id="run-001",
        feature_slug="my-feature",
        actor="agent-1",
        audit_scope_hash="sha256:aabbcc",
    )
    data = original.model_dump(mode="json")
    restored = MissionAuditStartedPayload.model_validate(data)
    assert restored.audit_scope_hash == original.audit_scope_hash
    assert restored.mission_id == original.mission_id


def test_decision_requested_payload_round_trip() -> None:
    original = MissionAuditDecisionRequestedPayload(
        mission_id="m-001",
        run_id="run-001",
        feature_slug="my-feature",
        actor="agent-1",
        decision_id="dec-001",
        question="Should we proceed?",
        context_summary="Found 2 warnings",
        severity=AuditSeverity.WARNING,
    )
    data = original.model_dump(mode="json")
    restored = MissionAuditDecisionRequestedPayload.model_validate(data)
    assert restored.decision_id == original.decision_id
    assert restored.severity == original.severity


def test_completed_payload_round_trip() -> None:
    artifact = _make_artifact_ref()
    original = MissionAuditCompletedPayload(
        mission_id="m-001",
        run_id="run-001",
        feature_slug="my-feature",
        actor="agent-1",
        verdict=AuditVerdict.PASS,
        severity=AuditSeverity.INFO,
        findings_count=0,
        artifact_ref=artifact,
        summary="All checks passed",
    )
    data = original.model_dump(mode="json")
    restored = MissionAuditCompletedPayload.model_validate(data)
    assert restored.verdict == original.verdict
    assert restored.findings_count == original.findings_count
    assert restored.artifact_ref.content_hash.hash == artifact.content_hash.hash


def test_failed_payload_round_trip() -> None:
    original = MissionAuditFailedPayload(
        mission_id="m-001",
        run_id="run-001",
        feature_slug="my-feature",
        actor="agent-1",
        error_code="TIMEOUT",
        error_message="Audit timed out after 60s",
        partial_artifact_ref=None,
    )
    data = original.model_dump(mode="json")
    restored = MissionAuditFailedPayload.model_validate(data)
    assert restored.error_code == original.error_code
    assert restored.partial_artifact_ref is None


# ── 2. Required field rejection ────────────────────────────────────────────────

def test_requested_payload_missing_mission_id_raises() -> None:
    with pytest.raises(ValidationError):
        MissionAuditRequestedPayload(  # type: ignore[call-arg]
            run_id="run-001",
            feature_slug="my-feature",
            actor="agent-1",
            trigger_mode="manual",
            audit_scope=["file1.py"],
            enforcement_mode="advisory",
        )


def test_completed_payload_missing_verdict_raises() -> None:
    with pytest.raises(ValidationError):
        MissionAuditCompletedPayload(  # type: ignore[call-arg]
            mission_id="m-001",
            run_id="run-001",
            feature_slug="my-feature",
            actor="agent-1",
            severity=AuditSeverity.INFO,
            findings_count=0,
            artifact_ref=_make_artifact_ref(),
            summary="ok",
        )


def test_decision_requested_payload_missing_decision_id_raises() -> None:
    with pytest.raises(ValidationError):
        MissionAuditDecisionRequestedPayload(  # type: ignore[call-arg]
            mission_id="m-001",
            run_id="run-001",
            feature_slug="my-feature",
            actor="agent-1",
            question="?",
            context_summary="ctx",
            severity=AuditSeverity.INFO,
        )


def test_failed_payload_missing_error_code_raises() -> None:
    with pytest.raises(ValidationError):
        MissionAuditFailedPayload(  # type: ignore[call-arg]
            mission_id="m-001",
            run_id="run-001",
            feature_slug="my-feature",
            actor="agent-1",
            error_message="oops",
        )


def test_started_payload_missing_audit_scope_hash_raises() -> None:
    with pytest.raises(ValidationError):
        MissionAuditStartedPayload(  # type: ignore[call-arg]
            mission_id="m-001",
            run_id="run-001",
            feature_slug="my-feature",
            actor="agent-1",
        )


# ── 3. Literal constraint rejection ───────────────────────────────────────────

def test_invalid_trigger_mode_raises() -> None:
    with pytest.raises(ValidationError):
        MissionAuditRequestedPayload(
            mission_id="m-001",
            run_id="run-001",
            feature_slug="my-feature",
            actor="agent-1",
            trigger_mode="invalid",  # type: ignore[arg-type]
            audit_scope=["file1.py"],
            enforcement_mode="advisory",
        )


def test_invalid_enforcement_mode_raises() -> None:
    with pytest.raises(ValidationError):
        MissionAuditRequestedPayload(
            mission_id="m-001",
            run_id="run-001",
            feature_slug="my-feature",
            actor="agent-1",
            trigger_mode="manual",
            audit_scope=["file1.py"],
            enforcement_mode="unknown",  # type: ignore[arg-type]
        )


# ── 4. Field constraint rejection ─────────────────────────────────────────────

def test_negative_findings_count_raises() -> None:
    with pytest.raises(ValidationError):
        MissionAuditCompletedPayload(
            mission_id="m-001",
            run_id="run-001",
            feature_slug="my-feature",
            actor="agent-1",
            verdict=AuditVerdict.PASS,
            severity=AuditSeverity.INFO,
            findings_count=-1,
            artifact_ref=_make_artifact_ref(),
            summary="ok",
        )


def test_empty_mission_id_raises() -> None:
    with pytest.raises(ValidationError):
        MissionAuditRequestedPayload(
            mission_id="",
            run_id="run-001",
            feature_slug="my-feature",
            actor="agent-1",
            trigger_mode="manual",
            audit_scope=["file1.py"],
            enforcement_mode="advisory",
        )


# ── 5. Enum validation ─────────────────────────────────────────────────────────

def test_invalid_audit_verdict_raises() -> None:
    with pytest.raises(ValidationError):
        MissionAuditCompletedPayload(
            mission_id="m-001",
            run_id="run-001",
            feature_slug="my-feature",
            actor="agent-1",
            verdict="not_a_verdict",  # type: ignore[arg-type]
            severity=AuditSeverity.INFO,
            findings_count=0,
            artifact_ref=_make_artifact_ref(),
            summary="ok",
        )


def test_invalid_audit_severity_raises() -> None:
    with pytest.raises(ValidationError):
        MissionAuditDecisionRequestedPayload(
            mission_id="m-001",
            run_id="run-001",
            feature_slug="my-feature",
            actor="agent-1",
            decision_id="dec-001",
            question="?",
            context_summary="ctx",
            severity="not_a_severity",  # type: ignore[arg-type]
        )


def test_invalid_audit_status_raises() -> None:
    with pytest.raises(ValidationError):
        ReducedMissionAuditState(audit_status="not_a_status")  # type: ignore[arg-type]


# ── 6. AuditArtifactRef composition ───────────────────────────────────────────

def test_audit_artifact_ref_round_trip() -> None:
    content_hash = _make_content_hash_ref()
    provenance = _make_provenance_ref()
    ref = AuditArtifactRef(
        report_path="/reports/audit.json",
        content_hash=content_hash,
        provenance=provenance,
    )
    data = ref.model_dump(mode="json")
    restored = AuditArtifactRef.model_validate(data)
    assert restored.content_hash.hash == content_hash.hash
    assert restored.provenance.git_sha == provenance.git_sha


# ── 7. Frozen immutability ─────────────────────────────────────────────────────

def test_requested_payload_is_frozen() -> None:
    payload = MissionAuditRequestedPayload(
        mission_id="m-001",
        run_id="run-001",
        feature_slug="my-feature",
        actor="agent-1",
        trigger_mode="manual",
        audit_scope=["file1.py"],
        enforcement_mode="advisory",
    )
    with pytest.raises(Exception):
        payload.mission_id = "changed"  # type: ignore[misc]


def test_completed_payload_is_frozen() -> None:
    payload = MissionAuditCompletedPayload(
        mission_id="m-001",
        run_id="run-001",
        feature_slug="my-feature",
        actor="agent-1",
        verdict=AuditVerdict.PASS,
        severity=AuditSeverity.INFO,
        findings_count=0,
        artifact_ref=_make_artifact_ref(),
        summary="ok",
    )
    with pytest.raises(Exception):
        payload.verdict = AuditVerdict.FAIL  # type: ignore[misc]


def test_audit_artifact_ref_is_frozen() -> None:
    ref = _make_artifact_ref()
    with pytest.raises(Exception):
        ref.report_path = "/changed"  # type: ignore[misc]


def test_pending_decision_is_frozen() -> None:
    pd = PendingDecision(
        decision_id="dec-001",
        question="?",
        context_summary="ctx",
        severity=AuditSeverity.INFO,
    )
    with pytest.raises(Exception):
        pd.decision_id = "changed"  # type: ignore[misc]


def test_reduced_state_is_frozen() -> None:
    state = ReducedMissionAuditState()
    with pytest.raises(Exception):
        state.audit_status = AuditStatus.RUNNING  # type: ignore[misc]


# ── 8. PendingDecision construction ───────────────────────────────────────────

def test_pending_decision_construction() -> None:
    pd = PendingDecision(
        decision_id="dec-001",
        question="Proceed?",
        context_summary="2 warnings found",
        severity=AuditSeverity.WARNING,
    )
    assert pd.decision_id == "dec-001"
    assert pd.question == "Proceed?"
    assert pd.context_summary == "2 warnings found"
    assert pd.severity == AuditSeverity.WARNING
    with pytest.raises(Exception):
        pd.decision_id = "changed"  # type: ignore[misc]


# ── 9. ReducedMissionAuditState defaults ──────────────────────────────────────

def test_reduced_state_defaults() -> None:
    state = ReducedMissionAuditState()
    assert state.audit_status == AuditStatus.PENDING
    assert state.event_count == 0
    assert state.anomalies == ()
    assert state.pending_decisions == ()
    assert state.verdict is None
    assert state.mission_id is None


# ── 10. Constants ──────────────────────────────────────────────────────────────

def test_mission_audit_event_types_count() -> None:
    assert len(MISSION_AUDIT_EVENT_TYPES) == 5


def test_audit_schema_version() -> None:
    assert AUDIT_SCHEMA_VERSION == "2.5.0"


def test_terminal_audit_statuses() -> None:
    assert TERMINAL_AUDIT_STATUSES == {AuditStatus.COMPLETED, AuditStatus.FAILED}
