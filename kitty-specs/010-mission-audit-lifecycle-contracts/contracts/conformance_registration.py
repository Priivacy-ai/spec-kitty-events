# Contract Specification: Conformance Registration
# Defines the additions to validators.py and loader.py for mission-audit.
# DESIGN ARTIFACT — not production code.

# ---------------------------------------------------------------------------
# validators.py additions
# ---------------------------------------------------------------------------

# New import block (add after dossier imports):
#
# from spec_kitty_events.mission_audit import (
#     MissionAuditRequestedPayload,
#     MissionAuditStartedPayload,
#     MissionAuditDecisionRequestedPayload,
#     MissionAuditCompletedPayload,
#     MissionAuditFailedPayload,
# )

# New entries in _EVENT_TYPE_TO_MODEL (FR-015):
_EVENT_TYPE_TO_MODEL_ADDITIONS = {
    "MissionAuditRequested": "MissionAuditRequestedPayload",
    "MissionAuditStarted": "MissionAuditStartedPayload",
    "MissionAuditDecisionRequested": "MissionAuditDecisionRequestedPayload",
    "MissionAuditCompleted": "MissionAuditCompletedPayload",
    "MissionAuditFailed": "MissionAuditFailedPayload",
}

# New entries in _EVENT_TYPE_TO_SCHEMA:
_EVENT_TYPE_TO_SCHEMA_ADDITIONS = {
    "MissionAuditRequested": "mission_audit_requested_payload",
    "MissionAuditStarted": "mission_audit_started_payload",
    "MissionAuditDecisionRequested": "mission_audit_decision_requested_payload",
    "MissionAuditCompleted": "mission_audit_completed_payload",
    "MissionAuditFailed": "mission_audit_failed_payload",
}

# ---------------------------------------------------------------------------
# loader.py additions
# ---------------------------------------------------------------------------

# Add "mission_audit" to _VALID_CATEGORIES:
# _VALID_CATEGORIES = frozenset({
#     "events", "lane_mapping", "edge_cases",
#     "collaboration", "glossary", "mission_next",
#     "dossier", "mission_audit",
# })

# ---------------------------------------------------------------------------
# Fixture directory structure
# ---------------------------------------------------------------------------
# conformance/fixtures/mission_audit/
# ├── valid/
# │   ├── mission_audit_requested_manual.json
# │   ├── mission_audit_requested_post_merge.json
# │   ├── mission_audit_started_valid.json
# │   ├── mission_audit_decision_requested_valid.json
# │   ├── mission_audit_completed_pass.json
# │   ├── mission_audit_completed_fail.json
# │   └── mission_audit_failed_valid.json
# ├── invalid/
# │   ├── mission_audit_completed_missing_verdict.json
# │   ├── mission_audit_completed_missing_artifact_ref.json
# │   ├── mission_audit_requested_bad_trigger.json
# │   └── mission_audit_decision_missing_id.json
# └── replay/
#     ├── mission_audit_replay_pass.jsonl
#     ├── mission_audit_replay_fail.jsonl
#     ├── mission_audit_replay_decision_checkpoint.jsonl
#     ├── mission_audit_replay_pass_output.json
#     ├── mission_audit_replay_fail_output.json
#     └── mission_audit_replay_decision_checkpoint_output.json

# ---------------------------------------------------------------------------
# Manifest entries (append to fixtures array in manifest.json)
# ---------------------------------------------------------------------------
# 7 valid + 4 invalid + 3 replay_stream + 3 reducer_output = 17 entries
# All with min_version: "2.5.0"
