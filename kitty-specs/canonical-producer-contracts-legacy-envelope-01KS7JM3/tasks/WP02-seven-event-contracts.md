---
work_package_id: WP02
title: Seven canonical event-type contracts and LOCAL_ONLY_EVENT_TYPES surface
dependencies: []
requirement_refs:
- FR-010
- FR-011
- FR-012
- FR-013
- NFR-004
- NFR-005
- C-004
- C-008
planning_base_branch: kitty/pr/1198-canonical-producer-contracts
merge_target_branch: kitty/pr/1198-canonical-producer-contracts
branch_strategy: Planning artifacts for this mission were generated on kitty/pr/1198-canonical-producer-contracts. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into kitty/pr/1198-canonical-producer-contracts unless the human explicitly redirects the landing branch.
base_branch: kitty/pr/1198-canonical-producer-contracts
base_commit: 2a0667a1131fbc9db3ff5dba4634f52521a5293c
created_at: '2026-05-22T10:22:16+00:00'
subtasks:
- T006
- T007
- T008
- T011
- T012
phase: Phase 2 - Canonical contracts
history:
- timestamp: '2026-05-22T10:22:16Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/spec_kitty_events/
execution_mode: code_change
lane: planned
owned_files:
- src/spec_kitty_events/build_lifecycle.py
- src/spec_kitty_events/project_lifecycle.py
- src/spec_kitty_events/lifecycle.py
- src/spec_kitty_events/conformance/fixtures/events/valid/wp_assigned.json
- src/spec_kitty_events/conformance/fixtures/events/valid/build_registered.json
- src/spec_kitty_events/conformance/fixtures/events/valid/build_heartbeat.json
- src/spec_kitty_events/conformance/fixtures/events/valid/history_added.json
- src/spec_kitty_events/conformance/fixtures/events/valid/error_logged.json
- src/spec_kitty_events/conformance/fixtures/events/valid/dependency_resolved.json
- src/spec_kitty_events/conformance/fixtures/events/valid/mission_origin_bound.json
- tests/unit/test_seven_event_contracts.py
review_status: ''
reviewed_by: ''
role: implementer
tags: []
---

# Work Package Prompt: WP02 — Seven canonical event-type contracts + `LOCAL_ONLY_EVENT_TYPES`

## ⚡ Do This First: Load Agent Profile

```text
/ad-hoc-profile-load python-pedro
```

Or:

```bash
spec-kitty agent profile show python-pedro
```

---

## ⚠️ Review Feedback Status

If `review_status` above says `has_feedback`, scroll to **Review Feedback** below. Update to `acknowledged` when you start.

## Review Feedback

*(empty)*

---

## Objective

Ship canonical pydantic payload models for the seven SaaS-bound event types currently emitted by spec-kitty without contracts: `WPAssigned`, `BuildRegistered`, `BuildHeartbeat`, `HistoryAdded`, `ErrorLogged`, `DependencyResolved`, `MissionOriginBound`. Land the seven model fixture files alongside.

WP02 is the model-class producer. Registration into `_EVENT_TYPE_TO_MODEL` is performed by WP01 (which owns `validators.py`). Public-surface exports (`__init__.py`) and manifest entries are performed by WP04 (the registration hub).

`LOCAL_ONLY_EVENT_TYPES: frozenset[str] = frozenset()` is exported by WP04 as part of the public-surface integration.

## Context

### The audit

`spec-kitty/src/specify_cli/sync/emitter.py` at commit `43305c12c`, lines 720–1431, contains the seven `emit_*` methods that produce these events. Every one routes through `self._emit(...)`, the SaaS-bound central path (durable outbox + drain to SaaS). The classification rule (per the mission brief and `research.md` R1) is: routes through `_emit()` → SaaS-bound → needs canonical contract.

All seven are SaaS-bound. The `LOCAL_ONLY_EVENT_TYPES` set ships empty.

### Field shapes (from `research.md` R1 table)

