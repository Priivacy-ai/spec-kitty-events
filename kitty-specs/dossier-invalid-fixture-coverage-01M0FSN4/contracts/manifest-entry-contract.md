# Contract: Fixture Manifest Entry

This mission introduces no new API, event, or webhook contract. The one contract worth stating explicitly — since it was the central finding of the post-spec adversarial review — is the internal registration contract between a fixture *file* and its `manifest.json` *entry*, enforced by `src/spec_kitty_events/conformance/loader.py`'s `load_fixtures()`.

## Contract

For a fixture to be exercised by the conformance suite (`test_valid_fixture_passes_conformance`, `test_invalid_fixture_fails_conformance`, and any other consumer of `load_fixtures("dossier")`), it MUST have a corresponding object in the `fixtures` array of `src/spec_kitty_events/conformance/fixtures/manifest.json` with this shape:

```json
{
  "id": "<kebab-case-unique-id>",
  "path": "dossier/invalid/<filename>.json",
  "event_type": "<one of the 4 MissionDossier* event type strings>",
  "expected_result": "invalid",
  "notes": "<names the exact field and rule broken, e.g. 'X is Y — violates Z'>",
  "min_version": "2.4.0"
}
```

- `path` is relative to the `fixtures/` directory and must exactly match the fixture file's real location — `load_fixtures()` filters entries by `path.startswith(category + "/")` and then opens that exact path.
- `expected_result: "invalid"` tells the parametrized test which assertion direction to apply (must fail `validate_event()`), as opposed to `"valid"` (must pass).
- Dropping a JSON file into `fixtures/dossier/invalid/` with **no** matching manifest entry is silently inert — no test discovers it, no test fails, nothing signals the gap. This is the failure mode this mission's FR-003 and NFR-002 exist to prevent.

## This mission's two new entries

See `data-model.md`'s "Entity: Manifest entry" table for the exact `id`/`path`/`notes` values for both new fixtures.
