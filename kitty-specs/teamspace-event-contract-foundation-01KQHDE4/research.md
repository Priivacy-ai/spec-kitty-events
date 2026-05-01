# Phase 0 Research: TeamSpace Event Contract Foundation

**Mission**: `teamspace-event-contract-foundation-01KQHDE4`
**Spec**: [spec.md](./spec.md) · **Plan**: [plan.md](./plan.md)
**Date**: 2026-05-01

This document resolves the Phase 0 research questions catalogued in [plan.md](./plan.md). Each item follows `Decision / Rationale / Alternatives Considered`. Resolutions here are normative inputs to the Phase 1 contract artifacts and to the work-package breakdown that `/spec-kitty.tasks` will produce.

The decisions below are **provisional engineering recommendations** and are explicitly subject to Codex review (per C-005). Where deeper survey work or stakeholder input is required during the work-package phase, this is called out in the Rationale.

---

## R-01 — Complete forbidden-key set

**Decision**: The forbidden-key set is treated as a **closed, named, versioned constant** in `src/spec_kitty_events/forbidden_keys.py`, seeded with the keys named in the epic (`feature_slug`, `feature_number`, `mission_key`) and **expanded during a dedicated work package** that audits the historical `status.events.jsonl` rows and the current `spec-kitty-saas` ingress rejection rules. The set is a Python `frozenset[str]`, exported, and consumed by the recursive validator and the conformance fixture generator. Changes to the set follow the same compatibility-review rule as schema-version bumps (C-003).

**Rationale**:
- Epic #920 reports 6,155 status event rows surveyed across 5 repos with 105 frontmatter signatures and 4 typed decision events. The named seeds are guaranteed-forbidden but cannot be assumed exhaustive.
- The current SaaS ingress already rejects "recursive legacy keys", per the spec — those rules are the natural cross-check. The audit work package will diff the SaaS rejection list against our seeded set and reconcile.
- Making the set a single named constant avoids duplication between the validator, the schema regeneration, and the fixtures.

**Alternatives Considered**:
- **Open set with regex pattern (e.g., `feature_*`)**: rejected — too easy to over-reject (e.g., a future legitimate field starting with `feature_`); explicit names are safer and reviewable.
- **Per-payload-type forbidden lists**: rejected — adds maintenance burden without protection benefit; envelope-level recursive rejection is sufficient and uniform.
- **Allowlist of acceptable keys at every nesting level**: rejected — too rigid for an evolving payload surface; it would force payload model changes to ripple into envelope-level allowlists.

**Risk addressed**: An incomplete forbidden-key set lets historical legacy keys slip through. The audit work package is mandatory before the contract version is bumped.

---

## R-02 — Reconciliation direction for `MissionCreated`, `WPStatusChanged`, `MissionClosed`

**Decision**: The events package's typed payload models are the **single source of truth**. CLI and SaaS producers must conform to those models. The CLI canonicalizer (Tranche B) is the **transformation layer** between historical-rendered shapes and the canonical payload schema; it normalizes legacy fields (e.g., dropping `feature_slug`, mapping legacy lane synonyms to canonical lanes) before producing the envelope. The events package itself does **not** widen to accept extra historical fields.

This direction is encoded in `contracts/payload-reconciliation.md` and is normative for Tranches A (CLI), B (CLI canonicalizer), A (SaaS), and B (SaaS projection reconciliation).

**Rationale**:
- The mission's whole purpose is fail-closed contract enforcement; widening the library to accept current emissions defeats it.
- The CLI canonicalizer is being designed in the next tranche specifically to be the transformation layer; reconciliation belongs there.
- A single canonical schema minimizes divergence risk between CLI and SaaS validators, addressing risk R-B in the plan.
- Producers (CLI, SaaS emitters) updating to conform is bounded work compared to the alternative of spreading forgiveness across every consumer.

**Alternatives Considered**:
- **(a) Library widens**: rejected — resurfaces the very contract drift this mission is fixing; long-term maintenance burden.
- **(c) Canonicalizer normalizes for historical only, producers stay loose**: rejected — leaves a gap where current-day producers can still drift from the contract. The contract must be fail-closed for both historical and live emission.

**Open follow-up for the work-package phase**: an inventory of the exact CLI/SaaS emission sites that need to change to conform. This will be produced as part of the WP that ships the reconciled payload models, with cross-references to the corresponding work in Tranches A (CLI) and A (SaaS).

---

## R-03 — Schema-version bump semantic

