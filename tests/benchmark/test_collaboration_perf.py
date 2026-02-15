"""Performance benchmark for collaboration reducer with 10K events."""

import random
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Dict, List

import pytest
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
    reduce_collaboration_events,
)
from spec_kitty_events.models import Event

_PROJECT_UUID = uuid.UUID("12345678-1234-5678-1234-567812345678")
_MISSION_ID = "BENCH-001"


def _generate_10k_events() -> tuple[List[Event], Dict[str, ParticipantIdentity]]:
    """Generate 10,000 collaboration events with 50 participants.

    Event type distribution:
    - ~5% join/left (500 events)
    - ~30% heartbeat (3000 events)
    - ~20% intent/focus (2000 events)
    - ~15% execution (1500 events)
    - ~10% warnings (1000 events)
    - ~10% comments (1000 events)
    - ~10% session (1000 events)
    """
    rng = random.Random(42)
    base_time = datetime(2026, 1, 1, tzinfo=timezone.utc)
    corr_id = str(ULID())
    events: List[Event] = []
    clock = 0

    num_participants = 50
    roster: Dict[str, ParticipantIdentity] = {}
    participant_ids: List[str] = []

    for i in range(num_participants):
        pid = f"agent-{i:03d}"
        participant_ids.append(pid)
        roster[pid] = ParticipantIdentity(
            participant_id=pid,
            participant_type="llm_context",
            display_name=f"Benchmark Agent {i}",
        )

    # Join events for all 50 participants
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

    # Weighted event types for remaining events
    # The weights produce roughly the target distribution
    weighted_types = (
        [PRESENCE_HEARTBEAT] * 30
        + [DRIVE_INTENT_SET] * 10
        + [FOCUS_CHANGED] * 10
        + [PROMPT_STEP_EXECUTION_STARTED] * 8
        + [PROMPT_STEP_EXECUTION_COMPLETED] * 7
        + [CONCURRENT_DRIVER_WARNING] * 5
        + [WARNING_ACKNOWLEDGED] * 5
        + [COMMENT_POSTED] * 10
        + [DECISION_CAPTURED] * 5
        + [SESSION_LINKED] * 10
    )

    warning_counter = 0
    step_counter = 0
    comment_counter = 0
    decision_counter = 0
    active_warnings: List[str] = []
    active_steps: Dict[str, List[str]] = {}

    remaining = 10000 - len(events)
    for _ in range(remaining):
        clock += 1
        et = rng.choice(weighted_types)
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
                    "target_id": f"WP{rng.randint(1, 10):02d}",
                },
                "previous_focus_target": None,
            }
        elif et == PROMPT_STEP_EXECUTION_STARTED:
            step_counter += 1
            step_id = f"step-{step_counter:06d}"
            if pid not in active_steps:
                active_steps[pid] = []
            active_steps[pid].append(step_id)
            payload = {
                "participant_id": pid,
                "mission_id": _MISSION_ID,
                "step_id": step_id,
                "wp_id": f"WP{rng.randint(1, 10):02d}",
            }
        elif et == PROMPT_STEP_EXECUTION_COMPLETED:
            # Complete an active step if available, else start+complete
            pid_steps = active_steps.get(pid, [])
            if pid_steps:
                completed_step = pid_steps.pop(0)
            else:
                step_counter += 1
                completed_step = f"step-{step_counter:06d}"
                # Insert a start event first
                events.append(
                    Event(
                        event_id=str(ULID()),
                        event_type=PROMPT_STEP_EXECUTION_STARTED,
                        aggregate_id=f"mission/{_MISSION_ID}",
                        payload={
                            "participant_id": pid,
                            "mission_id": _MISSION_ID,
                            "step_id": completed_step,
                        },
                        timestamp=base_time + timedelta(seconds=clock),
                        node_id="node-1",
                        lamport_clock=clock,
                        project_uuid=_PROJECT_UUID,
                        correlation_id=corr_id,
                    )
                )
                clock += 1
            payload = {
                "participant_id": pid,
                "mission_id": _MISSION_ID,
                "step_id": completed_step,
                "outcome": rng.choice(["success", "failure", "skipped"]),
            }
        elif et == CONCURRENT_DRIVER_WARNING:
            warning_counter += 1
            warn_id = f"warn-{warning_counter:06d}"
            active_warnings.append(warn_id)
            warn_pids = rng.sample(participant_ids, k=2)
            payload = {
                "warning_id": warn_id,
                "mission_id": _MISSION_ID,
                "participant_ids": warn_pids,
                "focus_target": {
                    "target_type": "wp",
                    "target_id": f"WP{rng.randint(1, 10):02d}",
                },
                "severity": rng.choice(["info", "warning"]),
            }
        elif et == WARNING_ACKNOWLEDGED:
            if active_warnings:
                warn_id = rng.choice(active_warnings)
            else:
                # Create a warning first
                warning_counter += 1
                warn_id = f"warn-{warning_counter:06d}"
                active_warnings.append(warn_id)
                warn_pids = rng.sample(participant_ids, k=2)
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
                                "target_id": "WP01",
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
                clock += 1
            payload = {
                "participant_id": pid,
                "mission_id": _MISSION_ID,
                "warning_id": warn_id,
                "acknowledgement": rng.choice(
                    ["continue", "hold", "reassign", "defer"]
                ),
            }
        elif et == COMMENT_POSTED:
            comment_counter += 1
            payload = {
                "participant_id": pid,
                "mission_id": _MISSION_ID,
                "comment_id": f"comment-{comment_counter:06d}",
                "content": f"Benchmark comment {comment_counter}",
            }
        elif et == DECISION_CAPTURED:
            decision_counter += 1
            payload = {
                "participant_id": pid,
                "mission_id": _MISSION_ID,
                "decision_id": f"dec-{decision_counter:06d}",
                "topic": f"Decision {decision_counter}",
                "chosen_option": "option-A",
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

    # Trim or pad to exactly 10K
    events = events[:10000]

    return events, roster


@pytest.mark.benchmark
def test_collaboration_reducer_10k_events() -> None:
    """Reduce 10,000 collaboration events in under 1.0 seconds."""
    events, roster = _generate_10k_events()

    assert len(events) == 10000, f"Expected 10000 events, got {len(events)}"

    start = time.perf_counter()
    state = reduce_collaboration_events(events, mode="permissive", roster=roster)
    elapsed = time.perf_counter() - start

    assert state.event_count > 0, "Reducer must process events"
    assert elapsed < 1.0, f"Reducer took {elapsed:.3f}s, expected < 1.0s"