| Event type | Required fields | Optional fields |
|------------|-----------------|-----------------|
| `WPAssigned` | `wp_id`, `agent_id`, `phase`, `retry_count` (default 0) | — |
| `BuildRegistered` | (envelope carries identity) | `repo_slug`, `git_branch`, `head_commit_sha` |
| `BuildHeartbeat` | (envelope carries identity) | `repo_slug`, `git_branch`, `head_commit_sha`, `remote_head`, `ahead_of_remote`, `behind_remote`, `recent_commits` |
| `HistoryAdded` | `wp_id`, `entry_type`, `entry_content`, `author` | — |
| `ErrorLogged` | `error_type`, `error_message` | `wp_id`, `stack_trace`, `agent_id` |
| `DependencyResolved` | `wp_id`, `dependency_wp_id`, `resolution_type` | — |
| `MissionOriginBound` | `mission_slug`, `provider`, `external_issue_id`, `external_issue_key`, `external_issue_url`, `title` | `mission_id` |

## Implementation guidance

### T006 — Create `src/spec_kitty_events/build_lifecycle.py`

**File**: NEW.

Template (follow the conventions of `project_lifecycle.py`):

```python
"""Build-aggregate event contracts.

Defines canonical pydantic payload models for build-lifecycle events emitted
by the spec-kitty CLI: ``BuildRegistered`` and ``BuildHeartbeat``. Build
identity (``build_id``, ``node_id``) lives on the canonical Event envelope;
these payloads carry only repo enrichment and (for BuildHeartbeat) sync
state vs the remote.

Aggregate type: ``Build``.
"""

from __future__ import annotations

from typing import FrozenSet, List, Optional

from pydantic import BaseModel, ConfigDict, Field

# Event type string constants
BUILD_REGISTERED: str = "BuildRegistered"
BUILD_HEARTBEAT: str = "BuildHeartbeat"

BUILD_LIFECYCLE_EVENT_TYPES: FrozenSet[str] = frozenset({
    BUILD_REGISTERED,
    BUILD_HEARTBEAT,
})


class BuildRegisteredPayload(BaseModel):
    """Typed payload for ``BuildRegistered`` events.

    Emitted once per build identity startup. Identity itself (``build_id``,
    ``node_id``) is on the envelope; this payload carries optional repo
    enrichment so consumers can correlate builds with git context.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    repo_slug: Optional[str] = Field(
        None, min_length=1, description="Git repository slug (e.g. 'org/repo')."
    )
    git_branch: Optional[str] = Field(
        None, min_length=1, description="Active git branch when the build registered."
    )
    head_commit_sha: Optional[str] = Field(
        None, min_length=1, description="Head commit SHA when the build registered."
    )


class BuildHeartbeatPayload(BaseModel):
    """Typed payload for ``BuildHeartbeat`` events.

    Emitted periodically by an active build. Carries repo enrichment plus
    optional sync state vs the remote so observers can detect divergence.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    repo_slug: Optional[str] = Field(
        None, min_length=1, description="Git repository slug."
    )
    git_branch: Optional[str] = Field(
        None, min_length=1, description="Active git branch at heartbeat time."
    )
    head_commit_sha: Optional[str] = Field(
        None, min_length=1, description="Head commit SHA at heartbeat time."
    )
    remote_head: Optional[str] = Field(
        None, min_length=1, description="Remote head commit SHA at heartbeat time."
    )
    ahead_of_remote: Optional[int] = Field(
        None, ge=0, description="Local commits ahead of the remote."
    )
    behind_remote: Optional[int] = Field(
        None, ge=0, description="Local commits behind the remote."
    )
    recent_commits: Optional[List[str]] = Field(
        None, description="Recent local commit SHAs (most-recent-first)."
    )


__all__ = [
    "BUILD_REGISTERED",
    "BUILD_HEARTBEAT",
    "BUILD_LIFECYCLE_EVENT_TYPES",
    "BuildRegisteredPayload",
    "BuildHeartbeatPayload",
]
```

