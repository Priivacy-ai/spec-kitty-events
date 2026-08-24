# Research: Dossier Invalid Fixture Coverage

## Decision: Violation kind per new fixture

- **Decision**: `MissionDossierArtifactMissing`'s invalid fixture sets `manifest_step: ""` (empty string), violating the model's `min_length=1` constraint. `MissionDossierSnapshotComputed`'s invalid fixture sets `artifact_count: -1`, violating the model's `ge=0` constraint.
- **Rationale**: Confirmed via `spec-kitty agent decision` (decision `01M0FTVXSW7FW2SZC9F2QWS9BP`, resolved 2026-08-20). These two violation kinds are each genuinely new against the three pre-existing invalid fixtures (invalid `Literal`/enum on `artifact_class`, one missing top-level required field, multiple missing nested `namespace` fields) and against each other (string-length constraint vs. numeric-bound constraint).
- **Alternatives considered**: An invalid `algorithm` literal (e.g. `"md4"`) was considered for `SnapshotComputed` but rejected — it repeats the same violation *category* (invalid `Literal`/enum) as the existing `dossier_artifact_indexed_invalid_class.json` fixture, just on a different field, which would not add a genuinely new violation kind to the suite.

## Decision: Fixture registration mechanism

- **Decision**: Both new fixtures are registered as entries in `src/spec_kitty_events/conformance/fixtures/manifest.json`, following the exact schema of the 14 existing entries (`id`, `path`, `event_type`, `expected_result`, `notes`, `min_version`).
- **Rationale**: `load_fixtures()` in `src/spec_kitty_events/conformance/loader.py` reads exclusively from `manifest.json`, filtered by `path` prefix — it does not glob the fixture directories. A JSON file with no manifest entry is invisible to `test_valid_fixture_passes_conformance` / `test_invalid_fixture_fails_conformance` and to any other consumer of `load_fixtures("dossier")`. This was the single most consequential finding from the post-spec adversarial review (converged on independently by 3 of 4 reviewing delegates).
- **Alternatives considered**: None — this is how every existing dossier fixture (valid and invalid) is already wired in; there is no alternative mechanism to consider.

## Decision: Test-suite wiring scope

- **Decision**: No new test function is added. The two hardcoded literals in `tests/test_dossier_conformance.py` — `test_dossier_fixture_count` (13→15) and `test_dossier_invalid_case_count` (3→5) — are updated; `test_dossier_valid_case_count` (10) is untouched since neither new fixture is valid.
- **Rationale**: `test_valid_fixture_passes_conformance` and `test_invalid_fixture_fails_conformance` are `@pytest.mark.parametrize`-driven off `load_fixtures("dossier")`, so once a fixture has a manifest entry it is automatically exercised by both tests with zero new code. The three hardcoded counts exist as a deliberate scaffold assertion (charter Testing Standards; DIRECTIVE_041) that catches exactly the failure mode where someone adds a fixture file but forgets the manifest entry — confirmed structurally correct by the adversarial review's debugger-debbie pass.
- **Alternatives considered**: Writing a bespoke `def test_dossier_artifact_missing_empty_step(): ...`-style function per fixture was considered and rejected — it would duplicate what the existing parametrization already does generically, and was explicitly flagged as a laziness/duplication risk during adversarial review (reviewer-renata).

## Decision: `spec-kitty` mirror-deletion status (informational, no action here)

- **Decision**: This mission takes no action on the `spec-kitty` repo's local `MissionDossierArtifactIndexedPayload` (and siblings) mirror in `src/specify_cli/dossier/events.py`.
- **Rationale**: Confirmed out of scope (spec C-002). Adversarial review corrected the original assumption that this work was "already in progress" — the actual state is `spec-kitty` issue #1058, open and unstarted, blocked on this issue (#23). No branch, commit, or PR activity was found evidencing active work as of 2026-08-20.
- **Alternatives considered**: Broadening this mission to include the spec-kitty-side deletion was considered (and was the initial framing floated in conversation) but rejected in favor of a fixtures-only, single-repo mission, per locality-of-change — cross-repo work belongs to its own mission/tracking issue (#1058), not bundled into this one.
