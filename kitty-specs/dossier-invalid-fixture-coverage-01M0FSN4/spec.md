# Mission Specification: Dossier Invalid Fixture Coverage

**Mission Branch**: `feat/dossier-invalid-fixture-coverage`
**Created**: 2026-08-20
**Status**: Draft
**Input**: Close the spec-kitty-events side of GitHub issue #23 (Priivacy-ai/spec-kitty-events) by adding the missing invalid conformance fixtures for the `MissionDossierArtifactMissing` and `MissionDossierSnapshotComputed` payloads.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Invalid-fixture coverage for MissionDossierArtifactMissing (Priority: P1)

As a maintainer of the dossier event contract, I want an invalid conformance fixture for `MissionDossierArtifactMissing` so that malformed payloads of this type are caught by the conformance suite, the same way `MissionDossierArtifactIndexed` and `MissionDossierParityDriftDetected` already are.

**Why this priority**: This is one of the two concrete gaps blocking full acceptance-criteria coverage for issue #23's fixture requirement ("golden conformance fixtures for each dossier event payload" — valid AND invalid).

**Independent Test**: Add `dossier_artifact_missing_<violation>.json` under `src/spec_kitty_events/conformance/fixtures/dossier/invalid/`, register it in `src/spec_kitty_events/conformance/fixtures/manifest.json` (`expected_result: invalid`, with a `notes` field naming the exact field/rule broken) — the manifest entry, not the file's mere presence, is what makes `load_fixtures()` and the parametrized conformance tests see it at all. The violation must target an actively-enforced Pydantic constraint on `MissionDossierArtifactMissingPayload` (e.g. `manifest_step`'s `min_length=1`, or a required nested field), not a docstring-only convention (e.g. a timestamp field has no format validator and would silently pass). The fixture must otherwise be a minimally-modified valid sibling — exactly one field/rule broken, everything else intact — and the violation kind must be genuinely new versus the three existing invalid fixtures (invalid Literal/enum, missing one field, missing multiple nested `namespace` fields).

**Acceptance Scenarios**:

1. **Given** the new invalid `MissionDossierArtifactMissing` fixture, **When** it is run through `validate_event()`, **Then** validation fails with a violation pointing at the deliberately broken field.
2. **Given** the existing valid `MissionDossierArtifactMissing` fixtures, **When** the full dossier conformance suite runs, **Then** they continue to pass unaffected by the new invalid fixture.

---

### User Story 2 - Invalid-fixture coverage for MissionDossierSnapshotComputed (Priority: P1)

As a maintainer of the dossier event contract, I want an invalid conformance fixture for `MissionDossierSnapshotComputed` so that this payload type has the same fail-closed test coverage as the other three dossier events.

**Why this priority**: The second (and last) concrete gap for issue #23's fixture requirement in this repo.

**Independent Test**: Add `dossier_snapshot_computed_negative_count.json` under `.../fixtures/dossier/invalid/` and register it in `src/spec_kitty_events/conformance/fixtures/manifest.json` the same way as User Story 1's fixture. Locked-in violation (per planning decision `01M0FTVXSW7FW2SZC9F2QWS9BP`): `artifact_count: -1`, violating `ge=0`. An invalid `algorithm` literal was considered and explicitly rejected — it would repeat the invalid-Literal/enum category already covered by the existing `ArtifactIndexed` fixture. Distinct from both the `ArtifactMissing` fixture in User Story 1 and the three pre-existing invalid fixtures — no repeat of "missing single field," "invalid Literal," or "missing multiple namespace fields."

**Acceptance Scenarios**:

1. **Given** the new invalid `MissionDossierSnapshotComputed` fixture, **When** it is run through `validate_event()`, **Then** validation fails with a violation pointing at the deliberately broken field.
2. **Given** both new invalid fixtures (User Stories 1 and 2), **When** compared, **Then** each exercises a distinct violation kind (not the same field/rule broken twice).

---

### User Story 3 - Confirm full acceptance-criteria closure for #23 in this repo (Priority: P2)

As the person tracking issue #23, I want a clear statement of which acceptance criteria are met by this repo after this mission, so I can distinguish "spec-kitty-events is done" from the separate `spec-kitty` mirror-deletion work, which is tracked in `spec-kitty` issue #1058 (open, explicitly blocked on this issue, not yet started as of 2026-08-20 — corrected from an earlier "already in progress" assumption that adversarial review found no evidence for).

**Why this priority**: Tracker hygiene — issue #23 spans two repos, and this mission only closes the spec-kitty-events half.

**Independent Test**: Review the mission's final report against the issue's five acceptance criteria and confirm which are met here versus owned elsewhere.

**Acceptance Scenarios**:

