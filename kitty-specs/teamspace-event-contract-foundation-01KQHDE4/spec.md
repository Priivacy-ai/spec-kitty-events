# Specification: TeamSpace Event Contract Foundation

**Mission ID**: `01KQHDE43F53RJJ5824QB544XD`
**Mission Slug**: `teamspace-event-contract-foundation-01KQHDE4`
**Mission Type**: software-dev
**Target Branch**: `main`
**Parent Epic**: https://github.com/Priivacy-ai/spec-kitty/issues/920
**Source Issues**:
- https://github.com/Priivacy-ai/spec-kitty-events/issues/18
- https://github.com/Priivacy-ai/spec-kitty-events/issues/19

**Reviewer**: Codex (mandatory)

---

## Purpose

### TLDR

Settle the canonical event contract so historical mission state can migrate safely to TeamSpace.

### Context

Existing Spec Kitty repositories contain years of historical mission state written across multiple schema eras: local `status.events.jsonl` rows, work-package frontmatter, runtime logs, and decision side-logs. The CLI tolerates much of that locally, but TeamSpace ingress is strict and a public launch must not import malformed historical mission data.

The `spec-kitty-events` package is the contractual gatekeeper for what constitutes a valid TeamSpace event. Today it has three known points of drift that block the rest of the migration program:

1. The package treats `in_review` as an **invalid** lane, while CLI and SaaS code paths use `in_review` in real workflows and historical data.
2. `MissionClosed` payload contracts disagree between CLI emission and the typed `MissionClosedPayload` model.
3. Recursive forbidden-key validation (e.g. `feature_slug`, `feature_number`, `mission_key`) needs to be the authoritative gate; today coverage is unclear and must be made explicit.

This mission produces the single source of truth all downstream tranches (CLI canonicalizer, SaaS ingress hardening, runtime/tracker consumers, end-to-end migration rehearsal) build on.

---

## User Scenarios & Testing

### Primary Scenario — CLI migration dry-run validates

A maintainer runs the CLI mission-state migration in dry-run mode against a real, historical Spec Kitty repository. The CLI synthesizes canonical 3.0.0 TeamSpace envelopes from local mission state. Every synthesized envelope passes `spec-kitty-events` validation, including missions that exercise the `in_review` lane and missions that emit `MissionClosed`. No envelope produced by the canonicalizer is rejected by the contract package. The user sees a clean validation report and can move on to the explicit import step.

### Primary Scenario — Raw historical row rejected

A user (or a buggy importer) attempts to send a raw row from a historical `status.events.jsonl` file to TeamSpace ingress. The events package rejects it with an actionable, structured error that names the violation (missing envelope wrapper, forbidden legacy keys, unknown lane, payload schema mismatch, etc.). No raw historical row ever validates as a TeamSpace payload.

### Primary Scenario — Cross-package vocabulary alignment

A developer working on the SaaS ingress, the CLI canonicalizer, or a tracker consumer reads the lane vocabulary from one place and gets the same answer everywhere. There is no version of "the canonical lane list" that disagrees between the events package, the CLI, and the SaaS projector. `in_review` is on that list.

### Edge Cases

- **Lane with mixed history**: a mission that historically used `in_review`, then `review`, then `in_review` again — canonicalizer maps each rendering deterministically; events package accepts each canonical envelope.
- **Forbidden key nested deep**: `feature_slug` appears five levels deep inside an otherwise-valid envelope — recursive validator rejects.
- **Forbidden key in array element**: `mission_key` appears inside an item in a list — recursive validator rejects.
- **`MissionClosed` with extra fields**: a closed-mission envelope arrives with fields the CLI used to emit but the typed payload does not declare — resolution is deterministic (the contract is the single source of truth).
- **Unknown lane in `WPStatusChanged`**: an envelope claims a lane outside the canonical vocabulary — rejected.
- **Locally-valid, ingress-invalid distinction**: a row that the local CLI considered a perfectly fine `status.events.jsonl` entry is still rejected as a TeamSpace payload — and the docs explain why this is by design.

---

## Domain Language

