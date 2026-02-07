---
work_package_id: WP03
title: Version Bump & Changelog
lane: "done"
dependencies:
- WP01
base_branch: main
base_commit: 6f5649455c9e1d561f7436829e62b95b5034826f
created_at: '2026-02-07T20:39:52.965991+00:00'
subtasks:
- T011
- T012
- T013
phase: Phase 2 - Release Prep
assignee: ''
agent: ''
shell_pid: "52812"
review_status: "approved"
reviewed_by: "Robert Douglass"
history:
- timestamp: '2026-02-07T00:00:00Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP03 – Version Bump & Changelog

## Review Feedback

> **Populated by `/spec-kitty.review`** – Reviewers add detailed feedback here when work needs changes.

*[This section is empty initially.]*

---

## Markdown Formatting
Wrap HTML/XML tags in backticks: `<div>`, `<script>`
Use language identifiers in code blocks: `python`, `bash`

---

## Objectives & Success Criteria

Bump the library version to `0.2.0-alpha`, write a complete changelog entry documenting all new public API additions, and validate that the quickstart code examples actually work with the implementation.

**Success criteria**:
- `python -c "import spec_kitty_events; assert spec_kitty_events.__version__ == '0.2.0-alpha'"` passes
- `pyproject.toml` shows `version = "0.2.0-alpha"`
- `CHANGELOG.md` contains a `## [0.2.0-alpha]` section with all 5 new exports documented
- Quickstart.md code snippets execute without error

## Context & Constraints

**Reference documents**:
- **Spec**: `kitty-specs/002-github-gate-observability-contracts/spec.md` — FR-013, User Story 4, SC-006
- **Plan**: `kitty-specs/002-github-gate-observability-contracts/plan.md` — Design decision D6
- **Quickstart**: `kitty-specs/002-github-gate-observability-contracts/quickstart.md` — code examples to validate
- **Existing changelog**: `CHANGELOG.md` — follow Keep a Changelog format

**Prerequisite**: WP01 and WP02 must be complete. All production code and tests must pass.

**Implementation command**: `spec-kitty implement WP03 --base WP02`

## Subtasks & Detailed Guidance

### Subtask T011 – Bump version to `0.2.0-alpha`

**Purpose**: Update the version string in both locations where it's defined. This is a minor version bump (additive, non-breaking changes per semver).

**Steps**:

1. Edit `pyproject.toml` — change the version field:
   ```
   # Before:
   version = "0.1.1-alpha"

   # After:
   version = "0.2.0-alpha"
   ```

2. Edit `src/spec_kitty_events/__init__.py` — change the `__version__` string:
   ```python
   # Before:
   __version__ = "0.1.1-alpha"

   # After:
   __version__ = "0.2.0-alpha"
   ```

3. **Verify consistency**: Run this check:
   ```bash
   python -c "import spec_kitty_events; print(spec_kitty_events.__version__)"
   ```
   Expected output: `0.2.0-alpha`

**Files**:
- `pyproject.toml` (line 3)
- `src/spec_kitty_events/__init__.py` (line 16)

**Parallel?**: Yes — can be done in parallel with T012.

### Subtask T012 – Update CHANGELOG.md

**Purpose**: Document all new public API additions for downstream consumers. This satisfies FR-013 and SC-006.

**Steps**:

1. Open `CHANGELOG.md`.

2. Under the existing `## [Unreleased]` section, add a new version section:

   ```markdown
   ## [0.2.0-alpha] - YYYY-MM-DD

   ### Added
   - `GatePayloadBase` — shared Pydantic base model for CI gate outcome event payloads
   - `GatePassedPayload(GatePayloadBase)` — typed payload for successful gate conclusions (`success`)
   - `GateFailedPayload(GatePayloadBase)` — typed payload for failed gate conclusions (`failure`, `timed_out`, `cancelled`, `action_required`)
   - `map_check_run_conclusion(conclusion, on_ignored=None)` — deterministic mapping from GitHub `check_run` conclusion strings to event type strings (`"GatePassed"`, `"GateFailed"`, or `None` for ignored)
   - `UnknownConclusionError(SpecKittyEventsError)` — raised for unrecognized conclusion values
   - Ignored conclusions (`neutral`, `skipped`, `stale`) are logged via `logging.getLogger("spec_kitty_events.gates")` and optionally reported via `on_ignored` callback
   - All new types exported from `spec_kitty_events` package public API
   - Unit tests for payload model validation, field constraints, and serialization round-trips
   - Hypothesis property tests for mapping determinism and exhaustiveness
   ```

