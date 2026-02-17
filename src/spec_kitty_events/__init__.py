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
"""

__version__ = "2.2.0"

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
]
