# Quickstart: Dossier Invalid Fixture Coverage

## Verify the current gap (before this mission's changes)

```bash
python3 -c "
import json
m = json.load(open('src/spec_kitty_events/conformance/fixtures/manifest.json'))
invalid = [e for e in m['fixtures'] if e['path'].startswith('dossier/invalid/')]
print(len(invalid), 'invalid dossier fixtures:', [e['event_type'] for e in invalid])
"
# Expect: 3 invalid dossier fixtures, event types MissionDossierArtifactIndexed (x2), MissionDossierParityDriftDetected (x1)
```

## Add a new fixture (repeat once per fixture)

1. Write the fixture JSON under `src/spec_kitty_events/conformance/fixtures/dossier/invalid/<name>.json` — a minimally-modified copy of a valid sibling fixture with exactly one field broken (see `data-model.md`).
2. Add a matching entry to `src/spec_kitty_events/conformance/fixtures/manifest.json` (see `contracts/manifest-entry-contract.md` for the exact shape).
3. Locally confirm the fixture genuinely fails validation before committing:
   ```bash
   python3 -c "
   import json
   from spec_kitty_events.conformance.validators import validate_event
   payload = json.load(open('src/spec_kitty_events/conformance/fixtures/dossier/invalid/<name>.json'))
   result = validate_event(payload, '<EventType>')
   assert not result.is_valid, 'Fixture did not fail validation — pick a real constraint violation'
   print('OK — fails as expected:', result.violations)
   "
   ```

## Update the count gates (once, after both fixtures exist)

In `tests/test_dossier_conformance.py`:
- `test_dossier_fixture_count`: `13` → `15`
- `test_dossier_invalid_case_count`: `3` → `5`
- `test_dossier_valid_case_count`: unchanged at `10`

## Run the suite

```bash
pytest tests/test_dossier_conformance.py -v
```

Expect all previously-passing tests to still pass, plus the two new fixtures to appear as new parametrized cases in `test_invalid_fixture_fails_conformance` (no new test function needed).
