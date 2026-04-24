"""Generate V1 golden replay fixtures for WP06.

Run from the worktree root with:
    python -c "import sys; sys.path.insert(0, 'src'); exec(open('scripts/generate_v1_golden_fixtures.py').read())"
"""
import json
import shutil
from pathlib import Path

# ── Imports ──────────────────────────────────────────────────────────────────
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from spec_kitty_events.models import Event
from spec_kitty_events.decisionpoint import reduce_decision_point_events

FIXTURE_DIR = Path("tests/fixtures/decisionpoint_golden")
CONFORMANCE_DIR = Path("src/spec_kitty_events/conformance/fixtures/decisionpoint/replay")

# ── Stable ULIDs per scenario ─────────────────────────────────────────────────
# Each scenario gets a block of 10 ULIDs (event_ids + correlation_ids)
# Format: 01J2A0000000000000000000XX  (stable, ULID-shaped)

PROJECT_UUID = "bbbbbbbb-cccc-dddd-eeee-ffffffffffff"

# ── Scenario 1: replay_interview_local_only_resolved ─────────────────────────
# 2 events: Opened(interview) -> Resolved(interview, terminal=resolved, final_answer="oauth2")

S1_EVENTS = [
    {
        "aggregate_id": "dp/dp-iv-001",
        "build_id": "test-build",
        "causation_id": None,
        "correlation_id": "01J2A0000000000000000000A2",
        "data_tier": 0,
        "event_id": "01J2A0000000000000000000A1",
        "event_type": "DecisionPointOpened",
        "lamport_clock": 1,
        "node_id": "node-1",
        "payload": {
            "origin_surface": "planning_interview",
            "decision_point_id": "dp-iv-001",
            "mission_id": "m-interview-001",
            "run_id": "run-iv-001",
            "mission_slug": "auth-migration",
            "mission_type": "software-dev",
            "phase": "P1",
            "origin_flow": "specify",
            "question": "Which authentication protocol should we adopt?",
            "options": ["session", "oauth2", "oidc"],
            "input_key": "auth_protocol",
            "step_id": "step-auth-001",
            "actor_id": "human-owner-1",
            "actor_type": "human",
            "state_entered_at": "2026-04-23T10:00:00+00:00",
            "recorded_at": "2026-04-23T10:00:00+00:00",
        },
        "project_slug": None,
        "project_uuid": PROJECT_UUID,
        "schema_version": "3.0.0",
        "timestamp": "2026-04-23T10:00:00+00:00",
    },
    {
        "aggregate_id": "dp/dp-iv-001",
        "build_id": "test-build",
        "causation_id": None,
        "correlation_id": "01J2A0000000000000000000A4",
        "data_tier": 0,
        "event_id": "01J2A0000000000000000000A3",
        "event_type": "DecisionPointResolved",
        "lamport_clock": 2,
        "node_id": "node-1",
        "payload": {
            "origin_surface": "planning_interview",
            "decision_point_id": "dp-iv-001",
            "mission_id": "m-interview-001",
            "run_id": "run-iv-001",
            "mission_slug": "auth-migration",
            "mission_type": "software-dev",
            "terminal_outcome": "resolved",
            "final_answer": "oauth2",
            "other_answer": False,
            "rationale": None,
            "summary": None,
            "actual_participants": [],
            "resolved_by": "human-owner-1",
            "closed_locally_while_widened": False,
            "closure_message": None,
            "state_entered_at": "2026-04-23T10:00:01+00:00",
            "recorded_at": "2026-04-23T10:00:01+00:00",
        },
        "project_slug": None,
        "project_uuid": PROJECT_UUID,
        "schema_version": "3.0.0",
        "timestamp": "2026-04-23T10:00:01+00:00",
    },
]

# ── Scenario 2: replay_interview_widened_resolved ────────────────────────────
# 4 events: Opened -> Widened -> Discussing(digest) -> Resolved

