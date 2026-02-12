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

__version__ = "2.0.0rc1"

# Core data models
from spec_kitty_events.models import (
    Event,
    ErrorEntry,
    ConflictResolution,
    SpecKittyEventsError,
    StorageError,
    ValidationError,
    CyclicDependencyError,
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

# Conformance fixtures
from spec_kitty_events.conformance.loader import (
    FixtureCase,
    load_fixtures,
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

# Public API (controls what's exported with "from spec_kitty_events import *")
__all__ = [
    # Version
    "__version__",
    # Models
    "Event",
    "ErrorEntry",
    "ConflictResolution",
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
    # Conformance fixtures
    "FixtureCase",
    "load_fixtures",
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
]
