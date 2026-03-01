"""DecisionPoint Lifecycle Event Contracts domain module.

Provides enums, event type constants, payload models,
the ReducedDecisionPointState output model, and a deterministic reducer
for the DecisionPoint Lifecycle contract.

Covers FR-001, FR-002, FR-003.
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import FrozenSet, List, Optional, Sequence, Tuple, Union

from pydantic import BaseModel, ConfigDict, Field

from spec_kitty_events.models import Event
from spec_kitty_events.status import dedup_events, status_event_sort_key

# ── Section 1: Schema Version ─────────────────────────────────────────────────

DECISIONPOINT_SCHEMA_VERSION: str = "2.6.0"

# ── Section 2: Event Type Constants (FR-001) ─────────────────────────────────

DECISION_POINT_OPENED: str = "DecisionPointOpened"
DECISION_POINT_DISCUSSING: str = "DecisionPointDiscussing"
DECISION_POINT_RESOLVED: str = "DecisionPointResolved"
DECISION_POINT_OVERRIDDEN: str = "DecisionPointOverridden"

DECISION_POINT_EVENT_TYPES: FrozenSet[str] = frozenset({
    DECISION_POINT_OPENED,
    DECISION_POINT_DISCUSSING,
    DECISION_POINT_RESOLVED,
    DECISION_POINT_OVERRIDDEN,
})

# ── Section 3: Enums (FR-001) ────────────────────────────────────────────────


class DecisionPointState(str, Enum):
    OPEN = "open"
    DISCUSSING = "discussing"
    RESOLVED = "resolved"
    OVERRIDDEN = "overridden"


class DecisionAuthorityRole(str, Enum):
    MISSION_OWNER = "mission_owner"
    ADVISORY = "advisory"
    INFORMED = "informed"


# Map event types to states
_EVENT_TO_STATE: dict[str, DecisionPointState] = {
    DECISION_POINT_OPENED: DecisionPointState.OPEN,
    DECISION_POINT_DISCUSSING: DecisionPointState.DISCUSSING,
    DECISION_POINT_RESOLVED: DecisionPointState.RESOLVED,
    DECISION_POINT_OVERRIDDEN: DecisionPointState.OVERRIDDEN,
}

# Allowed transitions: from_state -> set of valid to_states
_ALLOWED_TRANSITIONS: dict[Optional[DecisionPointState], FrozenSet[DecisionPointState]] = {
    None: frozenset({DecisionPointState.OPEN}),
    DecisionPointState.OPEN: frozenset({DecisionPointState.DISCUSSING, DecisionPointState.RESOLVED}),
    DecisionPointState.DISCUSSING: frozenset({DecisionPointState.DISCUSSING, DecisionPointState.RESOLVED}),
    DecisionPointState.RESOLVED: frozenset({DecisionPointState.OVERRIDDEN}),
    DecisionPointState.OVERRIDDEN: frozenset(),
}

# States that require human mission-owner authority
_AUTHORITY_REQUIRED_STATES: FrozenSet[DecisionPointState] = frozenset({
    DecisionPointState.RESOLVED,
    DecisionPointState.OVERRIDDEN,
})

# ── Section 4: Anomaly Model ─────────────────────────────────────────────────


class DecisionPointAnomaly(BaseModel):
    """Non-fatal issue recorded during DecisionPoint reduction.

    Valid kind values: "invalid_transition", "authority_policy_violation",
    "llm_policy_violation", "malformed_payload", "event_after_terminal".
    """

    model_config = ConfigDict(frozen=True)

    kind: str
    event_id: str
    message: str


# ── Section 5: Payload Models (FR-002) ───────────────────────────────────────


class DecisionPointOpenedPayload(BaseModel):
    """Payload for DecisionPointOpened events."""

    model_config = ConfigDict(frozen=True)

    decision_point_id: str = Field(..., min_length=1)
    mission_id: str = Field(..., min_length=1)
    run_id: str = Field(..., min_length=1)
    feature_slug: str = Field(..., min_length=1)
    phase: str = Field(..., min_length=1)
    actor_id: str = Field(..., min_length=1)
    actor_type: str = Field(..., pattern=r"^(human|llm|service)$")
    authority_role: DecisionAuthorityRole
    mission_owner_authority_flag: bool
    mission_owner_authority_path: str
    rationale: str = Field(..., min_length=1)
    alternatives_considered: Tuple[str, ...] = Field(..., min_length=1)
    evidence_refs: Tuple[str, ...] = Field(..., min_length=1)
    state_entered_at: datetime
    recorded_at: datetime


class DecisionPointDiscussingPayload(BaseModel):
    """Payload for DecisionPointDiscussing events."""

    model_config = ConfigDict(frozen=True)

    decision_point_id: str = Field(..., min_length=1)
    mission_id: str = Field(..., min_length=1)
    run_id: str = Field(..., min_length=1)
    feature_slug: str = Field(..., min_length=1)
    phase: str = Field(..., min_length=1)
    actor_id: str = Field(..., min_length=1)
    actor_type: str = Field(..., pattern=r"^(human|llm|service)$")
    authority_role: DecisionAuthorityRole
    mission_owner_authority_flag: bool
    mission_owner_authority_path: str
    rationale: str = Field(..., min_length=1)
    alternatives_considered: Tuple[str, ...] = Field(..., min_length=1)
    evidence_refs: Tuple[str, ...] = Field(..., min_length=1)
    state_entered_at: datetime
    recorded_at: datetime


class DecisionPointResolvedPayload(BaseModel):
    """Payload for DecisionPointResolved events."""

    model_config = ConfigDict(frozen=True)

    decision_point_id: str = Field(..., min_length=1)
    mission_id: str = Field(..., min_length=1)
    run_id: str = Field(..., min_length=1)
    feature_slug: str = Field(..., min_length=1)
    phase: str = Field(..., min_length=1)
    actor_id: str = Field(..., min_length=1)
    actor_type: str = Field(..., pattern=r"^(human|llm|service)$")
    authority_role: DecisionAuthorityRole
    mission_owner_authority_flag: bool
    mission_owner_authority_path: str
    rationale: str = Field(..., min_length=1)
    alternatives_considered: Tuple[str, ...] = Field(..., min_length=1)
    evidence_refs: Tuple[str, ...] = Field(..., min_length=1)
    state_entered_at: datetime
    recorded_at: datetime


class DecisionPointOverriddenPayload(BaseModel):
    """Payload for DecisionPointOverridden events."""

    model_config = ConfigDict(frozen=True)

    decision_point_id: str = Field(..., min_length=1)
    mission_id: str = Field(..., min_length=1)
    run_id: str = Field(..., min_length=1)
    feature_slug: str = Field(..., min_length=1)
    phase: str = Field(..., min_length=1)
    actor_id: str = Field(..., min_length=1)
    actor_type: str = Field(..., pattern=r"^(human|llm|service)$")
    authority_role: DecisionAuthorityRole
    mission_owner_authority_flag: bool
    mission_owner_authority_path: str
    rationale: str = Field(..., min_length=1)
    alternatives_considered: Tuple[str, ...] = Field(..., min_length=1)
    evidence_refs: Tuple[str, ...] = Field(..., min_length=1)
    state_entered_at: datetime
    recorded_at: datetime


# Union of all payload types for type-safe access in the reducer
DecisionPointPayload = Union[
    DecisionPointOpenedPayload,
    DecisionPointDiscussingPayload,
    DecisionPointResolvedPayload,
    DecisionPointOverriddenPayload,
]

# Map event types to their payload models
_EVENT_TO_PAYLOAD: dict[str, type[DecisionPointPayload]] = {
    DECISION_POINT_OPENED: DecisionPointOpenedPayload,
    DECISION_POINT_DISCUSSING: DecisionPointDiscussingPayload,
    DECISION_POINT_RESOLVED: DecisionPointResolvedPayload,
    DECISION_POINT_OVERRIDDEN: DecisionPointOverriddenPayload,
}

# ── Section 6: Reducer Output Model ──────────────────────────────────────────


class ReducedDecisionPointState(BaseModel):
    """Deterministic projection output of reduce_decision_point_events()."""

    model_config = ConfigDict(frozen=True)

    state: Optional[DecisionPointState] = None
    decision_point_id: Optional[str] = None
    mission_id: Optional[str] = None
    run_id: Optional[str] = None
    feature_slug: Optional[str] = None
    phase: Optional[str] = None
    last_actor_id: Optional[str] = None
    last_actor_type: Optional[str] = None
    last_authority_role: Optional[DecisionAuthorityRole] = None
    last_rationale: Optional[str] = None
    last_alternatives_considered: Optional[Tuple[str, ...]] = None
    last_evidence_refs: Optional[Tuple[str, ...]] = None
    last_state_entered_at: Optional[datetime] = None
    anomalies: Tuple[DecisionPointAnomaly, ...] = ()
    event_count: int = 0


# ── Section 7: Reducer (FR-003) ──────────────────────────────────────────────


def reduce_decision_point_events(
    events: Sequence[Event],
) -> ReducedDecisionPointState:
    """Deterministic reducer: Sequence[Event] -> ReducedDecisionPointState.

    Pipeline: sort -> dedup -> filter(DECISION_POINT_EVENT_TYPES) -> fold -> freeze.

    Transition rules:
      None -> open
      open -> discussing | resolved
      discussing -> discussing | resolved
      resolved -> overridden
      overridden -> (terminal, no further transitions)

    Authority policy:
      resolved and overridden require actor_type="human", authority_role="mission_owner",
      and mission_owner_authority_flag=True.

    LLM policy:
      LLM actors allowed only when phase="P0", authority_role in {advisory, informed},
      and mission_owner_authority_flag=False.
    """
    # Step 1: Sort for determinism
    sorted_events = sorted(events, key=status_event_sort_key)

    # Step 2: Deduplicate by event_id
    deduped = dedup_events(sorted_events)

    # Step 3: Count post-dedup (before filter)
    event_count = len(deduped)

    # Step 4: Filter to DecisionPoint family
    dp_events = [e for e in deduped if e.event_type in DECISION_POINT_EVENT_TYPES]

    # Step 5: Mutable accumulator for fold
    anomalies: List[DecisionPointAnomaly] = []
    current_state: Optional[DecisionPointState] = None
    decision_point_id: Optional[str] = None
    mission_id: Optional[str] = None
    run_id: Optional[str] = None
    feature_slug: Optional[str] = None
    phase: Optional[str] = None
    last_actor_id: Optional[str] = None
    last_actor_type: Optional[str] = None
    last_authority_role: Optional[DecisionAuthorityRole] = None
    last_rationale: Optional[str] = None
    last_alternatives_considered: Optional[Tuple[str, ...]] = None
    last_evidence_refs: Optional[Tuple[str, ...]] = None
    last_state_entered_at: Optional[datetime] = None

    for event in dp_events:
        event_type = event.event_type
        event_id = event.event_id
        payload_dict = event.payload if isinstance(event.payload, dict) else {}

        # Determine target state from event type
        target_state = _EVENT_TO_STATE.get(event_type)
        if target_state is None:
            anomalies.append(DecisionPointAnomaly(
                kind="malformed_payload",
                event_id=event_id,
                message=f"Unknown event type in DecisionPoint family: {event_type!r}",
            ))
            continue

        # Check: event after terminal (overridden)
        if current_state == DecisionPointState.OVERRIDDEN:
            anomalies.append(DecisionPointAnomaly(
                kind="event_after_terminal",
                event_id=event_id,
                message=f"Event {event_type!r} arrived after terminal state 'overridden'",
            ))
            continue

        # Check: valid transition
        allowed = _ALLOWED_TRANSITIONS.get(current_state, frozenset())
        if target_state not in allowed:
            anomalies.append(DecisionPointAnomaly(
                kind="invalid_transition",
                event_id=event_id,
                message=(
                    f"Invalid transition: {current_state.value if current_state else 'None'} "
                    f"-> {target_state.value}"
                ),
            ))
            continue

        # Parse payload
        payload_cls = _EVENT_TO_PAYLOAD[event_type]
        try:
            payload: DecisionPointPayload = payload_cls.model_validate(payload_dict)
        except Exception as exc:
            anomalies.append(DecisionPointAnomaly(
                kind="malformed_payload",
                event_id=event_id,
                message=f"Payload validation failed for {event_type!r}: {exc}",
            ))
            continue

        # Authority policy check for resolved/overridden (FR-003)
        if target_state in _AUTHORITY_REQUIRED_STATES:
            if (
                payload.actor_type != "human"
                or payload.authority_role != DecisionAuthorityRole.MISSION_OWNER
                or not payload.mission_owner_authority_flag
            ):
                anomalies.append(DecisionPointAnomaly(
                    kind="authority_policy_violation",
                    event_id=event_id,
                    message=(
                        f"{event_type!r} requires actor_type='human', "
                        f"authority_role='mission_owner', and "
                        f"mission_owner_authority_flag=True; got "
                        f"actor_type={payload.actor_type!r}, "
                        f"authority_role={payload.authority_role.value!r}, "
                        f"mission_owner_authority_flag={payload.mission_owner_authority_flag!r}"
                    ),
                ))
                continue

        # LLM policy check (FR-003)
        if payload.actor_type == "llm":
            if payload.phase != "P0":
                anomalies.append(DecisionPointAnomaly(
                    kind="llm_policy_violation",
                    event_id=event_id,
                    message=(
                        f"LLM actor only allowed in phase='P0'; "
                        f"got phase={payload.phase!r}"
                    ),
                ))
                continue
            if payload.authority_role not in (
                DecisionAuthorityRole.ADVISORY,
                DecisionAuthorityRole.INFORMED,
            ):
                anomalies.append(DecisionPointAnomaly(
                    kind="llm_policy_violation",
                    event_id=event_id,
                    message=(
                        f"LLM actor must have advisory or informed role; "
                        f"got authority_role={payload.authority_role.value!r}"
                    ),
                ))
                continue
            if payload.mission_owner_authority_flag:
                anomalies.append(DecisionPointAnomaly(
                    kind="llm_policy_violation",
                    event_id=event_id,
                    message="LLM actor must not carry mission-owner authority",
                ))
                continue

        # Apply transition
        current_state = target_state
        decision_point_id = payload.decision_point_id
        mission_id = payload.mission_id
        run_id = payload.run_id
        feature_slug = payload.feature_slug
        phase = payload.phase
        last_actor_id = payload.actor_id
        last_actor_type = payload.actor_type
        last_authority_role = payload.authority_role
        last_rationale = payload.rationale
        last_alternatives_considered = payload.alternatives_considered
        last_evidence_refs = payload.evidence_refs
        last_state_entered_at = payload.state_entered_at

    # Step 6: Freeze and return
    return ReducedDecisionPointState(
        state=current_state,
        decision_point_id=decision_point_id,
        mission_id=mission_id,
        run_id=run_id,
        feature_slug=feature_slug,
        phase=phase,
        last_actor_id=last_actor_id,
        last_actor_type=last_actor_type,
        last_authority_role=last_authority_role,
        last_rationale=last_rationale,
        last_alternatives_considered=last_alternatives_considered,
        last_evidence_refs=last_evidence_refs,
        last_state_entered_at=last_state_entered_at,
        anomalies=tuple(anomalies),
        event_count=event_count,
    )
