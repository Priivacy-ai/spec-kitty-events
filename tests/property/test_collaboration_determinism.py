"""Property tests proving collaboration reducer determinism."""

import random
import uuid
from datetime import datetime, timedelta, timezone
from itertools import groupby
from typing import Dict, List

from hypothesis import given, settings
from hypothesis import strategies as st
from ulid import ULID

from spec_kitty_events.collaboration import (
    COMMENT_POSTED,
    CONCURRENT_DRIVER_WARNING,
    DECISION_CAPTURED,
    DRIVE_INTENT_SET,
    FOCUS_CHANGED,
    PARTICIPANT_JOINED,
    PARTICIPANT_LEFT,
    PRESENCE_HEARTBEAT,
    PROMPT_STEP_EXECUTION_COMPLETED,
    PROMPT_STEP_EXECUTION_STARTED,
    SESSION_LINKED,
    WARNING_ACKNOWLEDGED,
    ParticipantIdentity,
    ReducedCollaborationState,
    reduce_collaboration_events,
)
from spec_kitty_events.models import Event

_PROJECT_UUID = uuid.UUID("12345678-1234-5678-1234-567812345678")
_MISSION_ID = "M001"


def _build_collaboration_sequence(
    rng: random.Random,
    num_participants: int,
    num_extra_events: int,
) -> tuple[List[Event], Dict[str, ParticipantIdentity]]:
    """Build a collaboration event sequence with join events first.

    Returns (events, roster) where roster maps participant_id -> ParticipantIdentity.
    """
    base_time = datetime(2026, 1, 1, tzinfo=timezone.utc)
    corr_id = str(ULID())
    events: List[Event] = []
    clock = 0

    # Build participant identities
    roster: Dict[str, ParticipantIdentity] = {}
    participant_ids: List[str] = []
    for i in range(num_participants):
        pid = f"agent-{i:03d}"
        participant_ids.append(pid)
        roster[pid] = ParticipantIdentity(
            participant_id=pid,
            participant_type="llm_context",
            display_name=f"Agent {i}",
        )

    # Join events for all participants
    for pid in participant_ids:
        clock += 1
        identity = roster[pid]
        events.append(
            Event(
                event_id=str(ULID()),
                event_type=PARTICIPANT_JOINED,
                aggregate_id=f"mission/{_MISSION_ID}",
                payload={
                    "participant_id": pid,
                    "participant_identity": identity.model_dump(),
                    "mission_id": _MISSION_ID,
                },
                timestamp=base_time + timedelta(seconds=clock),
                node_id="node-1",
                lamport_clock=clock,
                project_uuid=_PROJECT_UUID,
                correlation_id=corr_id,
            )
        )

    # Mixed event types
    event_types = [
        PRESENCE_HEARTBEAT,
        DRIVE_INTENT_SET,
        FOCUS_CHANGED,
        PROMPT_STEP_EXECUTION_STARTED,
        COMMENT_POSTED,
        SESSION_LINKED,
    ]

    warning_counter = 0
    step_counter = 0
    comment_counter = 0
    decision_counter = 0

    # Track active executions for proper completion pairing
    active_steps: Dict[str, List[str]] = {}

    for _ in range(num_extra_events):
        clock += 1
        et = rng.choice(event_types)
        pid = rng.choice(participant_ids)

        if et == PRESENCE_HEARTBEAT:
            payload = {
                "participant_id": pid,
                "mission_id": _MISSION_ID,
            }
        elif et == DRIVE_INTENT_SET:
            payload = {
                "participant_id": pid,
                "mission_id": _MISSION_ID,
                "intent": rng.choice(["active", "inactive"]),
            }
        elif et == FOCUS_CHANGED:
            payload = {
                "participant_id": pid,
                "mission_id": _MISSION_ID,
                "focus_target": {
                    "target_type": rng.choice(["wp", "step", "file"]),
                    "target_id": f"WP{rng.randint(1, 5):02d}",
                },
                "previous_focus_target": None,
            }
        elif et == PROMPT_STEP_EXECUTION_STARTED:
            step_counter += 1
            step_id = f"step-{step_counter:04d}"
            if pid not in active_steps:
                active_steps[pid] = []
            active_steps[pid].append(step_id)
            payload = {
                "participant_id": pid,
                "mission_id": _MISSION_ID,
                "step_id": step_id,
                "wp_id": f"WP{rng.randint(1, 5):02d}",
            }
        elif et == COMMENT_POSTED:
            comment_counter += 1
            payload = {
                "participant_id": pid,
                "mission_id": _MISSION_ID,
                "comment_id": f"comment-{comment_counter:04d}",
                "content": f"Comment {comment_counter}",
            }
        elif et == SESSION_LINKED:
            payload = {
                "participant_id": pid,
                "mission_id": _MISSION_ID,
                "primary_session_id": f"sess-{pid}-primary",
                "linked_session_id": f"sess-{pid}-linked-{clock}",
                "link_type": rng.choice(["cli_to_saas", "saas_to_cli"]),
            }
        else:
            continue

        events.append(
            Event(
                event_id=str(ULID()),
                event_type=et,
                aggregate_id=f"mission/{_MISSION_ID}",
                payload=payload,
                timestamp=base_time + timedelta(seconds=clock),
                node_id="node-1",
                lamport_clock=clock,
                project_uuid=_PROJECT_UUID,
                correlation_id=corr_id,
            )
        )

        # Occasionally complete an active step
        if active_steps.get(pid) and rng.random() < 0.5:
            clock += 1
            completed_step = active_steps[pid].pop(0)
            events.append(
                Event(
                    event_id=str(ULID()),
                    event_type=PROMPT_STEP_EXECUTION_COMPLETED,
                    aggregate_id=f"mission/{_MISSION_ID}",
                    payload={
                        "participant_id": pid,
                        "mission_id": _MISSION_ID,
                        "step_id": completed_step,
                        "outcome": rng.choice(["success", "failure", "skipped"]),
                    },
                    timestamp=base_time + timedelta(seconds=clock),
                    node_id="node-1",
                    lamport_clock=clock,
                    project_uuid=_PROJECT_UUID,
                    correlation_id=corr_id,
                )
            )

        # Occasionally emit a warning + acknowledgement
        if rng.random() < 0.1 and len(participant_ids) >= 2:
            clock += 1
            warning_counter += 1
            warn_id = f"warn-{warning_counter:04d}"
            warn_pids = rng.sample(participant_ids, k=min(2, len(participant_ids)))
            events.append(
                Event(
                    event_id=str(ULID()),
                    event_type=CONCURRENT_DRIVER_WARNING,
                    aggregate_id=f"mission/{_MISSION_ID}",
                    payload={
                        "warning_id": warn_id,
                        "mission_id": _MISSION_ID,
                        "participant_ids": warn_pids,
                        "focus_target": {
                            "target_type": "wp",
                            "target_id": f"WP{rng.randint(1, 5):02d}",
                        },
                        "severity": "warning",
                    },
                    timestamp=base_time + timedelta(seconds=clock),
                    node_id="node-1",
                    lamport_clock=clock,
                    project_uuid=_PROJECT_UUID,
                    correlation_id=corr_id,
                )
            )

            # Acknowledge warning
            clock += 1
            ack_pid = rng.choice(warn_pids)
            events.append(
                Event(
                    event_id=str(ULID()),
                    event_type=WARNING_ACKNOWLEDGED,
                    aggregate_id=f"mission/{_MISSION_ID}",
                    payload={
                        "participant_id": ack_pid,
                        "mission_id": _MISSION_ID,
                        "warning_id": warn_id,
                        "acknowledgement": rng.choice(
                            ["continue", "hold", "reassign", "defer"]
                        ),
                    },
                    timestamp=base_time + timedelta(seconds=clock),
                    node_id="node-1",
                    lamport_clock=clock,
                    project_uuid=_PROJECT_UUID,
                    correlation_id=corr_id,
                )
            )

        # Occasionally emit a decision
        if rng.random() < 0.08:
            clock += 1
            decision_counter += 1
            events.append(
                Event(
                    event_id=str(ULID()),
                    event_type=DECISION_CAPTURED,
                    aggregate_id=f"mission/{_MISSION_ID}",
                    payload={
                        "participant_id": pid,
                        "mission_id": _MISSION_ID,
                        "decision_id": f"dec-{decision_counter:04d}",
                        "topic": f"Decision topic {decision_counter}",
                        "chosen_option": "option-A",
                    },
                    timestamp=base_time + timedelta(seconds=clock),
                    node_id="node-1",
                    lamport_clock=clock,
                    project_uuid=_PROJECT_UUID,
                    correlation_id=corr_id,
                )
            )

    return events, roster


