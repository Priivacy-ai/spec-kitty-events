"""Public package exports for the canonical TeamSpace event vocabulary.

This release publishes:

- canonical mission taxonomy: ``mission_slug``, ``mission_number``, ``mission_type``
- canonical catalog events: ``MissionCreated`` and ``MissionClosed``
- explicit envelope identity split: ``build_id`` versus ``node_id``
- Decision Moment V1: discriminated-union DecisionPoint payloads, Widened event,
  interview-origin fields, terminal outcome rules, and shared V1 models
- TeamSpace readiness: canonical ``in_review`` lane handling and reconciled
  mission payloads.
- The status-diary reducer (``spec_kitty_events.diary``, re-exported as
  ``spec_kitty_events.status.reduce``): the shared
  ``status.events.jsonl`` -> kanban-state fold for the CLI and the Team Kitty
  repo dossier.
- Bounded moment-attribute projections (``spec_kitty_events.zeitgeist_attrs``):
  ``DecisionPointOpened``/``DecisionPointResolved`` and the
  ``Specify``/``Plan``/``Tasks`` ``Started``/``Completed`` lifecycle kinds
  join the volatile vocabulary, and a derived, bounded, truncatable
  ``summary`` attr is added for ``MissionCreated`` and the artifact-lifecycle
  ``*Completed`` kinds.
- Ops/Invocations bounded moment contracts (``spec_kitty_events.ops_invocation``):
  ``OpsInvocationStarted``/``OpsInvocationCompleted`` join the volatile
  vocabulary so operations can share the Team Kitty timeline with missions
  without reusing mission event kinds. Post-MVP; the CLI emitter, SaaS view,
  and detail service are not implemented here.

The offline sync/cutover surfaces (``spec_kitty_events.sync``, ``legacy``,
``cutover``) were removed in ``8.0.0``; envelope-level fail-closed gating now
lives in ``spec_kitty_events.strict.validate_strict_envelope``.
"""

__version__ = "9.1.6"

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
    MISSION_CREATED,
    MISSION_CLOSED,
    MISSION_STARTED,
    MISSION_COMPLETED,
    MISSION_CANCELLED,
    MISSION_ORIGIN_BOUND,
    MISSION_REOPENED,
    FOLLOW_UP_RECORDED,
    PHASE_ENTERED,
    REVIEW_ROLLBACK,
    MISSION_EVENT_TYPES,
    TERMINAL_MISSION_STATUSES,
    MissionStatus,
    MissionCreatedPayload,
    MissionClosedPayload,
    MissionStartedPayload,
    MissionCompletedPayload,
    MissionCancelledPayload,
    MissionOriginBoundPayload,
    MissionReopenedPayload,
    FollowUpRecordedPayload,
    PhaseEnteredPayload,
    ReviewRollbackPayload,
    LifecycleAnomaly,
    ReducedMissionState,
    reduce_lifecycle_events,
)

# Canonical project / artifact / WP lifecycle event contracts
from spec_kitty_events.project_lifecycle import (
    PROJECT_INITIALIZED,
    SPECIFY_STARTED,
    SPECIFY_COMPLETED,
    PLAN_STARTED,
    PLAN_COMPLETED,
    TASKS_STARTED,
    TASKS_COMPLETED,
    WP_CREATED,
    WP_ASSIGNED,
    HISTORY_ADDED,
    ERROR_LOGGED,
    DEPENDENCY_RESOLVED,
    PROJECT_LIFECYCLE_EVENT_TYPES,
    ARTIFACT_LIFECYCLE_EVENT_TYPES,
    WP_LIFECYCLE_EVENT_TYPES,
    CANONICAL_LIFECYCLE_EVENT_TYPES,
    ArtifactPhase,
    ProjectInitializedPayload,
    SpecifyStartedPayload,
    SpecifyCompletedPayload,
    PlanStartedPayload,
    PlanCompletedPayload,
    TasksStartedPayload,
    TasksCompletedPayload,
    WPCreatedPayload,
    WPAssignedPayload,
    HistoryAddedPayload,
    ErrorLoggedPayload,
    DependencyResolvedPayload,
)