| Canonical term | Meaning | Avoid these synonyms |
|---|---|---|
| **Envelope** | The TeamSpace 3.0.0 event wrapper produced by the CLI canonicalizer and validated by `spec-kitty-events`. | "event row", "event record", "TeamSpace JSON" |
| **Local status row** | A line from a historical `status.events.jsonl` file. Not a TeamSpace envelope. Locally valid, ingress invalid. | "event", "log line" (when ingress is in scope) |
| **Lane** | The canonical work-package status lane (e.g., `todo`, `in_progress`, `in_review`, `review`, `done`). | "status", "state", "column" |
| **Forbidden key** | A legacy field name (e.g., `feature_slug`, `feature_number`, `mission_key`) that must not appear anywhere inside a TeamSpace envelope. | "deprecated field" |
| **Conformance fixture** | A committed test artifact paired with `valid` or `invalid` and a class label (raw row, envelope, forbidden-key, lane edge). | "test data", "example" |
| **Local compatibility** vs **TeamSpace ingress validity** | Two distinct, documented validity domains. A payload may be locally compatible without being ingress-valid. | "valid" without qualifier |

---

## Functional Requirements

| ID | Description | Status |
|---|---|---|
| FR-001 | Publish a single canonical lane vocabulary that includes `in_review` and is the authoritative answer the contract package, the CLI, and the SaaS projector all reference. | Required |
| FR-002 | Update the events package so envelopes using `in_review` validate as canonical (not as an invalid-lane case). | Required |
| FR-003 | Resolve drift between CLI `MissionClosed` emission and the events-package `MissionClosedPayload` model so that a single payload contract governs both producers and consumers. | Required |
| FR-004 | Align `WPStatusChanged` and `MissionCreated` payload contracts with the same single-source-of-truth principle as `MissionClosed`. | Required |
| FR-005 | Enforce recursive forbidden-key validation that walks every nested object and array inside an envelope and rejects payloads containing any of `feature_slug`, `feature_number`, `mission_key`, or other legacy keys identified during research. | Required |
| FR-006 | Reject any raw historical `status.events.jsonl` row submitted as a TeamSpace payload, with a structured error that names the violation class. | Required |
| FR-007 | Accept exactly the canonical 3.0.0 envelopes that the CLI migration dry-run synthesizes for every historical-shape class identified in epic #920's survey (envelopes covering all surveyed lanes, all surveyed payload variants, and the `in_review` lane). | Required |
| FR-008 | Ship committed conformance fixtures covering: invalid raw local rows, valid synthesized envelopes, forbidden-legacy-key cases (including nested-key cases), lane edge cases (canonical lanes, `in_review`, unknown lanes), and `MissionClosed` payload edge cases. | Required |
| FR-009 | Document the distinction between **local-CLI compatibility** and **TeamSpace ingress validity**, including at minimum: which payload shapes are locally permitted but ingress-invalid, where each contract is enforced, and how to read a validation error. | Required |
| FR-010 | Bump the events-package contract version per the charter Review Policy when this mission lands, and record the change in compatibility documentation. | Required |

## Non-Functional Requirements

| ID | Description | Threshold | Status |
|---|---|---|---|
| NFR-001 | Validation paths are deterministic: identical input produces identical accept/reject outcomes and identical error structures. | 100% deterministic across repeated runs over the conformance fixture set. | Required |
| NFR-002 | Recursive forbidden-key validation traverses arbitrarily nested objects and arrays without truncation. | Rejects forbidden keys at depth ≥ 10 in dedicated fixtures. | Required |
| NFR-003 | Conformance fixture suite runs as part of the package CI gate. | Mandatory CI step; fails the build if any fixture's expected outcome regresses. | Required |
| NFR-004 | `pytest`, committed schema generation checks, and `mypy --strict` pass on the post-mission package. | Zero failures, zero new `# type: ignore` introduced for changed code. | Required |
| NFR-005 | Validation of a single envelope against the contract is fast enough not to dominate CLI/SaaS hot paths. | < 5 ms per envelope on a developer laptop for the 95th-percentile fixture; tracked as a measurable benchmark in tests. | Required |
| NFR-006 | Validation error messages are machine-readable (structured) and human-readable (actionable). | Each rejection in the fixture suite produces a structured error with a stable error class identifier and a one-line human summary. | Required |

## Constraints

| ID | Description | Status |
|---|---|---|
| C-001 | No raw historical `status.events.jsonl` row may validate as a TeamSpace payload, under any code path. | Required |
| C-002 | The events package, the CLI, and the SaaS projector must agree on the canonical lane list — no divergent constants. | Required |
| C-003 | Schema-version bump and compatibility review per charter Review Policy are mandatory for any envelope-, payload-, or fixture-level change. | Required |
| C-004 | The mission must not silently break existing valid envelopes already produced by current CLI/SaaS code in production, except where the change is the explicit point of this mission (notably `in_review` flipping from invalid to canonical). | Required |
| C-005 | Codex performs review before this mission is considered complete. The plan must include explicit tests and contract documentation as review-ready artifacts. | Required |
| C-006 | No wall-clock timestamps and no random IDs in fixture data or in deterministic validation output. | Required |

