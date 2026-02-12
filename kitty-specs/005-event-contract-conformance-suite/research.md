# Research: Event Contract Conformance Suite

**Feature**: 005-event-contract-conformance-suite
**Date**: 2026-02-12

## R1: JSON Schema Generation from Pydantic v2

**Decision**: Use build-time generation with `model_json_schema(mode="serialization")`, committed to repo. CI drift check regenerates and fails on diff.

**Rationale**:
- Pydantic v2 generates **JSON Schema Draft 2020-12** (uses `$defs`, `prefixItems`, `const`).
- `mode="serialization"` produces schemas matching the wire format (`model_dump()`).
- Each model generates a self-contained schema with its own `$defs` section — no manual wiring needed.
- `frozen=True` has zero effect on schema output; `AnyHttpUrl` renders as `{"format": "uri", "type": "string"}`.
- Must manually add `$schema` and `$id` keys (Pydantic omits them).
- `Optional[T]` uses `anyOf` with `null` branch (Draft 2020-12 pattern).
- Literal single values use `const`, multi-values use `enum`.

**Alternatives considered**:
- Runtime generation: Rejected — committed files serve as documentation and enable language-agnostic consumption.
- Single combined schema via `TypeAdapter(Union[...])`: Rejected — per-model files are simpler to consume and version independently.

## R2: pytest `--pyargs` Conformance Pattern

**Decision**: Ship conformance tests inside `src/spec_kitty_events/conformance/` as a proper Python package with `test_pyargs_entrypoint.py`.

**Rationale**:
- `pytest --pyargs spec_kitty_events.conformance` resolves the installed package path via `importlib.util.find_spec()`, then applies normal test collection rules.
- Requires `__init__.py` in `conformance/` (mandatory for discoverability).
- `conftest.py` in `conformance/` provides fixtures; `pytest_helpers.py` provides reusable utilities.
- Consumer's `testpaths` config does NOT interfere with `--pyargs` resolution.
- No changes needed to `pyproject.toml` package discovery — `find_packages(where=["src"])` auto-discovers subpackages.
- Should add `conformance/` to coverage `omit` so test code doesn't inflate library coverage metrics.

**Alternatives considered**:
- Shipping tests outside the package: Rejected — makes `--pyargs` impossible since pytest needs the files installed.
- Separate test package `spec-kitty-events-tests`: Rejected — adds cross-package version drift risk.

## R3: jsonschema Library for Schema Validation

**Decision**: Use `jsonschema>=4.21.0,<5.0.0` as the `[conformance]` optional extra.

**Rationale**:
- `Draft202012Validator` matches Pydantic v2's output draft.
- `iter_errors()` yields ALL `ValidationError` objects (not just first failure).
- Rich error attributes: `json_path`, `message`, `validator`, `validator_value`, `absolute_schema_path`, `instance`, `context`.
- Handles `$defs`/`$ref` within Pydantic-generated schemas automatically.
- Python `>=3.10` requirement matches the project.
- Performance is irrelevant (CI-time only, not hot path).

**Alternatives considered**:
- `fastjsonschema`: Rejected — no Draft 2020-12 support, no multi-error collection.
- `jsonschema-rs`: Rejected — adds compiled Rust extension dependency, poor trade-off for an optional extra. Could be future upgrade if performance matters.

## R4: Dual-Layer Validation Architecture

**Decision**: Pydantic-first (primary) + JSON Schema (secondary drift check). Separate violation buckets in `ConformanceResult`.

**Rationale**:
- Pydantic `model_validate()` catches ALL business rules (custom validators, cross-field constraints) — no duplication needed.
- JSON Schema validation catches schema drift and serves language-agnostic consumers.
- `ConformanceResult` has `model_violations` and `schema_violations` buckets.
- `passed` = both layers pass in strict mode (CI); Pydantic-only in graceful mode when `jsonschema` not installed (`schema_check_skipped=True`).
- If `jsonschema` is not importable, validator operates in Pydantic-only mode and sets `schema_check_skipped=True`.

**Alternatives considered**:
- JSON Schema-only: Rejected — misses Pydantic business rules (force requires reason, done requires evidence, etc.).
- Pydantic-only: Rejected — doesn't verify committed JSON Schema files stay aligned.

## R5: SyncLaneV1 Mapping Contract Design

**Decision**: `SyncLaneV1` enum (4 values) + `CANONICAL_TO_SYNC_V1` frozen mapping + `canonical_to_sync_v1()` function. V1 is immutable; new mappings are additive.

**Rationale**:
- Locked V1 mapping: `PLANNED→PLANNED`, `CLAIMED→PLANNED`, `IN_PROGRESS→DOING`, `FOR_REVIEW→FOR_REVIEW`, `DONE→DONE`, `BLOCKED→DOING`, `CANCELED→PLANNED`.
- Mutation of V1 mapping for any input = breaking change (major version bump).
- New mapping versions (V2, V3) coexist as additive exports.
- Consumers import the mapping function instead of hardcoding.

**Alternatives considered**:
- Advisory mapping (consumers override): Rejected — mapping is normative for conformance.
- Single mutable mapping: Rejected — breaks contract stability guarantees.