# Ops/Invocations bounded moment contracts (E-post-MVP, events#78). Shares
# the Team Kitty volatile-moment vocabulary via zeitgeist_attrs without
# reusing mission event kinds; no CLI emitter/SaaS view/detail service yet.
from spec_kitty_events.ops_invocation import (
    OPS_INVOCATION_STARTED,
    OPS_INVOCATION_COMPLETED,
    OPS_INVOCATION_EVENT_TYPES,
    OPS_INVOCATION_CONTRACT_VERSION,
    OpsInvocationOutcome,
    OpsInvocationStartedPayload,
    OpsInvocationCompletedPayload,
)

# Build-aggregate event contracts (shipped by mission
# canonical-producer-contracts-legacy-envelope-01KS7JM3).
from spec_kitty_events.build_lifecycle import (
    BUILD_REGISTERED,
    BUILD_HEARTBEAT,
    BUILD_LIFECYCLE_EVENT_TYPES,
    BuildRegisteredPayload,
    BuildHeartbeatPayload,
)

# HarnessObservation vocabulary (F1-T1, 7.0.0). F1 is the single owner of
# this vocabulary (draft §3.1 normative ownership clause).
from spec_kitty_events.harness_observation import (
    HARNESS_OBSERVATION,
    HARNESS_OBSERVATION_CONTRACT_VERSION,
    ObservationKind,
    PAYLOAD_ID_BY_KIND,
    HARNESS_OBSERVATION_PAYLOAD_IDS,
    FORBIDDEN_OBSERVATION_KEYS,
    FORBIDDEN_OBSERVATION_KEYS_VERSION,
    HarnessObservationPayload,
)

# Strict journal profile (F1-T1, 7.0.0): a deterministic, structured
# envelope validator layered over the existing lenient Event/lifecycle
# contracts. Opt-in for new producers/readers (F2 journal, D1 projector,
# Z1 client); Event itself stays lenient (decision 3).
from spec_kitty_events.strict import (
    STRICT_PROFILE_ID,
    STRICT_ENVELOPE_KEYS,
    STRICT_EVENT_TYPES,
    STRICT_TIMESTAMP_RULES,
    validate_strict_envelope,
    SupportRow,
    SUPPORT_MATRIX,
    support_matrix_digest,
)

# Zeitgeist attrs codecs for the volatile mission/WP families (E2). The
# single owner of the payload <-> bounded-attrs mapping the ephemeral
# status loop broadcasts through each team's relay.
from spec_kitty_events.zeitgeist_attrs import (
    VOLATILE_EVENT_TYPES,
    VolatileMoment,
    ZEITGEIST_ATTRS_MAX_BYTES,
    ZEITGEIST_ATTRS_MAX_KEYS,
    ZEITGEIST_ATTR_KEY_MAX_CHARS,
    from_zeitgeist_attrs,
    to_zeitgeist_attrs,
)

# Machine-readable classification surface for event types that are NOT
# routed through the SaaS-bound producer path. Empty in this release —
# every CLI-emitted event audited as of spec-kitty 43305c12c routes
# through SpecKittyEventEmitter._emit(). The surface is published so
# downstream consumers (CLI canonical-producer lint, SaaS adapter) can
# import the set and adjust enforcement without re-shipping a contract.
# Mission: canonical-producer-contracts-legacy-envelope-01KS7JM3.
LOCAL_ONLY_EVENT_TYPES: frozenset[str] = frozenset()

