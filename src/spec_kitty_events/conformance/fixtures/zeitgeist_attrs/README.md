# zeitgeist_attrs fixture `event_id` allocation

Every fixture's `event_id` (under `envelope.event_id` or `attrs.event_id`) must
be globally unique across this directory —
`tests/test_zeitgeist_attrs_conformance.py::test_fixture_event_ids_are_unique`
guards it, but only catches a clash once two fixture-adding PRs have both
merged (events#73, events#147: each PR's own blast-radius run only sees its
own fixtures, so two PRs allocating the same id in parallel both pass CI and
only collide on `main`).

Before adding a fixture, find the next free id and update this file in the
same PR:

```
grep -rho --include='*.json' 'e2e00000-0000-4000-8000-[0-9]\{12\}' . | sort -u | tail -1
```

Test-local synthetic envelopes must use the reserved
`e2e00000-0000-4000-8000-9000000000NN` block, never this fixture-allocation
sequence. That keeps the JSON-only grep authoritative by construction.

**Next free id: `e2e00000-0000-4000-8000-000000000209`**