1. **Given** this mission is merged, **When** the four dossier payload types are checked, **Then** all four have both valid and invalid conformance fixtures.
2. **Given** the mirror-deletion criterion (owned by `spec-kitty`, tracked in `spec-kitty`#1058), **When** this mission's report is read, **Then** it is explicitly marked out of scope / open elsewhere, not silently implied as done or in progress.
3. **Given** this mission merges, **When** it closes, **Then** a comment is posted on `Priivacy-ai/spec-kitty-events`#23 recording that the fixture-coverage acceptance criterion is now met via this mission, since automated tracker sync is currently blocked (TeamSpace migration pending) and no structured issue-linkage field exists in this project's mission metadata.

---

### Edge Cases

- What happens if a new "invalid" fixture accidentally still passes `validate_event()` (e.g. because Pydantic coerces the broken value, or the chosen field has no active constraint — several `dossier.py` timestamp fields are plain `str` with only a docstring claiming ISO 8601, no format validator)? The violation must target a field with a real Pydantic constraint (`Literal`, `min_length`, `ge`, or the model's `extra="forbid"`), and the fixture must be run through `validate_event()` locally before commit to confirm it genuinely fails.
- What happens if a new invalid fixture reintroduces a violation kind already covered by the existing `ArtifactIndexed`/`ParityDriftDetected` invalid fixtures? Each new fixture must exercise a distinct, previously-uncovered violation.
- What happens if a fixture file is added to `fixtures/dossier/invalid/` without a matching `manifest.json` entry? `load_fixtures()` reads only from the manifest, not the directory, so the fixture would be silently invisible to every conformance test — this is the primary failure mode this spec must guard against (see FR-003).

## Requirements *(mandatory)*

### Functional Requirements

| ID | Title | User Story | Priority | Status |
|----|-------|------------|----------|--------|
| FR-001 | Invalid fixture for MissionDossierArtifactMissing | As a contract maintainer, I want an invalid `MissionDossierArtifactMissing` fixture — targeting a real Pydantic constraint, minimally different from a valid sibling, registered in `manifest.json` — so that malformed payloads of this type are caught by the conformance suite. | High | Open |
| FR-002 | Invalid fixture for MissionDossierSnapshotComputed | As a contract maintainer, I want an invalid `MissionDossierSnapshotComputed` fixture — exercising a violation kind distinct from FR-001's and the three pre-existing invalid fixtures, registered in `manifest.json` — so that malformed payloads of this type are caught by the conformance suite. | High | Open |
| FR-003 | Register fixtures in the manifest and update fixture-count gates | As a contract maintainer, I want both new fixtures added as entries in `src/spec_kitty_events/conformance/fixtures/manifest.json` (`expected_result: invalid`) — the actual mechanism `load_fixtures()` uses, not directory-scanning — and the hardcoded counts in `tests/test_dossier_conformance.py` updated (`test_dossier_fixture_count` 13→15, `test_dossier_invalid_case_count` 3→5), so the existing manifest-driven parametrized tests (`test_valid_fixture_passes_conformance`, `test_invalid_fixture_fails_conformance`) pick both fixtures up automatically. No new bespoke per-fixture test function is needed or wanted. | High | Open |

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
|----|-------|-------------|----------|----------|--------|
| NFR-001 | No regression in existing dossier conformance | Full `pytest` run of `tests/test_dossier_conformance.py` passes with zero new failures. (`tests/test_fixture_determinism.py` does not walk `fixtures/dossier/` per its own module docstring, so it is not a relevant regression gate for this change and is excluded here.) | Reliability | High | Open |
| NFR-002 | Manifest/directory consistency | Every JSON file added under `fixtures/dossier/invalid/` has exactly one corresponding `manifest.json` entry, and vice versa — no orphaned fixture file and no dangling manifest entry. | Reliability | High | Open |

### Constraints

| ID | Title | Constraint | Category | Priority | Status |
|----|-------|------------|----------|----------|--------|
| C-001 | Fixtures-only change | No changes to `src/spec_kitty_events/dossier.py` payload models, the four JSON Schemas, or `validate_event()` — all already ship the needed surface. | Technical | High | Open |
| C-002 | Cross-repo work excluded | The `spec-kitty` repo's local MissionDossier payload mirror deletion (`src/specify_cli/dossier/events.py`) and its duplicate `_PAYLOAD_RULES` entries are explicitly out of scope. That work is tracked in `spec-kitty` issue #1058 (open, blocked on this issue, not yet started as of 2026-08-20) — not "in progress" as originally assumed; adversarial review found no branch, commit, or PR activity evidencing active work. | Business | High | Open |
| C-003 | Reviewer diff-scope check | Since conformance fixtures are part of the public contract surface, the PR reviewer must confirm the diff touches only `fixtures/dossier/invalid/*.json`, `fixtures/manifest.json`, and the two count literals in `tests/test_dossier_conformance.py` — no changes to `dossier.py`, the JSON Schema files, or `validate_event()`. | Regulatory | Medium | Open |

### Key Entities *(include if feature involves data)*

- **Invalid conformance fixture**: A JSON file under `src/spec_kitty_events/conformance/fixtures/dossier/invalid/` representing a `MissionDossier*` payload that must fail validation; used by the conformance suite as a golden negative example.
- **MissionDossierArtifactMissing payload**: One of the four canonical dossier event payloads; currently has valid-fixture coverage only.
- **MissionDossierSnapshotComputed payload**: One of the four canonical dossier event payloads; currently has valid-fixture coverage only.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: All four dossier event payload types (`ArtifactIndexed`, `ArtifactMissing`, `SnapshotComputed`, `ParityDriftDetected`) have at least one valid AND at least one invalid conformance fixture.
- **SC-002**: The two new invalid fixtures each target a distinct, previously-uncovered violation kind: `manifest_step` empty-string (min-length) on ArtifactMissing, negative `artifact_count` (`ge=0`) on SnapshotComputed — checkable by comparing each fixture's `manifest.json` `notes` field against the four existing violation kinds (3 pre-existing + the other new one).
- **SC-003**: `pytest tests/test_dossier_conformance.py` passes locally with the new fixtures in place, and `fixtures/dossier/invalid/` directory contents match `manifest.json` entries 1:1 (NFR-002).