### T007 — Extend `src/spec_kitty_events/project_lifecycle.py`

Add four new payload models and constants. Mirror the existing `WPCreatedPayload` conventions (frozen, extra=forbid, descriptive Field docs). Add to the file's `__all__` and to the event-type constants/frozensets at the top.

Add these constants near the existing ones:

```python
WP_ASSIGNED: str = "WPAssigned"
HISTORY_ADDED: str = "HistoryAdded"
ERROR_LOGGED: str = "ErrorLogged"
DEPENDENCY_RESOLVED: str = "DependencyResolved"
```

Update `WP_LIFECYCLE_EVENT_TYPES`:

```python
WP_LIFECYCLE_EVENT_TYPES: FrozenSet[str] = frozenset({
    WP_CREATED,
    WP_ASSIGNED,
    HISTORY_ADDED,
    ERROR_LOGGED,
    DEPENDENCY_RESOLVED,
})
```

Add the four payload models (place them after `WPCreatedPayload`):

```python
class WPAssignedPayload(BaseModel):
    """Typed payload for ``WPAssigned`` events.

    Emitted when a work-package is assigned to an agent for a specific
    phase (e.g. implement, review). Establishes the assignment record so
    later events (StatusChanged, HistoryAdded) can be correlated to the
    responsible agent.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    wp_id: str = Field(..., min_length=1, description="Work-package identifier.")
    agent_id: str = Field(..., min_length=1, description="Agent that picked up the WP.")
    phase: str = Field(..., min_length=1, description="Phase of work (e.g. 'implement', 'review').")
    retry_count: int = Field(0, ge=0, description="Number of times the assignment has been retried.")


class HistoryAddedPayload(BaseModel):
    """Typed payload for ``HistoryAdded`` events.

    Emitted when a free-form history entry is appended to a work-package's
    audit trail (notes, decisions, signal events that don't fit the lane
    state machine).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    wp_id: str = Field(..., min_length=1, description="Work-package the history entry attaches to.")
    entry_type: str = Field(..., min_length=1, description="Entry type code (e.g. 'note', 'decision').")
    entry_content: str = Field(..., min_length=1, description="Entry body.")
    author: str = Field(..., min_length=1, description="Who authored the entry.")


class ErrorLoggedPayload(BaseModel):
    """Typed payload for ``ErrorLogged`` events.

    Emitted when a runtime error is captured during agent execution.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    error_type: str = Field(..., min_length=1, description="Error class name or category.")
    error_message: str = Field(..., min_length=1, description="Human-readable error message.")
    wp_id: Optional[str] = Field(None, min_length=1, description="Work-package context, when known.")
    stack_trace: Optional[str] = Field(None, description="Stack trace text.")
    agent_id: Optional[str] = Field(None, min_length=1, description="Agent that observed the error.")


class DependencyResolvedPayload(BaseModel):
    """Typed payload for ``DependencyResolved`` events.

    Emitted when a work-package's blocking dependency resolves (merge,
    skip, cancellation).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    wp_id: str = Field(..., min_length=1, description="WP whose dependency resolved.")
    dependency_wp_id: str = Field(..., min_length=1, description="The dependency WP that resolved.")
    resolution_type: str = Field(..., min_length=1, description="How it resolved (e.g. 'merged', 'skipped').")
```

Append to `__all__`:

```python
"WP_ASSIGNED",
"HISTORY_ADDED",
"ERROR_LOGGED",
"DEPENDENCY_RESOLVED",
"WPAssignedPayload",
"HistoryAddedPayload",
"ErrorLoggedPayload",
"DependencyResolvedPayload",
```

### T008 — Extend `src/spec_kitty_events/lifecycle.py`

Add `MissionOriginBoundPayload` and its event-type constant, co-located with `MissionCreated`. Update `__all__`.

