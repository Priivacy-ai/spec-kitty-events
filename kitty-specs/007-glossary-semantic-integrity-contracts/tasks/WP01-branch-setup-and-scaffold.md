---
work_package_id: "WP01"
subtasks:
  - "T001"
  - "T002"
  - "T003"
  - "T004"
title: "Branch Setup & Module Scaffold"
phase: "Phase 0 - Setup"
lane: "planned"
assignee: ""
agent: ""
shell_pid: ""
review_status: ""
reviewed_by: ""
dependencies: []
history:
  - timestamp: "2026-02-16T12:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP01 – Branch Setup & Module Scaffold

## ⚠️ IMPORTANT: Review Feedback Status

- **Has review feedback?**: Check the `review_status` field above.
- **You must address all feedback** before your work is complete.

---

## Review Feedback

*[This section is empty initially.]*

---

## Objectives & Success Criteria

- Cut `2.x` branch from `main` HEAD (`4aa95a6`) and tag as `2.x-baseline`.
- Create the `glossary.py` module in `src/spec_kitty_events/` with the correct scaffold structure.
- Define all 8 event type constants and the `GLOSSARY_EVENT_TYPES` frozenset.
- Update `pyproject.toml` to include glossary conformance fixture paths.

**Success**: `from spec_kitty_events.glossary import GLOSSARY_EVENT_TYPES` works and contains exactly 8 members. `mypy --strict` passes on the scaffold.

## Context & Constraints

- **Reference**: `kitty-specs/007-glossary-semantic-integrity-contracts/plan.md` — Design Decision D7 (branch setup).
- **Reference**: `kitty-specs/007-glossary-semantic-integrity-contracts/data-model.md` — Event Type Constants table.
- **Reference**: `src/spec_kitty_events/collaboration.py` — Section structure to mirror (Constants → Value Objects → Payload Models → Reducer Output → Reducer).
- **Schema version**: `"2.0.0"` — import from `lifecycle.py`, do not redefine.
- **Branch**: All work after T001 happens on the `2.x` branch.

**Implementation command**: `spec-kitty implement WP01`

## Subtasks & Detailed Guidance

### Subtask T001 – Cut `2.x` branch and tag baseline

- **Purpose**: Establish the `2.x` branch as the target for all glossary feature work. Main stays maintenance-only.
- **Steps**:
  1. Verify current HEAD is `4aa95a6`: `git rev-parse HEAD`
  2. Create the branch: `git branch 2.x`
  3. Tag the cut point: `git tag 2.x-baseline`
  4. Switch to the new branch: `git checkout 2.x`
  5. Verify: `git branch --show-current` should output `2.x`
- **Files**: None (git operations only).
- **Parallel?**: No — must complete before any other subtask.
- **Notes**: Do NOT push to remote yet — coordinate with team. The tag allows downstream repos to align to the same baseline commit.

### Subtask T002 – Create `glossary.py` module scaffold

- **Purpose**: Establish the module file with the correct structure, imports, and section comments matching `collaboration.py`.
- **Steps**:
  1. Create `src/spec_kitty_events/glossary.py`
  2. Add module docstring:
     ```python
     """Glossary semantic integrity event contracts for Feature 007.

     Defines event type constants, value objects, payload models,
     reducer output models, and the glossary reducer for
     mission-level semantic integrity enforcement.
     """
     ```
  3. Add `from __future__ import annotations`
  4. Add imports:
     ```python
     from typing import Dict, FrozenSet, List, Literal, Optional, Sequence, Tuple
     from pydantic import BaseModel, ConfigDict, Field
     from spec_kitty_events.models import SpecKittyEventsError
     ```
  5. Add section comment markers:
     ```python
     # ── Section 1: Constants ─────────────────────────────────────────────────────
     # ── Section 2: Value Objects ─────────────────────────────────────────────────
     # ── Section 3: Payload Models ────────────────────────────────────────────────
     # ── Section 4: Reducer Output Models ─────────────────────────────────────────
     # ── Section 5: Glossary Reducer ──────────────────────────────────────────────
     ```