S2_EVENTS = [
    {
        "aggregate_id": "dp/dp-iv-002",
        "build_id": "test-build",
        "causation_id": None,
        "correlation_id": "01J2A0000000000000000000B2",
        "data_tier": 0,
        "event_id": "01J2A0000000000000000000B1",
        "event_type": "DecisionPointOpened",
        "lamport_clock": 1,
        "node_id": "node-1",
        "payload": {
            "origin_surface": "planning_interview",
            "decision_point_id": "dp-iv-002",
            "mission_id": "m-interview-002",
            "run_id": "run-iv-002",
            "mission_slug": "data-pipeline",
            "mission_type": "software-dev",
            "phase": "P2",
            "origin_flow": "plan",
            "question": "How should we handle schema migration in production?",
            "options": ["blue-green", "rolling", "canary", "Other"],
            "input_key": "migration_strategy",
            "step_id": "step-mig-001",
            "actor_id": "human-owner-2",
            "actor_type": "human",
            "state_entered_at": "2026-04-23T10:00:00+00:00",
            "recorded_at": "2026-04-23T10:00:00+00:00",
        },
        "project_slug": None,
        "project_uuid": PROJECT_UUID,
        "schema_version": "3.0.0",
        "timestamp": "2026-04-23T10:00:00+00:00",
    },
    {
        "aggregate_id": "dp/dp-iv-002",
        "build_id": "test-build",
        "causation_id": None,
        "correlation_id": "01J2A0000000000000000000B4",
        "data_tier": 0,
        "event_id": "01J2A0000000000000000000B3",
        "event_type": "DecisionPointWidened",
        "lamport_clock": 2,
        "node_id": "node-1",
        "payload": {
            "origin_surface": "planning_interview",
            "decision_point_id": "dp-iv-002",
            "mission_id": "m-interview-002",
            "run_id": "run-iv-002",
            "mission_slug": "data-pipeline",
            "mission_type": "software-dev",
            "channel": "slack",
            "teamspace_ref": {
                "teamspace_id": "ts-acme-001",
                "name": "Acme Engineering",
            },
            "default_channel_ref": {
                "channel_id": "C0123456789",
                "name": "spec-kitty-decisions",
            },
            "thread_ref": {
                "slack_team_id": "T0123456789",
                "channel_id": "C0123456789",
                "thread_ts": "1714464000.000100",
                "url": "https://acme.slack.com/archives/C0123456789/p1714464000000100",
            },
            "invited_participants": [
                {
                    "participant_id": "p-ext-001",
                    "participant_type": "human",
                    "display_name": "Alice Expert",
                    "session_id": None,
                    "external_refs": {
                        "slack_user_id": "U0000000001",
                        "slack_team_id": "T0123456789",
                        "teamspace_member_id": None,
                    },
                }
            ],
            "widened_by": "human-owner-2",
            "widened_at": "2026-04-23T10:00:01+00:00",
            "recorded_at": "2026-04-23T10:00:01+00:00",
        },
        "project_slug": None,
        "project_uuid": PROJECT_UUID,
        "schema_version": "3.0.0",
        "timestamp": "2026-04-23T10:00:01+00:00",
    },
    {
        "aggregate_id": "dp/dp-iv-002",
        "build_id": "test-build",
        "causation_id": None,
        "correlation_id": "01J2A0000000000000000000B6",
        "data_tier": 0,
        "event_id": "01J2A0000000000000000000B5",
        "event_type": "DecisionPointDiscussing",
        "lamport_clock": 3,
        "node_id": "node-1",
        "payload": {
            "origin_surface": "planning_interview",
            "decision_point_id": "dp-iv-002",
            "mission_id": "m-interview-002",
            "run_id": "run-iv-002",
            "mission_slug": "data-pipeline",
            "mission_type": "software-dev",
            "snapshot_kind": "digest",
            "contributions": [
                "Alice: blue-green avoids in-flight request failures during cutover",
                "Bob: rolling is simpler but risks mixed schema versions hitting the DB simultaneously",
            ],
            "actor_id": "human-owner-2",
            "actor_type": "human",
            "state_entered_at": "2026-04-23T10:00:02+00:00",
            "recorded_at": "2026-04-23T10:00:02+00:00",
        },
        "project_slug": None,
        "project_uuid": PROJECT_UUID,
        "schema_version": "3.0.0",
        "timestamp": "2026-04-23T10:00:02+00:00",
    },
    {
        "aggregate_id": "dp/dp-iv-002",
        "build_id": "test-build",
        "causation_id": None,
        "correlation_id": "01J2A0000000000000000000B8",
        "data_tier": 0,
        "event_id": "01J2A0000000000000000000B7",
        "event_type": "DecisionPointResolved",
        "lamport_clock": 4,
        "node_id": "node-1",
        "payload": {
            "origin_surface": "planning_interview",
            "decision_point_id": "dp-iv-002",
            "mission_id": "m-interview-002",
            "run_id": "run-iv-002",
            "mission_slug": "data-pipeline",
            "mission_type": "software-dev",
            "terminal_outcome": "resolved",
            "final_answer": "blue-green",
            "other_answer": False,
            "rationale": None,
            "summary": {
                "text": "Team consensus: blue-green deployment avoids schema version conflicts during migration.",
                "source": "slack_extraction",
                "extracted_at": "2026-04-23T10:00:03+00:00",
                "candidate_answer": "blue-green",
            },
            "actual_participants": [
                {
                    "participant_id": "p-ext-001",
                    "participant_type": "human",
                    "display_name": "Alice Expert",
                    "session_id": None,
                    "external_refs": {
                        "slack_user_id": "U0000000001",
                        "slack_team_id": "T0123456789",
                        "teamspace_member_id": None,
                    },
                },
                {
                    "participant_id": "p-ext-002",
                    "participant_type": "human",
                    "display_name": "Bob Engineer",
                    "session_id": None,
                    "external_refs": {
                        "slack_user_id": "U0000000002",
                        "slack_team_id": "T0123456789",
                        "teamspace_member_id": None,
                    },
                },
            ],
            "resolved_by": "human-owner-2",
            "closed_locally_while_widened": False,
            "closure_message": {
                "channel_id": "C0123456789",
                "thread_ts": "1714464000.000100",
                "message_ts": "1714464300.000200",
                "url": "https://acme.slack.com/archives/C0123456789/p1714464300000200",
            },
            "state_entered_at": "2026-04-23T10:00:03+00:00",
            "recorded_at": "2026-04-23T10:00:03+00:00",
        },
        "project_slug": None,
        "project_uuid": PROJECT_UUID,
        "schema_version": "3.0.0",
        "timestamp": "2026-04-23T10:00:03+00:00",
    },
]

