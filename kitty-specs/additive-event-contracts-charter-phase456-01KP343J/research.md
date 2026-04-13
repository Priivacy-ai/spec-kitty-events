# Research: Additive Event Contracts for Charter Phase 4/5/6

**Date**: 2026-04-13
**Mission ID**: `01KP343JBG2V7WSWSDJ0HD76BR`

## Status

All unknowns resolved. This tranche follows well-established patterns from 14 prior missions. No novel technology decisions required.

## Research Findings

### R1: Domain Module Pattern Verification

**Decision**: Follow the exact module structure used by all existing domain modules.

**Rationale**: 11 existing domain modules (`lifecycle.py`, `status.py`, `gates.py`, `collaboration.py`, `glossary.py`, `mission_next.py`, `dossier.py`, `mission_audit.py`, `decisionpoint.py`, `connector.py`, `sync.py`) all follow the same section structure. The pattern is proven and understood by consumers.

**Alternatives considered**: Bundling both domains into a single `charter_events.py`. Rejected because it breaks the one-domain-per-file convention and would couple unrelated contract surfaces.

### R2: Value Object Reuse Feasibility

**Decision**: Import `RuntimeActorIdentity` from `spec_kitty_events.mission_next` and `ProvenanceRef` from `spec_kitty_events.dossier` directly. Do NOT import from `spec_kitty_events.__init__`.

**Rationale**: `__init__.py` eagerly imports all domain modules. If a new domain module imports from `__init__`, it creates a circular import (init imports the new module, which imports from init). The established pattern is direct imports from defining modules -- e.g., `mission_audit.py` imports `ProvenanceRef` from `spec_kitty_events.dossier`, not from the package root. Import graph for new modules:
- `profile_invocation.py` imports: `spec_kitty_events.mission_next.RuntimeActorIdentity`
- `retrospective.py` imports: `spec_kitty_events.dossier.ProvenanceRef`
- Neither `mission_next.py` nor `dossier.py` will import from the new modules.

**Alternatives considered**: Duplicating the value objects into a shared `value_objects.py`. Rejected as unnecessary indirection.

### R3: Reserved Constant Pattern

**Decision**: Define `PROFILE_INVOCATION_COMPLETED` and `PROFILE_INVOCATION_FAILED` as string constants with `# Reserved` comments, include them in the event types frozenset, but create no payload models or fixtures.

**Rationale**: `NextStepPlanned` in `mission_next.py` establishes this exact pattern (line 20: `NEXT_STEP_PLANNED: str = "NextStepPlanned"  # Reserved — payload contract deferred until runtime emits`). The reducer skips reserved types (line 290: `if etype == NEXT_STEP_PLANNED: continue`). Since profile invocation has no reducer, the skip logic is unnecessary, but the constant and frozenset inclusion ensure the type name is claimed.

### R4: Conformance Fixture Category Extension

**Decision**: Add `"profile_invocation"` and `"retrospective"` to `_VALID_CATEGORIES` in `loader.py`.

**Rationale**: The loader uses a whitelist (`_VALID_CATEGORIES` frozenset) to prevent typos in category names. Adding two new entries is safe because: (a) it's additive to a frozenset, (b) existing categories are unaffected, (c) the fixture path convention (`category/valid/`, `category/invalid/`) naturally namespaces fixtures.

### R5: Manifest Entry Format

**Decision**: Use the standard manifest entry format with `min_version: "3.1.0"` for all new fixtures.

**Rationale**: The manifest uses `expected_result` (not `expected_valid`) as the validity field. The `min_version` field documents when the fixture was introduced. All existing post-3.0.0 fixtures use `"min_version": "3.0.0"` but new fixtures should use `"3.1.0"` since they exercise contracts introduced in that version.

### R6: WP03 Conformance Test Strategy

**Decision**: WP03 conformance tests validate fixtures using direct Pydantic model instantiation, not `validate_event()` dispatch.

**Rationale**: `validate_event()` requires entries in `_EVENT_TYPE_TO_MODEL` (added in WP04). To keep WP03 independent of WP04, conformance tests in WP03 directly instantiate payload models from fixture data and assert validity. WP04's integration step verifies the full `validate_event()` dispatch path.

**Alternatives considered**: Having WP03 also wire the dispatch entries. Rejected because it blurs the WP boundary — the plan assigns dispatch wiring to WP04 as the single integration point.

### R7: Glossary Summary Drift — Deferred with Clear Criteria

**Decision**: No glossary events in this tranche (C-003).

**Rationale**: The current 8 glossary events cover interaction-level mutations. The missing gap is mission/execution-level drift summaries. This was deferred because: (a) no concrete Phase 4/5/6 consumer is identified, (b) the payload shape is unclear without a consumer, (c) adding a speculative event violates the "smallest additive tranche" principle.

**Re-entry criteria**: Add a glossary summary event when a consumer can name: (1) what query it needs to answer, (2) what payload fields it needs, (3) why replaying low-level glossary events is insufficient.

### R8: Provenance Query — Not an Event

**Decision**: No provenance event (C-004).

**Rationale**: `ProvenanceRef` is a value object embedded in existing payloads (dossier artifacts, audit artifacts). Provenance query is a read-path concern — the consumer queries the event store with filters, not by subscribing to a provenance event stream. Adding a provenance-query event would conflate the CQRS boundary (events are the write side; queries are the read side).
