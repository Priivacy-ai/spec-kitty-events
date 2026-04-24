# Implementation Plan: Decision Moment V1 Contract Freeze

**Branch**: `main` (landing directly) | **Date**: 2026-04-23 | **Spec**: [spec.md](spec.md)
**Mission**: `decision-moment-v1-contract-freeze-01KPWA0N` (mid8: `01KPWA0N`)
**Input**: Feature specification from `kitty-specs/decision-moment-v1-contract-freeze-01KPWA0N/spec.md`

## Summary

Freeze the canonical `DecisionPoint` event contract as `spec-kitty-events 4.0.0` so it represents interview-originated Decision Moments end-to-end: interview-origin metadata at ask time, a new `DecisionPointWidened` event for Slack-backed discussion, a required `terminal_outcome` on `DecisionPointResolved` (`resolved`/`deferred`/`canceled`), structured `summary` with provenance, a `closed_locally_while_widened` boolean, and `ParticipantIdentity.external_refs` for replay-safe Slack/Teamspace identity carry. The 5 required golden replay pairs plus an `Other/free-text` golden and invalid fixtures lock the contract. Implementation keeps the existing `decisionpoint.py` module as the single source of truth and models Opened/Discussing/Resolved payloads as Pydantic v2 **discriminated unions keyed by `origin_surface ∈ {adr, planning_interview}`**, preserving 3.x ADR-style semantics exactly under `origin_surface="adr"`.

## Technical Context

**Language/Version**: Python 3.10+ (repo baseline; `requires-python = ">=3.10"`).
**Primary Dependencies**: `pydantic>=2.0.0,<3.0.0`, `python-ulid>=1.1.0`. Dev/test: `pytest`, `hypothesis`, `mypy --strict`. Optional conformance extra: `jsonschema>=4.21.0,<5.0.0`.
**Storage**: None at runtime; the package is a contract library. Committed JSON Schemas under `src/spec_kitty_events/schemas/` and committed conformance fixtures under `src/spec_kitty_events/conformance/fixtures/decisionpoint/` are part of the published surface.
**Testing**: pytest (unit, integration, property via Hypothesis, conformance schema tests, schema-drift check). Golden replay fixtures live under `tests/fixtures/decisionpoint_golden/` (events `.jsonl` + `_output.json` pairs) and are pulled into `tests/test_decisionpoint_conformance.py` and `tests/integration/test_lifecycle_replay.py`.
**Target Platform**: Pure Python library, no runtime targets.
**Project Type**: Single library.
**Performance Goals**: Reducer ≤10 ms for any golden fixture (≤32 events); ≤1 s for property-test streams of ≤10,000 events.
**Constraints**: Deterministic output (sorted-key JSON serialization, Lamport-ordered event sort); `mypy --strict` must pass; schema-drift check must be zero-diff; Hypothesis runs ≥500 generated streams/CI with zero determinism failures.
**Scale/Scope**: ~10 new/extended Pydantic models, 5 new/extended JSON schemas (Opened-adr, Opened-interview, Widened, Discussing union, Resolved union) + 3 reusable shared schemas (`participant_identity` extended, `summary_block`, `thread_ref` / `closure_message_ref`), 6 golden replay fixture pairs, ~4 invalid conformance fixtures, ~8 new Hypothesis property tests.

## Charter Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Charter summary for this repo (from `.kittify/charter/charter.md`):

- **Intent:** "Publish canonical event envelopes, conformance fixtures, and compatibility rules consumed by Spec Kitty systems." → **PASS.** This mission is the poster child for that intent.
- **Languages/Frameworks:** "Python 3.10+ with Pydantic event models, committed JSON Schemas, and conformance fixtures as part of the public contract." → **PASS.** Plan stays inside those constraints; no new dependencies.
- **Testing:** "pytest, hypothesis, schema drift checks, and conformance fixture validation for any event contract change." → **PASS.** All four gates are addressed (see Phase 2 mapping in `tasks.md` when generated).
- **Quality Gates:** "pytest, committed schema generation checks, and mypy --strict must pass before merge." → **PASS.** Plan treats these as hard exit criteria.
- **Review Policy:** "Any change to event envelopes, payload fields, schema versioning, or conformance fixtures requires deliberate compatibility review." → **PASS.** This plan *is* the compatibility review; 4.0.0 is a clean break for DecisionPoint while preserving 3.x compatibility for `DecisionInputRequested`/`DecisionInputAnswered`. `CHANGELOG.md` and `COMPATIBILITY.md` updates are mandatory outputs (FR-019).
- **Performance Targets:** "Validation and replay helpers should stay deterministic and efficient for normal CLI and SaaS event volumes." → **PASS.** NFR-001/NFR-003 bind this.
- **Deployment Constraints:** Python library with committed schemas/fixtures, fail-closed compatibility. → **PASS.** No relaxed validator path for missing `terminal_outcome`.

**Action Doctrine (plan):** Directives DIRECTIVE_003 (Decision Documentation) and DIRECTIVE_010 (Specification Fidelity) apply. An ADR-style rationale block lives in `research.md` (see R-1 through R-6) to satisfy DIRECTIVE_003. Every FR in `spec.md` maps to a concrete data-model entry and a contract fragment to satisfy DIRECTIVE_010.

Charter Check verdict: **PASS** with no waivers. No entries required in Complexity Tracking.

Will re-check after Phase 1 design.

