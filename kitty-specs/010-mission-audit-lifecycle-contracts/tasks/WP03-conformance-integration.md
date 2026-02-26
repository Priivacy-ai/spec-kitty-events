---
work_package_id: WP03
title: Conformance Integration
lane: "doing"
dependencies:
- WP01
base_branch: main
base_commit: 99c99d961d069053ea1d444c4f26d66026c99f1e
created_at: '2026-02-26T12:35:58.809376+00:00'
subtasks:
- T012
- T013
- T014
- T015
- T016
- T017
- T018
phase: Phase 3 - Conformance Integration
assignee: ''
agent: "claude-reviewer"
shell_pid: "45764"
review_status: ''
reviewed_by: ''
history:
- timestamp: '2026-02-25T00:00:00Z'
  lane: planned
  agent: system
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP03 – Conformance Integration

## Goal

Register the 5 new mission-audit event types in the conformance system: generate 5 JSON schema files, update `validators.py` and `loader.py`, create all fixture files (7 valid + 4 invalid + 3 replay JSONL + 3 golden reducer output), and update `manifest.json` with 17 new entries.

**Independent Test**: `pytest --pyargs spec_kitty_events.conformance` passes (all mission_audit fixtures load and validate). `python3.11 -c "from spec_kitty_events.conformance.loader import load_fixtures; load_fixtures('mission_audit')"` succeeds.

## Context