---

## Success Criteria

| ID | Outcome | Measurement |
|---|---|---|
| SC-001 | CLI canonicalizer's dry-run output validates 100% against the events package across the survey's historical-shape classes. | Dedicated cross-repo test (run as part of the conformance fixture suite) reports zero rejected envelopes for the dry-run synthesis. |
| SC-002 | Raw historical local rows are rejected 100% of the time. | Dedicated fixture class of raw-row inputs reports 100% rejection with structured errors. |
| SC-003 | A single canonical lane vocabulary is referenceable from one location and matches what CLI and SaaS code use. | Test or static check fails if the lane vocabulary diverges from a known reference; `in_review` is in the canonical list. |
| SC-004 | `MissionClosed` payload disagreement is resolved. | A test that simulates the historical CLI emission shape against `MissionClosedPayload` validation passes (or, where a historical shape must be normalized first, the test asserts the normalization rule deterministically). |
| SC-005 | Recursive forbidden-key validation is authoritative and proven. | Fixtures cover forbidden keys at top level, nested object level, deeply nested level, and inside array elements; all rejected. |
| SC-006 | Documentation distinguishes local compatibility from TeamSpace ingress validity. | A documentation page or section is committed and links from the package README or COMPATIBILITY doc; downstream tranches can cite it. |
| SC-007 | Codex review of this mission completes with no blocking findings. | Review record attached to mission, no unresolved blockers. |

---

## Key Entities

- **Canonical Envelope** — the TeamSpace 3.0.0 wrapper, produced by the CLI canonicalizer, validated by `spec-kitty-events`.
- **Lane Vocabulary** — the authoritative, ordered list of work-package lanes used across the program (includes `in_review`).
- **Typed Payload** (e.g., `MissionCreatedPayload`, `WPStatusChangedPayload`, `MissionClosedPayload`) — the per-event-type schema enforced inside the envelope.
- **Forbidden-Key Set** — the closed set of legacy keys that must never appear anywhere in an envelope.
- **Conformance Fixture** — a committed `(input, expected outcome, class)` triple that proves a contract rule.
- **Local Status Row** — a line from `status.events.jsonl`, valid for local CLI use, never valid as a TeamSpace payload.

---

## Assumptions

- The `in_review` lane is canonical going forward (decision recorded during this specify run; rationale: `in_review` is already present in historical data and supported by CLI/SaaS paths; migrating away would create unnecessary churn during the TeamSpace launch window).
- The full forbidden-key set will be finalized during plan/research from the survey in epic #920 and from current SaaS ingress rejection rules; this spec commits to the principle and to the named seeds (`feature_slug`, `feature_number`, `mission_key`).
- The exact `MissionClosed` payload reconciliation (whether the events package adds previously-CLI-only fields, whether the CLI drops fields, or whether the canonicalizer normalizes) is settled during plan/research; this spec commits to a single source of truth as the outcome.
- All fixtures and schema artifacts are committed to the repository as part of the public contract surface, per the charter.

---

## Out of Scope

- Implementing the CLI canonicalizer itself (Tranche B, separate mission).
- Implementing TeamSpace ingress hardening (Tranche A in `spec-kitty-saas`, separate mission).
- Implementing the `doctor mission-state` audit/fix CLI commands (separate missions in the program).
- Reconciliation reporting on the SaaS side after import (Tranche B in `spec-kitty-saas`, separate mission).
- Runtime-log and tracker-consumer changes (separate tranches).

---

## Dependencies

- This mission is the **upstream** dependency for: CLI Tranche A audit, CLI Tranche B canonicalizer, CLI Tranche D dry-run synthesizer, SaaS Tranche A ingress, SaaS Tranche B reconciliation, runtime Tranche A, tracker Tranche A, and end-to-end Tranche E. No work in those tranches can be considered correct until this mission's contract version ships.
- This mission depends on: the historical-shape survey already published in epic #920 (#920 lists the 6,155 status event rows, 105 frontmatter signatures, 4 typed decision events, etc.) and the existing `spec-kitty-events` 3.0.x schema.
