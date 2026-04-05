# Implementation Plan: Mission Contract Cutover

**Branch**: `main` | **Date**: 2026-04-05 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `kitty-specs/014-mission-contract-cutover/spec.md`

## Summary

Publish the breaking `spec-kitty-events` contract release that replaces mission-domain `feature*` terminology with canonical mission/build terminology, introduces explicit `build_id` checkout identity alongside `node_id`, removes the runtime `MissionCompleted` alias behavior, and defines one authoritative machine-readable cutover artifact for downstream compatibility gating. The implementation remains scoped to `spec-kitty-events`, while `spec-kitty-saas` and `spec-kitty` must enforce the same cutover artifact semantics in their own runtime code before rollout.

## Technical Context

**Language/Version**: Python 3.10+ package target, Python 3.11+ development environment  
**Primary Dependencies**: Pydantic v2, stdlib JSON/schema tooling, existing repo-local schema generation and conformance loaders  
**Storage**: Packaged JSON schemas and conformance fixtures under `src/spec_kitty_events/schemas/` and `src/spec_kitty_events/conformance/fixtures/`  
**Testing**: `pytest`, conformance fixture validation, replay fixture validation, `mypy --strict`, existing repo-local schema generation checks  
**Target Platform**: Python library on macOS and Linux developer environments  
**Project Type**: Single Python package in `src/spec_kitty_events/`  
**Performance Goals**: Preserve existing CLI and validation workflows so contract validation and schema generation remain fast, with repo CLI operations typically under 2 seconds outside full test runs  
**Constraints**: Fail-closed on all live ingestion paths from day one of the release; no compatibility mode, no downgrade path, no local/dev runtime exception; offline migration and rewrite flows may read legacy data only to rewrite it into canonical form; one authoritative machine-readable cutover artifact only  
**Scale/Scope**: Breaking major release touching core event envelope models, mission lifecycle and runtime contracts, projection modules, generated schemas, conformance fixtures, docs, and package version metadata

## Charter Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- Pass: Plan stays faithful to the approved specification and records the major technical decisions directly in planning artifacts.
- Pass: Quality gates remain explicit: tests, lint, type checks, and review findings must be clean before release.
- Pass: Performance expectations remain compatible with the charter because the plan extends existing repo-local schema and validation workflows rather than introducing networked or heavyweight planning dependencies.
- Pass: Platform support remains macOS and Linux because all planned artifacts stay within the existing Python package and packaged JSON assets.
- Pass: No unresolved clarification remains after planning interrogation.

Post-Phase 1 re-check: still passing. Phase 1 artifacts preserve the one-source-of-truth cutover policy, keep runtime enforcement ownership in downstream repos, and do not introduce spec drift.

## Project Structure

### Documentation (this feature)

```
kitty-specs/014-mission-contract-cutover/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── cutover_contract_artifact.schema.json
│   ├── mission_catalog_contract.schema.json
│   └── canonical_event_envelope_contract.schema.json
└── tasks.md             # Created later by /spec-kitty.tasks
```

### Source Code (repository root)

```
src/spec_kitty_events/
├── __init__.py                         # Public exports and versioned symbols
├── models.py                           # Canonical event envelope, build_id addition
├── lifecycle.py                        # MissionCreated/MissionClosed and lifecycle-only MissionCompleted
├── mission_next.py                     # MissionRun* payloads, remove MissionCompleted alias normalization
├── dossier.py                          # Mission taxonomy updates in projections and reducers
├── decisionpoint.py                    # mission_slug mission_type terminology updates
├── mission_audit.py                    # mission_slug mission_number taxonomy updates
├── status.py                           # legacy mission-domain status payload terminology hotspot
├── schemas/
│   ├── generate.py                     # Canonical schema generation registry
│   └── *.json                          # Regenerated public schemas
└── conformance/
    ├── validators.py                   # Event-type validators and cutover helper wiring
    ├── loader.py                       # Fixture manifest loader
    ├── fixtures/
    │   ├── manifest.json               # Existing fixture manifest surface
    │   ├── events/**/*.json            # Envelope and payload fixtures
    │   ├── mission_next/**/*.json*     # Mission runtime fixtures
    │   ├── dossier/**/*.json*          # Dossier fixtures
    │   ├── mission_audit/**/*.json*    # Mission audit fixtures
    │   └── decisionpoint/**/*.json*    # Decisionpoint fixtures
    └── test_pyargs_entrypoint.py       # Conformance entrypoint coverage

tests/
├── test_*.py                           # Existing unit/integration coverage
README.md                               # Public taxonomy and release guidance
COMPATIBILITY.md                        # Hard-cutover compatibility policy
pyproject.toml                          # Package major version bump
```

**Structure Decision**: Single Python package. The plan keeps all implementation inside `/private/tmp/mission/spec-kitty-events/src/spec_kitty_events/` plus regenerated schemas, conformance fixtures, and root documentation. No new deployable unit or repo split is introduced.

## Design Decisions

### D1: One authoritative cutover artifact