- **Files**: `src/spec_kitty_events/glossary.py` (new file, ~30 lines initially).
- **Parallel?**: Yes — can proceed alongside T004 after T001 completes.
- **Notes**: Use `from __future__ import annotations` to match existing modules. Import `SpecKittyEventsError` for strict-mode error raising in the reducer (WP05/WP06).

### Subtask T003 – Define event type constants and frozenset

- **Purpose**: Establish the 8 event type constants that identify glossary events in the `Event.event_type` field.
- **Steps**:
  1. In Section 1 of `glossary.py`, define:
     ```python
     GLOSSARY_SCOPE_ACTIVATED: str = "GlossaryScopeActivated"
     TERM_CANDIDATE_OBSERVED: str = "TermCandidateObserved"
     SEMANTIC_CHECK_EVALUATED: str = "SemanticCheckEvaluated"
     GLOSSARY_CLARIFICATION_REQUESTED: str = "GlossaryClarificationRequested"
     GLOSSARY_CLARIFICATION_RESOLVED: str = "GlossaryClarificationResolved"
     GLOSSARY_SENSE_UPDATED: str = "GlossarySenseUpdated"
     GENERATION_BLOCKED_BY_SEMANTIC_CONFLICT: str = "GenerationBlockedBySemanticConflict"
     GLOSSARY_STRICTNESS_SET: str = "GlossaryStrictnessSet"
     ```
  2. Define the frozenset:
     ```python
     GLOSSARY_EVENT_TYPES: FrozenSet[str] = frozenset({
         GLOSSARY_SCOPE_ACTIVATED,
         TERM_CANDIDATE_OBSERVED,
         SEMANTIC_CHECK_EVALUATED,
         GLOSSARY_CLARIFICATION_REQUESTED,
         GLOSSARY_CLARIFICATION_RESOLVED,
         GLOSSARY_SENSE_UPDATED,
         GENERATION_BLOCKED_BY_SEMANTIC_CONFLICT,
         GLOSSARY_STRICTNESS_SET,
     })
     ```
- **Files**: `src/spec_kitty_events/glossary.py` (Section 1).
- **Parallel?**: Yes — works alongside T004.
- **Notes**: String values use PascalCase matching existing conventions (`PARTICIPANT_INVITED = "ParticipantInvited"` in collaboration.py). The frozenset is used by the reducer's filter step.

### Subtask T004 – Update `pyproject.toml` package-data

- **Purpose**: Ensure glossary conformance fixture JSON files will be included in the installed package.
- **Steps**:
  1. Open `pyproject.toml`
  2. In `[tool.setuptools.package-data]` under `spec_kitty_events`, add:
     ```toml
     "conformance/fixtures/glossary/valid/*.json",
     "conformance/fixtures/glossary/invalid/*.json",
     ```
  3. Add these lines after the existing `collaboration` entries.
- **Files**: `pyproject.toml` (modify existing).
- **Parallel?**: Yes — independent of T002/T003.
- **Notes**: The actual fixture files are created in WP10. This just prepares the packaging config so it's ready.

## Risks & Mitigations

- **Risk**: `2.x` branch already exists from a previous attempt. **Mitigation**: Check `git branch --list 2.x` first. If it exists, verify it's at the expected commit or coordinate before overwriting.
- **Risk**: `pyproject.toml` format change. **Mitigation**: Follow exact TOML array-of-strings pattern used by existing entries.

## Review Guidance

- Verify `2.x` branch points to `4aa95a6`.
- Verify `2.x-baseline` tag points to the same commit.
- Verify `glossary.py` has correct section structure matching `collaboration.py`.
- Verify all 8 constant values are PascalCase and `GLOSSARY_EVENT_TYPES` has exactly 8 members.
- Verify `pyproject.toml` entries match the glob pattern of existing fixture paths.

## Activity Log

- 2026-02-16T12:00:00Z – system – lane=planned – Prompt created.