**Decision**: This mission lands as a **major schema-version bump** on the package's contract version axis (the version recorded in committed `*.schema.json` files and announced in `COMPATIBILITY.md`). Specifically: lane vocabulary changes that add a previously-rejected lane (`in_review` flips from invalid to canonical) are treated as **breaking** for consumers that switched on the lane vocabulary's exact membership. Producers benefit (more inputs are accepted) but downstream consumers must re-verify their lane handling.

**Rationale**:
- A consumer that does `if lane == "review"` followed by `else: error("unknown lane")` will silently mishandle `in_review` after the bump. That is a behavior change consumers must opt into.
- The charter Review Policy explicitly calls schema versioning out as a deliberate review item; reflecting reality (this is not a pure addition) preserves trust.
- The simultaneous payload reconciliation (R-02) is also a producer-side narrowing for any producer that emits non-canonical fields; that too warrants a major bump signal.

**Alternatives Considered**:
- **Minor bump (additive interpretation)**: rejected — accurate from the package's *acceptance* perspective but misleading from the *consumer behavior* perspective.
- **Patch bump with a "warnings only" period**: rejected — incompatible with TeamSpace's fail-closed posture and with the launch timeline.

**Communication**:
- `CHANGELOG.md`: a "Breaking Changes" section listing (i) `in_review` is now canonical, (ii) payload contracts are reconciled and CLI/SaaS producers must conform, (iii) recursive forbidden-key validator now rejects nested legacy keys.
- `COMPATIBILITY.md`: a new section explaining the bump and pointing readers to the canonical lane vocabulary contract and the payload reconciliation contract.

---

## R-04 — Structured error format on rejection

**Decision**: Adopt a structured `ValidationError` shape with three required fields and one optional field:

| Field | Type | Required | Meaning |
|---|---|---|---|
| `code` | `str` (enum-backed) | yes | Stable machine-readable rejection class identifier (e.g., `FORBIDDEN_KEY`, `UNKNOWN_LANE`, `PAYLOAD_SCHEMA_FAIL`, `ENVELOPE_SHAPE_INVALID`, `RAW_HISTORICAL_ROW`) |
| `message` | `str` | yes | One-line human-readable summary suitable for CLI/log output |
| `path` | `list[str \| int]` | yes (may be empty) | JSON pointer-like path to the offending location inside the input |
| `details` | `dict[str, Any]` | no | Class-specific structured detail (e.g., for `FORBIDDEN_KEY`, `{"key": "feature_slug"}`; for `UNKNOWN_LANE`, `{"lane": "blocked"}`) |

The set of `code` values is a closed enum exported from `spec_kitty_events`. New codes follow the same review process as schema bumps.

**Rationale**:
- NFR-006 requires both machine-readable and human-readable forms; this shape gives both without coupling them.
- Existing rejection points in the package already carry strings or lightweight tuples; centralizing them under one shape lets consumers (CLI error printers, SaaS ingress, tracker UIs) render errors uniformly.
- A `path` field is essential for forbidden-key rejections at depth: a consumer must be able to tell a user *where* the legacy key was found.

**Alternatives Considered**:
- **Reuse existing exception subclasses without a uniform schema**: rejected — leaves consumers to switch on exception type, which is more brittle than a stable `code` enum.
- **Free-form dict with no required fields**: rejected — fails NFR-006's machine-readable requirement.
- **JSON-Schema standard error format**: rejected for first iteration — overkill for our rejection classes; can be added as an alias later if a downstream consumer needs it.

**Existing taxonomy reuse**: the package already has `TransitionError` and a `TransitionValidationResult` (in `src/spec_kitty_events/status.py`). The new `ValidationError` shape is layered on top: where rejection paths already raise typed exceptions, those exceptions gain a method or property that returns the structured shape, preserving back-compat for code that catches the typed exception.

---

## R-05 — Historical-shape classes for conformance fixtures

**Decision**: Conformance fixtures are organized into eight named classes, each registered in `src/spec_kitty_events/conformance/fixtures/manifest.json` with a class label. Coverage is mandatory: if a class has no fixtures, the manifest fails CI.

