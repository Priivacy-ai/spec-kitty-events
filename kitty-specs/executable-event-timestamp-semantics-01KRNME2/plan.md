# Implementation Plan: Executable Event Timestamp Semantics

**Branch**: `main` (planning base) | **Date**: 2026-05-15 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `kitty-specs/executable-event-timestamp-semantics-01KRNME2/spec.md`

## Branch Strategy

- Current branch at plan start: `main`
- Planning/base branch for this mission: `main`
- Final merge target for completed changes: `main`
- `branch_matches_target`: true

## Summary

Make the canonical event-envelope `timestamp` field's semantic meaning (producer-assigned wall-clock occurrence time) executable. The wire format does not change. We strengthen the model docstrings and committed JSON Schema descriptions, document a consumer-owned receipt-time concept distinct from the canonical envelope, add at least one "old producer / recent receipt" conformance fixture, and ship a reusable conformance helper that fails loudly when a consumer substitutes receipt time for canonical occurrence time. The package's existing quality gates (pytest, schema drift, mypy --strict) carry the executable boundary.

## Technical Context

**Language/Version**: Python 3.10+
**Primary Dependencies**: pydantic >=2.0,<3.0; python-ulid >=1.1; jsonschema >=4.21 (conformance extra)
**Storage**: N/A (library; committed JSON Schemas + conformance fixtures on disk under `src/spec_kitty_events/`)
**Testing**: pytest, hypothesis, committed schema drift check, conformance fixture suite (already exposed via `pytest --pyargs spec_kitty_events.conformance`)
**Target Platform**: Python library distributed on PyPI; imported by `spec-kitty`, `spec-kitty-saas`, `spec-kitty-tracker`, `spec-kitty-hub`
**Project Type**: single (library)
**Performance Goals**: per spec NFR-002 conformance helper completes <250 ms per fixture; per NFR-003 added fixtures add <2 s to clean `pytest` wall time
**Constraints**: per spec C-001 public import paths must remain stable; per C-002 wire identifier remains `timestamp`; per C-003 no runtime dependency on any consumer repo; per C-004 reducer ordering must not regress; per C-005 no provenance/inference flag added
**Scale/Scope**: contract change touches one Pydantic field (`Event.timestamp`), one regenerated JSON schema description, one data-model document, one new conformance fixture pair, one new conformance helper, and 4–6 new pytest cases. Approximately 300–500 net lines including tests.

## Charter Check

Charter at `.kittify/charter/charter.md` requires:

- **Languages/Frameworks** — Python 3.10+ with Pydantic event models, committed JSON Schemas, conformance fixtures as part of the public contract. ✓ Mission stays inside this surface and does not introduce a new language or framework.
- **Testing** — pytest, hypothesis, schema drift checks, conformance fixture validation. ✓ Mission adds conformance fixtures and pytest cases, runs the existing schema drift check after regenerating schemas.
- **Quality Gates** — pytest, committed schema generation checks, mypy --strict. ✓ Mission carries all three. Schema regeneration is required when the `timestamp` description text changes.
- **Review Policy** — Any change to event envelopes, payload fields, schema versioning, or conformance fixtures requires deliberate compatibility review. ✓ Mission is intentionally additive; spec C-001 and C-002 forbid breaking the wire surface.
- **Performance Targets** — Validation and replay helpers stay deterministic and efficient. ✓ Mission's conformance helper is in-memory, deterministic, no network/filesystem writes (spec NFR-001), bounded fixture-suite time (NFR-003).
- **Deployment Constraints** — Library + committed schemas/fixtures; live consumers rely on fail-closed compatibility. ✓ Mission preserves fail-closed behaviour; consumer-facing helper raises a typed error when occurrence preservation fails.

**Gate result**: pass; no Complexity Tracking entries needed.

## Project Structure

### Documentation (this feature)

```
kitty-specs/executable-event-timestamp-semantics-01KRNME2/
├── spec.md
├── plan.md              # this file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output (timestamp-semantics conformance contract)
└── tasks.md             # /spec-kitty.tasks output (NOT created here)
```

### Source Code (repository root)

```
src/spec_kitty_events/
├── models.py                      # Event.timestamp docstring strengthened
├── schemas/                       # regenerated JSON Schemas (timestamp description updated)
└── conformance/
    ├── __init__.py                # re-exports new helper
    ├── timestamp_semantics.py     # NEW: assert_producer_occurrence_preserved + TimestampSubstitutionError
    ├── fixtures/
    │   └── timestamp_semantics/
    │       ├── valid/
    │       │   ├── old_producer_recent_receipt.json
    │       │   └── live_event_producer_equals_receipt.json
    │       └── invalid/
    │           └── consumer_substituted_receipt_time.json
    └── tests/
        └── test_timestamp_semantics.py   # NEW: good-consumer + bad-consumer cases

kitty-specs/teamspace-event-contract-foundation-01KQHDE4/
└── data-model.md                  # adds producer-vs-receipt section, updated timestamp row
```

**Structure Decision**: Mission stays within the existing single-package layout under `src/spec_kitty_events/`. New conformance code lives next to the existing `conformance/` subpackage so downstream consumers can `from spec_kitty_events.conformance import assert_producer_occurrence_preserved`. New fixtures are added to the existing conformance fixture root so they appear in the same drift envelope and the same fixture manifest.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|--------------------------------------|
| _none_ | n/a | n/a |

## Phase 0 — Research Outputs

See `research.md`. The Phase 0 research resolves:

1. Naming for the receipt-time slot (`received_at`) and whether it lives on the envelope or in consumer-only documentation.
2. Where the conformance helper should live in the package surface.
3. How the existing schema drift check detects description changes and what regeneration step is needed.
4. How "old producer, recent receipt" is best encoded in a fixture without introducing a real wall-clock value into the fixture file.

## Phase 1 — Design Outputs

### data-model.md

Documents the strengthened `Event.timestamp` semantics in this mission's `data-model.md`, with a cross-reference to the canonical contract document at `kitty-specs/teamspace-event-contract-foundation-01KQHDE4/data-model.md` (which is also updated as part of FR-004).

### contracts/

Adds `contracts/timestamp-semantics.md` describing the executable conformance contract a consumer must satisfy and the typed error raised on violation.

### quickstart.md

Documents how a downstream consumer (SaaS, CLI, tracker, hub) imports and runs `assert_producer_occurrence_preserved` against a fixture.

## Stop Point

Plan phase ends here. The user must run `/spec-kitty.tasks` to materialize work packages.
