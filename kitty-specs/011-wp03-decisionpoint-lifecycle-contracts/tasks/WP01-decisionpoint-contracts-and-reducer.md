---
work_package_id: WP01
title: DecisionPoint Event Constants, Payload Models, and Reducer Transitions
lane: "doing"
dependencies: []
base_branch: codex/wp03-events-decisionpoint-contracts
base_commit: d31fce18b5f215e0f12eddf2c5b051891e9207ba
created_at: '2026-02-27T11:06:48.227189+00:00'
agent: "codex"
shell_pid: "54810"
requirement_refs:
- FR-001
- FR-002
- FR-003
---

# Work Package Prompt: WP01 - DecisionPoint Event Constants, Payload Models, and Reducer Transitions

## Objective

Create the canonical DecisionPoint lifecycle contract core in the events package: constants, frozen payload models with mandatory audit fields, and a deterministic reducer that enforces authority policy.

## In-Scope Areas

- `src/spec_kitty_events/decisionpoint.py` (new module)
- Deterministic reducer behavior using `status_event_sort_key` and `dedup_events`
- Authority-policy validation for mission-owner and LLM roles
- Unit and reducer tests for lifecycle transitions and anomalies

## Implementation Instructions

1. Add DecisionPoint constants and event family set:
   - `DecisionPointOpened`, `DecisionPointDiscussing`, `DecisionPointResolved`, `DecisionPointOverridden`
   - `DECISION_POINT_EVENT_TYPES`
2. Add lifecycle and authority enums at minimum:
   - `DecisionPointState` (`open`, `discussing`, `resolved`, `overridden`)
   - `DecisionAuthorityRole` including `mission_owner`, `advisory`, `informed`
3. Implement frozen payload models for each lifecycle event with mandatory audit fields:
   - `decision_point_id`, `mission_id`, `run_id`, `feature_slug`, `phase`
   - `actor_id`, `actor_type`, `authority_role`
   - `mission_owner_authority_flag`, `mission_owner_authority_path`
   - `rationale`, `alternatives_considered`, `evidence_refs`
   - `state_entered_at`, `recorded_at`
4. Implement `reduce_decision_point_events(events)` with deterministic pipeline:
   - sort, dedup, filter to DecisionPoint events, fold transitions, freeze output
5. Enforce transition and policy rules:
   - `None -> open`, `open -> discussing|resolved`, `discussing -> discussing|resolved`, `resolved -> overridden`
   - `resolved` and `overridden` require human mission-owner authority
   - LLM actors allowed only in `phase="P0"` with `advisory|informed` roles and no mission-owner authority
6. Record anomalies for invalid transitions, policy violations, and malformed payloads without crashing reduction.
7. Add tests for payload validation, transition correctness, and anomaly behavior.

## Reviewer Checklist

- [ ] Event names and constants exactly match the spec.
- [ ] All audit-trail fields are mandatory and validated.
- [ ] Mission-owner and LLM policy rules are enforced in tests.
- [ ] Reducer output is deterministic for reordered input and deduped duplicates.
- [ ] No unrelated modules or legacy families are modified unnecessarily.

## Acceptance Checks

- `python3.11 -m mypy --strict src/spec_kitty_events/decisionpoint.py`
- `python3.11 -m pytest tests/unit/test_decisionpoint.py tests/test_decisionpoint_reducer.py -v`

## Dependencies

- None.

## PR Requirements

- Include a short contract summary listing event names, required payload fields, and transition rules.
- Cite FR coverage explicitly: FR-001, FR-002, FR-003.
- Include test evidence for authority-policy constraints and deterministic reduction.

## Activity Log

- 2026-02-27T11:06:48Z – coordinator – shell_pid=54810 – lane=doing – Assigned agent via workflow command
- 2026-02-27T11:21:27Z – coordinator – shell_pid=54810 – lane=for_review – Ready for review: DecisionPoint lifecycle contracts with mypy --strict passing, 65 tests (31 reducer + 34 unit), 99% coverage, authority/LLM policy enforcement, golden-file replay. FR-001/FR-002/FR-003 covered.
- 2026-02-27T11:23:55Z – codex – shell_pid=54810 – lane=doing – Started review via workflow command
