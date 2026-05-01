---
work_package_id: WP06
title: Compatibility Doc and Version Bump
dependencies:
- WP01
- WP02
- WP03
- WP04
- WP05
requirement_refs:
- C-003
- FR-009
- FR-010
planning_base_branch: main
merge_target_branch: main
branch_strategy: Worktree per lane; planning base main; merge target main
subtasks:
- T025
- T026
- T027
agent: claude
history:
- event: created
  at: '2026-05-01T09:44:26Z'
  by: /spec-kitty.tasks
agent_profile: implementer-ivan
authoritative_surface: COMPATIBILITY.md
execution_mode: code_change
owned_files:
- COMPATIBILITY.md
- CHANGELOG.md
- pyproject.toml
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load implementer-ivan
```

---

## Objective

Land the public-release artifacts: a major schema version bump (`pyproject.toml`), a `CHANGELOG.md` "Breaking Changes" entry, and a new `COMPATIBILITY.md` section explaining the local-CLI compatibility vs TeamSpace ingress validity distinction.

These artifacts are the public-facing record of this mission's contract change. Codex reviews them.

---

## Context

- Spec: FR-009, FR-010, C-003, SC-006.
- Contract: [contracts/versioning-and-compatibility.md](../contracts/versioning-and-compatibility.md).
- Research: [research.md R-03](../research.md#r-03--schema-version-bump-semantic).

---

## Subtasks

### T025 — Update `COMPATIBILITY.md`

**Purpose**: Document the two validity domains (local CLI vs TeamSpace ingress) and pin the bump rationale.

**Steps**:
1. Open `COMPATIBILITY.md`. Read the existing structure to find the right insertion point (typically after a header section, before historical entries).
2. Add a new section with the heading appropriate to the file's existing voice. Suggested title: `## Local-CLI compatibility vs TeamSpace ingress validity (added 2026-05-01)`.
3. The section MUST cover:
   - The two distinct validity domains:
     - **Local-CLI compatibility**: the CLI continues to read historical `status.events.jsonl` rows on local disk for users' own bookkeeping.
     - **TeamSpace ingress validity**: only canonical envelopes pass ingress.
   - One concrete example of each (a one-line JSON snippet of a valid local row that is invalid for ingress, and a canonical envelope that is valid for both).
   - A statement that local compatibility is **not** weakened by this mission's bump.
   - A pointer to the CLI canonicalizer in `spec-kitty` Tranche B as the documented bridge.
   - A pointer to [contracts/lane-vocabulary.md](../kitty-specs/teamspace-event-contract-foundation-01KQHDE4/contracts/lane-vocabulary.md) and [contracts/payload-reconciliation.md](../kitty-specs/teamspace-event-contract-foundation-01KQHDE4/contracts/payload-reconciliation.md).
   - The bump rationale (why this is a major bump, citing R-03).

**Files**:
- `COMPATIBILITY.md` (modified)

**Validation**:
- [ ] Section is present with the required content.
- [ ] Two examples (local-valid-only, both-valid) are concrete JSON snippets.
- [ ] Cross-links resolve.

---

### T026 — Update `CHANGELOG.md`

**Purpose**: Public release notes for the major bump.

**Steps**:
1. Open `CHANGELOG.md`. Identify the format (e.g., `## [version] - YYYY-MM-DD` headers) and follow it.
2. Add an entry at the top for the new version (matching the bump in T027). Include:

   ```markdown
   ## [<new-version>] - 2026-05-01

   ### Breaking Changes

   - **`in_review` is now a canonical lane** (FR-001, FR-002). Consumers that
     previously rejected `in_review` as an unknown lane now accept it. Update
     consumer code that switches on the lane vocabulary's exact membership.

   - **Payload contracts reconciled** (FR-003, FR-004). `MissionCreatedPayload`,
     `WPStatusChangedPayload`, and `MissionClosedPayload` are now the single
     source of truth; CLI and SaaS producers must conform. See the reconciliation
     log in `kitty-specs/teamspace-event-contract-foundation-01KQHDE4/contracts/payload-reconciliation.md`.

   - **Recursive forbidden-key validator** (FR-005). The package now rejects
     envelopes containing legacy keys (`feature_slug`, `feature_number`,
     `mission_key`, plus the audit-derived expansion) at any depth, including
     inside array elements.

   ### Added

   - `ValidationError` and `ValidationErrorCode` for structured rejection
     reporting (NFR-006).
   - `forbidden_keys` module with `FORBIDDEN_LEGACY_KEYS` and the recursive
     validator.
   - Eight-class conformance fixture suite covering canonical envelopes,
     historical synthesized envelopes, every rejection class, raw historical
     rows, and lane-mapping legacy.
   - `COMPATIBILITY.md` section: local-CLI compatibility vs TeamSpace ingress
     validity.

   ### Fixed

   - `MissionClosed` payload disagreement between CLI emission and library
     model (resolved per the reconciliation log).
   ```

