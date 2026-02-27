"""
spec-kitty-events: Event log library with Lamport clocks and systematic error tracking.

This library provides primitives for building distributed event-sourced systems
with causal metadata (Lamport clocks), conflict detection, and CRDT/state-machine
merge rules.

Example:
    >>> from spec_kitty_events import Event, LamportClock, InMemoryClockStorage
    >>> storage = InMemoryClockStorage()
    >>> clock = LamportClock(node_id="alice", storage=storage)
    >>> clock.tick()
    1

Versioning and Export Notes (2.6.0 -- DecisionPoint Lifecycle Contracts):
    The DecisionPoint domain (DECISIONPOINT_SCHEMA_VERSION = "2.6.0") is an
    **additive-only** extension.  No existing symbols, models, or schemas
    were modified.  All new symbols are listed under the "DecisionPoint
    Lifecycle Contracts (2.6.0)" block in ``__all__``.

    Exported symbols (15 total):
        Constants: DECISIONPOINT_SCHEMA_VERSION, DECISION_POINT_OPENED,
            DECISION_POINT_DISCUSSING, DECISION_POINT_RESOLVED,
            DECISION_POINT_OVERRIDDEN, DECISION_POINT_EVENT_TYPES
        Enums: DecisionPointState, DecisionAuthorityRole
        Models: DecisionPointAnomaly, DecisionPointOpenedPayload,
            DecisionPointDiscussingPayload, DecisionPointResolvedPayload,
            DecisionPointOverriddenPayload, ReducedDecisionPointState
        Reducer: reduce_decision_point_events

    Downstream Impact Notes:
        spec-kitty runtime:
            - Pin ``spec-kitty-events>=2.6.0`` once this version is published.
            - Import ``reduce_decision_point_events`` for DecisionPoint state
              projection alongside the existing mission-audit reducer.
            - The ``DECISION_POINT_EVENT_TYPES`` frozenset can be used to
              filter event streams by family.

        spec-kitty-saas:
            - Pin ``spec-kitty-events>=2.6.0``.
            - DecisionPoint schemas (decision_point_*.schema.json) are
              available via ``spec_kitty_events.schemas.load_schema()``
              for API contract validation.
            - Conformance fixtures in ``spec_kitty_events.conformance``
              include the ``"decisionpoint"`` category for integration test
              suites (``load_fixtures("decisionpoint")``).
"""

__version__ = "2.6.0"

# Core data models
from spec_kitty_events.models import (
    Event,
    ErrorEntry,
    ConflictResolution,
    SpecKittyEventsError,
    StorageError,
    ValidationError,
    CyclicDependencyError,
    normalize_event_id,
)

# Storage abstractions
from spec_kitty_events.storage import (
    EventStore,
    ClockStorage,
    ErrorStorage,
    InMemoryEventStore,
    InMemoryClockStorage,
    InMemoryErrorStorage,
)

# Lamport clock
from spec_kitty_events.clock import LamportClock

# Conflict detection
from spec_kitty_events.conflict import (
    is_concurrent,
    total_order_key,
)

# Topological sorting
from spec_kitty_events.topology import topological_sort

# CRDT merge functions
from spec_kitty_events.crdt import (
    merge_gset,
    merge_counter,
)

# State-machine merge
from spec_kitty_events.merge import state_machine_merge

# Error logging
from spec_kitty_events.error_log import ErrorLog

# Gate observability contracts
from spec_kitty_events.gates import (
    GatePayloadBase,
    GatePassedPayload,
    GateFailedPayload,
    UnknownConclusionError,
    map_check_run_conclusion,
)

# Lifecycle event contracts
from spec_kitty_events.lifecycle import (
    SCHEMA_VERSION,
    MISSION_STARTED,
    MISSION_COMPLETED,
    MISSION_CANCELLED,
    PHASE_ENTERED,
    REVIEW_ROLLBACK,
    MISSION_EVENT_TYPES,
    TERMINAL_MISSION_STATUSES,
    MissionStatus,
    MissionStartedPayload,
    MissionCompletedPayload,
    MissionCancelledPayload,
    PhaseEnteredPayload,
    ReviewRollbackPayload,
    LifecycleAnomaly,
    ReducedMissionState,
    reduce_lifecycle_events,
)