# ── Scenario 3: replay_interview_widened_closed_locally ───────────────────────
# 3 events: Opened -> Widened -> Resolved(closed_locally_while_widened=true)

S3_EVENTS = [
    {
        "aggregate_id": "dp/dp-iv-003",
        "build_id": "test-build",
        "causation_id": None,
        "correlation_id": "01J2A0000000000000000000C2",
        "data_tier": 0,
        "event_id": "01J2A0000000000000000000C1",
        "event_type": "DecisionPointOpened",
        "lamport_clock": 1,
        "node_id": "node-1",
        "payload": {
            "origin_surface": "planning_interview",
            "decision_point_id": "dp-iv-003",
            "mission_id": "m-interview-003",
            "run_id": "run-iv-003",
            "mission_slug": "infra-redesign",
            "mission_type": "software-dev",
            "phase": "P3",
            "origin_flow": "charter",
            "question": "Should we use Kubernetes or ECS for container orchestration?",
            "options": ["kubernetes", "ecs", "nomad"],
            "input_key": "orchestration_platform",
            "step_id": "step-orch-001",
            "actor_id": "human-owner-3",
            "actor_type": "human",
            "state_entered_at": "2026-04-23T10:00:00+00:00",
            "recorded_at": "2026-04-23T10:00:00+00:00",
        },
        "project_slug": None,
        "project_uuid": PROJECT_UUID,
        "schema_version": "3.0.0",
        "timestamp": "2026-04-23T10:00:00+00:00",
    },
    {
        "aggregate_id": "dp/dp-iv-003",
        "build_id": "test-build",
        "causation_id": None,
        "correlation_id": "01J2A0000000000000000000C4",
        "data_tier": 0,
        "event_id": "01J2A0000000000000000000C3",
        "event_type": "DecisionPointWidened",
        "lamport_clock": 2,
        "node_id": "node-1",
        "payload": {
            "origin_surface": "planning_interview",
            "decision_point_id": "dp-iv-003",
            "mission_id": "m-interview-003",
            "run_id": "run-iv-003",
            "mission_slug": "infra-redesign",
            "mission_type": "software-dev",
            "channel": "slack",
            "teamspace_ref": {
                "teamspace_id": "ts-acme-002",
                "name": "Acme Infrastructure",
            },
            "default_channel_ref": {
                "channel_id": "C9876543210",
                "name": "infra-decisions",
            },
            "thread_ref": {
                "slack_team_id": "T0123456789",
                "channel_id": "C9876543210",
                "thread_ts": "1714464100.000100",
                "url": "https://acme.slack.com/archives/C9876543210/p1714464100000100",
            },
            "invited_participants": [],
            "widened_by": "human-owner-3",
            "widened_at": "2026-04-23T10:00:01+00:00",
            "recorded_at": "2026-04-23T10:00:01+00:00",
        },
        "project_slug": None,
        "project_uuid": PROJECT_UUID,
        "schema_version": "3.0.0",
        "timestamp": "2026-04-23T10:00:01+00:00",
    },
    {
        "aggregate_id": "dp/dp-iv-003",
        "build_id": "test-build",
        "causation_id": None,
        "correlation_id": "01J2A0000000000000000000C6",
        "data_tier": 0,
        "event_id": "01J2A0000000000000000000C5",
        "event_type": "DecisionPointResolved",
        "lamport_clock": 3,
        "node_id": "node-1",
        "payload": {
            "origin_surface": "planning_interview",
            "decision_point_id": "dp-iv-003",
            "mission_id": "m-interview-003",
            "run_id": "run-iv-003",
            "mission_slug": "infra-redesign",
            "mission_type": "software-dev",
            "terminal_outcome": "resolved",
            "final_answer": "kubernetes",
            "other_answer": False,
            "rationale": None,
            "summary": {
                "text": "Mission owner overrode: Kubernetes is the approved platform per infrastructure policy.",
                "source": "mission_owner_override",
                "extracted_at": None,
                "candidate_answer": None,
            },
            "actual_participants": [],
            "resolved_by": "human-owner-3",
            "closed_locally_while_widened": True,
            "closure_message": {
                "channel_id": "C9876543210",
                "thread_ts": "1714464100.000100",
                "message_ts": "1714464200.000300",
                "url": "https://acme.slack.com/archives/C9876543210/p1714464200000300",
            },
            "state_entered_at": "2026-04-23T10:00:02+00:00",
            "recorded_at": "2026-04-23T10:00:02+00:00",
        },
        "project_slug": None,
        "project_uuid": PROJECT_UUID,
        "schema_version": "3.0.0",
        "timestamp": "2026-04-23T10:00:02+00:00",
    },
]

