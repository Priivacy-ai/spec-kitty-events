# Phase 0 Research — Executable Event Timestamp Semantics

## R-01: Naming the consumer-side receipt-time slot

**Decision**: The contract documents `received_at` as the canonical name for a consumer-owned receipt/import-time concept. It is NOT added to the wire envelope. It is named only in human-readable contract documentation (`Event` model docstring, `kitty-specs/teamspace-event-contract-foundation-01KQHDE4/data-model.md`, this mission's `data-model.md`) and is referenced by the conformance helper signature for documentation purposes only.

**Rationale**: The spec's C-002 forbids changing the wire identifier and C-005 forbids adding new envelope fields in this mission. Documenting `received_at` by name (without adding it to the envelope) gives downstream repos one canonical recommendation so each consumer does not invent its own naming. `received_at` matches the bug brief's suggested shape in `start-here.md` §1.

**Alternatives considered**:
- `import_time`, `ingest_time`, `server_time`: each is overloaded with specific consumer concerns (durable drain, server clock). `received_at` is neutral.
- Adding `received_at` to the envelope itself: rejected because consumer receipt time genuinely is consumer-owned data and varies by consumer; encoding it on the wire would require every producer to know when its consumer received the event.

## R-02: Public surface for the conformance helper

**Decision**: Export `assert_producer_occurrence_preserved` and the typed `TimestampSubstitutionError` from `spec_kitty_events.conformance` (extending `src/spec_kitty_events/conformance/__init__.py`'s `__all__`). The implementation lives at `src/spec_kitty_events/conformance/timestamp_semantics.py`.

**Rationale**: The conformance subpackage already groups every other reusable consumer-side assertion (`assert_payload_conforms`, `assert_payload_fails`, `assert_lane_mapping`). Co-locating keeps the public import shape consistent and avoids exposing a new top-level subpackage.

**Alternatives considered**:
- Top-level `spec_kitty_events.timestamp_semantics`: rejected; helpers belong with helpers.
- Method on `Event`: rejected; the assertion is consumer-side (compares an external value to the envelope), not envelope-side.

## R-03: Detecting `timestamp` description drift

**Decision**: Reuse the existing committed schema generation/drift check. When the Pydantic `Event.timestamp` `description=` argument changes, the regenerated `event.schema.json` (or the per-payload schema files under `src/spec_kitty_events/schemas/`) must be regenerated and committed. The drift check fails CI if regeneration is skipped.

**Rationale**: The charter already requires committed schema generation checks (`Quality Gates: pytest, committed schema generation checks, and mypy --strict`). We do not introduce a new mechanism; we exercise the existing one.

**Alternatives considered**:
- Add a custom lint to fail when a `*timestamp*` field is renamed: rejected as out of scope and brittle; we encode the same intent in the contract docs (FR-002) and via the conformance helper.

## R-04: Encoding "old producer, recent receipt" in a fixture deterministically

**Decision**: Fixtures use fixed ISO-8601 dates. Producer `timestamp` = `2026-01-01T00:00:00+00:00`. Receipt-time annotation (a sibling JSON metadata field, not part of the envelope) = a fixed recent date documented in the fixture, far enough after producer time to be material (per FR-005, at least 30 days apart). No real `datetime.now()` is captured at fixture-load time, preserving determinism (NFR-001) and aligning with the existing fixture convention.

**Rationale**: The existing conformance fixture framework expects deterministic JSON payloads; capturing real now() at load time would be non-reproducible and would break the schema drift envelope.

**Alternatives considered**:
- Compute `now()` inside the test: rejected, breaks NFR-001 determinism.
- Use only producer time and leave receipt time implicit: rejected; FR-005 requires the fixture pair to be machine-readable as both producer AND receipt time so consumer tests can construct the substitution scenario.

## R-05: Typed error for substitution

**Decision**: `TimestampSubstitutionError` is a `Exception` subclass with three attributes: `field_name: str`, `expected: datetime`, `actual: datetime`. Its `__str__` formats a human-readable message naming the canonical contract rule. The helper raises it directly (not via `pytest.fail`), so a consumer can run the helper outside pytest.

**Rationale**: FR-007 requires a typed error (not a bare assertion or string). FR-008 says the helper does not require a receipt-time field; raising a typed error keeps the helper neutral to consumer test framework choice and lets consumers catch the type.

**Alternatives considered**:
- `AssertionError` subclass: rejected; couples the helper to assertion semantics and is harder for non-pytest callers to handle.
- Returning a result object: rejected; convention in this package's other `assert_*` helpers is to raise on failure.

## R-06: Test fixtures for the "good consumer" and "bad consumer" paths

**Decision**: Two committed fixtures + a third "live event" fixture where producer time equals receipt time (edge case from the spec):
- `valid/old_producer_recent_receipt.json` — base case for FR-005.
- `valid/live_event_producer_equals_receipt.json` — equality edge case; the helper must accept this (edge case in spec).
- `invalid/consumer_substituted_receipt_time.json` — fixture where the "consumer-persisted occurrence time" key was replaced with the receipt-time value; the helper must reject this and raise `TimestampSubstitutionError`.

**Rationale**: Three fixtures exercise the three behavioural branches from FR-006/FR-007/FR-008 and the equality edge case from spec Edge Cases.

**Alternatives considered**:
- Single fixture with parameterized "consumer-side persisted value": rejected; explicit fixture files are easier to grep, version, and reuse across consumer repos.

## R-07: CHANGELOG entry

**Decision**: Add a "5.1.0 (unreleased)" or similarly named entry (whichever matches the current CHANGELOG style) describing the strengthened timestamp semantics, the new conformance helper, and a one-paragraph migration note for consumers that may have been using receipt time as canonical occurrence time. No version bump policy change; this mission is additive (C-001).

**Rationale**: FR-011 mandates the CHANGELOG entry; we follow the existing file's style and avoid changing the package version unless the maintainer wants to publish.

**Alternatives considered**: none material.
