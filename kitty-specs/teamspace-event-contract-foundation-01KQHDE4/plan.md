# Implementation Plan: TeamSpace Event Contract Foundation

**Branch**: `main` | **Date**: 2026-05-01 | **Spec**: [spec.md](./spec.md)
**Input**: [spec.md](./spec.md)
**Mission ID**: `01KQHDE43F53RJJ5824QB544XD`
**Mission Slug**: `teamspace-event-contract-foundation-01KQHDE4`
**Reviewer**: Codex (mandatory)
**Parent Epic**: https://github.com/Priivacy-ai/spec-kitty/issues/920

---

## Summary

Settle the canonical event contract in `spec-kitty-events` so it is the single source of truth for TeamSpace-safe migration of historical mission state. Concretely: (1) make `in_review` a canonical lane (the spec already records this decision); (2) reconcile `MissionCreated`, `WPStatusChanged`, and `MissionClosed` payload contracts across CLI, library, and SaaS; (3) make recursive forbidden-key validation authoritative and provably correct; (4) ship a conformance fixture pack covering invalid raw rows, valid envelopes, forbidden-key cases (including deeply nested), and lane edges; (5) document the **local-CLI compatibility vs TeamSpace ingress validity** distinction and bump the schema version per charter Review Policy.

The technical approach is targeted and library-internal: modify `src/spec_kitty_events/status.py` and `src/spec_kitty_events/lifecycle.py`, add a dedicated recursive forbidden-key validator, regenerate the committed JSON Schemas, expand `src/spec_kitty_events/conformance/fixtures/` and the manifest, and add a compatibility doc explaining the two validity domains.

---

## Technical Context

**Language/Version**: Python 3.10+
**Primary Dependencies**: Pydantic v2 (event models), `jsonschema` for committed schema validation, hypothesis for property-based tests, pytest for the conformance and unit suites
**Storage**: N/A (this is a contract library; fixtures and schemas are committed JSON files in the repo)
**Testing**: pytest, pytest-based conformance fixture runner (`src/spec_kitty_events/conformance/`), hypothesis property tests for the recursive forbidden-key validator, schema-drift checks against the committed `src/spec_kitty_events/schemas/`
**Target Platform**: Python library distributed on PyPI; consumed by `spec-kitty` CLI, `spec-kitty-saas`, `spec-kitty-runtime`, `spec-kitty-tracker`
**Project Type**: single (Python contract library)
**Performance Goals**: Single-envelope validation < 5 ms p95 on a developer laptop (NFR-005); the conformance fixture suite must complete fast enough not to dominate CI on the consuming repos
**Constraints**: Deterministic outputs only — no wall-clock timestamps, no random IDs in fixtures or in validation results (C-006); recursive validator must traverse depth ≥ 10 (NFR-002); Codex review required before merge (C-005); schema version bump and compatibility doc update required per charter Review Policy (C-003, FR-010)
**Scale/Scope**: Contract surface change touching ~6 source files in `src/spec_kitty_events/` (`status.py`, `lifecycle.py`, a new `forbidden_keys.py`, `conformance/validators.py`, `conformance/fixtures/`, `schemas/`), one new `COMPATIBILITY.md` section, ~20–30 new conformance fixture files spanning the historical-shape classes from epic #920's survey

---

## Charter Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Charter requirement | Plan alignment |
|---|---|
| **Intent**: Publish canonical event envelopes, conformance fixtures, and compatibility rules | This mission's deliverables are exactly that: updated envelopes, expanded conformance fixtures, and a new compatibility section. Aligned. |
| **Languages/Frameworks**: Python 3.10+ with Pydantic event models, committed JSON Schemas, conformance fixtures as part of the public contract | Plan uses Pydantic v2 models, regenerates committed JSON Schemas, and ships fixtures. Aligned. |
| **Testing**: pytest, hypothesis, schema drift checks, conformance fixture validation | All four are explicitly in the test plan (Phase 1). Aligned. |
| **Quality Gates**: pytest, committed schema generation checks, mypy --strict | Each is a CI gate this mission must keep green (NFR-004). Aligned. |
| **Review Policy**: Any envelope/payload/schema/fixture change requires deliberate compatibility review | Codex is the deliberate compatibility reviewer (C-005); FR-010 mandates a schema version bump and compatibility doc update. Aligned. |
| **Performance Targets**: Validation and replay helpers stay deterministic and efficient | NFR-001 (deterministic) and NFR-005 (< 5 ms p95) encode this. Aligned. |
| **Deployment Constraints**: Ship as a Python library with committed schemas and fixtures; live consumers rely on fail-closed compatibility behavior | Plan commits schemas and fixtures; the recursive forbidden-key validator and the lane-vocabulary check are fail-closed by construction. Aligned. |