3. Replace `YYYY-MM-DD` with today's date in ISO format.

4. Update the comparison links at the bottom of the file:
   ```markdown
   [Unreleased]: https://github.com/Priivacy-ai/spec-kitty-events/compare/v0.2.0-alpha...HEAD
   [0.2.0-alpha]: https://github.com/Priivacy-ai/spec-kitty-events/compare/v0.1.1-alpha...v0.2.0-alpha
   [0.1.1-alpha]: https://github.com/Priivacy-ai/spec-kitty-events/compare/v0.1.0-alpha...v0.1.1-alpha
   [0.1.0-alpha]: https://github.com/Priivacy-ai/spec-kitty-events/releases/tag/v0.1.0-alpha
   ```

**Files**: `CHANGELOG.md`
**Parallel?**: Yes — can be done in parallel with T011.

### Subtask T013 – Validate quickstart.md code examples

**Purpose**: Ensure that the quickstart documentation accurately reflects the actual implementation. Run each code snippet and verify it produces the expected results.

**Steps**:

1. Read `kitty-specs/002-github-gate-observability-contracts/quickstart.md`.

2. Test each code snippet in a Python shell or script:

   **Snippet 1 — Mapping conclusions**:
   ```python
   from spec_kitty_events import map_check_run_conclusion

   assert map_check_run_conclusion("success") == "GatePassed"
   assert map_check_run_conclusion("failure") == "GateFailed"
   assert map_check_run_conclusion("neutral") is None
   ```

   **Snippet 2 — Constructing a payload**:
   ```python
   from spec_kitty_events import GatePassedPayload

   payload = GatePassedPayload(
       gate_name="ci/build",
       gate_type="ci",
       conclusion="success",
       external_provider="github",
       check_run_id=123456,
       check_run_url="https://github.com/org/repo/runs/123456",
       delivery_id="webhook-delivery-uuid",
       pr_number=42,
   )
   assert payload.gate_name == "ci/build"
   assert payload.pr_number == 42
   ```

   **Snippet 3 — Attaching to Event**:
   ```python
   import uuid
   from datetime import datetime
   from spec_kitty_events import Event

   event = Event(
       event_id="01HXYZ" + "A" * 20,
       event_type="GatePassed",
       aggregate_id="my-project",
       payload=payload.model_dump(),
       timestamp=datetime.now(),
       node_id="worker-1",
       lamport_clock=1,
       project_uuid=uuid.uuid4(),
   )
   assert event.payload["gate_name"] == "ci/build"
   ```

   **Snippet 4 — Callback**:
   ```python
   calls = []
   result = map_check_run_conclusion("skipped", on_ignored=lambda c, r: calls.append((c, r)))
   assert result is None
   assert calls == [("skipped", "non_blocking")]
   ```

3. If any snippet fails, fix the **quickstart.md** to match the actual implementation (not the other way around — the code is the source of truth).

4. If all snippets pass, no changes needed.

**Files**: `kitty-specs/002-github-gate-observability-contracts/quickstart.md` (only if corrections needed)
**Parallel?**: No — depends on WP01 and WP02 being functionally complete.

## Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Version string mismatch between files | Low | High | Verify both locations in T011. Script check catches drift. |
| Changelog link URLs wrong | Low | Low | Copy existing link pattern exactly, just update version numbers. |
| Quickstart examples outdated after WP01/WP02 changes | Medium | Medium | Run all snippets; fix quickstart.md if needed. |

## Review Guidance

- Verify version is `0.2.0-alpha` in both `pyproject.toml` and `__init__.py`.
- Verify changelog lists all 5 new public API exports.
- Verify changelog date matches the implementation date.
- Verify comparison links are correct (new version compared to previous).
- Verify quickstart examples were actually tested (not just assumed correct).

## Activity Log

- 2026-02-07T00:00:00Z – system – lane=planned – Prompt created.
- 2026-02-07T20:41:24Z – unknown – shell_pid=52812 – lane=for_review – Version bumped, changelog complete, quickstart validated
- 2026-02-07T20:41:31Z – unknown – shell_pid=52812 – lane=done – Review passed: version consistent, changelog complete, quickstart validated