WP01 created the core types module. WP03 plugs those types into the existing conformance infrastructure without modifying the reducer (that is WP02's concern). WP03 can run in parallel with WP02.

**Existing patterns to follow**:
- `src/spec_kitty_events/conformance/validators.py` — follow the dossier import block and dict entry pattern.
- `src/spec_kitty_events/conformance/loader.py` — `_VALID_CATEGORIES` frozenset, add `"mission_audit"`.
- Fixture files follow the exact naming from `contracts/conformance_registration.py` (design artifact).
- Manifest entries follow the structure in `manifest.json` (see dossier entries for `min_version: "2.4.0"` pattern — use `"2.5.0"` here).
- Replay JSONL: each line is a complete Event envelope (raw dict, all Event fields including `payload` as nested dict).
- Schema generation: use `TypeAdapter(ModelClass).json_schema()` — run once, write to file, commit. Do not hand-write schemas.

**Branch**: `010-mission-audit-lifecycle-contracts` — WP01 worktree has the types. WP03 works in its own worktree.

## Subtasks

### T012 — Generate 5 JSON schema files in `src/spec_kitty_events/schemas/`

Run this schema generation script (in the worktree):

```python
#!/usr/bin/env python3.11
"""Generate JSON schema files for mission-audit payload models."""
import json
from pathlib import Path
from pydantic import TypeAdapter
from spec_kitty_events.mission_audit import (
    MissionAuditRequestedPayload,
    MissionAuditStartedPayload,
    MissionAuditDecisionRequestedPayload,
    MissionAuditCompletedPayload,
    MissionAuditFailedPayload,
)

SCHEMAS_DIR = Path("src/spec_kitty_events/schemas")
SCHEMAS_DIR.mkdir(exist_ok=True)

models = {
    "mission_audit_requested_payload": MissionAuditRequestedPayload,
    "mission_audit_started_payload": MissionAuditStartedPayload,
    "mission_audit_decision_requested_payload": MissionAuditDecisionRequestedPayload,
    "mission_audit_completed_payload": MissionAuditCompletedPayload,
    "mission_audit_failed_payload": MissionAuditFailedPayload,
}

for name, model_class in models.items():
    schema = TypeAdapter(model_class).json_schema()
    out_path = SCHEMAS_DIR / f"{name}.json"
    out_path.write_text(json.dumps(schema, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Generated: {out_path}")
```

Run as: `python3.11 scripts/generate_mission_audit_schemas.py` (or inline in Python). Commit all 5 generated `.json` files.

**File names** (exact — these map to `_EVENT_TYPE_TO_SCHEMA` in validators.py):
- `src/spec_kitty_events/schemas/mission_audit_requested_payload.json`
- `src/spec_kitty_events/schemas/mission_audit_started_payload.json`
- `src/spec_kitty_events/schemas/mission_audit_decision_requested_payload.json`
- `src/spec_kitty_events/schemas/mission_audit_completed_payload.json`
- `src/spec_kitty_events/schemas/mission_audit_failed_payload.json`

**Verify**: `python3.11 -c "from spec_kitty_events.schemas import load_schema; s = load_schema('mission_audit_requested_payload'); assert 'properties' in s"` succeeds.

### T013 — Update `src/spec_kitty_events/conformance/validators.py`

Add after the dossier import block (after the last `from spec_kitty_events.dossier import ...` line):

```python
from spec_kitty_events.mission_audit import (
    MissionAuditRequestedPayload,
    MissionAuditStartedPayload,
    MissionAuditDecisionRequestedPayload,
    MissionAuditCompletedPayload,
    MissionAuditFailedPayload,
)
```

Add 5 entries to `_EVENT_TYPE_TO_MODEL` dict (after the dossier entries, before the closing `}`):

```python
    # Mission audit lifecycle contracts (2.5.0)
    "MissionAuditRequested": MissionAuditRequestedPayload,
    "MissionAuditStarted": MissionAuditStartedPayload,
    "MissionAuditDecisionRequested": MissionAuditDecisionRequestedPayload,
    "MissionAuditCompleted": MissionAuditCompletedPayload,
    "MissionAuditFailed": MissionAuditFailedPayload,
```

Add 5 entries to `_EVENT_TYPE_TO_SCHEMA` dict (after the dossier entries):

```python
    # Mission audit lifecycle contracts (2.5.0)
    "MissionAuditRequested": "mission_audit_requested_payload",
    "MissionAuditStarted": "mission_audit_started_payload",
    "MissionAuditDecisionRequested": "mission_audit_decision_requested_payload",
    "MissionAuditCompleted": "mission_audit_completed_payload",
    "MissionAuditFailed": "mission_audit_failed_payload",
```

**Verify**: `python3.11 -c "from spec_kitty_events.conformance.validators import validate_event; r = validate_event({'mission_id':'m','run_id':'r','feature_slug':'f','actor':'a','trigger_mode':'manual','audit_scope':['spec.md'],'enforcement_mode':'blocking'}, 'MissionAuditRequested'); assert r.valid"` succeeds.

### T014 — Update `src/spec_kitty_events/conformance/loader.py`

Change the `_VALID_CATEGORIES` frozenset to include `"mission_audit"`:

```python
_VALID_CATEGORIES = frozenset({
    "events", "lane_mapping", "edge_cases",
    "collaboration", "glossary", "mission_next",
    "dossier", "mission_audit",
})
```

Also update the docstring of `load_fixtures()` to mention `"mission_audit"` in the list of valid categories.

**Verify**: `python3.11 -c "from spec_kitty_events.conformance.loader import load_fixtures; cases = load_fixtures('mission_audit'); print(f'{len(cases)} fixture cases loaded')"` runs without error.

### T015 — Create 7 valid fixture JSON files in `src/spec_kitty_events/conformance/fixtures/mission_audit/valid/`

Create the directory `src/spec_kitty_events/conformance/fixtures/mission_audit/valid/` and write these 7 files. Each file contains a payload dict (NOT an Event envelope — just the payload fields):

**1. `mission_audit_requested_manual.json`**
```json
{
  "mission_id": "mission-010",
  "run_id": "run-001",
  "feature_slug": "010-mission-audit-lifecycle-contracts",
  "actor": "agent-claude",
  "trigger_mode": "manual",
  "audit_scope": ["spec.md", "plan.md", "data-model.md"],
  "enforcement_mode": "advisory"
}
```

**2. `mission_audit_requested_post_merge.json`**
```json
{
  "mission_id": "mission-010",
  "run_id": "run-002",
  "feature_slug": "010-mission-audit-lifecycle-contracts",
  "actor": "ci-bot",
  "trigger_mode": "post_merge",
  "audit_scope": ["spec.md", "plan.md", "data-model.md", "tasks.md", "quickstart.md"],
  "enforcement_mode": "blocking"
}
```

**3. `mission_audit_started_valid.json`**
```json
{
  "mission_id": "mission-010",
  "run_id": "run-001",
  "feature_slug": "010-mission-audit-lifecycle-contracts",
  "actor": "agent-claude",
  "audit_scope_hash": "sha256:a1b2c3d4e5f6789012345678901234567890123456789012345678901234567890"
}
```

**4. `mission_audit_decision_requested_valid.json`**
```json
{
  "mission_id": "mission-010",
  "run_id": "run-001",
  "feature_slug": "010-mission-audit-lifecycle-contracts",
  "actor": "agent-claude",
  "decision_id": "dec-001",
  "question": "Should the missing acceptance criteria be treated as a blocker?",
  "context_summary": "spec.md section 3 lacks measurable success criteria for SC-003.",
  "severity": "warning"
}
```

**5. `mission_audit_completed_pass.json`**
```json
{
  "mission_id": "mission-010",
  "run_id": "run-001",
  "feature_slug": "010-mission-audit-lifecycle-contracts",
  "actor": "agent-claude",
  "verdict": "pass",
  "severity": "info",
  "findings_count": 0,
  "artifact_ref": {
    "report_path": "audits/mission-010/run-001/report.json",
    "content_hash": {
      "hash": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
      "algorithm": "sha256",
      "size_bytes": 4096,
      "encoding": "utf-8"
    },
    "provenance": {
      "source_event_ids": ["01JAUDIT000000000000000001", "01JAUDIT000000000000000002"],
      "git_sha": "abc123def456789",
      "git_ref": "refs/heads/010-mission-audit-lifecycle-contracts",
      "actor_id": "agent-claude",
      "actor_kind": "agent",
      "revised_at": "2026-02-25T16:30:00Z"
    }
  },
  "summary": "All acceptance criteria verified. No findings."
}
```

**6. `mission_audit_completed_fail.json`**
```json
{
  "mission_id": "mission-010",
  "run_id": "run-003",
  "feature_slug": "010-mission-audit-lifecycle-contracts",
  "actor": "agent-claude",
  "verdict": "fail",
  "severity": "error",
  "findings_count": 3,
  "artifact_ref": {
    "report_path": "audits/mission-010/run-003/report.json",
    "content_hash": {
      "hash": "sha256:b94d27b9934d3e08a52e52d7da7dabfac484efe04294e576d4ccc20c8bc39f1e",
      "algorithm": "sha256",
      "size_bytes": 8192,
      "encoding": "utf-8"
    },
    "provenance": {
      "source_event_ids": ["01JAUDIT000000000000000010"],
      "git_sha": "def456abc123789",
      "git_ref": "refs/heads/010-mission-audit-lifecycle-contracts",
      "actor_id": "agent-claude",
      "actor_kind": "agent",
      "revised_at": "2026-02-25T17:00:00Z"
    }
  },
  "summary": "3 blocking findings: missing test coverage, undefined acceptance criteria, incomplete data model."
}
```

**7. `mission_audit_failed_valid.json`**
```json
{
  "mission_id": "mission-010",
  "run_id": "run-004",
  "feature_slug": "010-mission-audit-lifecycle-contracts",
  "actor": "agent-claude",
  "error_code": "TIMEOUT",
  "error_message": "Audit execution timed out after 300 seconds.",
  "partial_artifact_ref": null
}
```

### T016 — Create 4 invalid fixture JSON files in `src/spec_kitty_events/conformance/fixtures/mission_audit/invalid/`

Create the directory and write these 4 files. Each represents a payload that Pydantic MUST reject:

**1. `mission_audit_completed_missing_verdict.json`** — missing required `verdict` field:
```json
{
  "mission_id": "mission-010",
  "run_id": "run-001",
  "feature_slug": "010-mission-audit-lifecycle-contracts",
  "actor": "agent-claude",
  "severity": "info",
  "findings_count": 0,
  "artifact_ref": {
    "report_path": "audits/mission-010/run-001/report.json",
    "content_hash": {
      "hash": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
      "algorithm": "sha256",
      "size_bytes": 4096,
      "encoding": "utf-8"
    },
    "provenance": {
      "source_event_ids": ["01JAUDIT000000000000000001"],
      "git_sha": "abc123",
      "git_ref": "refs/heads/main",
      "actor_id": "agent-claude",
      "actor_kind": "agent",
      "revised_at": "2026-02-25T16:30:00Z"
    }
  },
  "summary": "All checks passed."
}
```

**2. `mission_audit_completed_missing_artifact_ref.json`** — missing required `artifact_ref` (FR-006: artifact_ref is required, not Optional):
```json
{
  "mission_id": "mission-010",
  "run_id": "run-001",
  "feature_slug": "010-mission-audit-lifecycle-contracts",
  "actor": "agent-claude",
  "verdict": "pass",
  "severity": "info",
  "findings_count": 0,
  "summary": "All checks passed."
}
```

**3. `mission_audit_requested_bad_trigger.json`** — invalid `trigger_mode` value (Literal constraint violation):
```json
{
  "mission_id": "mission-010",
  "run_id": "run-001",
  "feature_slug": "010-mission-audit-lifecycle-contracts",
  "actor": "agent-claude",
  "trigger_mode": "scheduled",
  "audit_scope": ["spec.md"],
  "enforcement_mode": "advisory"
}
```

**4. `mission_audit_decision_missing_id.json`** — missing required `decision_id` (min_length=1):
```json
{
  "mission_id": "mission-010",
  "run_id": "run-001",
  "feature_slug": "010-mission-audit-lifecycle-contracts",
  "actor": "agent-claude",
  "question": "Should we block on this finding?",
  "context_summary": "Missing decision identifier.",
  "severity": "error"
}
```

### T017 — Create 3 replay JSONL files + 3 golden reducer output JSON files

Create directory `src/spec_kitty_events/conformance/fixtures/mission_audit/replay/`.

**JSONL format**: Each line is a complete Event envelope as a JSON object on one line (no pretty-printing). Mandatory Event fields: `event_id`, `event_type`, `aggregate_id`, `timestamp`, `node_id`, `lamport_clock`, `project_uuid`, `correlation_id`, `payload`.

Use these constants:
- `project_uuid`: `"a1b2c3d4-e5f6-7890-abcd-ef0123456789"`
- `aggregate_id`: `"audit/mission-010/run-001"` (or matching run)
- `node_id`: `"local-node-001"`
- `correlation_id`: `"01JCORR00000000000000000001"`

**1. `mission_audit_replay_pass.jsonl`** — 3-event pass lifecycle:

Line 1: `MissionAuditRequested`
```json
{"event_id": "01JAUDIT000000000000000001", "event_type": "MissionAuditRequested", "aggregate_id": "audit/mission-010/run-001", "timestamp": "2026-02-25T10:00:00.000Z", "node_id": "local-node-001", "lamport_clock": 1, "project_uuid": "a1b2c3d4-e5f6-7890-abcd-ef0123456789", "correlation_id": "01JCORR00000000000000000001", "payload": {"mission_id": "mission-010", "run_id": "run-001", "feature_slug": "010-mission-audit-lifecycle-contracts", "actor": "agent-claude", "trigger_mode": "post_merge", "audit_scope": ["spec.md", "plan.md", "data-model.md"], "enforcement_mode": "blocking"}}
```

Line 2: `MissionAuditStarted`
```json
{"event_id": "01JAUDIT000000000000000002", "event_type": "MissionAuditStarted", "aggregate_id": "audit/mission-010/run-001", "timestamp": "2026-02-25T10:01:00.000Z", "node_id": "local-node-001", "lamport_clock": 2, "project_uuid": "a1b2c3d4-e5f6-7890-abcd-ef0123456789", "correlation_id": "01JCORR00000000000000000001", "payload": {"mission_id": "mission-010", "run_id": "run-001", "feature_slug": "010-mission-audit-lifecycle-contracts", "actor": "agent-claude", "audit_scope_hash": "sha256:a1b2c3d4e5f6789012345678901234567890123456789012345678901234567890"}}
```

Line 3: `MissionAuditCompleted` (pass)
```json
{"event_id": "01JAUDIT000000000000000003", "event_type": "MissionAuditCompleted", "aggregate_id": "audit/mission-010/run-001", "timestamp": "2026-02-25T10:05:00.000Z", "node_id": "local-node-001", "lamport_clock": 3, "project_uuid": "a1b2c3d4-e5f6-7890-abcd-ef0123456789", "correlation_id": "01JCORR00000000000000000001", "payload": {"mission_id": "mission-010", "run_id": "run-001", "feature_slug": "010-mission-audit-lifecycle-contracts", "actor": "agent-claude", "verdict": "pass", "severity": "info", "findings_count": 0, "artifact_ref": {"report_path": "audits/mission-010/run-001/report.json", "content_hash": {"hash": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855", "algorithm": "sha256", "size_bytes": 4096, "encoding": "utf-8"}, "provenance": {"source_event_ids": ["01JAUDIT000000000000000001", "01JAUDIT000000000000000002"], "git_sha": "abc123def456789", "git_ref": "refs/heads/010-mission-audit-lifecycle-contracts", "actor_id": "agent-claude", "actor_kind": "agent", "revised_at": "2026-02-25T10:05:00Z"}}, "summary": "All acceptance criteria verified. No findings."}}
```

**2. `mission_audit_replay_fail.jsonl`** — 3-event fail lifecycle:

Same Requested and Started events (different `run_id="run-004"`, adjust `aggregate_id`, use `lamport_clock` 1/2). Line 3: `MissionAuditFailed`:
```json
{"event_id": "01JAUDIT000000000000000023", "event_type": "MissionAuditFailed", "aggregate_id": "audit/mission-010/run-004", "timestamp": "2026-02-25T11:05:00.000Z", "node_id": "local-node-001", "lamport_clock": 3, "project_uuid": "a1b2c3d4-e5f6-7890-abcd-ef0123456789", "correlation_id": "01JCORR00000000000000000004", "payload": {"mission_id": "mission-010", "run_id": "run-004", "feature_slug": "010-mission-audit-lifecycle-contracts", "actor": "agent-claude", "error_code": "TIMEOUT", "error_message": "Audit execution timed out after 300 seconds.", "partial_artifact_ref": null}}
```

**3. `mission_audit_replay_decision_checkpoint.jsonl`** — 4-event decision checkpoint lifecycle:

Requested (lc=1) → Started (lc=2) → DecisionRequested (lc=3) → Completed (lc=4). Use `run_id="run-002"`. DecisionRequested payload:
```json
{"decision_id": "dec-001", "question": "Should the missing acceptance criteria be treated as a blocker?", "context_summary": "spec.md section 3 lacks measurable success criteria for SC-003.", "severity": "warning", "mission_id": "mission-010", "run_id": "run-002", "feature_slug": "010-mission-audit-lifecycle-contracts", "actor": "agent-claude"}
```

**Golden output files** — generate these programmatically by running `reduce_mission_audit_events()` on each JSONL stream:

```python
#!/usr/bin/env python3.11
"""Generate golden reducer output files for mission-audit replay streams."""
import json
from pathlib import Path
from spec_kitty_events.conformance.loader import load_replay_stream
from spec_kitty_events.mission_audit import reduce_mission_audit_events
from spec_kitty_events.models import Event

REPLAY_DIR = Path("src/spec_kitty_events/conformance/fixtures/mission_audit/replay")

streams = {
    "mission_audit_replay_pass": "mission_audit_replay_pass_output",
    "mission_audit_replay_fail": "mission_audit_replay_fail_output",
    "mission_audit_replay_decision_checkpoint": "mission_audit_replay_decision_checkpoint_output",
}

for stream_id, output_name in streams.items():
    raw = load_replay_stream(stream_id)
    events = [Event(**e) for e in raw]
    state = reduce_mission_audit_events(events)
    output = json.dumps(state.model_dump(mode="json"), sort_keys=True, indent=2)
    out_path = REPLAY_DIR / f"{output_name}.json"
    out_path.write_text(output + "\n", encoding="utf-8")
    print(f"Generated: {out_path}")
```

**Important**: Golden files MUST be generated from the actual running reducer (WP02 must be merged or available in the worktree for this step). Since WP03 can run in parallel with WP02, you have two options:
- **Option A (preferred)**: Write placeholder golden files with a comment noting they need regeneration once WP02 is merged. The conformance fixtures (JSONL streams) are the deliverable of WP03; the golden output files are a joint deliverable.
- **Option B**: If WP02 is available, import the reducer and generate the golden files now.

If using Option A, create a `_PENDING` placeholder and mark T017 golden files as needing regeneration after WP02 merge. The WP04 conformance tests will validate the golden files anyway.

### T018 — Update `src/spec_kitty_events/conformance/fixtures/manifest.json`

Add 17 entries to the `fixtures` array. Append them after the dossier entries. Follow exact field names from existing entries.

**7 valid fixture entries**:
```json
{"id": "mission-audit-requested-manual", "path": "mission_audit/valid/mission_audit_requested_manual.json", "event_type": "MissionAuditRequested", "expected_result": "valid", "notes": "Manual trigger with advisory enforcement, 3-item audit scope", "min_version": "2.5.0"},
{"id": "mission-audit-requested-post-merge", "path": "mission_audit/valid/mission_audit_requested_post_merge.json", "event_type": "MissionAuditRequested", "expected_result": "valid", "notes": "Post-merge trigger with blocking enforcement, 5-item audit scope", "min_version": "2.5.0"},
{"id": "mission-audit-started-valid", "path": "mission_audit/valid/mission_audit_started_valid.json", "event_type": "MissionAuditStarted", "expected_result": "valid", "notes": "Valid started event with audit_scope_hash", "min_version": "2.5.0"},
{"id": "mission-audit-decision-requested-valid", "path": "mission_audit/valid/mission_audit_decision_requested_valid.json", "event_type": "MissionAuditDecisionRequested", "expected_result": "valid", "notes": "Decision checkpoint with warning severity", "min_version": "2.5.0"},
{"id": "mission-audit-completed-pass", "path": "mission_audit/valid/mission_audit_completed_pass.json", "event_type": "MissionAuditCompleted", "expected_result": "valid", "notes": "Pass verdict with info severity, zero findings, artifact_ref populated", "min_version": "2.5.0"},
{"id": "mission-audit-completed-fail", "path": "mission_audit/valid/mission_audit_completed_fail.json", "event_type": "MissionAuditCompleted", "expected_result": "valid", "notes": "Fail verdict with error severity, 3 findings, artifact_ref populated", "min_version": "2.5.0"},
{"id": "mission-audit-failed-valid", "path": "mission_audit/valid/mission_audit_failed_valid.json", "event_type": "MissionAuditFailed", "expected_result": "valid", "notes": "Timeout failure with null partial_artifact_ref", "min_version": "2.5.0"}
```

**4 invalid fixture entries**:
```json
{"id": "mission-audit-completed-missing-verdict", "path": "mission_audit/invalid/mission_audit_completed_missing_verdict.json", "event_type": "MissionAuditCompleted", "expected_result": "invalid", "notes": "verdict field absent — Pydantic must reject with missing field violation", "min_version": "2.5.0"},
{"id": "mission-audit-completed-missing-artifact-ref", "path": "mission_audit/invalid/mission_audit_completed_missing_artifact_ref.json", "event_type": "MissionAuditCompleted", "expected_result": "invalid", "notes": "artifact_ref absent — required (not Optional) per FR-006; Pydantic must reject", "min_version": "2.5.0"},
{"id": "mission-audit-requested-bad-trigger", "path": "mission_audit/invalid/mission_audit_requested_bad_trigger.json", "event_type": "MissionAuditRequested", "expected_result": "invalid", "notes": "trigger_mode='scheduled' violates Literal[manual, post_merge] constraint", "min_version": "2.5.0"},
{"id": "mission-audit-decision-missing-id", "path": "mission_audit/invalid/mission_audit_decision_missing_id.json", "event_type": "MissionAuditDecisionRequested", "expected_result": "invalid", "notes": "decision_id field absent — required with min_length=1", "min_version": "2.5.0"}
```

**3 replay stream entries**:
```json
{"id": "mission-audit-replay-pass", "path": "mission_audit/replay/mission_audit_replay_pass.jsonl", "fixture_type": "replay_stream", "event_type": "mixed", "expected_result": "valid", "notes": "3-event pass lifecycle: Requested → Started → Completed(pass)", "min_version": "2.5.0"},
{"id": "mission-audit-replay-fail", "path": "mission_audit/replay/mission_audit_replay_fail.jsonl", "fixture_type": "replay_stream", "event_type": "mixed", "expected_result": "valid", "notes": "3-event fail lifecycle: Requested → Started → Failed(TIMEOUT)", "min_version": "2.5.0"},
{"id": "mission-audit-replay-decision-checkpoint", "path": "mission_audit/replay/mission_audit_replay_decision_checkpoint.jsonl", "fixture_type": "replay_stream", "event_type": "mixed", "expected_result": "valid", "notes": "4-event decision checkpoint: Requested → Started → DecisionRequested → Completed", "min_version": "2.5.0"}
```

**3 reducer output (golden) entries**:
```json
{"id": "mission-audit-replay-pass-output", "path": "mission_audit/replay/mission_audit_replay_pass_output.json", "fixture_type": "reducer_output", "event_type": "MissionAuditState", "expected_result": "valid", "notes": "Golden reducer output for mission_audit_replay_pass.jsonl — audit_status=completed, verdict=pass", "min_version": "2.5.0"},
{"id": "mission-audit-replay-fail-output", "path": "mission_audit/replay/mission_audit_replay_fail_output.json", "fixture_type": "reducer_output", "event_type": "MissionAuditState", "expected_result": "valid", "notes": "Golden reducer output for mission_audit_replay_fail.jsonl — audit_status=failed", "min_version": "2.5.0"},
{"id": "mission-audit-replay-decision-checkpoint-output", "path": "mission_audit/replay/mission_audit_replay_decision_checkpoint_output.json", "fixture_type": "reducer_output", "event_type": "MissionAuditState", "expected_result": "valid", "notes": "Golden reducer output for mission_audit_replay_decision_checkpoint.jsonl — pending_decisions cleared on Completed", "min_version": "2.5.0"}
```

## Acceptance Criteria

- [ ] 5 JSON schema files generated and committed in `src/spec_kitty_events/schemas/`
- [ ] `load_schema("mission_audit_requested_payload")` returns a valid JSON Schema dict with `"properties"` key
- [ ] `validate_event({...valid requested payload...}, "MissionAuditRequested")` returns `ConformanceResult(valid=True)`
- [ ] `validate_event({...missing verdict...}, "MissionAuditCompleted")` returns `ConformanceResult(valid=False)` with at least one `model_violations` entry
- [ ] `load_fixtures("mission_audit")` returns exactly 11 `FixtureCase` objects (7 valid + 4 invalid; replay/output entries are not returned by `load_fixtures`)
- [ ] `load_replay_stream("mission-audit-replay-pass")` returns a list of 3 event dicts
- [ ] `load_replay_stream("mission-audit-replay-decision-checkpoint")` returns a list of 4 event dicts
- [ ] `pytest --pyargs spec_kitty_events.conformance` passes with mission_audit fixtures present
- [ ] No regressions in existing dossier, collaboration, glossary, mission_next fixtures
- [ ] Manifest updated with exactly 17 new entries (7 valid + 4 invalid + 3 replay_stream + 3 reducer_output)
- [ ] All 7 valid fixture JSON files parse as valid Python dicts (no JSON syntax errors)
- [ ] All 4 invalid fixture JSON files parse correctly but are rejected by `validate_event()`

## Implementation Notes

- **Install first**: `python3.11 -m pip install -e ".[dev]"` immediately after entering worktree.
- **Manifest format**: Load existing `manifest.json` with `json.load()`, append entries to `manifest["fixtures"]`, write back with `json.dumps(manifest, indent=2, sort_keys=False)`. Preserve existing entry order — append-only.
- **Fixture file content**: These are payload-only dicts (not Event envelopes). The conformance `validate_event()` function validates payload dicts, not full Event envelopes.
- **Replay JSONL**: These ARE full Event envelopes (each line is a complete Event dict including `payload` as a nested dict). Follow the dossier replay format exactly.
- **ContentHashRef fields**: Must include `hash`, `algorithm`, `size_bytes`, `encoding` (check dossier.py for exact field names).
- **ProvenanceRef fields**: Must include `source_event_ids`, `git_sha`, `git_ref`, `actor_id`, `actor_kind`, `revised_at` (check dossier.py for exact field names).
- **Golden files dependency**: Golden reducer output files (`*_output.json`) require the working reducer (WP02). If WP02 is not merged yet, create placeholder `{}` files and flag them for regeneration. The WP04 conformance tests will fail on wrong golden content — this is acceptable as a joint WP02+WP03 integration issue.
- **`__init__.py` for fixtures directory**: The `mission_audit/` fixture directory does NOT need an `__init__.py` — it is a data directory, not a Python package.
- **Verify manifest count**: After updating manifest, run `python3.11 -c "import json; d=json.load(open('src/spec_kitty_events/conformance/fixtures/manifest.json')); audit=[f for f in d['fixtures'] if 'mission_audit' in f['path']]; print(len(audit))"` — should print 17.

## Test Commands

```bash
# Install editable package in worktree
python3.11 -m pip install -e ".[dev]"

# Verify schema loading
python3.11 -c "from spec_kitty_events.schemas import load_schema; s = load_schema('mission_audit_requested_payload'); print('Schema ok, properties:', list(s.get('properties',{}).keys()))"

# Verify validate_event works for mission-audit types
python3.11 -c "
from spec_kitty_events.conformance.validators import validate_event
r = validate_event({
    'mission_id': 'm', 'run_id': 'r', 'feature_slug': 'f', 'actor': 'a',
    'trigger_mode': 'manual', 'audit_scope': ['spec.md'], 'enforcement_mode': 'blocking'
}, 'MissionAuditRequested')
assert r.valid, f'Expected valid: {r.model_violations}'
print('validate_event OK')
"

# Verify load_fixtures returns 11 cases
python3.11 -c "
from spec_kitty_events.conformance.loader import load_fixtures
cases = load_fixtures('mission_audit')
print(f'{len(cases)} fixture cases (expected 11)')
assert len(cases) == 11
"

# Run full conformance suite
pytest --pyargs spec_kitty_events.conformance -v

# Full test suite (no regressions)
python3.11 -m pytest tests/ -v --tb=short
```

## Files to Create/Modify

| File | Action |
|---|---|
| `src/spec_kitty_events/schemas/mission_audit_requested_payload.json` | **CREATE** — generated JSON schema |
| `src/spec_kitty_events/schemas/mission_audit_started_payload.json` | **CREATE** — generated JSON schema |
| `src/spec_kitty_events/schemas/mission_audit_decision_requested_payload.json` | **CREATE** — generated JSON schema |
| `src/spec_kitty_events/schemas/mission_audit_completed_payload.json` | **CREATE** — generated JSON schema |
| `src/spec_kitty_events/schemas/mission_audit_failed_payload.json` | **CREATE** — generated JSON schema |
| `src/spec_kitty_events/conformance/validators.py` | **MODIFY** — add 5 imports + 10 dict entries |
| `src/spec_kitty_events/conformance/loader.py` | **MODIFY** — add "mission_audit" to _VALID_CATEGORIES |
| `src/spec_kitty_events/conformance/fixtures/mission_audit/valid/` (7 files) | **CREATE** — valid fixture JSONs |
| `src/spec_kitty_events/conformance/fixtures/mission_audit/invalid/` (4 files) | **CREATE** — invalid fixture JSONs |
| `src/spec_kitty_events/conformance/fixtures/mission_audit/replay/` (6 files) | **CREATE** — 3 JSONL + 3 golden JSON |
| `src/spec_kitty_events/conformance/fixtures/manifest.json` | **MODIFY** — append 17 new entries |

## Dependencies

- **Depends on**: WP01 (payload models needed for schema generation and validator imports).
- **Runs in parallel with**: WP02 (conformance integration does not depend on the reducer implementation; golden output files may need WP02 for generation).
- **Unblocks**: WP04 (conformance tests need fixtures and validator registrations).

## Completion Steps

When all subtasks are done and acceptance criteria pass:

1. Run the test commands above.
2. Commit: `git add src/ && git commit -m "feat(010): conformance integration — schemas, fixtures, validators — WP03"`
3. Mark subtasks done: `spec-kitty agent tasks mark-status T012 T013 T014 T015 T016 T017 T018 --status done`
4. Rebase on main: `git rebase main`
5. Move to review: `spec-kitty agent tasks move-task WP03 --to for_review --note "Conformance integration complete: 5 schemas, 7 valid + 4 invalid + 3 replay fixtures, manifest updated with 17 entries"`

## Activity Log

- 2026-02-26T12:35:58Z – claude-sonnet – shell_pid=34120 – lane=doing – Assigned agent via workflow command
- 2026-02-26T12:46:51Z – claude-sonnet – shell_pid=34120 – lane=for_review – Conformance integration complete: 5 schemas (with $schema/$id), 7 valid + 4 invalid + 3 replay JSONL fixtures, manifest updated with 17 entries, validators.py and loader.py updated. Golden reducer output files are placeholders pending WP02 merge. All 1119 unit tests pass, 11/11 mission_audit fixture validation tests pass.
- 2026-02-26T12:48:35Z – claude-reviewer – shell_pid=45764 – lane=doing – Started review via workflow command