def _shuffle_preserving_causal_order(
    events: List[Event], rng: random.Random
) -> List[Event]:
    """Shuffle events while preserving causal order (Lamport clock)."""
    sorted_events = sorted(events, key=lambda e: e.lamport_clock)
    groups: List[List[Event]] = []
    for _clock, group_iter in groupby(
        sorted_events, key=lambda e: e.lamport_clock
    ):
        group = list(group_iter)
        rng.shuffle(group)
        groups.append(group)
    rng.shuffle(groups)
    # Re-sort groups by their first event's clock to preserve causal order
    groups.sort(key=lambda g: g[0].lamport_clock)
    return [e for g in groups for e in g]


@settings(max_examples=200, deadline=None)
@given(seed=st.integers(min_value=0, max_value=2**32))
def test_reducer_determinism_strict_mode(seed: int) -> None:
    """Same events in different physical orderings produce identical state (strict)."""
    rng = random.Random(seed)
    num_participants = rng.randint(2, 5)
    num_extra = rng.randint(5, 20)
    events, roster = _build_collaboration_sequence(rng, num_participants, num_extra)

    shuffled = _shuffle_preserving_causal_order(list(events), random.Random(seed + 1))

    result_original = reduce_collaboration_events(
        events, mode="strict", roster=roster
    )
    result_shuffled = reduce_collaboration_events(
        shuffled, mode="strict", roster=roster
    )

    assert result_original == result_shuffled


