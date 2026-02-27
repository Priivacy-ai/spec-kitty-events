---
work_package_id: WP02
title: DecisionPoint Conformance, Replay Determinism, Versioning, and Downstream Notes
lane: "for_review"
dependencies:
- WP01
base_branch: 011-wp03-decisionpoint-lifecycle-contracts-WP01
base_commit: 28c480c2203b1e73db29db8502f3dd3a85b2360e
created_at: '2026-02-27T11:31:10.629612+00:00'
agent: coordinator
shell_pid: '54810'
review_status: has_feedback
reviewed_by: Robert Douglass
requirement_refs:
- FR-004
- FR-005
- FR-006
review_feedback_file: /private/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-review-feedback-WP02.md
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

## Review Feedback

**Reviewed by**: Robert Douglass
**Status**: ❌ Changes Requested
**Date**: 2026-02-27
**Feedback file**: `/private/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-review-feedback-WP02.md`

# WP02 Review Feedback (Codex)

## Finding 1 (P1): Package version mismatch
- Evidence: `src/spec_kitty_events/__init__.py` keeps `__version__ = "2.5.0"` while DecisionPoint release artifacts and notes are explicitly 2.6.0.
- Impact: Downstream pinning / release automation ambiguity; docs and artifact versioning diverge from package version.
- Required change:
  - Update `__version__` to `2.6.0`.
- Acceptance check:
  - Re-run WP acceptance checks and ensure all remain green.

## Finding 2 (P3): Docstring export count mismatch
- Evidence: Versioning notes say "Exported symbols (14 total)" but list 15 symbols.
- Impact: Minor documentation inaccuracy.
- Required change:
  - Fix symbol count or list.


## Activity Log

- 2026-02-27T11:31:10Z – coordinator – shell_pid=54810 – lane=doing – Assigned agent via workflow command
- 2026-02-27T11:44:53Z – coordinator – shell_pid=54810 – lane=for_review – Ready for review: 8 valid + 6 invalid conformance fixtures, 3 replay streams with golden outputs, 4 JSON schemas generated, conformance and property tests passing (1278 tests total), downstream impact notes added
- 2026-02-27T11:45:27Z – codex – shell_pid=54810 – lane=doing – Started review via workflow command
- 2026-02-27T11:49:45Z – codex – shell_pid=54810 – lane=planned – Moved to planned
- 2026-02-27T11:49:55Z – coordinator – shell_pid=54810 – lane=doing – Started implementation via workflow command
- 2026-02-27T11:54:51Z – coordinator – shell_pid=54810 – lane=for_review – Ready for re-review: fixed package version to 2.6.0 and corrected export count note