# Status state model contracts
from spec_kitty_events.status import (
    Lane,
    SyncLaneV1,
    CANONICAL_TO_SYNC_V1,
    canonical_to_sync_v1,
    ExecutionMode,
    RepoEvidence,
    VerificationEntry,
    ReviewVerdict,
    DoneEvidence,
    ForceMetadata,
    StatusTransitionPayload,
    TransitionError,
    TransitionValidationResult,
    normalize_lane,
    validate_transition,
    TERMINAL_LANES,
    LANE_ALIASES,
    WP_STATUS_CHANGED,
    status_event_sort_key,
    dedup_events,
    reduce_status_events,
    WPState,
    TransitionAnomaly,
    ReducedStatus,
)

# Collaboration event contracts
from spec_kitty_events.collaboration import (
    PARTICIPANT_INVITED,
    PARTICIPANT_JOINED,
    PARTICIPANT_LEFT,
    PRESENCE_HEARTBEAT,
    DRIVE_INTENT_SET,
    FOCUS_CHANGED,
    PROMPT_STEP_EXECUTION_STARTED,
    PROMPT_STEP_EXECUTION_COMPLETED,
    CONCURRENT_DRIVER_WARNING,
    POTENTIAL_STEP_COLLISION_DETECTED,
    WARNING_ACKNOWLEDGED,
    COMMENT_POSTED,
    DECISION_CAPTURED,
    SESSION_LINKED,
    COLLABORATION_EVENT_TYPES,
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
    ReducedCollaborationState,
    CollaborationAnomaly,
    UnknownParticipantError,
    reduce_collaboration_events,
)

# Glossary semantic integrity contracts
from spec_kitty_events.glossary import (
    GLOSSARY_SCOPE_ACTIVATED,
    TERM_CANDIDATE_OBSERVED,
    SEMANTIC_CHECK_EVALUATED,
    GLOSSARY_CLARIFICATION_REQUESTED,
    GLOSSARY_CLARIFICATION_RESOLVED,
    GLOSSARY_SENSE_UPDATED,
    GENERATION_BLOCKED_BY_SEMANTIC_CONFLICT,
    GLOSSARY_STRICTNESS_SET,
    GLOSSARY_EVENT_TYPES,
    SemanticConflictEntry,
    GlossaryScopeActivatedPayload,
    TermCandidateObservedPayload,
    SemanticCheckEvaluatedPayload,
    GlossaryClarificationRequestedPayload,
    GlossaryClarificationResolvedPayload,
    GlossarySenseUpdatedPayload,
    GenerationBlockedBySemanticConflictPayload,
    GlossaryStrictnessSetPayload,
    GlossaryAnomaly,
    ClarificationRecord,
    ReducedGlossaryState,
    reduce_glossary_events,
)

# Mission-next runtime contracts
from spec_kitty_events.mission_next import (
    MISSION_RUN_STARTED,
    NEXT_STEP_PLANNED,
    NEXT_STEP_ISSUED,
    NEXT_STEP_AUTO_COMPLETED,
    DECISION_INPUT_REQUESTED,
    DECISION_INPUT_ANSWERED,
    MISSION_RUN_COMPLETED,
    _COMPLETION_ALIAS,
    MISSION_NEXT_EVENT_TYPES,
    MissionRunStatus,
    TERMINAL_RUN_STATUSES,
    RuntimeActorIdentity,
    MissionRunStartedPayload,
    NextStepIssuedPayload,
    NextStepAutoCompletedPayload,
    DecisionInputRequestedPayload,
    DecisionInputAnsweredPayload,
    MissionRunCompletedPayload,
    MissionNextAnomaly,
    ReducedMissionRunState,
    reduce_mission_next_events,
)

# Dossier event contracts (v2.4.0)
from spec_kitty_events.dossier import (
    MISSION_DOSSIER_ARTIFACT_INDEXED,
    MISSION_DOSSIER_ARTIFACT_MISSING,
    MISSION_DOSSIER_SNAPSHOT_COMPUTED,
    MISSION_DOSSIER_PARITY_DRIFT_DETECTED,
    DOSSIER_EVENT_TYPES,
    NamespaceMixedStreamError,
    LocalNamespaceTuple,
    ArtifactIdentity,
    ContentHashRef,
    ProvenanceRef,
    MissionDossierArtifactIndexedPayload,
    MissionDossierArtifactMissingPayload,
    MissionDossierSnapshotComputedPayload,
    MissionDossierParityDriftDetectedPayload,
    ArtifactEntry,
    AnomalyEntry,
    SnapshotSummary,
    DriftRecord,
    MissionDossierState,
    reduce_mission_dossier,
)