@settings(max_examples=200, deadline=None)
@given(seed=st.integers(min_value=0, max_value=2**32))
def test_reducer_determinism_permissive_mode(seed: int) -> None:
    """Same events in different physical orderings produce identical state (permissive)."""
    rng = random.Random(seed)
    num_participants = rng.randint(2, 5)
    num_extra = rng.randint(5, 20)
    events, roster = _build_collaboration_sequence(rng, num_participants, num_extra)

    shuffled = _shuffle_preserving_causal_order(list(events), random.Random(seed + 1))

    result_original = reduce_collaboration_events(
        events, mode="permissive", roster=roster
    )
    result_shuffled = reduce_collaboration_events(
        shuffled, mode="permissive", roster=roster
    )

    assert result_original == result_shuffled


@settings(max_examples=200, deadline=None)
@given(seed=st.integers(min_value=0, max_value=2**32))
def test_idempotent_dedup_property(seed: int) -> None:
    """Duplicating events does not change reducer output."""
    rng = random.Random(seed)
    num_participants = rng.randint(2, 5)
    num_extra = rng.randint(5, 20)
    events, roster = _build_collaboration_sequence(rng, num_participants, num_extra)

    # Duplicate some events randomly
    duplicated = list(events)
    for event in events:
        if rng.random() < 0.5:
            duplicated.append(event)

    result_original = reduce_collaboration_events(
        events, mode="strict", roster=roster
    )
    result_duplicated = reduce_collaboration_events(
        duplicated, mode="strict", roster=roster
    )

    assert result_original.event_count == result_duplicated.event_count
    assert result_original.participants == result_duplicated.participants
    assert result_original.active_drivers == result_duplicated.active_drivers
    assert result_original.warnings == result_duplicated.warnings
    assert result_original.decisions == result_duplicated.decisions
    assert result_original.comments == result_duplicated.comments