# ── Scenario 4: replay_interview_deferred ─────────────────────────────────────
# 2 events: Opened -> Resolved(terminal=deferred, rationale="need security review")

S4_EVENTS = [
    {
        "aggregate_id": "dp/dp-iv-004",
        "build_id": "test-build",
        "causation_id": None,
        "correlation_id": "01J2A0000000000000000000D2",
        "data_tier": 0,
        "event_id": "01J2A0000000000000000000D1",
        "event_type": "DecisionPointOpened",
        "lamport_clock": 1,
        "node_id": "node-1",
        "payload": {
            "origin_surface": "planning_interview",
            "decision_point_id": "dp-iv-004",
            "mission_id": "m-interview-004",
            "run_id": "run-iv-004",
            "mission_slug": "security-hardening",
            "mission_type": "software-dev",
            "phase": "P1",
            "origin_flow": "specify",
            "question": "Which encryption algorithm should we use for at-rest data?",
            "options": ["AES-256", "ChaCha20", "Other"],
            "input_key": "encryption_algorithm",
            "step_id": "step-enc-001",
            "actor_id": "human-owner-4",
            "actor_type": "human",
            "state_entered_at": "2026-04-23T10:00:00+00:00",
            "recorded_at": "2026-04-23T10:00:00+00:00",
        },
        "project_slug": None,
        "project_uuid": PROJECT_UUID,
        "schema_version": "3.0.0",
        "timestamp": "2026-04-23T10:00:00+00:00",
    },
    {
        "aggregate_id": "dp/dp-iv-004",
        "build_id": "test-build",
        "causation_id": None,
        "correlation_id": "01J2A0000000000000000000D4",
        "data_tier": 0,
        "event_id": "01J2A0000000000000000000D3",
        "event_type": "DecisionPointResolved",
        "lamport_clock": 2,
        "node_id": "node-1",
        "payload": {
            "origin_surface": "planning_interview",
            "decision_point_id": "dp-iv-004",
            "mission_id": "m-interview-004",
            "run_id": "run-iv-004",
            "mission_slug": "security-hardening",
            "mission_type": "software-dev",
            "terminal_outcome": "deferred",
            "final_answer": None,
            "other_answer": False,
            "rationale": "need security review",
            "summary": None,
            "actual_participants": [],
            "resolved_by": "human-owner-4",
            "closed_locally_while_widened": False,
            "closure_message": None,
            "state_entered_at": "2026-04-23T10:00:01+00:00",
            "recorded_at": "2026-04-23T10:00:01+00:00",
        },
        "project_slug": None,
        "project_uuid": PROJECT_UUID,
        "schema_version": "3.0.0",
        "timestamp": "2026-04-23T10:00:01+00:00",
    },
]