## Project Structure

### Documentation (this feature)

```
kitty-specs/decision-moment-v1-contract-freeze-01KPWA0N/
├── plan.md              # This file
├── research.md          # Phase 0 output (this command)
├── data-model.md        # Phase 1 output (this command)
├── quickstart.md        # Phase 1 output (this command)
├── contracts/           # Phase 1 output (this command)
│   ├── decision_point_opened_adr.payload.json
│   ├── decision_point_opened_interview.payload.json
│   ├── decision_point_widened.payload.json
│   ├── decision_point_discussing_adr.payload.json
│   ├── decision_point_discussing_interview.payload.json
│   ├── decision_point_resolved_adr.payload.json
│   ├── decision_point_resolved_interview.payload.json
│   ├── participant_identity_v4.schema.json
│   ├── summary_block.schema.json
│   ├── thread_ref.schema.json
│   └── closure_message_ref.schema.json
├── spec.md              # Feature spec (already exists)
└── tasks.md             # Created later by /spec-kitty.tasks
```

### Source Code (repository root)

```
src/spec_kitty_events/
├── __init__.py                       # EXTEND: re-export new V1 classes + version bump
├── decisionpoint.py                  # EXTEND: tagged-union payloads, new Widened, V1 reducer fields
├── collaboration.py                  # EXTEND: ParticipantIdentity gains optional external_refs
├── models.py                         # UNCHANGED (envelope layer)
├── status.py                         # UNCHANGED (already provides sort/dedup helpers)
├── schemas/
│   ├── decision_point_opened_payload.schema.json       # REPLACE: discriminated union shape
│   ├── decision_point_widened_payload.schema.json      # NEW
│   ├── decision_point_discussing_payload.schema.json   # REPLACE: discriminated union shape
│   ├── decision_point_resolved_payload.schema.json     # REPLACE: discriminated union shape
│   ├── decision_point_overridden_payload.schema.json   # EXTEND: optional origin_surface
│   ├── participant_identity.schema.json                # NEW (shared; extracted from collaboration payloads)
│   ├── participant_external_refs.schema.json           # NEW
│   ├── summary_block.schema.json                       # NEW
│   ├── thread_ref.schema.json                          # NEW
│   ├── closure_message_ref.schema.json                 # NEW
│   ├── teamspace_ref.schema.json                       # NEW
│   ├── default_channel_ref.schema.json                 # NEW
│   └── generate.py                                     # EXTEND: register new payloads
└── conformance/
    └── fixtures/
        └── decisionpoint/
            ├── valid/                                  # EXTEND with 5 V1 envelopes + Other
            ├── invalid/                                # EXTEND with 4 negative cases
            └── replay/
                ├── replay_interview_local_only_resolved.jsonl
                ├── replay_interview_local_only_resolved_output.json
                ├── replay_interview_widened_resolved.jsonl
                ├── replay_interview_widened_resolved_output.json
                ├── replay_interview_widened_closed_locally.jsonl
                ├── replay_interview_widened_closed_locally_output.json
                ├── replay_interview_deferred.jsonl
                ├── replay_interview_deferred_output.json
                ├── replay_interview_canceled.jsonl
                ├── replay_interview_canceled_output.json
                ├── replay_interview_resolved_other.jsonl
                └── replay_interview_resolved_other_output.json

tests/
├── unit/
│   ├── test_decisionpoint.py                           # EXTEND: interview-variant unit coverage
│   └── test_collaboration_models.py                    # EXTEND: ParticipantIdentity.external_refs coverage
├── test_decisionpoint_conformance.py                   # EXTEND: V1 valid/invalid fixture cases
├── test_decisionpoint_reducer.py                       # EXTEND: Widened, terminal_outcome, closed-locally paths
├── property/
│   └── test_decisionpoint_determinism.py               # EXTEND: V1 generators (origin=planning_interview, Other path, closed-locally)
├── integration/
│   └── test_lifecycle_replay.py                        # EXTEND: assert V1 golden replays produce byte-identical output
└── fixtures/
    └── decisionpoint_golden/                           # EXTEND with 6 new golden pairs (mirrors conformance replay dir)

CHANGELOG.md                                            # EXTEND: 4.0.0 section documenting contract boundary
COMPATIBILITY.md                                        # EXTEND: DecisionPoint 4.0.0 rules, DecisionInput* unchanged
pyproject.toml                                          # EXTEND: version = "4.0.0"
```

**Structure Decision**: Single-library layout. We extend `decisionpoint.py` rather than fork a V1 module because the user directive is "keep the existing DecisionPoint vocabulary" and the reducer must produce one canonical `ReducedDecisionPointState`. New *types* (discriminated-union variants, shared identity/summary/thread models) land alongside existing ones. Conformance and golden fixtures extend the existing directory trees. No new top-level package is introduced.

## Complexity Tracking

*No Charter Check violations. Nothing to track.*

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| _(none)_  | _(n/a)_    | _(n/a)_                             |

## Branch Strategy (final restatement)

- Current branch: `main`
- Planning/base branch: `main`
- Final merge target: `main`
- `branch_matches_target`: `true` — planning and merge both target `main`.
- No worktree created by this command; worktrees are created later by `/spec-kitty.tasks` → `spec-kitty next --agent <name> --mission 01KPWA0N`.

## Next Command

Run `/spec-kitty.tasks --mission 01KPWA0N` to generate work packages.