**Action Doctrine alignment**:
- DIRECTIVE_003 (Decision Documentation): all material decisions land in [research.md](./research.md), in `COMPATIBILITY.md`, and in mission decision records.
- DIRECTIVE_010 (Specification Fidelity): plan deliverables map 1:1 to spec FR/NFR/C/SC IDs (see [Requirements Trace](#requirements-trace) below).

**No charter violations.** Complexity Tracking section is intentionally empty.

---

## Project Structure

### Documentation (this feature)

```
kitty-specs/teamspace-event-contract-foundation-01KQHDE4/
├── plan.md              # This file
├── spec.md              # Mission specification (already committed)
├── research.md          # Phase 0 output (open questions resolved here)
├── data-model.md        # Phase 1 output (entities and invariants)
├── quickstart.md        # Phase 1 output (developer onboarding for the contract changes)
├── contracts/           # Phase 1 output (mission-level contract artifacts)
├── checklists/
│   └── requirements.md  # Spec quality checklist (already committed)
└── tasks/               # Reserved for /spec-kitty.tasks (NOT created by /spec-kitty.plan)
```

### Source Code (repository root)

This is a single Python contract library. The relevant tree:

```
spec-kitty-events/
├── src/spec_kitty_events/
│   ├── status.py                  # Lane enum + StatusTransitionPayload (modified: add in_review)
│   ├── lifecycle.py               # MissionCreatedPayload, MissionClosedPayload (modified: reconciled)
│   ├── forbidden_keys.py          # NEW: recursive forbidden-key validator (extracted/centralized)
│   ├── conformance/
│   │   ├── validators.py          # Existing event-type → payload model dispatch (touched if needed)
│   │   └── fixtures/
│   │       ├── manifest.json      # Modified: register new fixture classes
│   │       ├── events/
│   │       │   ├── valid/         # Modified: add in_review-using envelopes; align MissionClosed
│   │       │   └── invalid/       # Modified: move in_review out of invalid; add forbidden-key cases
│   │       ├── lane_mapping/      # Modified: in_review moves out of "unknown_lanes"
│   │       └── historical_rows/   # NEW: raw status.events.jsonl rows that must be rejected
│   └── schemas/
│       ├── generate.py            # Used to regenerate committed JSON Schemas after model changes
│       ├── status_transition_payload.schema.json   # Regenerated
│       ├── mission_closed_payload.schema.json      # Regenerated
│       └── mission_created_payload.schema.json     # Regenerated
├── tests/
│   ├── (existing test modules)
│   ├── test_lane_vocabulary.py    # NEW: asserts canonical lane list (incl. in_review) is the single source of truth
│   ├── test_forbidden_keys.py     # NEW: hypothesis property tests + targeted depth/array cases
│   ├── test_payload_reconciliation.py  # NEW: MissionCreated/WPStatusChanged/MissionClosed cross-shape tests
│   └── test_historical_rejection.py    # NEW: every fixture in historical_rows/ is rejected with a structured error
├── COMPATIBILITY.md               # Modified: add "Local-CLI compatibility vs TeamSpace ingress validity" section
└── CHANGELOG.md                   # Modified: schema version bump entry per FR-010 / C-003
```

**Structure Decision**: Single Python package; modifications stay inside `src/spec_kitty_events/`, `tests/`, and the two top-level docs. No new top-level packages, no reorganization. The new `forbidden_keys.py` module isolates the recursive validator so it can be reused by both the typed payload models and the envelope-level guard.

---

## Phase 0 — Outline & Research

The spec settled `in_review` as canonical. The remaining open questions are intentionally captured here as research tasks; each is resolved in [research.md](./research.md) before the work is broken into work packages by `/spec-kitty.tasks`.

| ID | Research Question | Why It Matters |
|---|---|---|
| R-01 | What is the **complete** forbidden-key set? Survey the historical `status.events.jsonl` rows in epic #920, current SaaS ingress rejection rules, and the CLI canonicalizer's planned mapping. | FR-005 must enumerate every key, not just the named seeds (`feature_slug`, `feature_number`, `mission_key`). Missing a key here lets legacy data through. |
| R-02 | What is the canonical **reconciliation direction** for `MissionClosed`, `MissionCreated`, and `WPStatusChanged` payload contracts? Three shapes: (a) library widens to accept current CLI/SaaS emission; (b) producers narrow to a tightened library schema; (c) the CLI canonicalizer normalizes between historical-rendered shapes and the library schema. | FR-003, FR-004 require a single source of truth; the choice changes whether downstream tranches must change emission code or just call the canonicalizer. |
| R-03 | What is the **schema-version bump** semantic for adding `in_review` and reconciling payload contracts? Minor (additive lane addition) or major (any consumer that switched on the lane vocabulary may break)? | FR-010 / C-003 require a deliberate version bump and compatibility note; downstream tranches plan their releases against this. |
| R-04 | What is the **structured error format** the events package returns on rejection (envelope-shape mismatch, forbidden key, unknown lane, payload schema fail)? Are there existing taxonomies in the package we extend, or do we add a new one? | NFR-006 mandates structured + human-readable errors; consistency across rejection classes makes downstream tranches' error reporting reliable. |
| R-05 | What is the survey-derived enumeration of **historical-shape classes** the conformance fixtures must cover? (e.g., pre-3.0 envelopes, in_review-using rows, raw status rows with `feature_slug` at depth, MissionClosed with extra fields, lane-mapping rows that resolved to in_review historically.) | FR-007, FR-008 / SC-005 require fixtures to cover every class; missing a class lets a real historical shape slip past CI. |
| R-06 | Is there an existing **deterministic-fixture** convention in the repo (fixed IDs, fixed timestamps) we extend, or is one needed? | C-006 forbids wall-clock and random; without a convention, fixtures drift between contributors. |

These questions are resolved in [research.md](./research.md) below. Their resolution does **not** require additional user input — they are tractable from the existing repo state, the survey in epic #920, and the SaaS ingress rules; the resolutions are recorded in `research.md` as `Decision / Rationale / Alternatives Considered` triples.

**Output**: [research.md](./research.md)

---

## Phase 1 — Design & Contracts

**Prerequisites**: Phase 0 research complete.

1. **Entities** → [data-model.md](./data-model.md)
   - Canonical Envelope (TeamSpace 3.0.x wrapper), Lane Vocabulary (the authoritative ordered list incl. `in_review`), Typed Payloads (`MissionCreatedPayload`, `WPStatusChangedPayload`, `MissionClosedPayload`), Forbidden-Key Set, Conformance Fixture, Local Status Row, Structured Validation Error.

2. **Contracts** → [contracts/](./contracts/)
   - `lane-vocabulary.md` — the canonical ordered list, single source of truth, with `in_review` included; rule that the contract package, CLI, and SaaS must reference the same constant.
   - `forbidden-key-validation.md` — recursive walk algorithm contract: rejection at any depth, in any nested object or array element, with deterministic structured error.
   - `payload-reconciliation.md` — outcome of R-02: per-event-type contract for `MissionCreated`, `WPStatusChanged`, `MissionClosed` (the **what**, not the **how** — implementation chooses the path).
   - `conformance-fixture-classes.md` — the survey-derived list of fixture classes from R-05, with mandatory coverage rules.
   - `validation-error-shape.md` — outcome of R-04: structured error schema (machine-readable code + human-readable message).
   - `versioning-and-compatibility.md` — outcome of R-03: bump rule and compatibility-doc obligations.

3. **Quickstart** → [quickstart.md](./quickstart.md)
   - How a downstream tranche author validates a candidate envelope against the contract; how to add a fixture; how to interpret a structured error; how to read the `COMPATIBILITY.md` section.

4. **Re-evaluate Charter Check post-design**: schedule re-check at the end of Phase 1 once the contracts above are written. If any new gap surfaces (e.g., a contract that conflicts with the existing schema-drift CI), document it under Complexity Tracking and resolve before /spec-kitty.tasks.

**Output**: [data-model.md](./data-model.md), [contracts/](./contracts/), [quickstart.md](./quickstart.md)

---

## Requirements Trace

Every spec ID is allocated to a Phase or contract artifact below. `/spec-kitty.tasks` will use this trace to build work packages.

| Spec ID | Owned by | Notes |
|---|---|---|
| FR-001 | contracts/lane-vocabulary.md | Single source-of-truth contract |
| FR-002 | data-model.md (Lane Vocabulary), tests/test_lane_vocabulary.py | `in_review` accepted as canonical |
| FR-003 | research.md R-02, contracts/payload-reconciliation.md | MissionClosed reconciliation |
| FR-004 | research.md R-02, contracts/payload-reconciliation.md | WPStatusChanged + MissionCreated reconciliation |
| FR-005 | research.md R-01, contracts/forbidden-key-validation.md, tests/test_forbidden_keys.py | Recursive forbidden-key validator |
| FR-006 | tests/test_historical_rejection.py, fixtures/historical_rows/ | Raw row rejection |
| FR-007 | research.md R-05, fixtures/events/valid/ | Envelope acceptance for survey shapes |
| FR-008 | research.md R-05, contracts/conformance-fixture-classes.md, fixtures/* | Conformance fixture pack |
| FR-009 | COMPATIBILITY.md update | Local vs ingress validity |
| FR-010 | research.md R-03, contracts/versioning-and-compatibility.md, CHANGELOG.md | Schema-version bump |
| NFR-001 | All test modules; deterministic-fixture convention from R-06 | Determinism |
| NFR-002 | tests/test_forbidden_keys.py (depth ≥ 10 fixture) | Depth coverage |
| NFR-003 | CI configuration (existing pytest run on conformance fixtures) | CI gate |
| NFR-004 | CI gates (pytest + schema generation + mypy --strict) | Existing gates kept green |
| NFR-005 | Benchmark in tests/ measuring 95th-percentile fixture | < 5 ms p95 |
| NFR-006 | research.md R-04, contracts/validation-error-shape.md | Structured + human errors |
| C-001 | tests/test_historical_rejection.py | Raw row never validates |
| C-002 | contracts/lane-vocabulary.md | One vocabulary across packages |
| C-003 | contracts/versioning-and-compatibility.md, CHANGELOG.md | Version bump + review |
| C-004 | tests/test_lane_vocabulary.py + payload reconciliation tests | No silent break of existing valid envelopes |
| C-005 | Mission close gate (Codex review) | Reviewer mandate |
| C-006 | research.md R-06, fixtures/* | Determinism |
| SC-001 | tests/test_payload_reconciliation.py + cross-repo dry-run fixture | 100% acceptance for dry-run shapes |
| SC-002 | tests/test_historical_rejection.py | 100% rejection of raw rows |
| SC-003 | tests/test_lane_vocabulary.py + lint / static check | Vocabulary single-source check |
| SC-004 | tests/test_payload_reconciliation.py | MissionClosed disagreement resolved |
| SC-005 | tests/test_forbidden_keys.py | Recursive coverage proven |
| SC-006 | COMPATIBILITY.md update | Local vs ingress doc |
| SC-007 | Codex review record | Review completion |

---

## Test Strategy

Codex review will explicitly check this section, per C-005.

- **Conformance fixtures** (declarative): every change to envelopes, payloads, lane vocabulary, or forbidden keys is paired with at least one valid and one invalid fixture in `src/spec_kitty_events/conformance/fixtures/`, registered in `manifest.json`. The conformance runner asserts each fixture's expected outcome.
- **Hypothesis property tests** (`tests/test_forbidden_keys.py`): generated nested structures of arbitrary depth are checked against the recursive validator; any structure containing a forbidden key is rejected.
- **Schema-drift check** (existing CI): `src/spec_kitty_events/schemas/*.schema.json` regenerated from Pydantic models must match the committed files byte-for-byte.
- **Deterministic-fixture audit** (per C-006): a small audit test scans fixtures for forbidden patterns (wall-clock-shaped strings, suspicious random-looking IDs) and fails CI on drift.
- **mypy --strict**: must pass for changed modules; new `forbidden_keys.py` is fully typed.
- **Cross-repo dry-run fixture** (for SC-001): a dedicated fixture file or test simulates the CLI canonicalizer's planned dry-run synthesis output and validates it; this is the contract handshake to Tranche B in `spec-kitty`.

---

## Open Risks (carried into research)

- **R-A**: An overly aggressive forbidden-key set could reject envelopes that legitimately reference a key name (e.g., a string field whose *value* happens to be `"feature_slug"`). The recursive validator must inspect *keys* only, never *values*. Mitigation: explicit fixture covering this case, encoded as a "must accept" valid fixture.
- **R-B**: Reconciliation direction (R-02) ripples downstream. If the library widens to accept current CLI emissions but the SaaS projector tightens differently, we re-create the drift the mission was supposed to fix. Mitigation: pin the reconciliation in `contracts/payload-reconciliation.md` and require Tranche A (CLI), Tranche A (SaaS), and Tranche A (events) to all reference the same contract file.
- **R-C**: A schema version bump that's too cautious (minor when it should be major) lets consumers think they don't need to update. Mitigation: follow the rule from R-03 strictly and document the rationale in `COMPATIBILITY.md`.
- **R-D**: Conformance fixtures grow large; CI time grows. Mitigation: NFR-005's per-envelope benchmark plus a simple fixture-count audit in CI; if growth becomes a problem, partition fixtures by class and run in matrix.

---

## Complexity Tracking

*Empty.* The plan follows charter intent and adds no new top-level packages or architectural patterns. The new `forbidden_keys.py` module is a single-file extraction motivated directly by FR-005 / NFR-002 and is the simplest reasonable home for the recursive validator.

---

## Branch Contract (restated, per command guidance)

- Current branch at plan start: `main`
- Planning/base branch: `main`
- Final merge target for completed changes: `main`
- `branch_matches_target` reported by `setup-plan --json`: `true`

After `/spec-kitty.tasks` runs, work packages will be implemented in `.worktrees/<slug>-<mid8>-lane-<x>/` worktrees; merges land back on `main`.