# ── Scenario 5: replay_interview_canceled ─────────────────────────────────────
# 2 events: Opened -> Resolved(terminal=canceled, rationale="out of scope")

S5_EVENTS = [
    {
        "aggregate_id": "dp/dp-iv-005",
        "build_id": "test-build",
        "causation_id": None,
        "correlation_id": "01J2A0000000000000000000E2",
        "data_tier": 0,
        "event_id": "01J2A0000000000000000000E1",
        "event_type": "DecisionPointOpened",
        "lamport_clock": 1,
        "node_id": "node-1",
        "payload": {
            "origin_surface": "planning_interview",
            "decision_point_id": "dp-iv-005",
            "mission_id": "m-interview-005",
            "run_id": "run-iv-005",
            "mission_slug": "frontend-redesign",
            "mission_type": "software-dev",
            "phase": "P1",
            "origin_flow": "specify",
            "question": "Which CSS framework should we adopt?",
            "options": ["tailwind", "bootstrap", "material-ui"],
            "input_key": "css_framework",
            "step_id": "step-css-001",
            "actor_id": "human-owner-5",
            "actor_type": "human",
            "state_entered_at": "2026-04-23T10:00:00+00:00",
            "recorded_at": "2026-04-23T10:00:00+00:00",
        },
        "project_slug": None,
        "project_uuid": PROJECT_UUID,
        "schema_version": "3.0.0",
        "timestamp": "2026-04-23T10:00:00+00:00",
    },
    {
        "aggregate_id": "dp/dp-iv-005",
        "build_id": "test-build",
        "causation_id": None,
        "correlation_id": "01J2A0000000000000000000E4",
        "data_tier": 0,
        "event_id": "01J2A0000000000000000000E3",
        "event_type": "DecisionPointResolved",
        "lamport_clock": 2,
        "node_id": "node-1",
        "payload": {
            "origin_surface": "planning_interview",
            "decision_point_id": "dp-iv-005",
            "mission_id": "m-interview-005",
            "run_id": "run-iv-005",
            "mission_slug": "frontend-redesign",
            "mission_type": "software-dev",
            "terminal_outcome": "canceled",
            "final_answer": None,
            "other_answer": False,
            "rationale": "out of scope",
            "summary": None,
            "actual_participants": [],
            "resolved_by": "human-owner-5",
            "closed_locally_while_widened": False,
            "closure_message": None,
            "state_entered_at": "2026-04-23T10:00:01+00:00",
            "recorded_at": "2026-04-23T10:00:01+00:00",
        },
        "project_slug": None,
        "project_uuid": PROJECT_UUID,
        "schema_version": "3.0.0",
        "timestamp": "2026-04-23T10:00:01+00:00",
    },
]

# ── Scenario 6: replay_interview_resolved_other ───────────────────────────────
# 2 events: Opened(options=["session","oauth2","oidc","Other"]) ->
#           Resolved(terminal=resolved, final_answer="internal SSO proxy", other_answer=true)

