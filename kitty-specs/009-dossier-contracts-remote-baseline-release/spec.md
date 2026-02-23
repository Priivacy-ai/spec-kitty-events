# Feature Specification: Dossier Contracts Remote Baseline Release

**Feature Branch**: `009-dossier-contracts-remote-baseline-release`
**Created**: 2026-02-23
**Status**: Draft
**Input**: Remote Baseline Promotion + Dossier Contract Release (Team Prompt 2)

## Background

Feature 008 (Mission Dossier Parity Event Contracts) was implemented and tested locally,
producing four canonical dossier/parity event contracts, a dossier reducer, four JSON
schemas, thirteen conformance fixtures, and a complete test suite (1,117 tests passing).
The implementation was never pushed to `origin/2.x`.

The goal of this feature is to promote that completed implementation to the remote branch,
verify its integrity against the current upstream baseline, and publish a tagged release
so that runtime and SaaS consumers can depend on the contracts without local patching.

Recovery commits available in git reflog:

- `5237894` — `feat(008): merge Mission Dossier Parity Event Contracts into 2.x`
- `139ca09` — `fix(dossier): namespace mismatch false-positive on step_id variance and malformed-first-event`
- `640709f` — `docs: add security position statement` (upstream-only, must be included)

Implementation strategy: **Path A — Recover & Promote** (Path B re-implementation only
if integrity or test checks fail after recovery).

## User Scenarios & Testing

### User Story 1 — Runtime Consumer Installs Dossier Contracts from PyPI/Tag (Priority: P1)

A runtime engineer adds `spec-kitty-events>=2.4.0` to their dependency manifest.
After the package is available at the published tag, they can import the four dossier
contract classes and the dossier reducer directly from `spec_kitty_events`.
No local repo clone or manual patching is required.

**Why this priority**: Unblocks all downstream consumption. Without this, runtime and
SaaS teams must work around a remote that does not contain the contracts.

**Independent Test**: Install the package from the published `v2.4.0` tag and run
`from spec_kitty_events import MissionDossierArtifactIndexed` — import succeeds and
the class is the canonical Pydantic model with all documented fields.

**Acceptance Scenarios**:

1. **Given** `v2.4.0` is tagged on `origin/2.x`, **When** a consumer installs
   `spec-kitty-events==2.4.0`, **Then** all four dossier contract classes and
   `reduce_mission_dossier` are importable from the top-level package.

2. **Given** the tagged release, **When** a consumer inspects published JSON schemas,
   **Then** schemas for all four contract payloads are present and validate the
   corresponding conformance fixtures without errors.

3. **Given** `origin/2.x` at `v2.4.0`, **When** runtime or SaaS references the remote
   branch in a dependency lock, **Then** no local override or ad hoc patch is needed.

---

### User Story 2 — SaaS Parity Logic Reads Namespace Tuple Fields (Priority: P1)

A SaaS engineer building the parity projection queries the `LocalNamespaceTuple` fields
on `MissionDossierParityDriftDetected` events to scope drift detection per mission context.
All six namespace fields are present, documented, and schema-validated.

**Why this priority**: SaaS parity logic cannot scope drift correctly without a stable,
documented namespace contract. This unblocks the first SaaS ingestion milestone.

**Independent Test**: Load a `dossier_parity_drift_artifact_mutated.json` conformance
fixture, validate it against the published schema, and assert that all six namespace
fields (`project_uuid`, `feature_slug`, `target_branch`, `mission_key`,
`manifest_version`, and optional `step_id`) are present and typed correctly.

**Acceptance Scenarios**:

1. **Given** a `MissionDossierParityDriftDetected` event, **When** the SaaS parity
   projection extracts the namespace tuple, **Then** all five required fields are
   non-empty strings and `step_id` is either a non-empty string or absent/null.

