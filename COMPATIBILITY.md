# Compatibility Guide

**Current package version**: `9.1.3`

The on-wire envelope schema version is `3.0.0` and has been unchanged since
the cutover. The package version and the envelope schema version move
independently — see
[`contracts/versioning-and-compatibility.md`](contracts/versioning-and-compatibility.md).

`spec-kitty-events` is a fail-closed contract package. Released sections
below are ordered newest-first by the release that introduced them. An
unreleased `## Known gap (not yet closed)` section documents a gap no
release has closed yet; it carries no version number and precedes every
released section, regardless of when the gap it describes will close.

> The single declaration above is the only place this document states the
> package version; `tests/test_compatibility_doc.py` pins it to
> `spec_kitty_events.__version__`. Do not restate it in prose.

This document is the public compatibility policy for consumers of:

- `spec-kitty-events`
- `spec-kitty-saas`
- `spec-kitty`

## Known gap (not yet closed) — `to_zeitgeist_attrs` does not yet reject control characters on encode

`from_zeitgeist_attrs` rejects an attrs value carrying a non-printable
character on decode (`str.isprintable()`, EXPERIMENTAL-spec-kitty-events#25,
then widened by #63), but `to_zeitgeist_attrs` does not yet run the same
check on encode (EXPERIMENTAL-spec-kitty-events#64): a producer can
successfully encode and broadcast an attrs value carrying a control
character that a consumer's decode will then reject, silently dropping the
moment. The fix — both directions sharing one predicate and raising the
same typed `ZeitgeistAttrsControlCharacterError` — is open as
EXPERIMENTAL-spec-kitty-events#104 and not yet merged to `main`. This
section is written ahead of that merge so the documentation gap doesn't
reopen once it lands; it becomes a normal dated-version entry, and this
"known gap" framing goes away, when #104 merges.

## `9.1.3` — encode rejects unknown Ops Invocation contract versions

`9.1.3` tightens `to_zeitgeist_attrs` for every contract-versioned event
type. Before encoding, it checks the payload's `contract_version` against
the same `KNOWN_CONTRACT_VERSIONS_BY_EVENT_TYPE` table used by
`from_zeitgeist_attrs`. A producer that mis-stamps version `1` payloads with
an unknown version now fails locally with `UnknownContractVersionError`
rather than emitting a frame this same package version discards on decode.
Known-version frames are unaffected.

## `9.1.2` — derived `detail_ref` attrs must resolve to their own moment

`9.1.2` tightens `from_zeitgeist_attrs` for the Ops Invocation event types.
Their `detail_ref` attr is mechanically derived as
`"<event_type>:<event_id>"`, so decode now rejects a wire frame whose
`detail_ref` points at another event or uses an unrelated value. Frames
produced by this package are unaffected; only malformed inbound frames that
previously decoded are rejected.

## `9.1.1` — timestamp parsing normalized across supported Python versions

`9.1.1` is a parser bug fix, not a new event family or payload field. The
strict envelope validator, retrospective timestamp validation, and packaged
timestamp conformance helper now normalize supported ISO-8601 spellings
before calling `datetime.fromisoformat`, so Python 3.10 accepts the same
fractional-second precision, basic format, reduced precision, and numeric
offset spellings that Python 3.11+ already accepted. No producer or consumer
migration is required.

## `9.0.2` — mixed-case doubled `Z` UTC designators are rejected

`9.0.2` tightens timestamp validation at three normalization sites:
`strict.validate_strict_envelope`, the retrospective payload validators, and
the packaged conformance timestamp helper. A malformed value ending in `zZ`
is now rejected instead of being normalized to a lowercase-`z` form that some
supported Python interpreters accept. Producers already sending one valid UTC
designator are unaffected.

## `9.0.1` — `zeitgeist_ref_for` rejects control characters in the derived ref

`9.0.1` tightens the producer-side reject boundary for volatile moments.
`zeitgeist_ref_for` now applies the same `str.isprintable()` check as attrs
values to its derived `ref`, so a control or formatting character in a ref
source such as `mission_slug`, `mission_id`, `run_id`, or
`decision_point_id` raises `ZeitgeistAttrsControlCharacterError` instead of
reaching the relay. Producers with printable refs are unaffected; producers
that previously relied on non-printable ref values must clean or reject those
values before calling the codec.

## `9.0.0` — `mission_id` widened onto `WPStatusChanged`/`MissionCreated`/`MissionClosed` for cross-family join (breaking)

`9.0.0` is a **breaking accept/decode-boundary change**, not additive,
despite the Pydantic-model diff itself being a new optional field.
`PhaseEnteredPayload` has always used `mission_id` (required) as its
`REF_FIELD_BY_EVENT_TYPE` frame ref, while the other three mission-scoped
volatile families — `WPStatusChangedPayload` (`StatusTransitionPayload`),
`MissionCreatedPayload`, and `MissionClosedPayload` — use `mission_slug` as
their ref. Until this release, `StatusTransitionPayload` and
`MissionClosedPayload` did not declare `mission_id` at all, so
`from_zeitgeist_attrs`'s closed, schema-derived key vocabulary
(`_schema_keys_for_model`) never admitted it for either family: an attrs
frame carrying `mission_id` for a `WPStatusChanged` or `MissionClosed`
moment raised `ZeitgeistAttrsError` on decode. A consumer therefore had no
shared key to join one of their moments against a `PhaseEntered` moment for
the same mission aggregate — and, symmetrically, no way to receive one
without it being rejected.

This release adds an optional `mission_id` field (default `None`) to
`StatusTransitionPayload` and `MissionClosedPayload`; when a producer
populates it, `mission_id` rides alongside `mission_slug` in the encoded
`to_zeitgeist_attrs` projection for all three families. Per
[`EXPERIMENTAL-spec-kitty-planning`#1012](https://github.com/spec-kitty/EXPERIMENTAL-spec-kitty-planning/issues/1012),
this is Option 2: `REF_FIELD_BY_EVENT_TYPE` itself is unchanged —
`PhaseEntered`'s ref stays `mission_id` and the other three keep
`mission_slug` as their ref — only the attrs widen.

**Why this is major, not minor.** Per
[`contracts/versioning-and-compatibility.md`](contracts/versioning-and-compatibility.md),
"any change to an existing event contract that makes a previously-rejected
envelope accepted" is major. A producer that starts populating `mission_id`
on `WPStatusChanged`/`MissionClosed` moves those two families' encoded
attrs from a shape every `<9.0.0` decode rejected to one every `>=9.0.0`
decode accepts — the accept/reject boundary moved, which is exactly the
"new capability that widens an existing family's contract" case the
`6.1.0` new-event-type precedent does *not* cover (a whole new event type
is additive because no existing contract's boundary moves; this is the
opposite: an existing family's own boundary moves). `MissionCreatedPayload`
is excluded from this classification — it already declared `mission_id`
before this release (prior, unrelated work), so its decode boundary
already admitted the key and this bump changes nothing about its
compatibility story.

**Producers that omit `mission_id` are unaffected**: the field stays
optional and is omitted from attrs when absent, so a producer that never
populates it is wire-compatible with every `<9.0.0` consumer, exactly as
before. The breaking surface is scoped entirely to producers that *do*
populate the field.

**Required migration.**

- Consumers (`spec-kitty-saas`, `spec-kitty`, any other reader of
  `WPStatusChanged`/`MissionClosed` zeitgeist attrs) must bump their
  `spec-kitty-events` pin to `>=9.0.0` before a producer in their path
  starts populating `mission_id` on these two families.
- Producers MUST capability-gate the rollout exactly like the `6.0.0`
  `genesis`-lane precedent (see
  [`contracts/lane-vocabulary.md`](contracts/lane-vocabulary.md)'s
  "Versioning" section): do not populate `mission_id` on
  `WPStatusChanged`/`MissionClosed` for a given broadcast until every
  consumer that will read it is known to be on `>=9.0.0`. Populating it
  while any live consumer is still pinned `<9.0.0` causes that consumer's
  `from_zeitgeist_attrs` call to raise on decode, silently dropping the
  moment.
- `EXPERIMENTAL-spec-kitty-events#69` closes with this artifact set;
  `EXPERIMENTAL-spec-kitty-events#197`/`#198` track the two MINOR
  documentation/conformance-coverage follow-ups the squad also filed
  against the originating PR.

## `8.2.1` — forbidden attrs rejected in every dot segment (breaking boundary shipped without a major bump)

PR
[`EXPERIMENTAL-spec-kitty-events#139`](https://github.com/spec-kitty/EXPERIMENTAL-spec-kitty-events/pull/139)
widened `_forbidden_key_hits` on both `to_zeitgeist_attrs` encode and
`from_zeitgeist_attrs` decode. The old predicate rejected an exact forbidden
key and a forbidden trailing segment, but missed the same name in a prefix or
middle segment. Consequently `token.sub`, `url.href`, `team.name`, and
`a.token.b` previously passed; starting at implementation commit `d18a67a`
(merge commit `1e21a29`) each is rejected because at least one dot-separated
segment belongs to `FORBIDDEN_ATTR_KEYS`.

This is a **breaking reject-boundary widening**, not an additive validation
improvement. `contracts/versioning-and-compatibility.md` explicitly classifies
"adding to the forbidden-key set, or widening where it is enforced" as major:
a producer or consumer can move from accepting an identical attrs frame to
raising the existing forbidden-key error solely by updating this package.
The behavior is intentional and security-motivated; forbidden names include
`token`, `authorization`, `bearer`, `password`, `url`, and team/deployment
identifiers that must not leak into broadcast attrs.

**Historical version boundary.** The package declared `8.2.1` at `1e21a29`.
That version number had already been used at earlier trees, so `8.2.1` alone
cannot identify whether this rule is present: exact git pins before `1e21a29`
lack it, while pins at or after that merge contain it. The later `9.0.0`
release records a separate `mission_id` accept-boundary widening; it does not
retroactively make PR #139 a correctly-versioned 9.0.0 change. This section
documents the shipped boundary rather than rewriting package history.

**Required migration.** Before moving a consumer or producer pin across
`1e21a29`, inspect every emitted and stored zeitgeist attrs key. Rename or
remove a key when any dot-separated segment matches `FORBIDDEN_ATTR_KEYS`;
do not bypass or weaken the guard. Consumers already pinned to current
`9.0.0` have this rejection behavior.

## `8.0.0` — Sync, legacy-envelope, and cutover surfaces deleted

`8.0.0` deletes three modules whose only consumer was the offline
CLI→SaaS sync/replay story that the programme retired:

- `spec_kitty_events.sync` (Sync lifecycle contracts + reducer) — had no
  production consumers.
- `spec_kitty_events.legacy` (`legacy_envelope_v1` normalizer).
- `spec_kitty_events.cutover` (`CUTOVER_ARTIFACT` and helpers).

Consumer-visible consequence beyond the missing imports: `validate_event()`
no longer applies the envelope-level cutover gate. An envelope with a
missing or non-canonical `schema_version`, or one carrying forbidden legacy
keys/names at envelope level, can now pass `validate_event` when its payload
shape validates. Fail-closed envelope validation still exists as the opt-in
strict profile — `validate_strict_envelope()` enforces
`schema_version == "3.0.0"`, the recursive forbidden-key walk
(`forbidden_keys.find_forbidden_keys`), the full envelope key set, and the
forbidden legacy aggregate-name prefixes (`strict.FORBIDDEN_LEGACY_AGGREGATE_NAMES`,
re-homed from the deleted artifact per issue #10).
Producers and ingress paths that relied on `validate_event` for the gate
must switch to the strict profile.

That switch is a single call only for the event types
`spec_kitty_events.strict.STRICT_EVENT_TYPES` admits (the fixed
lifecycle/WP/project/harness allowlist) — `validate_strict_envelope()`
rejects every other event type with `UNKNOWN_EVENT_TYPE` regardless of
whether the envelope is otherwise well-formed. Callers whose event type is
outside that allowlist must reproduce the removed gate's checks directly
instead: `forbidden_keys.validate_no_forbidden_keys(record,
forbidden=FORBIDDEN_LEGACY_KEYS) is None` for the recursive legacy-key walk
(callers needing every error rather than just the first can use
`list(forbidden_keys.find_forbidden_keys(record,
forbidden=FORBIDDEN_LEGACY_KEYS))` instead), an
explicit `record.get("schema_version") == "3.0.0"` check for the envelope
signal, `(not isinstance(aggregate_id := record.get("aggregate_id"), str)) or
aggregate_id.split("/", 1)[0] not in strict.FORBIDDEN_LEGACY_AGGREGATE_NAMES`
for the forbidden legacy aggregate-name prefix, and
`record.get("event_type") not in {"FeatureCreated",
"FeatureClosed"}` for the forbidden legacy event names (see `## Forbidden
Legacy Surfaces` below for that list's source). The `isinstance` guard on
the aggregate-name check matters: a wire record can carry `aggregate_id:
null` or another non-string, and `strict.py`'s own gate
(`isinstance(aggregate_id, str)`) treats that as not-forbidden rather than
raising, so a recipe that instead does `record.get("aggregate_id",
"").split(...)` raises `AttributeError` on exactly that input instead of
reproducing the gate. Unlike the other three checks, no package constant
survives for the legacy event names — they were deleted outright in
`8.0.0` and not re-homed — so this document is the only place a caller
outside the strict profile can find them.

Migration: pin `>=8.0.0`; delete or re-home any import of the three
modules. There are no aliases. See `CHANGELOG.md` (`### Breaking`) for the
full removed-name list.

## `7.0.0` — Strict journal profile + HarnessObservation

`7.0.0` publishes `spec_kitty_events.strict.validate_strict_envelope`: an
opt-in, deterministic, structured validator over the existing envelope and
lifecycle/WP contracts (`Event` itself is unchanged and stays lenient — see
`### Breaking` below for what *is* newly rejected by the strict profile).
It also publishes `spec_kitty_events.harness_observation`: a new, volatile
`HarnessObservation` event family with exactly six payload IDs
(`harness.presence.v1`, `harness.lane_signal.v1`, `harness.focus_started.v1`,
`harness.focus_heartbeat.v1`, `harness.focus_paused.v1`,
`harness.focus_ended.v1`). Observations are never reduced into mission/WP
state and carry no time/TTL/user/team field.

The machine-readable **support matrix** —
`spec_kitty_events.strict.SUPPORT_MATRIX` / the published
`support_matrix.json` package-data copy, generated by `schemas/generate.py`
and drift-checked alongside every other schema — is the authority for
"which payload IDs / event types this package supports": 14 journal rows,
16 volatile rows (the Ephemeral Team Status vocabulary — `WPStatusChanged`,
`MissionCreated`, `MissionClosed`, `PhaseEntered`, the six `mission_next`
mission-run types — plus 6 observation rows, one per `ObservationKind`,
each with its payload ID). See the `[8.0.0]` CHANGELOG section for the
E2 durability promotion and the `zeitgeist_attrs` codecs.
`spec_kitty_events.strict.support_matrix_digest()` is what downstream
candidates pin in `declared_dependency_contracts` (see
`tests/test_support_matrix.py` for the pinned row/payload-ID counts; the
row contents are not restated here per the anti-restatement rule below).

Skew story (6.x ↔ 7.0):

- a 6.x consumer calling `validate_event(payload, "HarnessObservation")`
  raises `ValueError("Unknown event type: ...")` — fail closed, unchanged
  API shape;
- a 6.x consumer given a 7.0 `MissionStarted` payload that carries the new
  optional `mission_slug` field still accepts it (the 6.x model is lenient)
  — benign forward-compat;
- a 7.0 consumer rejects a `MissionStarted` payload carrying an unknown
  extra field with `PAYLOAD_SCHEMA_FAIL` (new in `7.0.0`; the four-field
  shape with no `mission_slug` remains valid, since the field is optional).

Local-appender canonicalization debt (out of scope for this release):
every envelope written today by
`spec-kitty/src/specify_cli/status/lifecycle_events.py`'s `_build_envelope`
(`.kittify/canonical-events.jsonl`, `status.events.jsonl`) fails the strict
profile on multiple counts (`schema_version="5.0.0"`, an extra
`aggregate_type` key, several missing envelope keys) and its
`ReviewerSelfApproval` rows additionally have no events model. This
package does not rewrite those rows; local-CLI permissive reading of them
is unweakened. Canonicalizing the appender is out of scope for this
release (tracked for the journal-writer work that consumes this contract).

## Canonical On-Wire Policy

Note: the **envelope schema on the wire** is at version `3.0.0`, which is not
the package version declared at the top of this document. The two are
intentionally distinct (see the bump-rationale section below).

- Signal field: `schema_version`
- Signal location: event envelope
- Required value: `3.0.0`

Since `8.0.0` removed the cutover artifact, this gate is enforced by the
strict profile (`validate_strict_envelope`) and by the recursive
forbidden-key walker (`spec_kitty_events.forbidden_keys`), not by
`validate_event`. Live ingestion paths fail closed when any of the
following are true:

- the envelope is missing `schema_version`
- `schema_version` does not equal `3.0.0`
- the envelope or nested payload contains forbidden legacy keys (recursive walk)
- `aggregate_id` uses a forbidden legacy aggregate name (`feature`,
  `feature_catalog`) — rejected with `FORBIDDEN_AGGREGATE_NAME`

## Forbidden Legacy Surfaces

Legacy mission-domain surfaces rejected on live paths (as of `8.0.0`, by
the strict profile / forbidden-key walker rather than `validate_event`):

- keys: `feature_slug`, `feature_number`, `mission_key`, `legacy_aggregate_id`
  — rejected at any depth by `forbidden_keys.find_forbidden_keys`.
- event names: `FeatureCreated`, `FeatureClosed` — not members of
  `STRICT_EVENT_TYPES`, so the strict profile rejects them.
- aggregate name prefixes: `feature`, `feature_catalog` — the dedicated
  prefix check shipped with the cutover artifact and left `validate_event`
  with it in `8.0.0`; it was deliberately **re-homed onto the strict
  profile** (`strict.FORBIDDEN_LEGACY_AGGREGATE_NAMES`, error code
  `FORBIDDEN_AGGREGATE_NAME`) rather than dropped, so a live path that
  validates strictly still fails closed on `aggregate_id="feature/WP01"`
  (issue #10). `validate_event` stays lenient; offline rewrite jobs should
  still convert such ids.

## Canonical Mission And Build Taxonomy

Public mission-domain payloads use:

- `mission_slug`: canonical mission instance identifier
- `mission_number`: canonical numeric mission identifier
- `mission_type`: canonical workflow/template identifier

Event envelopes distinguish build and node identity explicitly:

- `build_id`: emitting build identifier
- `node_id`: emitting node identifier within that build

## Rollout Policy

There are no runtime compatibility bridges in live ingestion.

- New producers must emit canonical envelopes (`schema_version="3.0.0"`) from day one.
- Consumers must reject legacy mission-domain envelopes on live paths.
- Historical `2.x` or pre-cutover data may only be read by offline migration or rewrite jobs.
- Offline rewrite workflows must convert historical data into canonical `schema_version="3.0.0"` form before re-ingestion.

## Cross-Repo Release Gates

`spec-kitty-events` should only be treated as released when all of the following are true:

1. `spec-kitty-events` package metadata matches the version declared at the top of this document.
2. Committed JSON Schemas are regenerated and drift-free.
3. Conformance fixtures and replay goldens pass with artifact-driven validation.
4. `spec-kitty-saas` is updated to emit canonical envelopes (`schema_version="3.0.0"`) only.
5. `spec-kitty` is updated to consume canonical mission/build terminology and fail-closed validation outcomes.

## Consumer Guidance

If you operate a producer:

- emit `schema_version="3.0.0"` (see the note above)
- emit `build_id`
- emit canonical mission-domain fields only

If you operate a consumer:

- validate the envelope signal before processing payload content
- reject forbidden legacy mission-domain fields and names
- treat pre-cutover data as migration input, not live traffic

## Quick Reference

Accepted live envelope:

```json
{
  "event_type": "WPStatusChanged",
  "aggregate_id": "mission/WP01",
  "schema_version": "3.0.0",
  "build_id": "build-2026-04-05",
  "node_id": "runner-01",
  "payload": {
    "mission_slug": "mission-001",
    "wp_id": "WP01",
    "from_lane": "planned",
    "to_lane": "claimed",
    "actor": "ci-bot",
    "execution_mode": "worktree"
  }
}
```

Rejected live envelope examples:

- envelope without `schema_version`
- envelope with `schema_version="2.9.0"`
- payload containing `feature_slug`
- envelope with `event_type="FeatureCreated"`
- envelope with `aggregate_id="feature/123"`

## Versioning

The on-wire envelope schema is `3.0.0`; the package version is declared at the
top of this document. Together they publish the canonical mission/build contract
and the recursive forbidden-key gate.

The full policy — what requires a major bump, what artifacts a bump must update,
and why the two version numbers are distinct — lives in
[`contracts/versioning-and-compatibility.md`](contracts/versioning-and-compatibility.md).

- `2.x` additive compatibility language no longer applies.
- Future breaking contract changes require a new major **package** release; whether they also bump the envelope schema version depends on whether they change the wire format. Neither the `5.0.0` nor the `6.0.0` package release bumped the wire-format envelope version — both changed contract behaviour with the existing `3.0.0` envelope shape.

### Post-mission lifecycle events (6.1.0)

The `6.1.0` release is **additive and wire-compatible**. It adds the
`MissionReopened` and `FollowUpRecorded` contracts, the
`MissionStatus.REOPENED` enum member (actionable, not terminal), and their
handling in `reduce_lifecycle_events`. The envelope shape is unchanged, but
consumers that validate or switch on exact event types must be upgraded before
they receive either new type. Producers must capability-gate emission until
each intended consumer recognizes it. Consumers that never receive the new
types are unaffected.

Producers emitting post-mission lifecycle facts need `>=6.1.0`.

### Genesis lane (6.0.0)

The `6.0.0` package release adds the `genesis` canonical lane (a non-display,
pre-finalize origin state; see `CHANGELOG.md`). Like `5.0.0`, this is a major
**package** bump that intentionally does **not** bump the wire-format envelope
version — it widens the set of accepted `Lane` values (`from_lane="genesis"` on
`WPStatusChanged`) while keeping the existing `3.0.0` envelope shape. Consumers
on `<6.0.0` will fail-closed (reject) a `from_lane="genesis"` payload; producers
must therefore gate genesis fan-out on the installed package's lane capability
until every consumer is on `>=6.0.0`.

Display consumers must not derive board columns, summary chips, progress rows,
or lane filters from every `Lane` member. Use `DISPLAY_LANES` for ordered
display/summary surfaces and `NON_DISPLAY_LANES` for explicit exclusions;
`Lane.GENESIS` is canonical for validation/replay but is not displayable.

## Local-CLI compatibility vs TeamSpace ingress validity (5.0.0)

The `5.0.0` major release sharpens a distinction that has always been implicit in
`spec-kitty-events`: there are two distinct validity domains, and a row that is
acceptable in one is not necessarily acceptable in the other. This section is the
authoritative explanation. Consumers and producers must read it before assuming
that "valid" is a single global property.

### The two validity domains

- **Local-CLI compatibility.** The `spec-kitty` CLI continues to read historical
  `status.events.jsonl` rows on local disk for users' own bookkeeping —
  reconstructing a mission's history, rendering local dashboards, replaying
  status, computing diff summaries, etc. The CLI's local reader is deliberately
  permissive: it tolerates pre-cutover envelope shapes (including legacy keys
  such as `feature_slug`, `mission_key`, raw rows missing `schema_version`, and
  pre-canonical lane vocabularies) so that users do not lose access to their own
  historical data after this bump. Local compatibility is **not** weakened by
  the `5.0.0` release.

- **TeamSpace ingress validity.** Only canonical envelopes pass TeamSpace
  ingress. The ingress path runs the full fail-closed contract gate from
  `4.0.0` plus the additions landed in this mission (canonical lane vocabulary
  including `in_review`, reconciled `MissionCreated`/`WPStatusChanged`/
  `MissionClosed` payloads, and the recursive forbidden-key validator that
  rejects legacy keys at any depth, including inside array elements). A row
  that the local CLI happily reads off disk will be rejected at TeamSpace
  ingress unless it has been canonicalized first.

### Concrete examples

A historical row that is **valid for the local CLI** but **invalid for
TeamSpace ingress** (legacy `feature_slug` key, missing `schema_version`):

```json
{"event_type":"FeatureCreated","aggregate_id":"feature/123","payload":{"feature_slug":"my-feature","feature_number":7}}
```

A canonical envelope that is **valid for both** the local CLI and TeamSpace
ingress (canonical mission-domain fields, canonical lane vocabulary including
`in_review`, `schema_version="3.0.0"`, no forbidden legacy keys at any depth):

```json
{"event_type":"WPStatusChanged","aggregate_id":"mission/WP01","schema_version":"3.0.0","build_id":"build-2026-05-01","node_id":"runner-01","payload":{"mission_slug":"mission-001","wp_id":"WP01","from_lane":"claimed","to_lane":"in_review","actor":"implementer-ivan","execution_mode":"worktree"}}
```

> **Package version vs envelope schema version (read this carefully).**
> The **package version** is the value in `pyproject.toml` and
> `__version__`, declared once at the top of this document. The
> **envelope schema version on the wire** is **`3.0.0`** — the default
> for `Event.schema_version` (and the value the strict profile requires).
> They are not the same number and they do not move together. The major
> package bump from `4.x` to `5.0.0` reflected contract behaviour changes
> (`in_review` canonical, payload reconciliation, recursive forbidden-key
> validator), NOT a wire-format envelope-version bump; `6.0.0`, `7.0.0`,
> and `8.0.0` likewise. Producers must continue to emit
> `schema_version="3.0.0"` on the envelope regardless of the package
> major; the strict profile rejects anything else.

### The documented bridge

The bridge between these two domains is the **CLI canonicalizer** that ships in
`spec-kitty` Tranche B. The canonicalizer reads historical `status.events.jsonl`
rows and produces canonical envelopes (`schema_version="3.0.0"`, accepted by
the strict profile) suitable for ingress. Producers that need to
forward historical data into TeamSpace MUST run it through the canonicalizer
first; ingress will not accept raw historical rows. Consumers that read locally
MUST NOT assume their local-disk rows have already been canonicalized.

### Cross-references

- [`contracts/lane-vocabulary.md`](contracts/lane-vocabulary.md) — the canonical lane vocabulary and the major-bump rule that governs changing it.
- [`contracts/versioning-and-compatibility.md`](contracts/versioning-and-compatibility.md) — what requires a major bump and which artifacts a bump must update.
- [`kitty-specs/teamspace-event-contract-foundation-01KQHDE4/contracts/payload-reconciliation.md`](kitty-specs/teamspace-event-contract-foundation-01KQHDE4/contracts/payload-reconciliation.md) — the reconciliation log for `MissionCreated`, `WPStatusChanged`, and `MissionClosed` payloads.

### Bump rationale (per R-03)

The `5.0.0` package bump is a genuine major bump under semantic versioning.
The envelope schema version on the wire stays at `3.0.0`; only the *package*
moves to `5.0.0`. Per
research item R-03 (schema version bump semantic), each of the following is a
behavior change for at least one role and therefore each independently
justifies a major:

1. **Lane vocabulary widens.** `in_review` is now a canonical lane (FR-001,
   FR-002). Consumers that previously rejected `in_review` as unknown now
   accept it; consumers that switch on exact lane-set membership are
   behaviorally affected.
2. **Payload reconciliation.** `MissionCreatedPayload`,
   `WPStatusChangedPayload`, and `MissionClosedPayload` are now the single
   source of truth (FR-003, FR-004). CLI emission and library models have been
   reconciled; pre-bump producers of disagreeing shapes are now invalid.
3. **Recursive forbidden-key validator.** Legacy keys (`feature_slug`,
   `feature_number`, `mission_key`, plus the audit-derived expansion) are now
   rejected at any depth, including inside array elements (FR-005). Envelopes
   that previously slipped through with a deeply nested legacy key are now
   rejected.

These three changes compound: any one of them is a contract change for at
least one role, and together they require a major bump rather than a minor or
patch.

## Decision Moment V1 (4.0.0)

### Scope

- **Breaking for DecisionPoint.** The `DecisionPoint*` event family (excluding `DecisionPointOverridden`) now carries `origin_surface` and supports discriminated-union payloads. `DecisionPointResolved` (interview variant) requires `terminal_outcome`.
- **Compatible for DecisionInput.** `DecisionInputRequested` and `DecisionInputAnswered` payloads are unchanged. 3.x consumers continue to validate.

### Producer migration

| Producer                | 3.x action                         | 4.0.0 action                                                   |
|-------------------------|------------------------------------|----------------------------------------------------------------|
| ADR DecisionPoint       | Emit 3.x payload                   | Add `origin_surface: "adr"` to every payload                    |
| Interview DecisionPoint | (n/a — didn't exist)               | Use `origin_surface: "planning_interview"` + V1 fields          |
| DecisionInput* events   | Emit as-is                         | No change                                                       |

### Consumer migration

| Consumer                              | 3.x action                                       | 4.0.0 action                                                                 |
|---------------------------------------|--------------------------------------------------|------------------------------------------------------------------------------|
| DecisionPoint replay / reducer        | Reduce 3.x ADR payloads                          | Reduce ADR + V1 interview events via the single reducer (discriminated by `origin_surface`) |
| DecisionInput* consumers              | Consume as-is                                    | No change                                                                    |
| Slack orchestrator                    | (n/a)                                            | Subscribe to `DecisionPointWidened`; post closure message on `DecisionPointResolved` |
| Teamspace projection                  | (n/a)                                            | Project V1 fields from `DecisionPointResolved` interview variant             |

### Terminal outcome / write-back rules

- `DecisionInputAnswered` is emitted ONLY when `DecisionPointResolved.terminal_outcome == "resolved"` AND `final_answer` is populated. Deferred and canceled outcomes do NOT emit a `DecisionInputAnswered` (no answer exists).
- `DecisionPointResolved.closed_locally_while_widened=true` is legal only when a prior `DecisionPointWidened` exists for the same `decision_point_id`. Reducers raise an anomaly (`kind="invalid_transition"`) and project the field as `false` if the precondition is not met.

### No grace period

4.x validators fail closed on missing `terminal_outcome` or missing `origin_surface`. There is no temporary permissive path. Downstream consumers must migrate deliberately against this contract boundary.
