# Phase 0 — Research: Force-Required Review-Rejection Contract

This mission has one material design decision and a small set of
mechanical fixture decisions. There are no unresolved
`[NEEDS CLARIFICATION]` markers from the spec. The package's existing
documentation and tracker history are the authoritative sources.

## Decision 1 — Enforcement mechanism for the family

**Decision**: Add an **explicit family-guard** at the top of
`validate_transition()` that rejects every unforced backward transition
in the review-rejection family with the violation message
`"review-rejection rollback {from} -> {to} requires force=True"`. Keep
the four pairs in `_ALLOWED_TRANSITIONS` so they remain valid under
`force=True` via the existing matrix flow.

**Rationale**:

- Produces a single, code-greppable violation that names the missing
  element (`force=True`). Consumers can dispatch on that string without
  introspecting the matrix.
- Honors R-4 (no inference): the violation tells the consumer exactly
  which field is missing.
- Localizes the rule to one predicate so docs/module docstring/tests can
  point at a single owner of the truth.
- Bootstrap-planned (`from_lane=None -> planned, force=True`) cannot be
  misclassified because the predicate short-circuits on `from_lane is
  None`.

**Alternatives considered**:

1. **Remove the four pairs from `_ALLOWED_TRANSITIONS`.** Rejected.
   Unforced rollbacks would still be rejected, but the violation would
   be the generic `"Transition X -> Y is not allowed"`, which violates
   FR-002 (must name `force=True`) and forces every consumer to know the
   family by heart. It also conflates "this transition is forbidden in
   any direction" with "this transition requires force".
2. **Auto-promote `force=True` inside the validator** when the pair
   matches the family. Rejected. The validator is documented as a pure
   checker that never mutates payload state and never raises (NFR-005).
   Auto-promotion would be done by the emitter (CLI), not the validator
   — and that is Phase 2 of the operator brief, in a different
   repository.
3. **Raise an exception from the validator.** Rejected. The validator's
   contract is explicit: return a `TransitionValidationResult`, never
   raise on business-rule violations. Changing that contract is a
   wire-shape change for consumers that wrap validator output.

## Decision 2 — Wording of the violation message

**Decision**: `"review-rejection rollback {from} -> {to} requires force=True"`,
where `{from}` and `{to}` are the literal `Lane` enum values
(`in_progress`, `for_review`, `in_review`, `approved`, `planned`).

**Rationale**: Contains both `force=True` (FR-002 substring) and the
canonical phrase `review-rejection` so consumers can route on family
membership without re-deriving it. The `from -> to` arrow matches the
existing matrix-violation wording for grep continuity.

**Alternatives considered**:

- `"force=True required for backward transition to planned"` — drops
  family naming; consumers cannot route on "review-rejection".
- `"missing force"` — too terse; collides with other lanes that might
  need force in the future.

## Decision 3 — Whether to bump `_ALLOWED_TRANSITIONS`

**Decision**: Leave `_ALLOWED_TRANSITIONS` as-is. The four family pairs
stay listed so that the matrix check accepts the **forced** cases via
the existing flow once the explicit guard short-circuits on `force=True`.

**Rationale**: Minimum-diff change; no risk of breaking unrelated tests
that enumerate the matrix.

## Decision 4 — Fixture coverage shape

**Decision**: For each of the four family pairs, ship one VALID fixture
(force=True, reason populated, review_ref optional but populated by
default for the recommended canonical shape) and one INVALID fixture
(force=False, review_ref AND reason populated to isolate `force=True` as
the missing element).

**Rationale**: FR-007 and FR-008 require coverage per pair. Populating
the optional fields in the INVALID fixtures is what makes the new test
truly prove the family-guard fires; otherwise the existing
missing-`review_ref` guard could be the actual cause and the new guard
would be silent.

**Alternatives considered**:

- One INVALID fixture per pair with only force=False (no other fields).
  Rejected — the existing `review_ref` guard would mask the test; we
  could not tell from fixture metadata alone which guard fired.

## Decision 5 — Documentation surface to update

**Decision**: Update two places:

1. The "Unforced backward transitions are contract-invalid" section of
   `src/spec_kitty_events/status.py` module docstring — replace
   "via the lane matrix check" with the explicit family-guard mechanism
   name.
2. The "Wire requirements" / "Unforced backward invalid" sections of
   `docs/consumer-contract-dossier-v2.4.0.md` — align wording to match.

**Rationale**: Per FR-006, docs must point at the actual enforcement
point. The consumer-contract dossier is the public-facing surface; the
module docstring is the library-facing surface.

**Out of scope**: Anything in `CHANGELOG.md`, `RELEASE_NOTES.md`,
`COMPATIBILITY.md`. Release artifacts are operator-controlled; this
mission drafts a release-note block in `quickstart.md` but does not
publish.

## Open questions

None.

## Compatibility analysis (per charter "compatibility review" policy)

- **Wire shape**: unchanged.
- **JSON Schema**: regenerated schema should be byte-equivalent for
  `StatusTransitionPayload`. Schema-drift test will assert this.
- **Replay corpora**: forced rewinds remain valid; unforced rewinds were
  already documented as invalid and were already classified as
  business-rule rejections by SaaS — no SaaS regression expected.
- **Library version**: a patch bump (`5.1.0 → 5.1.1`) is the
  recommended downstream action but is not landed by this mission.