# Status state model contracts
from spec_kitty_events.status import (
    Lane,
    SyncLaneV1,
    SyncLaneV2,
    CANONICAL_TO_SYNC_V1,
    CANONICAL_TO_SYNC_V2,
    canonical_to_sync_v1,
    canonical_to_sync_v2,
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
    NON_DISPLAY_LANES,
    DISPLAY_LANES,
    LANE_ALIASES,
    WP_STATUS_CHANGED,
    is_bootstrap_planned_event,
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
    ParticipantExternalRefs,
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

# Analytics event contracts
from spec_kitty_events.analytics import (
    TOKEN_USAGE_RECORDED,
    DIFF_SUMMARY_RECORDED,
    ANALYTICS_EVENT_TYPES,
    TokenUsageRecordedPayload,
    DiffSummaryRecordedPayload,
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

# DecisionPoint Lifecycle Contracts (4.0.0 / V1)
from spec_kitty_events.decisionpoint import (
    DECISIONPOINT_SCHEMA_VERSION as DECISIONPOINT_SCHEMA_VERSION,
    DECISION_POINT_OPENED as DECISION_POINT_OPENED,
    DECISION_POINT_DISCUSSING as DECISION_POINT_DISCUSSING,
    DECISION_POINT_RESOLVED as DECISION_POINT_RESOLVED,
    DECISION_POINT_OVERRIDDEN as DECISION_POINT_OVERRIDDEN,
    DECISION_POINT_WIDENED as DECISION_POINT_WIDENED,
    DECISION_POINT_EVENT_TYPES as DECISION_POINT_EVENT_TYPES,
    DecisionPointState as DecisionPointState,
    DecisionAuthorityRole as DecisionAuthorityRole,
    DecisionPointAnomaly as DecisionPointAnomaly,
    DecisionPointOpenedPayload as DecisionPointOpenedPayload,
    DecisionPointOpenedAdrPayload as DecisionPointOpenedAdrPayload,
    DecisionPointOpenedInterviewPayload as DecisionPointOpenedInterviewPayload,
    DecisionPointDiscussingPayload as DecisionPointDiscussingPayload,
    DecisionPointDiscussingAdrPayload as DecisionPointDiscussingAdrPayload,
    DecisionPointDiscussingInterviewPayload as DecisionPointDiscussingInterviewPayload,
    DecisionPointResolvedPayload as DecisionPointResolvedPayload,
    DecisionPointResolvedAdrPayload as DecisionPointResolvedAdrPayload,
    DecisionPointResolvedInterviewPayload as DecisionPointResolvedInterviewPayload,
    DecisionPointOverriddenPayload as DecisionPointOverriddenPayload,
    DecisionPointWidenedPayload as DecisionPointWidenedPayload,
    ReducedDecisionPointState as ReducedDecisionPointState,
    reduce_decision_point_events as reduce_decision_point_events,
)

# Decision Moment V1 shared models (4.0.0)
from spec_kitty_events.decision_moment import (
    ClosureMessageRef,
    DefaultChannelRef,
    DiscussingSnapshotKind,
    OriginFlow,
    OriginSurface,
    SummaryBlock,
    SummarySource,
    TeamspaceRef,
    TerminalOutcome,
    ThreadRef,
    WideningChannel,
    WideningProjection,
)

# Connector Lifecycle Contracts (2.7.0) — extended in 2.8.0
from spec_kitty_events.connector import (
    CONNECTOR_SCHEMA_VERSION as CONNECTOR_SCHEMA_VERSION,
    CONNECTOR_PROVISIONED as CONNECTOR_PROVISIONED,
    CONNECTOR_HEALTH_CHECKED as CONNECTOR_HEALTH_CHECKED,
    CONNECTOR_DEGRADED as CONNECTOR_DEGRADED,
    CONNECTOR_REVOKED as CONNECTOR_REVOKED,
    CONNECTOR_RECONNECTED as CONNECTOR_RECONNECTED,
    CONNECTOR_EVENT_TYPES as CONNECTOR_EVENT_TYPES,
    ConnectorState as ConnectorState,
    HealthStatus as HealthStatus,
    ReconnectStrategy as ReconnectStrategy,
    ConnectorAnomaly as ConnectorAnomaly,
    ConnectorProvisionedPayload as ConnectorProvisionedPayload,
    ConnectorHealthCheckedPayload as ConnectorHealthCheckedPayload,
    ConnectorDegradedPayload as ConnectorDegradedPayload,
    ConnectorRevokedPayload as ConnectorRevokedPayload,
    ConnectorReconnectedPayload as ConnectorReconnectedPayload,
    USER_CONNECTED as USER_CONNECTED,
    USER_DISCONNECTED as USER_DISCONNECTED,
    UserConnectedPayload as UserConnectedPayload,
    UserDisconnectedPayload as UserDisconnectedPayload,
    UserConnectionStatus as UserConnectionStatus,
    ReducedConnectorState as ReducedConnectorState,
    reduce_connector_events as reduce_connector_events,
)

# Profile invocation contracts (3.1.0)
from spec_kitty_events.profile_invocation import (
    PROFILE_INVOCATION_SCHEMA_VERSION as PROFILE_INVOCATION_SCHEMA_VERSION,
    PROFILE_INVOCATION_STARTED as PROFILE_INVOCATION_STARTED,
    PROFILE_INVOCATION_COMPLETED as PROFILE_INVOCATION_COMPLETED,
    PROFILE_INVOCATION_FAILED as PROFILE_INVOCATION_FAILED,
    PROFILE_INVOCATION_EVENT_TYPES as PROFILE_INVOCATION_EVENT_TYPES,
    PROFILE_INVOCATION_RESERVED_TYPES as PROFILE_INVOCATION_RESERVED_TYPES,
    ProfileInvocationStartedPayload as ProfileInvocationStartedPayload,
)

# Retrospective contracts (4.1.0)
from spec_kitty_events.retrospective import (
    RETROSPECTIVE_SCHEMA_VERSION as RETROSPECTIVE_SCHEMA_VERSION,
    RETROSPECTIVE_COMPLETED as RETROSPECTIVE_COMPLETED,
    RETROSPECTIVE_SKIPPED as RETROSPECTIVE_SKIPPED,
    RETROSPECTIVE_REQUESTED_EVENT as RETROSPECTIVE_REQUESTED_EVENT,
    RETROSPECTIVE_STARTED_EVENT as RETROSPECTIVE_STARTED_EVENT,
    RETROSPECTIVE_COMPLETED_EVENT as RETROSPECTIVE_COMPLETED_EVENT,
    RETROSPECTIVE_SKIPPED_EVENT as RETROSPECTIVE_SKIPPED_EVENT,
    RETROSPECTIVE_FAILED_EVENT as RETROSPECTIVE_FAILED_EVENT,
    RETROSPECTIVE_PROPOSAL_GENERATED_EVENT as RETROSPECTIVE_PROPOSAL_GENERATED_EVENT,
    RETROSPECTIVE_PROPOSAL_APPLIED_EVENT as RETROSPECTIVE_PROPOSAL_APPLIED_EVENT,
    RETROSPECTIVE_PROPOSAL_REJECTED_EVENT as RETROSPECTIVE_PROPOSAL_REJECTED_EVENT,
    RETROSPECTIVE_EVENT_NAMES as RETROSPECTIVE_EVENT_NAMES,
    RETROSPECTIVE_EVENT_TYPES as RETROSPECTIVE_EVENT_TYPES,
    RetrospectiveActorRef as RetrospectiveActorRef,
    RetrospectiveModeSourceSignal as RetrospectiveModeSourceSignal,
    RetrospectiveMode as RetrospectiveMode,
    RetrospectiveRequestedPayload as RetrospectiveRequestedPayload,
    RetrospectiveStartedPayload as RetrospectiveStartedPayload,
    RetrospectiveLifecycleCompletedPayload as RetrospectiveLifecycleCompletedPayload,
    RetrospectiveLifecycleSkippedPayload as RetrospectiveLifecycleSkippedPayload,
    RetrospectiveFailedPayload as RetrospectiveFailedPayload,
    RetrospectiveProposalGeneratedPayload as RetrospectiveProposalGeneratedPayload,
    RetrospectiveProposalAppliedPayload as RetrospectiveProposalAppliedPayload,
    RetrospectiveProposalRejectedPayload as RetrospectiveProposalRejectedPayload,
    RequestedPayload as RequestedPayload,
    StartedPayload as StartedPayload,
    CompletedPayload as CompletedPayload,
    SkippedPayload as SkippedPayload,
    FailedPayload as FailedPayload,
    ProposalGeneratedPayload as ProposalGeneratedPayload,
    ProposalAppliedPayload as ProposalAppliedPayload,
    ProposalRejectedPayload as ProposalRejectedPayload,
    RetrospectiveCompletedPayload as RetrospectiveCompletedPayload,
    RetrospectiveSkippedPayload as RetrospectiveSkippedPayload,
    TriggerSourceT as TriggerSourceT,
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
    "MISSION_CREATED",
    "MISSION_CLOSED",
    "MISSION_STARTED",
    "MISSION_COMPLETED",
    "MISSION_CANCELLED",
    "PHASE_ENTERED",
    "REVIEW_ROLLBACK",
    "MISSION_EVENT_TYPES",
    "TERMINAL_MISSION_STATUSES",
    "MissionStatus",
    "MissionCreatedPayload",
    "MissionClosedPayload",
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
    "SyncLaneV2",
    "CANONICAL_TO_SYNC_V1",
    "CANONICAL_TO_SYNC_V2",
    "canonical_to_sync_v1",
    "canonical_to_sync_v2",
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
    "NON_DISPLAY_LANES",
    "DISPLAY_LANES",
    "LANE_ALIASES",
    "WP_STATUS_CHANGED",
    "is_bootstrap_planned_event",
    "status_event_sort_key",
    "dedup_events",
    "reduce_status_events",
    "WPState",
    "TransitionAnomaly",
    "ReducedStatus",
    # Canonical project / artifact / WP lifecycle event contracts
    "PROJECT_INITIALIZED",
    "SPECIFY_STARTED",
    "SPECIFY_COMPLETED",
    "PLAN_STARTED",
    "PLAN_COMPLETED",
    "TASKS_STARTED",
    "TASKS_COMPLETED",
    "WP_CREATED",
    "PROJECT_LIFECYCLE_EVENT_TYPES",
    "ARTIFACT_LIFECYCLE_EVENT_TYPES",
    "WP_LIFECYCLE_EVENT_TYPES",
    "CANONICAL_LIFECYCLE_EVENT_TYPES",
    "ArtifactPhase",
    "ProjectInitializedPayload",
    "SpecifyStartedPayload",
    "SpecifyCompletedPayload",
    "PlanStartedPayload",
    "PlanCompletedPayload",
    "TasksStartedPayload",
    "TasksCompletedPayload",
    "WPCreatedPayload",
    # Ops/Invocations bounded moment contracts
    "OPS_INVOCATION_STARTED",
    "OPS_INVOCATION_COMPLETED",
    "OPS_INVOCATION_EVENT_TYPES",
    "OPS_INVOCATION_CONTRACT_VERSION",
    "OpsInvocationOutcome",
    "OpsInvocationStartedPayload",
    "OpsInvocationCompletedPayload",
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
    "ParticipantExternalRefs",
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
    # Analytics event contracts
    "TOKEN_USAGE_RECORDED",
    "DIFF_SUMMARY_RECORDED",
    "ANALYTICS_EVENT_TYPES",
    "TokenUsageRecordedPayload",
    "DiffSummaryRecordedPayload",
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
    # DecisionPoint Lifecycle Contracts (4.0.0 / V1)
    "DECISIONPOINT_SCHEMA_VERSION",
    "DECISION_POINT_DISCUSSING",
    "DECISION_POINT_EVENT_TYPES",
    "DECISION_POINT_OPENED",
    "DECISION_POINT_OVERRIDDEN",
    "DECISION_POINT_RESOLVED",
    "DECISION_POINT_WIDENED",
    "DecisionAuthorityRole",
    "DecisionPointAnomaly",
    "DecisionPointDiscussingAdrPayload",
    "DecisionPointDiscussingInterviewPayload",
    "DecisionPointDiscussingPayload",
    "DecisionPointOpenedAdrPayload",
    "DecisionPointOpenedInterviewPayload",
    "DecisionPointOpenedPayload",
    "DecisionPointOverriddenPayload",
    "DecisionPointResolvedAdrPayload",
    "DecisionPointResolvedInterviewPayload",
    "DecisionPointResolvedPayload",
    "DecisionPointState",
    "DecisionPointWidenedPayload",
    "ReducedDecisionPointState",
    "reduce_decision_point_events",
    # Decision Moment V1 shared models (4.0.0)
    "ClosureMessageRef",
    "DefaultChannelRef",
    "DiscussingSnapshotKind",
    "OriginFlow",
    "OriginSurface",
    "SummaryBlock",
    "SummarySource",
    "TeamspaceRef",
    "TerminalOutcome",
    "ThreadRef",
    "WideningChannel",
    "WideningProjection",
    # Connector Lifecycle Contracts (2.7.0)
    "CONNECTOR_SCHEMA_VERSION",
    "CONNECTOR_PROVISIONED",
    "CONNECTOR_HEALTH_CHECKED",
    "CONNECTOR_DEGRADED",
    "CONNECTOR_REVOKED",
    "CONNECTOR_RECONNECTED",
    "CONNECTOR_EVENT_TYPES",
    "ConnectorState",
    "HealthStatus",
    "ReconnectStrategy",
    "ConnectorAnomaly",
    "ConnectorProvisionedPayload",
    "ConnectorHealthCheckedPayload",
    "ConnectorDegradedPayload",
    "ConnectorRevokedPayload",
    "ConnectorReconnectedPayload",
    "USER_CONNECTED",
    "USER_DISCONNECTED",
    "UserConnectedPayload",
    "UserDisconnectedPayload",
    "UserConnectionStatus",
    "ReducedConnectorState",
    "reduce_connector_events",
    # Profile invocation contracts (3.1.0)
    "PROFILE_INVOCATION_SCHEMA_VERSION",
    "PROFILE_INVOCATION_STARTED",
    "PROFILE_INVOCATION_COMPLETED",
    "PROFILE_INVOCATION_FAILED",
    "PROFILE_INVOCATION_EVENT_TYPES",
    "PROFILE_INVOCATION_RESERVED_TYPES",
    "ProfileInvocationStartedPayload",
    # Retrospective contracts (4.1.0)
    "RETROSPECTIVE_SCHEMA_VERSION",
    "RETROSPECTIVE_COMPLETED",
    "RETROSPECTIVE_SKIPPED",
    "RETROSPECTIVE_REQUESTED_EVENT",
    "RETROSPECTIVE_STARTED_EVENT",
    "RETROSPECTIVE_COMPLETED_EVENT",
    "RETROSPECTIVE_SKIPPED_EVENT",
    "RETROSPECTIVE_FAILED_EVENT",
    "RETROSPECTIVE_PROPOSAL_GENERATED_EVENT",
    "RETROSPECTIVE_PROPOSAL_APPLIED_EVENT",
    "RETROSPECTIVE_PROPOSAL_REJECTED_EVENT",
    "RETROSPECTIVE_EVENT_NAMES",
    "RETROSPECTIVE_EVENT_TYPES",
    "RetrospectiveActorRef",
    "RetrospectiveModeSourceSignal",
    "RetrospectiveMode",
    "RetrospectiveRequestedPayload",
    "RetrospectiveStartedPayload",
    "RetrospectiveLifecycleCompletedPayload",
    "RetrospectiveLifecycleSkippedPayload",
    "RetrospectiveFailedPayload",
    "RetrospectiveProposalGeneratedPayload",
    "RetrospectiveProposalAppliedPayload",
    "RetrospectiveProposalRejectedPayload",
    "RequestedPayload",
    "StartedPayload",
    "CompletedPayload",
    "SkippedPayload",
    "FailedPayload",
    "ProposalGeneratedPayload",
    "ProposalAppliedPayload",
    "ProposalRejectedPayload",
    "RetrospectiveCompletedPayload",
    "RetrospectiveSkippedPayload",
    "TriggerSourceT",
    # Seven canonical contracts shipped by
    # canonical-producer-contracts-legacy-envelope-01KS7JM3 (5.2.0).
    "WP_ASSIGNED",
    "HISTORY_ADDED",
    "ERROR_LOGGED",
    "DEPENDENCY_RESOLVED",
    "WPAssignedPayload",
    "HistoryAddedPayload",
    "ErrorLoggedPayload",
    "DependencyResolvedPayload",
    "MISSION_ORIGIN_BOUND",
    "MissionOriginBoundPayload",
    # Post-mission lifecycle events
    # (mission-lifecycle-dispatch-drg-closeout-01KV0S99).
    "MISSION_REOPENED",
    "FOLLOW_UP_RECORDED",
    "MissionReopenedPayload",
    "FollowUpRecordedPayload",
    "BUILD_REGISTERED",
    "BUILD_HEARTBEAT",
    "BUILD_LIFECYCLE_EVENT_TYPES",
    "BuildRegisteredPayload",
    "BuildHeartbeatPayload",
    # Machine-readable classification surface.
    "LOCAL_ONLY_EVENT_TYPES",
    # HarnessObservation vocabulary (F1-T1, 7.0.0).
    "HARNESS_OBSERVATION",
    "HARNESS_OBSERVATION_CONTRACT_VERSION",
    "ObservationKind",
    "PAYLOAD_ID_BY_KIND",
    "HARNESS_OBSERVATION_PAYLOAD_IDS",
    "FORBIDDEN_OBSERVATION_KEYS",
    "FORBIDDEN_OBSERVATION_KEYS_VERSION",
    "HarnessObservationPayload",
    # Strict journal profile (F1-T1, 7.0.0).
    "STRICT_PROFILE_ID",
    "STRICT_ENVELOPE_KEYS",
    "STRICT_EVENT_TYPES",
    "STRICT_TIMESTAMP_RULES",
    "validate_strict_envelope",
    "SupportRow",
    "SUPPORT_MATRIX",
    "support_matrix_digest",
    # Zeitgeist attrs codecs for the volatile families (E2).
    "VOLATILE_EVENT_TYPES",
    "VolatileMoment",
    "ZEITGEIST_ATTRS_MAX_BYTES",
    "ZEITGEIST_ATTRS_MAX_KEYS",
    "ZEITGEIST_ATTR_KEY_MAX_CHARS",
    "from_zeitgeist_attrs",
    "to_zeitgeist_attrs",
]