2. **Given** two events from the same mission but different `step_id` values,
   **When** the namespace consistency check runs, **Then** they are treated as the
   same namespace (no false-positive `NamespaceMixedStreamError`).

3. **Given** a malformed first event with an unparseable namespace, **When** the
   dossier reducer processes the stream, **Then** the reducer skips the malformed
   event and establishes the canonical namespace from the first parseable event.

---

### User Story 3 — QA Validates Conformance Fixtures Against Published Schemas (Priority: P2)

A QA engineer runs the conformance suite against the `v2.4.0` fixtures to confirm that
valid fixtures pass and invalid fixtures are correctly rejected.

**Why this priority**: Validates the handoff baseline and gates downstream SaaS test
authoring on a known-good fixture set.

**Independent Test**: `python -m pytest tests/test_dossier_conformance.py` passes with
all valid fixtures accepted and all invalid fixtures rejected with specific, documented
error messages.

**Acceptance Scenarios**:

1. **Given** the nine valid dossier conformance fixtures, **When** the conformance
   validator runs, **Then** all nine pass without errors.

2. **Given** the two invalid dossier conformance fixtures, **When** the conformance
   validator runs, **Then** both are rejected with schema-validation errors identifying
   the specific field violation.

3. **Given** the two replay scenario files (`dossier_drift_scenario.jsonl`,
   `dossier_happy_path.jsonl`), **When** the dossier reducer processes each replay
   stream, **Then** the resulting `MissionDossierState` matches the expected snapshot
   for that scenario.

---

### User Story 4 — Release Tag Is Discoverable and Stable (Priority: P2)

A dependency manager or CI pipeline pins `v2.4.0`. The tag points to the exact commit
that merged the recovered and tested dossier work, is immutable once published, and
follows the existing `vX.Y.Z` format used by prior releases.

**Why this priority**: Consumers cannot reliably pin a branch HEAD; a proper tag is
required for reproducible installs and changelogs.

**Independent Test**: `git tag --list "v2.4.0"` returns the tag; `git show v2.4.0`
displays the merge commit including the CHANGELOG entry for 2.4.0; the tag is visible
on `origin`.

**Acceptance Scenarios**:

1. **Given** the promotion is merged to `origin/2.x`, **When** `v2.4.0` is pushed
   to origin, **Then** the tag is visible to all remote clones.

2. **Given** the `v2.4.0` tag, **When** `CHANGELOG.md` is inspected at that ref,
   **Then** it contains the 2.4.0 release section listing all four dossier contracts
   and the namespace-mismatch fix.

---

### Edge Cases

- **Recovery integrity failure**: If the recovered commits do not apply cleanly onto
  current `origin/2.x` HEAD, the implementation team falls back to Path B
  (re-implementation from scratch). The spec for Path B is the Feature 008 spec,
  which must be reconstructed from the reflog artifacts.

- **Upstream divergence**: If `origin/2.x` has received additional commits between
  feature start and merge, the integration branch must be rebased or merged before
  pushing; the test suite must pass on the rebased state.

- **Tag collision**: If a `v2.4.0` tag already exists on origin pointing to a
  different commit, the release must not overwrite it; investigation and coordination
  with the release manager is required before proceeding.

- **Namespace step_id false positive**: Events from the same mission with differing
  `step_id` values must not trigger `NamespaceMixedStreamError`. The recovered
  bugfix commit (`139ca09`) addresses this; the test suite must cover this scenario.

## Requirements

### Functional Requirements

- **FR-001**: The four event contracts (`MissionDossierArtifactIndexed`,
  `MissionDossierArtifactMissing`, `MissionDossierSnapshotComputed`,
  `MissionDossierParityDriftDetected`) MUST be exported from the top-level
  `spec_kitty_events` package on `origin/2.x`.

- **FR-002**: Each contract payload MUST include a `LocalNamespaceTuple` with fields
  `project_uuid`, `feature_slug`, `target_branch`, `mission_key`, `manifest_version`,
  and optional `step_id`, matching the namespace defined in PRD §8.5.

