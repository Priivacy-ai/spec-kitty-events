# Contract: Payload Reconciliation

**Mission**: `teamspace-event-contract-foundation-01KQHDE4`
**Source spec FRs**: FR-003, FR-004, C-002, C-004 · **Research**: [research.md R-02](../research.md#r-02--reconciliation-direction-for-missioncreated-wpstatuschanged-missionclosed)

## Rule

The events package's typed payload models are the **single source of truth** for `MissionCreated`, `WPStatusChanged`, and `MissionClosed` payloads. CLI and SaaS producers must conform to these models. Where historical or legacy emissions diverge, the **CLI canonicalizer** (Tranche B in `spec-kitty`) is the transformation layer; the events package itself does not widen to accept legacy fields.

## Per-event-type contract

### `MissionCreated`

The authoritative model is `MissionCreatedPayload` in `src/spec_kitty_events/lifecycle.py`. The work-package-phase reconciliation:

1. Read the current `MissionCreatedPayload` definition.
2. Read the current CLI emission site(s) for `MissionCreated`.
3. Diff the field set.
4. For each divergent field, decide: **retain in canonical** (update CLI to emit), or **drop** (update CLI to stop emitting). The decision is recorded in this contract's "Reconciliation log" (a section appended during the WP).
5. Update CLI emission to conform.
6. Regenerate `mission_created_payload.schema.json`.

### `WPStatusChanged`

The authoritative model is `StatusTransitionPayload` in `src/spec_kitty_events/status.py`. Reconciliation follows the same diff-decide-update pattern as `MissionCreated`, with the additional concrete change that the lane vocabulary now includes `in_review` (so `from_lane` and `to_lane` accept it).

### `MissionClosed`

The authoritative model is `MissionClosedPayload` in `src/spec_kitty_events/lifecycle.py`. The spec calls out that current CLI emission and `MissionClosedPayload` "appear to disagree." The reconciliation work package:

1. Identifies every field the CLI currently emits in its `MissionClosed` envelope.
2. Identifies every field declared in `MissionClosedPayload`.
3. For each field in the symmetric difference, decides retain-or-drop with a written rationale.
4. Updates the CLI emission code (Tranche A in `spec-kitty`, coordinated cross-tranche).
5. Regenerates `mission_closed_payload.schema.json`.

## Strictness

After reconciliation, payload models use Pydantic `model_config = ConfigDict(extra='forbid')` at the payload boundary. Unknown fields are rejected with `ValidationError(code="PAYLOAD_SCHEMA_FAIL", ...)`.

## Cross-tranche coordination

This contract is normative for:

- Tranche A in `spec-kitty` (audit), which surfaces emission divergence.
- Tranche B in `spec-kitty` (canonicalizer), which normalizes historical-rendered shapes into the canonical models.
- Tranche A in `spec-kitty-saas` (ingress), which enforces the canonical models at the API boundary.

Each tranche must reference this file in its own plan/spec and assert the same direction.

## Reconciliation log

The work package that performs the reconciliation MUST append a section to this file recording the resolved field disposition, per event type. Format:

```
### Reconciliation log — <YYYY-MM-DD>

#### MissionClosed
- Field `legacy_aggregate_id`: **dropped** from canonical; CLI emission removed in `<repo>:<commit>`. Rationale: ...
- Field `closed_by`: **retained** in canonical; CLI emission unchanged. Rationale: ...
```

(The log captures the actual decisions made during implementation; it is a live record of the contract's evolution and is read by Codex during review.)

## Forbidden patterns

- Adding `model_config = ConfigDict(extra='allow')` to any of the three payload models.
- Allowing producers to emit fields the canonical model does not declare.
- Skipping the regeneration of the committed JSON Schemas after reconciliation.

## Versioning

Reconciliation is a major bump (per [versioning-and-compatibility.md](./versioning-and-compatibility.md)) because producers must change to conform.
