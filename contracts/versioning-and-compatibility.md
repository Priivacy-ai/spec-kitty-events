# Contract: Versioning and Compatibility

**Status**: durable · **Applies to**: every release of `spec-kitty-events`

> Promoted here from
> [`kitty-specs/teamspace-event-contract-foundation-01KQHDE4/contracts/versioning-and-compatibility.md`](../kitty-specs/teamspace-event-contract-foundation-01KQHDE4/contracts/versioning-and-compatibility.md),
> which remains as that mission's historical artifact and is scoped to the
> `4.x → 5.0.0` bump specifically. **This document governs**; that one records
> one application of it.

## Two version numbers, deliberately distinct

| Axis | Where it lives | Current |
|---|---|---|
| **Package version** | `pyproject.toml` `[project].version`, `spec_kitty_events.__version__` | see [COMPATIBILITY.md](../COMPATIBILITY.md) |
| **On-wire envelope schema version** | `Event.schema_version`; pinned by `cutover.py::CUTOVER_ARTIFACT.cutover_contract_version` | `3.0.0` |

These move independently and conflating them is the most common misreading of
this package. A major **package** bump signals a contract-behaviour change for
at least one role. It does **not** imply a wire-format change, and producers
must keep emitting `schema_version="3.0.0"` regardless of the package major —
the cutover gate rejects anything else.

Both `5.0.0` and `6.0.0` were major package bumps that intentionally left the
envelope at `3.0.0`.

## What requires a major package bump

A change is major if it is a behaviour change for **any** role — producer or
consumer. Concretely:

- **Widening or narrowing the canonical lane vocabulary.** See
  [lane-vocabulary.md](./lane-vocabulary.md). Consumers on the previous major
  fail closed on a new lane value.
- **Changing a typed payload's required fields, or renaming a field.** Producers
  of the previous shape become invalid.
- **Adding to the forbidden-key set, or widening where it is enforced.**
  Envelopes that previously passed are now rejected.
- **Any change to an existing event contract that makes a previously-accepted
  envelope rejected, or a previously-rejected envelope accepted.**

Adding a new event type with its own payload model is **additive** and takes a
minor bump: the new event family is a new capability, while every existing
event contract keeps the same accept/reject boundary. `6.1.0` added
`MissionReopened` and `FollowUpRecorded` this way. A minor version does not make
an unknown event safe for every consumer: producers MUST capability-gate
emission until each intended consumer can validate and process the new type.

## Required artifacts on a major bump

The work package landing the bump MUST update all of:

1. **`CHANGELOG.md`** — a `### Breaking` section naming each breaking change
   with a one-line summary and the consumer-visible consequence.
2. **`COMPATIBILITY.md`** — the `Current package version` line (see below), plus
   a section explaining the bump's drivers and the migration each affected role
   must perform.
3. **`pyproject.toml`** and `__version__`.
4. **Every committed `*.schema.json`** under `src/spec_kitty_events/schemas/`,
   regenerated from the updated Pydantic models.
5. **Conformance fixtures** covering the new accept/reject boundary.

## The `Current package version` line

`COMPATIBILITY.md` carries a single machine-readable declaration:

```
**Current package version**: `X.Y.Z`
```

`tests/test_compatibility_doc.py` asserts it equals
`spec_kitty_events.__version__`. This exists because
`COMPATIBILITY.md` spent the whole of `6.0.0` and `6.1.0` asserting in
present tense that the current release was `5.0.0` — a documented requirement
that nothing in CI checked. State the version in that one place and reference it
elsewhere; do not restate it in prose.

## Local-CLI compatibility vs TeamSpace ingress validity

Two distinct validity domains. A row acceptable in one is not necessarily
acceptable in the other, and `COMPATIBILITY.md` is the authoritative
explanation:

- **Local-CLI compatibility** — the `spec-kitty` CLI reads historical
  `status.events.jsonl` rows off local disk permissively, tolerating pre-cutover
  shapes so users never lose access to their own history. Not weakened by any
  package bump.
- **TeamSpace ingress validity** — only canonical envelopes pass. Full
  fail-closed contract gate.

The documented bridge between them is the CLI canonicalizer. Ingress will not
accept raw historical rows; consumers reading locally must not assume their rows
have been canonicalized.

## Forbidden patterns

- Bumping any version without updating `CHANGELOG.md`.
- Updating Pydantic models without regenerating `*.schema.json`.
- Documenting a breaking change as additive.
- Restating the current package version in prose instead of referencing the
  single declaration.
- Weakening the local-CLI-compatibility wording to imply it has been reduced.

## Validation

- The existing schema-drift CI check asserts committed `*.schema.json` files
  match what the model regenerator produces.
- `tests/test_lane_vocabulary.py::test_canonical_lane_set_is_pinned` fails on
  any undeclared lane change.
- `tests/test_compatibility_doc.py` fails when `COMPATIBILITY.md`'s declared
  version drifts from the package version.
