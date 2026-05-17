# Implementation Plan: Backward-Transition Contract

**Branch**: `main` | **Date**: 2026-05-17 | **Spec**: [spec.md](./spec.md)
**Mission ID**: 01KRV52CHQFTJ522SMP9NDNZ41 | **Mid8**: 01KRV52C
**Input**: [kitty-specs/backward-transition-contract-01KRV52C/spec.md](./spec.md)

## Summary

Land the contract source of truth for the **review-rejection transition family** (`{in_review → planned, approved → planned, for_review → planned, in_progress → planned}`) in the canonical `WPStatusChanged` payload contract. Deliverables are docstring updates in `src/spec_kitty_events/status.py`, a normative contract markdown section under `docs/`, three new JSON conformance fixtures under `src/spec_kitty_events/conformance/fixtures/edge_cases/` (two valid: review-rejection cycle, approved-rewind; one invalid: unforced in_review→planned), parametrized test entries in `tests/unit/test_fixtures.py`, and dedicated assertions in `tests/unit/test_status.py`. No wire-schema changes; existing `ReviewRollback` mission-level event remains untouched and is referenced as the higher-level intent record.

The technical approach is to extend the existing JSON-driven conformance fixture system (loader, manifest, validators already present at `src/spec_kitty_events/conformance/`) by registering three new fixture files with explicit edge-case categories. Documentation goes both inline (module docstring of `status.py`) and as a referenced section in the existing `docs/consumer-contract-dossier-v2.4.0.md` file so downstream missions (`spec-kitty` CLI, `spec-kitty-saas` materializer/drain) have a single stable anchor.

## Technical Context

**Language/Version**: Python 3.10+ (charter mandate)
**Primary Dependencies**: Pydantic v2 (existing event models), pytest 7+ (existing test runner), hypothesis (charter mandate for property tests where applicable), committed JSON Schema generation via `src/spec_kitty_events/schemas/generate.py`
**Storage**: N/A — this is a contract library, no runtime storage
**Testing**: `uv run pytest tests/unit/test_status.py tests/unit/test_fixtures.py -q` plus `uv run pytest tests/unit/ -q` for the full unit suite; `mypy --strict` over `src/spec_kitty_events/` for type safety; the schema-drift check (committed JSON schemas under `src/spec_kitty_events/schemas/*.schema.json`) must produce a clean diff after this mission
**Target Platform**: PyPI-published Python library consumed by `spec-kitty` CLI and `spec-kitty-saas` services
**Project Type**: single (Python library)
**Performance Goals**: New tests complete in under 10 seconds wall-clock (NFR-001); fixtures are file-system reads + Pydantic validation only, no I/O fanout
**Constraints**: No wire-schema changes (C-003); additive surface only (C-006); no copy of the 22 dev evidence events (C-005); `SPEC_KITTY_ENABLE_SAAS_SYNC=1` for CLI invocations (C-004)
**Scale/Scope**: Three new fixture files (≤ 12 keys each per NFR-002), one module docstring section, one referenced markdown section, ~6 new test assertions

## Charter Check

| Charter dimension | Status | Notes |
|---|---|---|
| Intent: Publish canonical event envelopes, conformance fixtures, and compatibility rules | ✅ Pass | This mission adds conformance fixtures and explicit compatibility documentation for the review-rejection family. |
| Languages/Frameworks: Python 3.10+ with Pydantic event models | ✅ Pass | No new dependencies. Uses existing Pydantic models. |
| Testing: pytest, hypothesis, schema drift checks, conformance fixture validation | ✅ Pass | Plan extends pytest + conformance fixture validation. No hypothesis property tests added because the change is enumerative (4 family members, 3 fixtures). |
| Quality Gates: pytest, schema generation checks, mypy --strict | ✅ Pass | All three gates must pass before merge per FR-013, NFR-004, NFR-005. |
| Review Policy: deliberate compatibility review for envelope / payload / schema / fixture changes | ✅ Pass | This mission IS the deliberate compatibility review for the review-rejection family. |
| Performance Targets: deterministic and efficient validation | ✅ Pass | NFR-001 caps test runtime at 10s. |
| Deployment Constraints: ship committed schemas + fixtures, fail-closed compatibility | ✅ Pass | Fixtures are committed under `src/spec_kitty_events/conformance/fixtures/`; manifest updated; no behavior change to schema generation. |

Action doctrine (`plan` action):
- DIRECTIVE_003 (Decision Documentation): satisfied by this plan + spec + research.md (Phase 0 below).
- DIRECTIVE_010 (Specification Fidelity): every plan deliverable maps to an FR/NFR/C ID from spec.md.

## Project Structure

### Documentation (this feature)

```
kitty-specs/backward-transition-contract-01KRV52C/
├── plan.md                  # This file
├── spec.md                  # Mission spec
├── meta.json                # Mission identity
├── checklists/
│   └── requirements.md      # Spec quality checklist
├── research.md              # Phase 0 output (this command)
├── data-model.md            # Phase 1 output — domain shape recap
├── quickstart.md            # Phase 1 output — sibling-mission consumer recipe
└── contracts/
    └── backward-transition-family.md   # Phase 1 output — normative section text
```

### Source Code (repository root)

```
src/spec_kitty_events/
├── status.py                # Existing — module docstring section EXTENDED with review-rejection family
└── conformance/
    └── fixtures/
        ├── manifest.json    # Existing — REGISTER three new fixtures
        └── edge_cases/
            ├── valid/
            │   ├── wp_status_changed_review_rejection_cycle.json   # NEW (positive, FR-004)
            │   └── wp_status_changed_approved_rewind.json          # NEW (positive, FR-005)
            └── invalid/
                └── wp_status_changed_unforced_in_review_to_planned.json  # NEW (negative, FR-006)

tests/unit/
├── test_status.py           # Existing — ADD review-rejection family tests (FR-007)
└── test_fixtures.py         # Existing — REGISTER new fixtures in parametrize lists (FR-008)

docs/
└── consumer-contract-dossier-v2.4.0.md  # Existing — ADD review-rejection family normative section (FR-001, FR-010, FR-013)
```

