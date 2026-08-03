# Contract: Canonical Lane Vocabulary

**Status**: durable · **Applies to**: every release of `spec-kitty-events`
**Enforced by**: [`tests/test_lane_vocabulary.py`](../tests/test_lane_vocabulary.py)

> This is the repo-level, durable home for the lane-vocabulary contract. It was
> promoted here from
> [`kitty-specs/teamspace-event-contract-foundation-01KQHDE4/contracts/lane-vocabulary.md`](../kitty-specs/teamspace-event-contract-foundation-01KQHDE4/contracts/lane-vocabulary.md),
> which remains in place as that mission's historical artifact. Where the two
> differ, **this document governs** — the mission copy is scoped to the
> vocabulary as it stood at the `5.0.0` release and does not know about
> `genesis`.

## Rule

There is exactly one canonical **wire/event** lane vocabulary. This contract
package owns that vocabulary. Consumers may keep host-internal state enums or
sentinels (for example, the CLI's non-persisted `uninitialized` read state), but
they must translate those states before the event boundary and must never emit
them as canonical lane values.

## Authoritative location

[`src/spec_kitty_events/status.py`](../src/spec_kitty_events/status.py) — the
`Lane` enum is the single source of truth. Consumers import from
`spec_kitty_events`.

## Vocabulary

Ten canonical lanes, in enum order:

| Lane | Value | Display |
|---|---|---|
| `Lane.GENESIS` | `genesis` | **no** — pre-finalize origin state |
| `Lane.PLANNED` | `planned` | yes |
| `Lane.CLAIMED` | `claimed` | yes |
| `Lane.IN_PROGRESS` | `in_progress` | yes |
| `Lane.FOR_REVIEW` | `for_review` | yes |
| `Lane.IN_REVIEW` | `in_review` | yes |
| `Lane.APPROVED` | `approved` | yes |
| `Lane.DONE` | `done` | yes |
| `Lane.BLOCKED` | `blocked` | yes |
| `Lane.CANCELED` | `canceled` | yes |

`genesis` is producer-side only. A work package with no recorded lane events
derives as `genesis` until `finalize-tasks` seeds it to `planned`. The only
legal edges out of it are `genesis -> planned` (the seed, no `force` required)
and `genesis -> canceled` via the generic non-terminal cancel rule.

**Display consumers must not derive board columns, summary chips, progress rows,
or lane filters from every `Lane` member.** Use `DISPLAY_LANES` for ordered
display surfaces and `NON_DISPLAY_LANES` for explicit exclusions
(`status.py:256-260`). `Lane.GENESIS` is canonical for validation and replay but
is not displayable.

## Versioning

**Adding or removing a canonical lane is a breaking contract change and requires
a major package-version bump.** See
[versioning-and-compatibility.md](./versioning-and-compatibility.md).

This holds even when the on-wire envelope shape is unchanged. Widening the
accepted lane value set is breaking because consumers on the previous major
**fail closed** on the new value: a consumer pinned `<6.0.0` rejects
`from_lane="genesis"` as `UNKNOWN_LANE`. Producers must therefore gate fan-out
of a newly added lane on the installed package's lane capability until every
consumer has rolled forward.

Precedent: `6.0.0` added `genesis` and took a major bump while leaving the
envelope `schema_version` at `3.0.0`.

### Consumers cannot be assumed to be typed

Not every consumer of this vocabulary is Python with an imported enum.
`spec-kitty-go` carries the work-package lane as a bare `string`
(`domaincore/operation/runtime_port.go`, `adapters/orchestratorapi/read.go`) by
deliberate design — its domain core is lane-agnostic and host-owned vocabulary
is kept out of it. An untyped consumer will accept an unknown lane value
silently rather than failing closed, which is a further reason the major-bump
signal is the only reliable coordination mechanism here.

## Validation

- An envelope whose payload references a lane outside the canonical vocabulary
  is rejected with
  `ValidationError(code="UNKNOWN_LANE", path=..., details={"lane": "<value>"})`.
- Lane values are matched exactly. There is no case folding and no alias
  resolution at the validation boundary.

## Forbidden patterns

- Defining an independent wire/event lane vocabulary instead of importing this
  package or validating a consumer translation against it.
- Emitting a host-internal state or sentinel as a canonical event lane.
- Comparing lane values to string literals (`if lane == "in_review"`) at API
  boundaries. Compare to `Lane.IN_REVIEW`.
- Inferring a display surface from `Lane` membership rather than from
  `DISPLAY_LANES`.

## Enforcement

[`tests/test_lane_vocabulary.py`](../tests/test_lane_vocabulary.py) is the gate,
not this document. It must contain:

1. `test_in_review_is_canonical` — membership and round-trip via `Lane(value)`.
2. `test_canonical_lane_set_is_pinned` — compares the live enum against a
   committed `EXPECTED_CANONICAL_LANES` frozenset and fails on any drift. This
   is what makes a silent lane addition impossible; changing it is a deliberate
   edit that a reviewer sees.
3. `test_lane_vocabulary_is_single_source_of_truth` — scans
   `src/spec_kitty_events/` for canonical lane string literals outside
   `status.py`, catching a parallel vocabulary before it ships.

`EXPECTED_CANONICAL_LANES` is an in-repository test constant, not a public
cross-repo API. Downstream consumers enforce boundary parity through their own
consumer/compatibility tests against the exported `Lane` enum. Their internal
state sets may be supersets, provided every persisted or wire value is either a
canonical `Lane` value or is translated before the event boundary.

## History

| Release | Change |
|---|---|
| `5.0.0` | `in_review` became canonical; contract first written, as a mission artifact |
| `6.0.0` | `genesis` added; `NON_DISPLAY_LANES` / `DISPLAY_LANES` introduced |
