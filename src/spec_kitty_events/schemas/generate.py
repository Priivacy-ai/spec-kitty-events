"""Build-time JSON Schema generation script for spec-kitty-events models."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Type

from pydantic import TypeAdapter
from pydantic import BaseModel

# Import all models to generate schemas for
from spec_kitty_events.models import Event
from spec_kitty_events.status import (
    Lane,
    SyncLaneV1,
    StatusTransitionPayload,
)
from spec_kitty_events.lifecycle import (
    MissionStartedPayload,
    MissionCompletedPayload,
    MissionCancelledPayload,
    PhaseEnteredPayload,
    ReviewRollbackPayload,
)
from spec_kitty_events.gates import (
    GatePassedPayload,
    GateFailedPayload,
)
from spec_kitty_events.collaboration import (
    ParticipantIdentity,
    AuthPrincipalBinding,
    FocusTarget,
    ParticipantInvitedPayload,
    ParticipantJoinedPayload,
    ParticipantLeftPayload,
    PresenceHeartbeatPayload,
    DriveIntentSetPayload,
    FocusChangedPayload,
    PromptStepExecutionStartedPayload,
    PromptStepExecutionCompletedPayload,
    ConcurrentDriverWarningPayload,
    PotentialStepCollisionDetectedPayload,
    WarningAcknowledgedPayload,
    CommentPostedPayload,
    DecisionCapturedPayload,
    SessionLinkedPayload,
)
from spec_kitty_events.glossary import (
    SemanticConflictEntry,
    GlossaryScopeActivatedPayload,
    TermCandidateObservedPayload,
    GlossarySenseUpdatedPayload,
    GlossaryStrictnessSetPayload,
    SemanticCheckEvaluatedPayload,
    GlossaryClarificationRequestedPayload,
    GlossaryClarificationResolvedPayload,
    GenerationBlockedBySemanticConflictPayload,
)
from spec_kitty_events.mission_next import (
    RuntimeActorIdentity,
    MissionRunStartedPayload,
    NextStepIssuedPayload,
    NextStepAutoCompletedPayload,
    DecisionInputRequestedPayload,
    DecisionInputAnsweredPayload,
    MissionRunCompletedPayload,
)
from spec_kitty_events.dossier import (
    ArtifactIdentity,
    ContentHashRef,
    ProvenanceRef,
    LocalNamespaceTuple,
    MissionDossierArtifactIndexedPayload,
    MissionDossierArtifactMissingPayload,
    MissionDossierSnapshotComputedPayload,
    MissionDossierParityDriftDetectedPayload,
)
from spec_kitty_events.mission_audit import (
    MissionAuditRequestedPayload,
    MissionAuditStartedPayload,
    MissionAuditDecisionRequestedPayload,
    MissionAuditCompletedPayload,
    MissionAuditFailedPayload,
)
from spec_kitty_events.decisionpoint import (
    DecisionPointOpenedPayload,
    DecisionPointDiscussingPayload,
    DecisionPointResolvedPayload,
    DecisionPointOverriddenPayload,
)
from spec_kitty_events.connector import (
    ConnectorProvisionedPayload,
    ConnectorHealthCheckedPayload,
    ConnectorDegradedPayload,
    ConnectorRevokedPayload,
    ConnectorReconnectedPayload,
)
from spec_kitty_events.sync import (
    SyncIngestAcceptedPayload,
    SyncIngestRejectedPayload,
    SyncRetryScheduledPayload,
    SyncDeadLetteredPayload,
    SyncReplayCompletedPayload,
    ExternalReferenceLinkedPayload,
)


# Schema directory (same directory as this script)
SCHEMA_DIR = Path(__file__).parent

# Registry of models to generate schemas for
PYDANTIC_MODELS: List[tuple[str, Type[BaseModel]]] = [
    ("event", Event),
    ("status_transition_payload", StatusTransitionPayload),
    ("gate_passed_payload", GatePassedPayload),
    ("gate_failed_payload", GateFailedPayload),
    ("mission_started_payload", MissionStartedPayload),
    ("mission_completed_payload", MissionCompletedPayload),
    ("mission_cancelled_payload", MissionCancelledPayload),
    ("phase_entered_payload", PhaseEnteredPayload),
    ("review_rollback_payload", ReviewRollbackPayload),
    # Collaboration identity models
    ("participant_identity", ParticipantIdentity),
    ("auth_principal_binding", AuthPrincipalBinding),
    ("focus_target", FocusTarget),
    # Collaboration payload models
    ("participant_invited_payload", ParticipantInvitedPayload),
    ("participant_joined_payload", ParticipantJoinedPayload),
    ("participant_left_payload", ParticipantLeftPayload),
    ("presence_heartbeat_payload", PresenceHeartbeatPayload),
    ("drive_intent_set_payload", DriveIntentSetPayload),
    ("focus_changed_payload", FocusChangedPayload),
    ("prompt_step_execution_started_payload", PromptStepExecutionStartedPayload),
    ("prompt_step_execution_completed_payload", PromptStepExecutionCompletedPayload),
    ("concurrent_driver_warning_payload", ConcurrentDriverWarningPayload),
    ("potential_step_collision_detected_payload", PotentialStepCollisionDetectedPayload),
    ("warning_acknowledged_payload", WarningAcknowledgedPayload),
    ("comment_posted_payload", CommentPostedPayload),
    ("decision_captured_payload", DecisionCapturedPayload),
    ("session_linked_payload", SessionLinkedPayload),
    # Glossary semantic integrity models
    ("semantic_conflict_entry", SemanticConflictEntry),
    ("glossary_scope_activated_payload", GlossaryScopeActivatedPayload),
    ("term_candidate_observed_payload", TermCandidateObservedPayload),
    ("glossary_sense_updated_payload", GlossarySenseUpdatedPayload),
    ("glossary_strictness_set_payload", GlossaryStrictnessSetPayload),
    ("semantic_check_evaluated_payload", SemanticCheckEvaluatedPayload),
    ("glossary_clarification_requested_payload", GlossaryClarificationRequestedPayload),
    ("glossary_clarification_resolved_payload", GlossaryClarificationResolvedPayload),
    ("generation_blocked_by_semantic_conflict_payload", GenerationBlockedBySemanticConflictPayload),
    # Mission-next runtime models
    ("runtime_actor_identity", RuntimeActorIdentity),
    ("mission_run_started_payload", MissionRunStartedPayload),
    ("next_step_issued_payload", NextStepIssuedPayload),
    ("next_step_auto_completed_payload", NextStepAutoCompletedPayload),
    ("decision_input_requested_payload", DecisionInputRequestedPayload),
    ("decision_input_answered_payload", DecisionInputAnsweredPayload),
    ("mission_run_completed_payload", MissionRunCompletedPayload),
    # Dossier event contract models
    ("artifact_identity", ArtifactIdentity),
    ("content_hash_ref", ContentHashRef),
    ("provenance_ref", ProvenanceRef),
    ("local_namespace_tuple", LocalNamespaceTuple),
    ("mission_dossier_artifact_indexed_payload", MissionDossierArtifactIndexedPayload),
    ("mission_dossier_artifact_missing_payload", MissionDossierArtifactMissingPayload),
    ("mission_dossier_snapshot_computed_payload", MissionDossierSnapshotComputedPayload),
    ("mission_dossier_parity_drift_detected_payload", MissionDossierParityDriftDetectedPayload),
    # Mission audit lifecycle contracts (2.5.0)
    ("mission_audit_requested_payload", MissionAuditRequestedPayload),
    ("mission_audit_started_payload", MissionAuditStartedPayload),
    ("mission_audit_decision_requested_payload", MissionAuditDecisionRequestedPayload),
    ("mission_audit_completed_payload", MissionAuditCompletedPayload),
    ("mission_audit_failed_payload", MissionAuditFailedPayload),
    # DecisionPoint lifecycle contracts (2.6.0)
    ("decision_point_opened_payload", DecisionPointOpenedPayload),
    ("decision_point_discussing_payload", DecisionPointDiscussingPayload),
    ("decision_point_resolved_payload", DecisionPointResolvedPayload),
    ("decision_point_overridden_payload", DecisionPointOverriddenPayload),
    # Connector lifecycle contracts (2.7.0)
    ("connector_provisioned_payload", ConnectorProvisionedPayload),
    ("connector_health_checked_payload", ConnectorHealthCheckedPayload),
    ("connector_degraded_payload", ConnectorDegradedPayload),
    ("connector_revoked_payload", ConnectorRevokedPayload),
    ("connector_reconnected_payload", ConnectorReconnectedPayload),
    # Sync lifecycle contracts (2.7.0)
    ("sync_ingest_accepted_payload", SyncIngestAcceptedPayload),
    ("sync_ingest_rejected_payload", SyncIngestRejectedPayload),
    ("sync_retry_scheduled_payload", SyncRetryScheduledPayload),
    ("sync_dead_lettered_payload", SyncDeadLetteredPayload),
    ("sync_replay_completed_payload", SyncReplayCompletedPayload),
    ("external_reference_linked_payload", ExternalReferenceLinkedPayload),
]

# Enums (use TypeAdapter)
ENUM_TYPES: List[tuple[str, type]] = [
    ("lane", Lane),
    ("sync_lane_v1", SyncLaneV1),
]


def generate_schema(name: str, model: Type[BaseModel]) -> Dict[str, Any]:
    """Generate JSON Schema for a Pydantic model.

    Args:
        name: Schema name for $id field
        model: Pydantic model class

    Returns:
        JSON Schema dict with $schema and $id fields
    """
    schema = model.model_json_schema(mode="serialization")
    schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
    schema["$id"] = f"spec-kitty-events/{name}"
    return schema


def generate_enum_schema(name: str, enum_cls: type) -> Dict[str, Any]:
    """Generate JSON Schema for an enum using TypeAdapter.

    Args:
        name: Schema name for $id field
        enum_cls: Enum class

    Returns:
        JSON Schema dict with $schema and $id fields
    """
    adapter: TypeAdapter[Any] = TypeAdapter(enum_cls)
    schema = adapter.json_schema(mode="serialization")
    schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
    schema["$id"] = f"spec-kitty-events/{name}"
    return schema


def schema_to_json(schema: Dict[str, Any]) -> str:
    """Serialize schema to deterministic JSON string.

    Args:
        schema: JSON Schema dict

    Returns:
        Formatted JSON string with trailing newline
    """
    return json.dumps(schema, indent=2, sort_keys=True) + "\n"


def write_schema_file(name: str, schema: Dict[str, Any]) -> None:
    """Write schema to disk.

    Args:
        name: Schema name (filename will be {name}.schema.json)
        schema: JSON Schema dict
    """
    path = SCHEMA_DIR / f"{name}.schema.json"
    content = schema_to_json(schema)
    path.write_text(content, encoding="utf-8")
    print(f"Generated {path}")


def generate_all_schemas() -> Dict[str, Dict[str, Any]]:
    """Generate all schemas and return them as a dict.

    Returns:
        Dict mapping schema name to schema dict
    """
    schemas: Dict[str, Dict[str, Any]] = {}

    # Generate Pydantic model schemas
    for name, model in PYDANTIC_MODELS:
        schemas[name] = generate_schema(name, model)

    # Generate enum schemas
    for name, enum_cls in ENUM_TYPES:
        schemas[name] = generate_enum_schema(name, enum_cls)

    return schemas


def write_all_schemas(schemas: Dict[str, Dict[str, Any]]) -> None:
    """Write all schemas to disk.

    Args:
        schemas: Dict mapping schema name to schema dict
    """
    for name, schema in schemas.items():
        write_schema_file(name, schema)


def check_drift() -> int:
    """Check if generated schemas match committed files.

    Returns:
        0 if all schemas match, 1 if any drift detected
    """
    schemas = generate_all_schemas()
    drift_detected = False

    for name, schema in schemas.items():
        path = SCHEMA_DIR / f"{name}.schema.json"
        expected_content = schema_to_json(schema)

        if not path.exists():
            print(f"ERROR: Missing schema file: {path}", file=sys.stderr)
            drift_detected = True
            continue

        actual_content = path.read_text(encoding="utf-8")

        if actual_content != expected_content:
            print(f"ERROR: Schema drift detected in {path}", file=sys.stderr)
            print("--- Expected", file=sys.stderr)
            print(expected_content, file=sys.stderr)
            print("--- Actual", file=sys.stderr)
            print(actual_content, file=sys.stderr)
            drift_detected = True

    # Check for orphaned schema files not in the registry
    expected_files = {f"{name}.schema.json" for name in schemas}
    actual_files = {p.name for p in SCHEMA_DIR.glob("*.schema.json")}
    orphaned = actual_files - expected_files
    for orphan in sorted(orphaned):
        print(f"Orphaned schema {orphan}", file=sys.stderr)
        drift_detected = True

    if drift_detected:
        print("\nSchema drift detected. Run without --check to regenerate.", file=sys.stderr)
        return 1

    print(f"All {len(schemas)} schemas are up to date.")
    return 0


def main() -> int:
    """Main entry point for schema generation script.

    Returns:
        Exit code (0 for success, 1 for failure/drift)
    """
    parser = argparse.ArgumentParser(
        description="Generate JSON schemas for spec-kitty-events models"
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check for schema drift without writing files (CI mode)",
    )
    args = parser.parse_args()

    if args.check:
        return check_drift()

    schemas = generate_all_schemas()
    write_all_schemas(schemas)
    print(f"\nSuccessfully generated {len(schemas)} schemas.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