```python
MISSION_ORIGIN_BOUND: str = "MissionOriginBound"


class MissionOriginBoundPayload(BaseModel):
    """Typed payload for ``MissionOriginBound`` events.

    Records that a mission is bound to an external tracker issue (GitHub,
    Linear, Jira, etc.). Observational telemetry: the binding is a
    correlation hint, not an authority for mission state.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    mission_slug: str = Field(..., min_length=1, description="Canonical mission slug.")
    provider: str = Field(..., min_length=1, description="External tracker provider (e.g. 'github', 'linear').")
    external_issue_id: str = Field(..., min_length=1, description="Provider-native issue identifier.")
    external_issue_key: str = Field(..., min_length=1, description="Display key (e.g. 'PROJ-123').")
    external_issue_url: str = Field(..., min_length=1, description="Browser URL to the external issue.")
    title: str = Field(..., min_length=1, description="External issue title.")
    mission_id: Optional[str] = Field(None, min_length=1, description="Canonical mission ULID (when known).")
```

Add `MISSION_ORIGIN_BOUND` and `MissionOriginBoundPayload` to the module's exports.

### T011 — Add seven canonical fixtures (manifest entries land in WP04)

**Files**: seven new JSON files under `src/spec_kitty_events/conformance/fixtures/events/valid/`.

Each fixture is produced by `Model(...).model_dump(mode="json")` so it round-trips against the model. Example for `wp_assigned.json`:

```json
{
  "wp_id": "WP01",
  "agent_id": "claude",
  "phase": "implement",
  "retry_count": 0
}
```

Build the seven fixtures by instantiating each payload with realistic values, then `json.dumps(payload.model_dump(mode="json"), indent=2, sort_keys=True)` and write to disk. (Sorted keys keeps `test_fixture_determinism.py` green.)

The manifest entry registration for these fixtures is performed by WP04 (the public-surface registration hub), not by WP02.

### T012 — Add `tests/unit/test_seven_event_contracts.py`

**File**: NEW.

The test imports payload models directly from their source modules (not from `spec_kitty_events`) so the test can run before WP04 ships the package-root re-exports. Registry-presence (FR-011) and `LOCAL_ONLY_EVENT_TYPES` (FR-013) tests are deferred to WP04's verification step — WP02's tests cover FR-010 (models exist, round-trip, frozen+forbid).

```python
"""Tests for the seven canonical contracts shipped with WP02.

Covers FR-010 (model classes exist, round-trip, and reject extras).
Registry and public-surface tests live in WP04's verification step.
"""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from spec_kitty_events.build_lifecycle import (
    BuildRegisteredPayload,
    BuildHeartbeatPayload,
)
from spec_kitty_events.project_lifecycle import (
    WPAssignedPayload,
    HistoryAddedPayload,
    ErrorLoggedPayload,
    DependencyResolvedPayload,
)
from spec_kitty_events.lifecycle import MissionOriginBoundPayload

_SEVEN = [
    ("WPAssigned", WPAssignedPayload, {"wp_id": "WP01", "agent_id": "claude", "phase": "implement"}),
    ("BuildRegistered", BuildRegisteredPayload, {"repo_slug": "org/repo", "git_branch": "main", "head_commit_sha": "abc123"}),
    ("BuildHeartbeat", BuildHeartbeatPayload, {"repo_slug": "org/repo", "ahead_of_remote": 0, "behind_remote": 0}),
    ("HistoryAdded", HistoryAddedPayload, {"wp_id": "WP01", "entry_type": "note", "entry_content": "started", "author": "claude"}),
    ("ErrorLogged", ErrorLoggedPayload, {"error_type": "ValueError", "error_message": "oops"}),
    ("DependencyResolved", DependencyResolvedPayload, {"wp_id": "WP02", "dependency_wp_id": "WP01", "resolution_type": "merged"}),
    ("MissionOriginBound", MissionOriginBoundPayload, {"mission_slug": "demo", "provider": "github", "external_issue_id": "1198", "external_issue_key": "spec-kitty#1198", "external_issue_url": "https://github.com/Priivacy-ai/spec-kitty/issues/1198", "title": "Epic"}),
]


@pytest.mark.parametrize(("event_type", "model_cls", "fields"), _SEVEN, ids=[t[0] for t in _SEVEN])
def test_payload_round_trip(event_type: str, model_cls, fields: dict) -> None:
    model = model_cls(**fields)
    data = model.model_dump(mode="json")
    restored = model_cls.model_validate(data)
    assert restored == model


@pytest.mark.parametrize(("event_type", "model_cls", "fields"), _SEVEN, ids=[t[0] for t in _SEVEN])
def test_payload_is_frozen(event_type: str, model_cls, fields: dict) -> None:
    """C-004 + plan: every model uses ConfigDict(frozen=True, extra='forbid')."""
    assert model_cls.model_config.get("frozen") is True
    assert model_cls.model_config.get("extra") == "forbid"


@pytest.mark.parametrize(("event_type", "model_cls", "fields"), _SEVEN, ids=[t[0] for t in _SEVEN])
def test_payload_rejects_extra_fields(event_type: str, model_cls, fields: dict) -> None:
    """extra='forbid' is the drift-detection mechanism."""
    polluted = {**fields, "this_field_does_not_exist": True}
    with pytest.raises(ValidationError):
        model_cls(**polluted)
```

