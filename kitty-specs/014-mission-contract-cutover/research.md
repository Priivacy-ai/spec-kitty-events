# Research: Mission Contract Cutover

**Feature**: 014-mission-contract-cutover
**Date**: 2026-04-05
**Status**: Complete

## R1: Authoritative cutover policy source

**Decision**: Publish one canonical machine-readable cutover artifact as the sole authoritative source for compatibility gating.
**Rationale**: The specification requires machine-checkable classification of pre-cutover clients. A single artifact prevents drift between validators, fixtures, docs, and downstream consumer enforcement.
**Alternatives considered**: (a) Derive policy from scattered schemas and prose — rejected because downstream repos could classify legacy payloads differently. (b) Keep only docs-level rollout guidance — rejected because it is not machine-checkable.

## R2: Existing manifest extension versus dedicated artifact

**Decision**: Prefer extending an existing versioned manifest only if it already has clear release authority and can encode the full cutover policy. Otherwise, introduce a dedicated cutover artifact and make it authoritative.
**Rationale**: Reusing a release-authoritative manifest minimizes new surface area, but only if it can carry the full policy: version signal, forbidden legacy key set, and forbidden legacy catalog event names. Partial reuse would recreate the ambiguity the cutover is meant to remove.
**Alternatives considered**: Always create a new artifact — rejected because an existing authoritative manifest may already be sufficient. Always reuse the existing fixture manifest — rejected because it may not be semantically appropriate as a release-policy authority.

## R3: Runtime enforcement model

**Decision**: All live ingestion paths fail closed from day one. Missing cutover version signal or presence of forbidden legacy surfaces results in immediate rejection.
**Rationale**: The release is a hard cutover with no mixed-version support. Any compatibility mode would undermine deterministic rollout control.
**Alternatives considered**: (a) Compatibility mode for local/dev — rejected because it creates a hidden bridge path. (b) Warning-only mode before strict enforcement — rejected because it permits mixed-version operation.

## R3a: One on-wire compatibility signal

**Decision**: The cutover artifact must declare one exact on-wire signal name and location that downstream repos must read for compatibility gating, plus the exact cutover value and accepted-major policy derived from it.
**Rationale**: Without one explicit signal binding, downstream repos could enforce the same artifact through different fields or headers and drift in behavior.
**Alternatives considered**: Infer compatibility from multiple available version fields — rejected because it recreates ambiguity and inconsistent gate logic.

## R4: Legacy handling boundary

**Decision**: Legacy payload handling is allowed only in explicit offline migration or rewrite workflows.
**Rationale**: Historical data may need rewriting into canonical form, but runtime consumer paths must never become bridge layers. This keeps migration concerns separate from live interoperability.
**Alternatives considered**: Shared runtime helper that both migrates and validates — rejected because it risks reuse on normal ingestion paths.

## R5: Ownership split between events and consuming repos

**Decision**: `spec-kitty-events` owns the authoritative artifact and reference/helper implementation for conformance within this repository. `spec-kitty-saas` and `spec-kitty` own their runtime enforcement implementations against the same artifact semantics, deriving version signal, accepted-major policy, and forbidden surfaces from the artifact rather than repo-local constants.
**Rationale**: This centralizes policy while avoiding cross-repo runtime coupling to internal helper code.
**Alternatives considered**: Shared imported helper package for runtime gating — rejected because it would create hidden implementation coupling and could mask policy drift.

## R6: Versioning strategy

**Decision**: Bump the package from `2.9.0` to `3.0.0`.
**Rationale**: The cutover removes public legacy terms, changes the canonical envelope, changes event-name semantics, and rejects mixed old/new operation. This is a breaking contract release.
**Alternatives considered**: Minor version bump — rejected because downstream consumers must not treat this as backward-compatible.