- **FR-003**: JSON schemas for all four contract payloads MUST be committed to the
  `schemas/` directory and validated by the conformance suite.

- **FR-004**: The conformance fixture set MUST include: nine valid fixtures, two
  invalid fixtures, and two replay scenario files covering missing-artifact and
  parity-drift scenarios.

- **FR-005**: The full test suite MUST pass on the integrated branch before the push
  to `origin/2.x` (baseline from Feature 008: 1,117 tests; regression tests for the
  namespace-mismatch bugfix must be included).

- **FR-006**: The dossier reducer (`reduce_mission_dossier`) MUST correctly handle
  streams where: (a) events share the same mission but differ in `step_id`, and
  (b) the first event has a malformed namespace payload.

- **FR-007**: Upstream commit `640709f` (security position statement) MUST be
  included in the final state on `origin/2.x` — either as an ancestor of the
  integration branch or merged in before the push.

- **FR-008**: A `v2.4.0` tag MUST be created and pushed to `origin` pointing to the
  merge commit on `origin/2.x`.

- **FR-009**: `CHANGELOG.md` at the tagged commit MUST contain the 2.4.0 release
  section documenting all four contracts and the namespace-mismatch fix.

### Key Entities

- **LocalNamespaceTuple**: Six-field namespace value object (`project_uuid`,
  `feature_slug`, `target_branch`, `mission_key`, `manifest_version`, optional
  `step_id`) that scopes dossier events to a unique mission context and prevents
  cross-feature drift collisions.

- **MissionDossierState**: Aggregate projection of all dossier events for a mission,
  produced by `reduce_mission_dossier`. Contains indexed artifacts, missing artifact
  records, the latest snapshot, and detected parity drifts.

- **ConformanceFixture**: Typed JSON file (valid, invalid, or replay/jsonl) used by
  the conformance suite to assert contract shape correctness and reducer behavior.

## Success Criteria

### Measurable Outcomes

- **SC-001**: All four dossier contract classes are importable from a fresh install
  of the `v2.4.0` package on a machine with no local clone of the repository.

- **SC-002**: The full test suite (≥1,117 tests) passes on the integrated branch
  with zero failures and ≥98% coverage on `src/spec_kitty_events/dossier.py`.

- **SC-003**: All nine valid conformance fixtures pass schema validation; both invalid
  fixtures are rejected with specific, documented field errors.

- **SC-004**: Both replay scenarios produce a deterministic `MissionDossierState`
  that matches their expected snapshot in ≤3 replay passes.

- **SC-005**: `v2.4.0` tag is visible on `origin/2.x` and `git show v2.4.0` returns
  the correct merge commit within one working session of the merge.

- **SC-006**: Zero ad hoc local patching is required by runtime or SaaS teams to
  consume the dossier contracts after `v2.4.0` is tagged.

## Assumptions

1. Commits `5237894` and `139ca09` remain accessible in the local git reflog throughout
   the duration of this feature's implementation. If reflog expiry occurs, Path B
   (re-implementation) becomes mandatory.

2. `origin/2.x` will not receive additional breaking changes between feature start and
   the merge; minor commits (docs, CI) are acceptable and will be rebased over.

3. The `v2.4.0` version number is correct and has not been reserved by another release
   on any branch or tag.

4. The conformance fixture schema is stable for `v2.4.0`; no fixture-format migration
   is required as part of this promotion.

5. No new contracts beyond the four dossier/parity contracts are in scope for `v2.4.0`.

## Out of Scope

1. SaaS UI implementation or dashboard rendering of dossier artifacts.
2. Runtime orchestration behavior changes.
3. New event contracts beyond the four dossier/parity contracts defined in Feature 008.
4. Cross-org or global namespace federation (deferred per PRD §15).
5. Dashboard framework migration (deferred per PRD §4.6).