**Structure Decision**: Single Python library. All work happens inside `src/spec_kitty_events/`, `tests/unit/`, and `docs/`. No new directories. Reuses existing JSON conformance fixture system with three new fixtures registered through the existing `manifest.json` and `_FIXTURES_DIR / "edge_cases" / ...` loader.

## Implementation Strategy

### Approach summary

The conformance fixture system already supports `edge_cases/valid/` and `edge_cases/invalid/` subdirectories (`tests/unit/test_fixtures.py:TestFixtureDirectoryStructure.EXPECTED_DIRS` enumerates them). The cleanest path is:

1. **Author three JSON fixtures** under `edge_cases/`:
   - `valid/wp_status_changed_review_rejection_cycle.json` — a *list* of `WPStatusChanged` payloads representing the full minimal lifecycle including one review-rejection round-trip (FR-004). Loader-supported list shape per existing edge-case patterns.
   - `valid/wp_status_changed_approved_rewind.json` — single `WPStatusChanged` payload for the approved → planned forced-backward case (FR-005). Matches the evidence-pack wire shape but with synthetic identifiers; no copy of any of the 22 dev events.
   - `invalid/wp_status_changed_unforced_in_review_to_planned.json` — single `WPStatusChanged` payload with `from_lane=in_review, to_lane=planned, force=False` (FR-006). Validator must reject.
2. **Register the three fixtures** in `src/spec_kitty_events/conformance/fixtures/manifest.json` and in the parametrize lists of `tests/unit/test_fixtures.py` (FR-008).
3. **Add explicit family tests** in `tests/unit/test_status.py` (FR-007): a parametrized test that walks the four family members (`in_review→planned, approved→planned, for_review→planned, in_progress→planned`) and asserts:
   - `force=True + reason` accepted by `validate_transition()`
   - `force=False` rejected with a graph-violation diagnostic
   - `force=True + reason=""` or `reason=None` rejected with the existing `force=True requires a non-empty reason` error
4. **Extend the `status.py` module docstring** with a normative section titled "Review-Rejection Transition Family" that enumerates the family, states the `force=True + reason` requirement, declares unforced backward transitions invalid, and recommends the canonical `reason` shape (`"backward rewind: <from> -> <to>[: <feedback-ref>]"`). Cross-link to the new fixture filenames and to the docs section (FR-001, FR-002, FR-003, FR-010, FR-013).
5. **Add a normative section** to `docs/consumer-contract-dossier-v2.4.0.md` titled "Backward Transitions: The Review-Rejection Family" with the same content, cross-linked back to `status.py` and the fixtures (FR-001, FR-013).
6. **Cross-link the existing `ReviewRollback` lifecycle event** in both anchor locations as the higher-level mission-intent record. This makes the "no new event type" rule (FR-009) visible to readers.

### Phase deliverables

| Phase | Output | Maps to |
|---|---|---|
| Phase 0 (research) | `research.md` resolving: exact docs section heading, exact normative `reason` shape, fixture identifier convention | FR-010, FR-013 |
| Phase 1 (design) | `data-model.md`, `contracts/backward-transition-family.md`, `quickstart.md` | FR-001, FR-002, FR-003 |
| Phase 2 (tasks, run by `/spec-kitty.tasks`) | `tasks.md` with WP breakdown | All FRs |
| Phase 3 (implement, per WP) | Source/test/fixture edits | FR-004 through FR-008 |
| Phase 4 (review + mission-review) | All gates green | NFR-001 through NFR-005, SC-001 through SC-005 |

### Risk + Mitigation

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| The review-rejection cycle fixture (list shape) is not supported by the existing loader | Low | Medium — fixture format would need adaptation | Phase 0 research validates loader behavior against existing list fixtures before committing to the list shape. If unsupported, split into per-event fixtures and parametrize tests over them. |
| `validate_transition()` already rejects unforced backward but the rejection message changes meaningfully for in_review→planned | Low | Low | Phase 0 research reads the validator code path; if a gap is found, fix is in-scope as FR-007 completeness. |
| Schema generation produces a non-empty diff after adding fixtures | Low | Medium — would break NFR-004 / NFR-005 | Schemas are generated from Pydantic models, not fixtures; adding fixture files does not regenerate schemas. Confirm during implement. |
| `mypy --strict` over `tests/unit/` fails on new parametrize tuples | Low | Low | Match the existing parametrize tuple type signatures already in `test_fixtures.py`. |
| Sibling missions cite a path that later moves | Medium | Low | Phase 1 design pins the anchor at module docstring (stable) plus a heading in `docs/consumer-contract-dossier-v2.4.0.md` (versioned filename → already stable across releases). |

### Cycle preview

This is a small mission. Estimated WP shape after `/spec-kitty.tasks`:

- WP01: Author the three JSON conformance fixtures + register in manifest
- WP02: Add normative section to `status.py` module docstring
- WP03: Add normative section to `docs/consumer-contract-dossier-v2.4.0.md`
- WP04: Add family tests to `tests/unit/test_status.py` and fixture-load tests to `tests/unit/test_fixtures.py`

Lanes: WP01 and WP02 can run in parallel (different files). WP03 depends on WP02 for cross-link text. WP04 depends on WP01 (loads new fixtures) and references WP02 (cites docstring section).

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| (none) | — | — |

No charter violations. All work is additive, fits the existing fixture + docstring + test surface, and introduces no new dependencies or runtime behavior.