3. Make sure the entry is grammatical and concise; Codex reviews this.

**Files**:
- `CHANGELOG.md` (modified)

**Validation**:
- [ ] New version header at the top.
- [ ] Three Breaking Changes bullets covering lane vocabulary, payload reconciliation, and the recursive validator.
- [ ] Cross-references to FR IDs preserved.

---

### T027 — Bump package version in `pyproject.toml`

**Purpose**: Apply the version bump per major-bump rule.

**Steps**:
1. Open `pyproject.toml`. Locate the `[project]` (or equivalent) section and the `version = "..."` line.
2. Bump the major component. If the package is currently at `3.0.x`, the new version is `4.0.0`. If the package is at a `3.0.0a` pre-release line, the new version is `4.0.0` (a major release ends the pre-release of 3.x).
3. If the package's version is referenced anywhere else (e.g., in `__init__.py` `__version__ = "..."`), update those references — but be cautious about file ownership: this WP only owns `pyproject.toml`. If `__init__.py` carries a `__version__` constant, leave a TODO comment in this WP's commit message and propose a follow-up; do not silently break ownership.

   **Best path**: confirm before editing whether `__version__` is read from `pyproject.toml` at runtime (e.g., via `importlib.metadata`). If yes, no separate edit needed.

**Files**:
- `pyproject.toml` (modified, one-line version bump plus any required dependency tweaks)

**Validation**:
- [ ] `pyproject.toml` parses (try `python -c "import tomllib; tomllib.load(open('pyproject.toml','rb'))"` for Python 3.11+; otherwise use `tomli`).
- [ ] `pip install .` (or `uv pip install .`) succeeds.
- [ ] Schema-drift CI gate is still green (the version bump should not change committed `*.schema.json` content unless a schema's `$id` includes the version — coordinate with WP04's regeneration).

---

## Branch Strategy

- Planning/base branch: `main` · Merge target: `main` · Worktree allocated by `finalize-tasks`.

---

## Definition of Done

- [ ] `COMPATIBILITY.md` has the new section with both validity domains, examples, and the bump rationale.
- [ ] `CHANGELOG.md` has the new version entry with Breaking Changes bullets.
- [ ] `pyproject.toml` version is bumped to the new major.
- [ ] `pip install .` (or `uv pip install .`) succeeds.
- [ ] Full pytest still green.
- [ ] No file outside `owned_files` modified.

---

## Risks

- **R-1**: A `__version__` constant in `__init__.py` becomes stale. Mitigation: confirm it's runtime-derived from package metadata; if not, surface as follow-up.
- **R-2**: Schema `$id` URLs include the version, so the regenerated schemas drift on bump. Mitigation: coordinate with WP04's regeneration script; the schema-drift CI gate will catch the mismatch. If the gate fails, run the regenerator from WP04's owned set.
- **R-3**: Downstream tranche pinning. Mitigation: cross-tranche communication; each downstream tranche updates its `spec-kitty-events` pin during its own WP.

---

## Reviewer Guidance

Codex reviewer will check:

1. The version bump is genuinely major (e.g., 3.x → 4.0.0), not a minor or patch.
2. The CHANGELOG entry uses "Breaking Changes" language honestly — no euphemism.
3. `COMPATIBILITY.md` does not weaken the local-CLI compatibility wording.
4. Both examples (local-only-valid, both-valid) are real, copy-pasteable JSON.
5. No silent rebase of unrelated CHANGELOG entries.
