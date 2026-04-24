# Contract Artifacts — Decision Moment V1

These are planning-phase contract sketches. They are **not** the committed wire schemas. The authoritative JSON Schemas are regenerated from the Pydantic models in `src/spec_kitty_events/` via `src/spec_kitty_events/schemas/generate.py` during implementation and live under `src/spec_kitty_events/schemas/`.

Use these sketches to:

1. Validate the contract shape during plan review before any code is written.
2. Give downstream mission implementers (`spec-kitty#757`, `spec-kitty-saas#110`, `spec-kitty-saas#111`, `spec-kitty#758`) a stable target to build against while the events implementation lands.

Each file below is a JSON Schema fragment (`draft/2020-12`) representing one payload or shared model.

- `participant_external_refs.schema.json`
- `participant_identity_v4.schema.json`
- `summary_block.schema.json`
- `teamspace_ref.schema.json`
- `default_channel_ref.schema.json`
- `thread_ref.schema.json`
- `closure_message_ref.schema.json`
- `decision_point_opened_payload.schema.json` (discriminated union)
- `decision_point_widened_payload.schema.json`
- `decision_point_discussing_payload.schema.json` (discriminated union)
- `decision_point_resolved_payload.schema.json` (discriminated union, with cross-field constraints)
- `decision_point_overridden_payload.schema.json` (3.x + optional origin_surface)
