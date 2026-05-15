# Quickstart — Executable Event Timestamp Semantics

## For consumer authors (SaaS, CLI, tracker, hub)

1. Pin or upgrade to a `spec-kitty-events` version that includes
   `assert_producer_occurrence_preserved`.
2. Add a regression test exercising your ingestion path end-to-end and assert producer occurrence preservation:

   ```python
   from datetime import datetime, timezone

   from spec_kitty_events.conformance import (
       assert_producer_occurrence_preserved,
       TimestampSubstitutionError,
       load_fixtures,
   )

   def test_consumer_preserves_producer_occurrence_time():
       # Load a committed "old producer, recent receipt" fixture.
       fixture = load_fixtures(kind="timestamp_semantics").get_valid("old_producer_recent_receipt")
       envelope = fixture["envelope"]

       # Run the actual ingestion path under test.
       my_app.ingest_event(envelope)
       persisted = my_app.lookup_persisted_occurrence_time(envelope["event_id"])

       # Will raise TimestampSubstitutionError if the ingestion path substituted receipt time.
       assert_producer_occurrence_preserved(envelope, persisted)
   ```

3. (Optional) Persist your own receipt time under a clearly named field:

   ```python
   received_at = datetime.now(timezone.utc)
   ```

   Do not use this value for canonical occurrence time, mission age, completed-window membership, or scorecard timestamps.

## For contract maintainers (this repo)

1. Edit `src/spec_kitty_events/models.py` to strengthen the `Event.timestamp` docstring and `description=`.
2. Regenerate the committed JSON Schemas with the existing schema generation tooling so the schema description reflects the new text.
3. Update `kitty-specs/teamspace-event-contract-foundation-01KQHDE4/data-model.md` with Rule R-T-01/02/03.
4. Add fixtures under `src/spec_kitty_events/conformance/fixtures/timestamp_semantics/`.
5. Add `src/spec_kitty_events/conformance/timestamp_semantics.py`.
6. Re-export the helper and error from `src/spec_kitty_events/conformance/__init__.py`.
7. Add `tests/test_timestamp_semantics.py` covering the good and bad consumer paths.
8. Update `CHANGELOG.md`.
9. Run charter quality gates: `pytest`, schema drift check, `mypy --strict`.