## Branch Strategy

Same as WP01.

## Definition of Done

- [ ] `src/spec_kitty_events/build_lifecycle.py` exists with `BuildRegisteredPayload`, `BuildHeartbeatPayload`, constants, `__all__`.
- [ ] `project_lifecycle.py` extended with four payload models + constants + `__all__`.
- [ ] `lifecycle.py` extended with `MissionOriginBoundPayload` + constant + export.
- [ ] Seven canonical fixtures under `events/valid/` (one per event type), each produced by `model.model_dump(mode="json")` with `sort_keys=True`.
- [ ] `tests/unit/test_seven_event_contracts.py` exists; runs without depending on `validators.py` registry or `__init__.py` re-exports.
- [ ] `uv run pytest tests/unit/test_seven_event_contracts.py tests/unit/test_fixtures.py -q` exits 0.
- [ ] `uv run pytest tests/test_fixture_determinism.py -q` exits 0 (sorted-keys discipline preserved; new fixture files are sorted).
- [ ] No new pip dependencies in `pyproject.toml`.
- [ ] WP02 does NOT touch `validators.py`, `__init__.py`, or `manifest.json` (those are WP01 and WP04 territory).

## Reviewer guidance

1. Verify every model uses `ConfigDict(frozen=True, extra="forbid")`.
2. Verify the seven fixtures are byte-for-byte the output of `json.dumps(model.model_dump(mode="json"), indent=2, sort_keys=True)`.
3. Verify the seven `_EVENT_TYPE_TO_MODEL` entries are present and bind to the correct classes.
4. Verify `LOCAL_ONLY_EVENT_TYPES` is `frozenset[str]` (not list, not set, not mutable).
5. Verify no schema files were added under `src/spec_kitty_events/schemas/` for the seven new types (intentional per plan; schemas are deferred to Phase 5).
6. Verify the manifest entries are inserted in sorted-by-id order if the existing manifest follows that pattern (it does — preserve it).

## Risks

- **Risk**: Fixtures drift from models. **Mitigation**: T011 specifies `model_dump(mode="json")` + `sort_keys=True`; T012's round-trip test catches drift.
- **Risk**: A `ConfigDict(frozen=True, extra="forbid")` choice rejects valid future fields. **Mitigation**: spec C-004 explicitly accepts this trade — drift surfaces at the contract boundary, not silently downstream.
- **Risk**: WP02 and WP01 both edit `validators.py`. **Mitigation**: WP01 edits are inside `validate_event()` body and add `_SEMANTIC_VALIDATORS`; WP02 edits add seven entries to `_EVENT_TYPE_TO_MODEL` (a different dict in the same file). Lane merge handles textually disjoint edits.