# Mission Audit Lifecycle Contracts (2.5.0)
from spec_kitty_events.mission_audit import (
    AUDIT_SCHEMA_VERSION as AUDIT_SCHEMA_VERSION,
    MISSION_AUDIT_REQUESTED as MISSION_AUDIT_REQUESTED,
    MISSION_AUDIT_STARTED as MISSION_AUDIT_STARTED,
    MISSION_AUDIT_DECISION_REQUESTED as MISSION_AUDIT_DECISION_REQUESTED,
    MISSION_AUDIT_COMPLETED as MISSION_AUDIT_COMPLETED,
    MISSION_AUDIT_FAILED as MISSION_AUDIT_FAILED,
    MISSION_AUDIT_EVENT_TYPES as MISSION_AUDIT_EVENT_TYPES,
    TERMINAL_AUDIT_STATUSES as TERMINAL_AUDIT_STATUSES,
    AuditVerdict as AuditVerdict,
    AuditSeverity as AuditSeverity,
    AuditStatus as AuditStatus,
    AuditArtifactRef as AuditArtifactRef,
    PendingDecision as PendingDecision,
    MissionAuditAnomaly as MissionAuditAnomaly,
    MissionAuditRequestedPayload as MissionAuditRequestedPayload,
    MissionAuditStartedPayload as MissionAuditStartedPayload,
    MissionAuditDecisionRequestedPayload as MissionAuditDecisionRequestedPayload,
    MissionAuditCompletedPayload as MissionAuditCompletedPayload,
    MissionAuditFailedPayload as MissionAuditFailedPayload,
    ReducedMissionAuditState as ReducedMissionAuditState,
    reduce_mission_audit_events as reduce_mission_audit_events,
)

# DecisionPoint Lifecycle Contracts (2.6.0)
from spec_kitty_events.decisionpoint import (
    DECISIONPOINT_SCHEMA_VERSION as DECISIONPOINT_SCHEMA_VERSION,
    DECISION_POINT_OPENED as DECISION_POINT_OPENED,
    DECISION_POINT_DISCUSSING as DECISION_POINT_DISCUSSING,
    DECISION_POINT_RESOLVED as DECISION_POINT_RESOLVED,
    DECISION_POINT_OVERRIDDEN as DECISION_POINT_OVERRIDDEN,
    DECISION_POINT_EVENT_TYPES as DECISION_POINT_EVENT_TYPES,
    DecisionPointState as DecisionPointState,
    DecisionAuthorityRole as DecisionAuthorityRole,
    DecisionPointAnomaly as DecisionPointAnomaly,
    DecisionPointOpenedPayload as DecisionPointOpenedPayload,
    DecisionPointDiscussingPayload as DecisionPointDiscussingPayload,
    DecisionPointResolvedPayload as DecisionPointResolvedPayload,
    DecisionPointOverriddenPayload as DecisionPointOverriddenPayload,
    ReducedDecisionPointState as ReducedDecisionPointState,
    reduce_decision_point_events as reduce_decision_point_events,
)

# Backward-compatible dossier aliases without the Payload suffix.
# Older consumers import these names directly.
MissionDossierArtifactIndexed = MissionDossierArtifactIndexedPayload
MissionDossierArtifactMissing = MissionDossierArtifactMissingPayload
MissionDossierSnapshotComputed = MissionDossierSnapshotComputedPayload
MissionDossierParityDriftDetected = MissionDossierParityDriftDetectedPayload

