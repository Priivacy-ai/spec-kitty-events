# Contract: Versioning and Compatibility

**Mission**: `teamspace-event-contract-foundation-01KQHDE4`
**Source spec FRs**: FR-009, FR-010, C-003 · **Research**: [research.md R-03](../research.md#r-03--schema-version-bump-semantic)

## Rule

This mission lands as a **major package-version bump** on the package's contract behaviour axis (package `4.x` → `5.0.0`). The on-wire envelope schema version stays at `3.0.0` (the cutover-contract version pinned by `cutover.py::CUTOVER_ARTIFACT.cutover_contract_version`). The package bump is recorded in `CHANGELOG.md`, in `COMPATIBILITY.md`, and in the committed JSON Schemas. Producers must continue to emit `schema_version="3.0.0"` on the envelope; the cutover gate will reject anything else.

## Why major

- The lane vocabulary changes: `in_review` flips from invalid to canonical. Consumers that switched on the lane vocabulary's exact membership will silently mishandle `in_review` after the bump.
- Payload contracts are reconciled (see [payload-reconciliation.md](./payload-reconciliation.md)). Producers must change to conform.
- The recursive forbidden-key validator now rejects nested legacy keys at any depth. Previously-accepted historical envelopes that contained a deeply nested forbidden key are now rejected.

Each of these is a behavior change for at least one role (consumer or producer). Per the charter Review Policy, we surface them as a major change rather than burying them under a minor bump.

## What gets versioned

| Artifact | Where versioned |
|---|---|
| Envelope contract | `schema_version` field on the public `Event` model in the envelope; the package's cutover-contract version constant (`cutover.py::CUTOVER_ARTIFACT.cutover_contract_version` = `3.0.0`). The PACKAGE version (e.g. `5.0.0`) is recorded separately in `pyproject.toml` and `__version__`. |
| Typed payload schemas | Each `*.schema.json` under `src/spec_kitty_events/schemas/` carries a `$id` and is regenerated on bump |
| Conformance fixtures | Class taxonomy and fixture format are versioned with the package |
| Forbidden-key set | `since_version` field on the named constant |

## Required artifacts on bump

The work package that lands the bump MUST update:

1. `CHANGELOG.md` — a "Breaking Changes" section listing the three changes above with one-line summaries.
2. `COMPATIBILITY.md` — a new section (or updated version) explaining:
   - The bump and its drivers.
   - The local-CLI compatibility vs TeamSpace ingress validity distinction (FR-009 / SC-006).
   - Pointer to the lane vocabulary contract and the payload reconciliation contract.
   - Migration notes for consumers (what to switch on, what to stop emitting).
3. `pyproject.toml` (or wherever the package version is recorded) — the package version is bumped.
4. Every committed `*.schema.json` — regenerated from the updated Pydantic models.

## Local-CLI compatibility vs TeamSpace ingress validity

A core acceptance condition (FR-009) is that the new compatibility doc explains the two validity domains:

- **Local-CLI compatibility**: the CLI continues to read historical `status.events.jsonl` rows on local disk for the user's own bookkeeping, even though those rows are not TeamSpace envelopes.
- **TeamSpace ingress validity**: only canonical envelopes pass ingress. The contract package enforces this domain.

The compatibility doc must:

- Show one example per validity domain.
- State that local compatibility is **not** weakened by this mission's bump.
- Point readers to the CLI canonicalizer (Tranche B in `spec-kitty`) as the documented bridge between the two domains.

## Forbidden patterns

- Bumping the schema version without updating `CHANGELOG.md`.
- Updating Pydantic models without regenerating `*.schema.json`.
- Documenting the bump as additive when it is in fact breaking.
- Removing or rewriting the local-CLI-compatibility wording in the doc to suggest it has been weakened.

## Validation

A schema-drift CI check (existing) asserts that committed `*.schema.json` files match what the model regenerator produces. This mission must keep that check green after the bump.