`spec-kitty-events` will publish exactly one machine-readable cutover artifact as the authoritative compatibility source. The plan prefers extending an existing versioned manifest only if that surface already has release authority and can encode the full cutover policy without ambiguity. Otherwise, the implementation adds a dedicated cutover artifact and makes it the sole source of truth.

The artifact must enumerate:

- the exact on-wire signal name and location that live consumers must read and compare
- the required cutover contract-version value carried by that signal
- the accepted major-version policy for fail-closed rollout
- the forbidden legacy key set
- the forbidden legacy catalog event names
- the forbidden legacy aggregate-name set

No runtime policy may be split across scattered schemas, fixtures, docs, or repo-local constants without that artifact remaining authoritative.

### D2: Fail-closed runtime enforcement, migration-only legacy handling

All live ingestion paths are fail-closed from day one of the release. Any payload that omits the required cutover version signal or contains a forbidden legacy surface is rejected immediately, even if other fields appear canonical. No compatibility mode, downgrade path, or local/dev interoperability exception is allowed.

Legacy handling is allowed only inside explicit offline migration or rewrite workflows whose purpose is to convert historical data to canonical form. That handling must not become reusable runtime bridge logic.

### D3: Artifact-owned semantics, repo-local helper implementation

`spec-kitty-events` owns the authoritative cutover artifact and a reference/helper implementation used for schema validation, conformance validation, and fixture/replay checks within this repository. Consuming repos must enforce the same artifact semantics in their own runtime code and may not substitute repo-local policy definitions.

This preserves one policy source while preventing downstream runtime coupling to `spec-kitty-events` internal helper implementations.

### D4: Envelope identity split becomes first-class

The canonical event envelope in `src/spec_kitty_events/models.py` becomes explicitly dual-identity:

- `build_id` is the checkout or worktree identity
- `node_id` remains the causal emitter identity used for Lamport ordering and deterministic tie-breaking

All build registration and heartbeat-style contracts adopt `build_id` as canonical checkout identity while retaining `node_id` as a separate required causal field.

### D4a: One exact on-wire compatibility gate

The cutover artifact must bind compatibility gating to one exact on-wire signal so every downstream repo enforces the same rule. The implementation must choose one canonical signal name and location for live payloads, and the artifact must declare:

- the signal field name
- where it appears on wire
- the exact cutover value to require
- the accepted major-version rule derived from that value

If the canonical signal reuses the existing event envelope `schema_version`, the artifact must say so explicitly. If a different signal is required for non-envelope contract surfaces, the artifact must define that exact signal and require downstream repos to use it instead of inventing repo-local alternatives.

### D5: Mission taxonomy cutover is a major release

The package version in `/private/tmp/mission/spec-kitty-events/pyproject.toml` moves from `2.9.0` to `3.0.0`. This aligns the code, schemas, fixtures, validators, docs, and compatibility guidance with a hard breaking cutover and creates a clean downstream release gate.

### D6: Existing fixture manifest is a likely extension point, not a guaranteed answer

`src/spec_kitty_events/conformance/fixtures/manifest.json` already carries versioned fixture metadata and may be a candidate release-authority surface. The implementation must evaluate whether it can encode the full cutover artifact cleanly. If it cannot, the implementation must add a dedicated artifact rather than overloading the fixture manifest with partial policy.

## Phase 0: Research Output

Phase 0 resolves the planning decisions already confirmed during interrogation and records the extension-vs-new artifact rule, fail-closed runtime policy, and helper-versus-runtime enforcement split in `research.md`.

## Phase 1: Design & Contracts

### Planned implementation slices

1. Introduce the canonical cutover artifact and its helper interpretation layer.
2. Bind the cutover artifact to one exact on-wire compatibility signal and update the event envelope and any build registration contracts to require `build_id` distinct from `node_id`.
3. Rename mission-domain public payload fields and mission workflow identifiers across lifecycle, runtime, and projection modules.
4. Define `MissionCreated` and `MissionClosed`, preserve lifecycle `MissionCompleted`, and remove the `MissionCompleted` runtime alias path from mission-next.
5. Regenerate schemas, conformance fixtures, and replay fixtures from the canonicalized models and artifact policy.
6. Update documentation and compatibility guidance to describe the one-source-of-truth cutover policy and downstream rollout gates.
7. Bump the package major version and keep all validation gates green.

### Contracts to generate in this plan phase

- `contracts/cutover_contract_artifact.schema.json`: planned shape of the authoritative cutover artifact.
- `contracts/mission_catalog_contract.schema.json`: planned canonical mission catalog payload and event semantics.
- `contracts/canonical_event_envelope_contract.schema.json`: planned envelope requirements, including `build_id` and `node_id` split.

### Agent Context Update

No plan-time agent-context resolver is currently exposed by this repository. `spec-kitty agent context resolve` rejects `plan` as an invalid action, and `implement` cannot resolve before work packages exist. No agent-specific context file was updated during this planning phase.

## Complexity Tracking

No charter violations require justification.
