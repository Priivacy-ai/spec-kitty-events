# Phase 0 Research: Backward-Transition Contract

**Date**: 2026-05-17
**Mission**: backward-transition-contract-01KRV52C
**Inputs**: plan.md risk register; existing source files cited below.

This document resolves the three open questions named in the plan's risk register and pins concrete decisions for Phase 1 design.

---

## R-001 — Fixture Format for the Full Review-Rejection Cycle

### Decision

Use a **`replay_stream` JSONL fixture** at `src/spec_kitty_events/conformance/fixtures/edge_cases/replay/wp_review_rejection_cycle.jsonl` (one full canonical `Event` envelope per line). Register it in `manifest.json` with `fixture_type: "replay_stream"`, `event_type: "mixed"`, `expected_result: "valid"`. Single-event fixtures (FR-005 positive approved-rewind, FR-006 negative unforced) remain plain JSON under `edge_cases/valid/` and `edge_cases/invalid/`.

### Rationale

- The conformance loader already supports `replay_stream` JSONL fixtures (`src/spec_kitty_events/conformance/loader.py:121` — `load_replay_stream()`). The fixture type is registered in `_SPECIAL_FIXTURE_TYPES`.
- Precedent fixtures in the same shape exist:
  - `dossier/replay/dossier_happy_path.jsonl` — 6-event happy path
  - `dossier/replay/dossier_drift_scenario.jsonl` — 5-event drift scenario
  - `sync/replay/sync-ingest-lifecycle.jsonl` — sync ingest lifecycle
  - `mission_audit/replay/mission_audit_replay_*.jsonl` — multi-event audit replays
  - `replay/mixed-connector-sync-lifecycle.jsonl` — top-level mixed lifecycle
- The plain-JSON `edge_cases/valid/*.json` fixtures (`alias_doing_normalized.json`, `event_with_all_optional_fields.json`, `optional_fields_omitted.json`) are all single-payload — they cannot represent a multi-event lifecycle without splitting.
- A single JSONL stream keeps the temporal ordering, Lamport clock, and event-id continuity legible to a reader in one file — which is the whole point of the FR-011 readability success criterion.

### Alternatives Considered

| Alternative | Rejected because |
|---|---|
| Split the cycle into N single-event JSON fixtures (e.g. `cycle_step_01.json` … `cycle_step_11.json`) | Multiplies fixture count from 1 to ~11, requires composite test that reassembles them, loses temporal coherence in a single file, no precedent in the codebase. |
| Embed cycle as a nested list inside one JSON file under `edge_cases/valid/` | Loader returns `payload: Any` so this is technically possible, but every existing edge-case fixture is single-payload — diverging from convention creates contributor friction and would need a new test variant in `test_fixtures.py` rather than reusing the existing `replay_stream` test machinery. |
| Generate fixtures programmatically in a test factory rather than committing them | Loses the on-disk reviewability that makes FR-011 ("2-minute read") satisfiable. Conformance fixtures are the public contract. |

### Implementation Note

The JSONL will contain canonical `Event` envelopes (matching `events/valid/event.json` shape) wrapping `WPStatusChangedPayload`. Lamport clocks are strictly monotonic. Each event has a unique deterministic `event_id` (`01KCYCLE000…000XX`).

---

## R-002 — Current Behavior of `validate_transition()` for the Family

### Decision

The existing validator already rejects unforced backward transitions in the matrix check (`src/spec_kitty_events/status.py:395-420`):

- Line 395: `if payload.from_lane is not None and payload.from_lane in TERMINAL_LANES and not payload.force` — handles terminal-lane exits (e.g. `approved` is terminal in some interpretations).
- Lines 400-401: `if not payload.force: # Force check — if force is True, skip matrix check` — the matrix check on lines that follow returns "invalid transition" for backward moves.
- The `force=True + reason` requirement is already enforced via `WPStatusChangedPayload` model validator (lines 318-321: `force=True requires a non-empty reason`).

**Conclusion**: No validator behavior change is required. FR-007 tests will codify *currently passing* behavior as a contract-stable property. The single gap is **documentation** (FR-001/-002/-003/-010) and **conformance fixtures** (FR-004/-005/-006).

### Rationale

- Source-code spelunking shows the matrix path is exercised; existing test coverage in `tests/unit/test_status.py:438-460` already proves `force=True requires reason` and `force=False rejected` for general transitions — what's missing is the family-named parameterization.

### Alternatives Considered