| Class | Expected outcome | Examples |
|---|---|---|
| `envelope_valid_canonical` | accept | Canonical 3.0.0 envelopes with all canonical lanes incl. `in_review`; one per supported event type |
| `envelope_valid_historical_synthesized` | accept | Envelopes synthesized by the CLI canonicalizer's planned dry-run output (the cross-repo handshake for SC-001) |
| `envelope_invalid_unknown_lane` | reject (`UNKNOWN_LANE`) | Envelope claiming a lane outside the canonical vocabulary |
| `envelope_invalid_forbidden_key` | reject (`FORBIDDEN_KEY`) | Forbidden key at top level, nested object, deep depth (≥ 10), and inside an array element |
| `envelope_invalid_payload_schema` | reject (`PAYLOAD_SCHEMA_FAIL`) | Envelope where payload fails its typed schema |
| `envelope_invalid_shape` | reject (`ENVELOPE_SHAPE_INVALID`) | Missing required envelope fields, wrong wrapper |
| `historical_row_raw` | reject (`RAW_HISTORICAL_ROW`) | Lines from real historical `status.events.jsonl` files; covers pre-3.0 shapes, in_review-using rows, rows containing `feature_slug`/`feature_number`/`mission_key` |
| `lane_mapping_legacy` | depends on entry | Resolutions of legacy lane strings to canonical lanes (e.g., `awaiting-review` → `in_review`); split into `valid` and `invalid` sub-cases |

Fixture files use the existing on-disk convention (a JSON file per case, with `expected: valid|invalid`, `class: <class label>`, optional `notes`).

**Rationale**:
- The class taxonomy maps directly to the rejection codes from R-04, making the fixture suite a complete coverage matrix.
- Pulling raw rows from real history (the survey in epic #920) is what proves SC-002 (100% rejection of raw historical rows).
- Splitting `lane_mapping_legacy` into valid/invalid sub-cases captures the mixed history described in the spec's edge cases.

**Alternatives Considered**:
- **One flat directory of fixtures with notes**: rejected — already present and obscured the in_review issue; a labeled class taxonomy makes coverage gaps visible.
- **Generated-only fixtures (hypothesis)**: rejected — generated fixtures can't replace real historical-row evidence; hypothesis is used for the recursive forbidden-key property test (NFR-002), not for the conformance manifest.

**Coverage minimum (per class)**: at least three fixtures per class for the first ship; the manifest-level audit fails CI on any class with zero fixtures.

---

## R-06 — Deterministic-fixture convention

**Decision**: Fixtures use **fixed, repository-pinned values** for any field that would otherwise be wall-clock or random:

- Timestamps: `2026-01-01T00:00:00+00:00` (a single, repo-pinned anchor) unless the fixture's class specifically tests timestamp variation.
- Mission/WP/event ULIDs: deterministic-looking but pinned strings (e.g., `01J0000000000000000000FIX1`, `01J0000000000000000000FIX2`); never freshly generated.
- Hashes/digests: precomputed and committed; never recomputed at test time from environmental data.

The convention is documented in `src/spec_kitty_events/conformance/fixtures/README.md` (created as part of the conformance work package). A small audit test scans fixture JSON for forbidden patterns (e.g., timestamps that look recent, ULIDs that don't match the pinned prefix) and fails CI on drift.

**Rationale**:
- Directly satisfies C-006 ("no wall-clock timestamps and no random IDs in fixture data").
- Aligns with NFR-001 (deterministic validation) — fixtures must themselves be reproducible.
- Repo pinning avoids the legitimate-but-confusing situation where a contributor's local clock or RNG produces fixture diffs that look meaningful but aren't.

**Alternatives Considered**:
- **Per-fixture-author values, no convention**: rejected — drift is invisible until a consuming repo's CI complains; the audit test is the cheap fix.
- **Programmatically generate fixtures at test time from a seed**: rejected — adds a test-time codepath that itself needs review; committed JSON is simpler.

---

## Cross-cutting outputs of Phase 0

These resolutions feed directly into Phase 1's contract artifacts:

| Research item | Phase 1 artifact |
|---|---|
| R-01 | [contracts/forbidden-key-validation.md](./contracts/forbidden-key-validation.md) — closed-set rule and audit obligation |
| R-02 | [contracts/payload-reconciliation.md](./contracts/payload-reconciliation.md) — single source of truth direction |
| R-03 | [contracts/versioning-and-compatibility.md](./contracts/versioning-and-compatibility.md) — major bump rule |
| R-04 | [contracts/validation-error-shape.md](./contracts/validation-error-shape.md) — structured error schema |
| R-05 | [contracts/conformance-fixture-classes.md](./contracts/conformance-fixture-classes.md) — eight-class taxonomy |
| R-06 | [contracts/conformance-fixture-classes.md](./contracts/conformance-fixture-classes.md) §Determinism | Fixed-value convention |

No `[NEEDS CLARIFICATION]` markers remain. Phase 1 may begin.
