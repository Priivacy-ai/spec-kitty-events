# Contract: Recursive Forbidden-Key Validation

**Mission**: `teamspace-event-contract-foundation-01KQHDE4`
**Source spec FRs**: FR-005, NFR-002, C-001 · **Research**: [research.md R-01](../research.md#r-01--complete-forbidden-key-set)

## Rule

The contract package rejects any envelope or payload that contains a forbidden legacy key, **anywhere**, at any nesting depth, in any object's keys, including inside elements of arrays.

## The Forbidden-Key Set

A closed, named, versioned constant (per [research.md R-01](../research.md#r-01--complete-forbidden-key-set)).

- **Seed members**: `feature_slug`, `feature_number`, `mission_key`.
- **Final members**: determined by the audit work package; the audit cross-references the survey in epic #920 and the current `spec-kitty-saas` ingress rejection rules.
- **Storage**: `src/spec_kitty_events/forbidden_keys.py`, exported as `FORBIDDEN_LEGACY_KEYS` (a `frozenset[str]`).

## Algorithm

The recursive validator walks the input as JSON-shaped data:

1. If the current node is a `dict`/object: for each key, if `key in FORBIDDEN_LEGACY_KEYS`, emit a `ValidationError(code="FORBIDDEN_KEY", path=<current path>, details={"key": <key>})`. Then recurse into each value.
2. If the current node is a `list`/array: recurse into each element, with the path extended by the element index.
3. Otherwise (string, number, bool, null): no-op.

The validator is **key-only**: it never inspects values for matching strings. A field whose *value* happens to equal `"feature_slug"` MUST NOT trigger rejection. Test coverage MUST include this case as a "must accept" fixture.

## Path representation

The `path` field on `ValidationError` is a list of `str | int` representing JSON-pointer-like navigation (object keys as strings, array indices as integers). The empty list `[]` denotes the envelope root. Example: a forbidden key found at `payload.metadata.tags[2].feature_slug` produces `path = ["payload", "metadata", "tags", 2, "feature_slug"]`.

## Determinism

The validator MUST visit nested children in a deterministic order so that, for any given input, the first reported error (when short-circuiting) is stable. Recommended order: object keys in insertion order; array elements in index order; depth-first.

## Test obligations

`tests/test_forbidden_keys.py` MUST include:

1. A targeted fixture for each forbidden key at: top level, depth-1 nested object, depth-3 nested object, depth ≥ 10 nested object, inside an array element.
2. A "must accept" fixture where a forbidden key name appears as a string *value* (not a key).
3. A hypothesis property test: for any generated nested structure that contains at least one forbidden key, the validator returns `code="FORBIDDEN_KEY"` and a `path` whose terminal segment equals that key.
4. A hypothesis property test: for any generated nested structure that contains **no** forbidden key, the validator does not emit `FORBIDDEN_KEY`.
5. A determinism test: validating the same input twice yields byte-identical results.

## Edge cases the contract resolves

- Forbidden key inside an array element ("inside-array" case from spec edge cases): rejected.
- Forbidden key as a *value*: accepted.
- Forbidden key at depth ≥ 10: rejected (NFR-002).
- Mixed object/array nesting: handled by the unified recursion.

## Forbidden patterns

- Inspecting forbidden keys via a regex or pattern at the top level only.
- Skipping array elements during the walk.
- Constructing the forbidden-key set at runtime from a list of strings; it MUST be the named constant exported from `spec_kitty_events.forbidden_keys`.

## Versioning

Changing the membership of `FORBIDDEN_LEGACY_KEYS` is a contract change subject to the version-bump rule (see [versioning-and-compatibility.md](./versioning-and-compatibility.md)). Additions are typically major-bump-worthy because they tighten acceptance.