| Alternative | Rejected because |
|---|---|
| Refactor `validate_transition()` to surface "review-rejection family" as a typed enum return | Out of scope — wire shape and validator API stay frozen per C-003 / C-006. |
| Add a `is_review_rejection()` helper function | Premature abstraction. The plan's parametrized test enumerates the four family members directly; a helper would be tested only by the same enumeration. Re-evaluate if a sibling repo asks for it. |

---

## R-003 — Schema Generation Stability After Adding Fixtures

### Decision

Adding new fixture files under `src/spec_kitty_events/conformance/fixtures/` does **not** trigger schema regeneration. Schemas are produced from Pydantic models by `src/spec_kitty_events/schemas/generate.py`; the fixture files are *consumers* of the schemas, not inputs to them.

### Rationale

- `src/spec_kitty_events/schemas/generate.py` exists and is the only generator script in the repo.
- Quick read of the generator (Pydantic `model_json_schema()` call path) confirms it iterates over model classes, not over fixture JSON.
- Confirmation step during implement: after fixture additions, run schema generation and diff the committed `*.schema.json` files — diff MUST be empty (NFR-004, NFR-005).

### Alternatives Considered

| Alternative | Rejected because |
|---|---|
| Treat fixtures as schema inputs | Wrong direction. The whole point of a schema/fixture split is that schemas describe the wire model and fixtures exemplify it. |

---

## R-004 — Normative `reason` Field Shape

### Decision

Recommended canonical form: `"backward rewind: <from_lane> -> <to_lane>[: <feedback-ref>]"`.

- `<from_lane>` and `<to_lane>` are the literal `Lane` enum values (`in_review`, `approved`, `planned`, etc.).
- `[: <feedback-ref>]` is optional. When present, the feedback-ref SHOULD be a URI-shaped pointer (e.g. `feedback://<mission-slug>/<wp-id>/<timestamp>-<hash>.md`) — the same convention seen in the evidence pack (`review_ref: feedback://...`).
- The contract validator does NOT enforce the shape (no regex tightening). Consumers MAY parse; the recommendation is binding on the CLI emit path (sibling mission 2) and non-binding on the contract validator.

### Rationale

- The evidence-pack stuck events already use a similar shape: `"reason": "move-task: approved -> planned"`. The recommended shape is intentionally close so that a future CLI fix can produce something a human can recognize as the same family member, but with the explicit "backward rewind" prefix that distinguishes it from forward-transition reasons.
- A formal validator regex would be over-reach: it would force every consumer to update if the shape ever evolves. Recommendation-only keeps the wire contract permissive and the human contract clear.
- The `<feedback-ref>` segment lets the CLI carry the human review feedback file pointer in one place — useful for the SaaS materializer (mission 3) when it persists a `ProjectionAnomaly` diagnostic.

### Alternatives Considered

| Alternative | Rejected because |
|---|---|
| Enforce a regex inside `WPStatusChangedPayload` field validator | Tightens the wire contract — would break existing consumers (including the current CLI emit path before mission 2 lands). |
| Require a structured `reason_metadata` object instead of free text | New wire field — C-003 forbids. |
| Leave reason shape unspecified | Defeats FR-010; sibling missions would each invent their own conventions. |

---

## R-005 — Anchor Locations for Cross-Reference

### Decision

Two stable anchors with mutual cross-links:

1. **Module docstring of `src/spec_kitty_events/status.py`** — top-of-file section titled "Review-Rejection Transition Family". This is the primary anchor; Python `help(spec_kitty_events.status)` surfaces it.
2. **`docs/consumer-contract-dossier-v2.4.0.md`** — a new section titled "Backward Transitions: The Review-Rejection Family". The dossier filename includes a version suffix and is stable across releases.

Both anchors reference each other by relative path and reference the three new fixture filenames.

### Rationale

- `docs/consumer-contract-dossier-v2.4.0.md` already exists and is the conventional location for consumer-facing contract documentation in this repo.
- Module docstrings are the most discoverable anchor for downstream Python consumers using `help()` or IDE introspection.
- The mutual cross-link triangle (docstring ↔ docs ↔ fixtures) satisfies NFR-005.

### Alternatives Considered

| Alternative | Rejected because |
|---|---|
| Create a brand-new `docs/backward-transitions.md` | Adds a new top-level docs file when an existing dossier already covers consumer contracts. |
| Add only docstring (no docs file change) | Reduces discoverability for non-Python readers (planning issue is cross-repo; SaaS reviewers may not pip-install the events package locally). |

---

## Open Questions Carried Forward

None. All Phase 0 questions resolved with explicit decisions.
