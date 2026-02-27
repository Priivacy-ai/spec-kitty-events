---
work_package_id: WP02
title: DecisionPoint Conformance, Replay Determinism, Versioning, and Downstream Notes
lane: "doing"
dependencies:
- WP01
base_branch: 011-wp03-decisionpoint-lifecycle-contracts-WP01
base_commit: 28c480c2203b1e73db29db8502f3dd3a85b2360e
created_at: '2026-02-27T11:31:10.629612+00:00'
requirement_refs:
- FR-004
- FR-005
- FR-006
shell_pid: "54810"
---

# Work Package Prompt: WP02 - DecisionPoint Conformance, Replay Determinism, Versioning, and Downstream Notes

## Objective

Deliver conformance-grade DecisionPoint fixtures and replay scenarios, register schemas and validators, and complete export/versioning/downstream-impact documentation for additive 2.x adoption.

## In-Scope Areas

- `src/spec_kitty_events/conformance/validators.py`
- `src/spec_kitty_events/conformance/loader.py`
- `src/spec_kitty_events/conformance/fixtures/manifest.json`
- `src/spec_kitty_events/conformance/fixtures/decisionpoint/{valid,invalid,replay}`
- `src/spec_kitty_events/schemas/generate.py` and generated schema files
- `src/spec_kitty_events/__init__.py` and package version notes
- Conformance and property tests for DecisionPoint replay safety

## Implementation Instructions

1. Register DecisionPoint event type -> model and schema mappings in conformance validators.
2. Add `decisionpoint` fixture category support in fixture loader.
3. Add fixture set with minimum coverage:
   - 8 valid fixtures
   - 6 invalid fixtures (include authority-policy and missing audit field failures)
   - 3 replay JSONL streams and 3 reducer-output golden JSON files
4. Add manifest entries for all DecisionPoint fixtures with `min_version: "2.6.0"`.
5. Extend schema generation to include DecisionPoint payload models and commit generated schema files.
6. Add DecisionPoint conformance and property tests for replay determinism and dedup idempotence.
7. Export DecisionPoint public API from `spec_kitty_events.__init__` and add versioning/export notes plus downstream impact notes for `spec-kitty` runtime and `spec-kitty-saas`.

## Reviewer Checklist

- [ ] Fixture counts and manifest entries meet minimum coverage and version tagging.
- [ ] Invalid fixtures include policy and required-field failures, not only type errors.
- [ ] Replay streams validate and match committed golden reducer outputs exactly.
- [ ] DecisionPoint schemas are generated deterministically and checked in.
- [ ] Public exports and downstream adoption notes are complete and additive-only.

## Acceptance Checks

- `python3.11 -m pytest tests/test_decisionpoint_conformance.py tests/property/test_decisionpoint_determinism.py -v`
- `python3.11 -m pytest --pyargs spec_kitty_events.conformance`
- `python3.11 -m pytest tests/ -q`

## Dependencies

- Depends on WP01.

## PR Requirements

- Include fixture inventory table (valid/invalid/replay/reducer-output) in PR description.
- Cite FR coverage explicitly: FR-004, FR-005, FR-006.
- Include downstream migration note block: required version pin, exported symbols, and expected consumer code touchpoints.