S6_EVENTS = [
    {
        "aggregate_id": "dp/dp-iv-006",
        "build_id": "test-build",
        "causation_id": None,
        "correlation_id": "01J2A0000000000000000000F2",
        "data_tier": 0,
        "event_id": "01J2A0000000000000000000F1",
        "event_type": "DecisionPointOpened",
        "lamport_clock": 1,
        "node_id": "node-1",
        "payload": {
            "origin_surface": "planning_interview",
            "decision_point_id": "dp-iv-006",
            "mission_id": "m-interview-006",
            "run_id": "run-iv-006",
            "mission_slug": "sso-integration",
            "mission_type": "software-dev",
            "phase": "P1",
            "origin_flow": "specify",
            "question": "Which SSO mechanism should we implement?",
            "options": ["session", "oauth2", "oidc", "Other"],
            "input_key": "sso_mechanism",
            "step_id": "step-sso-001",
            "actor_id": "human-owner-6",
            "actor_type": "human",
            "state_entered_at": "2026-04-23T10:00:00+00:00",
            "recorded_at": "2026-04-23T10:00:00+00:00",
        },
        "project_slug": None,
        "project_uuid": PROJECT_UUID,
        "schema_version": "3.0.0",
        "timestamp": "2026-04-23T10:00:00+00:00",
    },
    {
        "aggregate_id": "dp/dp-iv-006",
        "build_id": "test-build",
        "causation_id": None,
        "correlation_id": "01J2A0000000000000000000F4",
        "data_tier": 0,
        "event_id": "01J2A0000000000000000000F3",
        "event_type": "DecisionPointResolved",
        "lamport_clock": 2,
        "node_id": "node-1",
        "payload": {
            "origin_surface": "planning_interview",
            "decision_point_id": "dp-iv-006",
            "mission_id": "m-interview-006",
            "run_id": "run-iv-006",
            "mission_slug": "sso-integration",
            "mission_type": "software-dev",
            "terminal_outcome": "resolved",
            "final_answer": "internal SSO proxy",
            "other_answer": True,
            "rationale": None,
            "summary": None,
            "actual_participants": [],
            "resolved_by": "human-owner-6",
            "closed_locally_while_widened": False,
            "closure_message": None,
            "state_entered_at": "2026-04-23T10:00:01+00:00",
            "recorded_at": "2026-04-23T10:00:01+00:00",
        },
        "project_slug": None,
        "project_uuid": PROJECT_UUID,
        "schema_version": "3.0.0",
        "timestamp": "2026-04-23T10:00:01+00:00",
    },
]

SCENARIOS = [
    ("replay_interview_local_only_resolved", S1_EVENTS),
    ("replay_interview_widened_resolved", S2_EVENTS),
    ("replay_interview_widened_closed_locally", S3_EVENTS),
    ("replay_interview_deferred", S4_EVENTS),
    ("replay_interview_canceled", S5_EVENTS),
    ("replay_interview_resolved_other", S6_EVENTS),
]


def generate_fixtures():
    FIXTURE_DIR.mkdir(parents=True, exist_ok=True)
    CONFORMANCE_DIR.mkdir(parents=True, exist_ok=True)

    for name, event_dicts in SCENARIOS:
        # ── Write .jsonl ──────────────────────────────────────────────────────
        jsonl_lines = []
        for ed in event_dicts:
            # Serialize deterministically: sort_keys
            jsonl_lines.append(json.dumps(ed, sort_keys=True, ensure_ascii=False))

        jsonl_content = "\n".join(jsonl_lines) + "\n"

        # ── Run reducer to produce output ──────────────────────────────────────
        events = [Event.model_validate_json(line) for line in jsonl_lines if line.strip()]
        reduced = reduce_decision_point_events(events)
        output = json.dumps(
            reduced.model_dump(mode="json", by_alias=True),
            sort_keys=True,
            indent=2,
        )

        # Verify no anomalies
        if reduced.anomalies:
            print(f"WARNING: {name} has anomalies: {reduced.anomalies}")

        # ── Write to tests/fixtures/decisionpoint_golden/ ────────────────────
        fx_jsonl = FIXTURE_DIR / f"{name}.jsonl"
        fx_json = FIXTURE_DIR / f"{name}_output.json"
        fx_jsonl.write_text(jsonl_content, encoding="utf-8")
        fx_json.write_text(output + "\n", encoding="utf-8")
        print(f"Written: {fx_jsonl}")
        print(f"Written: {fx_json}")

        # ── Mirror to conformance tree ────────────────────────────────────────
        conf_jsonl = CONFORMANCE_DIR / f"{name}.jsonl"
        conf_json = CONFORMANCE_DIR / f"{name}_output.json"
        shutil.copy2(fx_jsonl, conf_jsonl)
        shutil.copy2(fx_json, conf_json)
        print(f"Mirrored: {conf_jsonl}")
        print(f"Mirrored: {conf_json}")

    print(f"\nDone. {len(SCENARIOS)} scenarios generated.")


if __name__ == "__main__":
    generate_fixtures()