# Public API (controls what's exported with "from spec_kitty_events import *")
__all__ = [
    # Version
    "__version__",
    # Models
    "Event",
    "ErrorEntry",
    "ConflictResolution",
    "normalize_event_id",
    # Exceptions
    "SpecKittyEventsError",
    "StorageError",
    "ValidationError",
    "CyclicDependencyError",
    # Storage
    "EventStore",
    "ClockStorage",
    "ErrorStorage",
    "InMemoryEventStore",
    "InMemoryClockStorage",
    "InMemoryErrorStorage",
    # Clock
    "LamportClock",
    # Conflict detection
    "is_concurrent",
    "total_order_key",
    "topological_sort",
    # Merge functions
    "merge_gset",
    "merge_counter",
    "state_machine_merge",
    # Error logging
    "ErrorLog",
    # Gate observability
    "GatePayloadBase",
    "GatePassedPayload",
    "GateFailedPayload",
    "UnknownConclusionError",
    "map_check_run_conclusion",
    # Lifecycle event contracts
    "SCHEMA_VERSION",
    "MISSION_STARTED",
    "MISSION_COMPLETED",
    "MISSION_CANCELLED",
    "PHASE_ENTERED",
    "REVIEW_ROLLBACK",
    "MISSION_EVENT_TYPES",
    "TERMINAL_MISSION_STATUSES",
    "MissionStatus",
    "MissionStartedPayload",
    "MissionCompletedPayload",
    "MissionCancelledPayload",
    "PhaseEnteredPayload",
    "ReviewRollbackPayload",
    "LifecycleAnomaly",
    "ReducedMissionState",
    "reduce_lifecycle_events",
    # Status state model
    "Lane",
    "SyncLaneV1",
    "CANONICAL_TO_SYNC_V1",
    "canonical_to_sync_v1",
    "ExecutionMode",
    "RepoEvidence",
    "VerificationEntry",
    "ReviewVerdict",
    "DoneEvidence",
    "ForceMetadata",
    "StatusTransitionPayload",
    "TransitionError",
    "TransitionValidationResult",
    "normalize_lane",
    "validate_transition",
    "TERMINAL_LANES",
    "LANE_ALIASES",
    "WP_STATUS_CHANGED",
    "status_event_sort_key",
    "dedup_events",
    "reduce_status_events",
    "WPState",
    "TransitionAnomaly",
    "ReducedStatus",
    # Collaboration event contracts
    "PARTICIPANT_INVITED",
    "PARTICIPANT_JOINED",
    "PARTICIPANT_LEFT",
    "PRESENCE_HEARTBEAT",
    "DRIVE_INTENT_SET",
    "FOCUS_CHANGED",
    "PROMPT_STEP_EXECUTION_STARTED",
    "PROMPT_STEP_EXECUTION_COMPLETED",
    "CONCURRENT_DRIVER_WARNING",
    "POTENTIAL_STEP_COLLISION_DETECTED",
    "WARNING_ACKNOWLEDGED",
    "COMMENT_POSTED",
    "DECISION_CAPTURED",
    "SESSION_LINKED",
    "COLLABORATION_EVENT_TYPES",
    "ParticipantIdentity",
    "AuthPrincipalBinding",
    "FocusTarget",
    "ParticipantInvitedPayload",
    "ParticipantJoinedPayload",
    "ParticipantLeftPayload",
    "PresenceHeartbeatPayload",
    "DriveIntentSetPayload",
    "FocusChangedPayload",
    "PromptStepExecutionStartedPayload",
    "PromptStepExecutionCompletedPayload",
    "ConcurrentDriverWarningPayload",
    "PotentialStepCollisionDetectedPayload",
    "WarningAcknowledgedPayload",
    "CommentPostedPayload",
    "DecisionCapturedPayload",
    "SessionLinkedPayload",
    "ReducedCollaborationState",
    "CollaborationAnomaly",
    "UnknownParticipantError",
    "reduce_collaboration_events",
    # Glossary semantic integrity contracts
    "GLOSSARY_SCOPE_ACTIVATED",
    "TERM_CANDIDATE_OBSERVED",
    "SEMANTIC_CHECK_EVALUATED",
    "GLOSSARY_CLARIFICATION_REQUESTED",
    "GLOSSARY_CLARIFICATION_RESOLVED",
    "GLOSSARY_SENSE_UPDATED",
    "GENERATION_BLOCKED_BY_SEMANTIC_CONFLICT",
    "GLOSSARY_STRICTNESS_SET",
    "GLOSSARY_EVENT_TYPES",
    "SemanticConflictEntry",
    "GlossaryScopeActivatedPayload",
    "TermCandidateObservedPayload",
    "SemanticCheckEvaluatedPayload",
    "GlossaryClarificationRequestedPayload",
    "GlossaryClarificationResolvedPayload",
    "GlossarySenseUpdatedPayload",
    "GenerationBlockedBySemanticConflictPayload",
    "GlossaryStrictnessSetPayload",
    "GlossaryAnomaly",
    "ClarificationRecord",
    "ReducedGlossaryState",
    "reduce_glossary_events",
    # Mission-next runtime contracts
    "MISSION_RUN_STARTED",
    "NEXT_STEP_PLANNED",
    "NEXT_STEP_ISSUED",
    "NEXT_STEP_AUTO_COMPLETED",
    "DECISION_INPUT_REQUESTED",
    "DECISION_INPUT_ANSWERED",
    "MISSION_RUN_COMPLETED",
    "_COMPLETION_ALIAS",
    "MISSION_NEXT_EVENT_TYPES",
    "MissionRunStatus",
    "TERMINAL_RUN_STATUSES",
    "RuntimeActorIdentity",
    "MissionRunStartedPayload",
    "NextStepIssuedPayload",
    "NextStepAutoCompletedPayload",
    "DecisionInputRequestedPayload",
    "DecisionInputAnsweredPayload",
    "MissionRunCompletedPayload",
    "MissionNextAnomaly",
    "ReducedMissionRunState",
    "reduce_mission_next_events",
    # Dossier event contracts
    "MISSION_DOSSIER_ARTIFACT_INDEXED",
    "MISSION_DOSSIER_ARTIFACT_MISSING",
    "MISSION_DOSSIER_SNAPSHOT_COMPUTED",
    "MISSION_DOSSIER_PARITY_DRIFT_DETECTED",
    "DOSSIER_EVENT_TYPES",
    "NamespaceMixedStreamError",
    "LocalNamespaceTuple",
    "ArtifactIdentity",
    "ContentHashRef",
    "ProvenanceRef",
    "MissionDossierArtifactIndexedPayload",
    "MissionDossierArtifactMissingPayload",
    "MissionDossierSnapshotComputedPayload",
    "MissionDossierParityDriftDetectedPayload",
    "MissionDossierArtifactIndexed",
    "MissionDossierArtifactMissing",
    "MissionDossierSnapshotComputed",
    "MissionDossierParityDriftDetected",
    "ArtifactEntry",
    "AnomalyEntry",
    "SnapshotSummary",
    "DriftRecord",
    "MissionDossierState",
    "reduce_mission_dossier",
    # Mission Audit Lifecycle Contracts (2.5.0)
    "AUDIT_SCHEMA_VERSION",
    "MISSION_AUDIT_REQUESTED",
    "MISSION_AUDIT_STARTED",
    "MISSION_AUDIT_DECISION_REQUESTED",
    "MISSION_AUDIT_COMPLETED",
    "MISSION_AUDIT_FAILED",
    "MISSION_AUDIT_EVENT_TYPES",
    "TERMINAL_AUDIT_STATUSES",
    "AuditVerdict",
    "AuditSeverity",
    "AuditStatus",
    "AuditArtifactRef",
    "PendingDecision",
    "MissionAuditAnomaly",
    "MissionAuditRequestedPayload",
    "MissionAuditStartedPayload",
    "MissionAuditDecisionRequestedPayload",
    "MissionAuditCompletedPayload",
    "MissionAuditFailedPayload",
    "ReducedMissionAuditState",
    "reduce_mission_audit_events",
    # DecisionPoint Lifecycle Contracts (2.6.0)
    "DECISIONPOINT_SCHEMA_VERSION",
    "DECISION_POINT_OPENED",
    "DECISION_POINT_DISCUSSING",
    "DECISION_POINT_RESOLVED",
    "DECISION_POINT_OVERRIDDEN",
    "DECISION_POINT_EVENT_TYPES",
    "DecisionPointState",
    "DecisionAuthorityRole",
    "DecisionPointAnomaly",
    "DecisionPointOpenedPayload",
    "DecisionPointDiscussingPayload",
    "DecisionPointResolvedPayload",
    "DecisionPointOverriddenPayload",
    "ReducedDecisionPointState",
    "reduce_decision_point_events",
]
