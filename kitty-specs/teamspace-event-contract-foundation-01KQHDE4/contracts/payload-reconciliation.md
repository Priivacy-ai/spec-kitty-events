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

### Reconciliation log — 2026-05-01

#### Scope note

A full audit of CLI emission sites in the `spec-kitty` repo is **out of scope**
for this WP — it lives in a different repository (`../spec-kitty/`) which the
events-package isolation rules forbid us from reading. This events-package-side
reconciliation pins the canonical payload field set as the baseline; downstream
`spec-kitty` Tranche A (audit) and Tranche B (CLI canonicalizer) tranches must
conform to the field lists below. The cross-tranche caller list will be filled
in by those tranches when they land.

#### MissionCreated

Authoritative model: `MissionCreatedPayload` in
`src/spec_kitty_events/lifecycle.py`.

Canonical fields (after this WP):

- `mission_id: Optional[str]` — Canonical machine-facing mission identity (ULID).
- `mission_slug: str` — Canonical mission slug.
- `mission_number: Optional[int]` — Canonical mission number (≥ 1 when set).
- `mission_type: str` — Canonical mission workflow/template type
  (e.g. `software-dev`, `research`, `plan`).
- `target_branch: str` — Target branch for mission planning artifacts.
- `wp_count: int` — Work-package count at mission creation time (≥ 0).
- `friendly_name: str` — Human-friendly mission title.
- `purpose_tldr: str` — One-line stakeholder-facing mission summary.
- `purpose_context: str` — Short stakeholder-facing context paragraph.
- `created_at: Optional[str]` — Mission creation timestamp.

Disposition: `extra='forbid'` is now enforced (was already present from prior
work — re-affirmed and pinned by tests in this WP). Producers that emit any
field not on this list will be rejected with `PAYLOAD_SCHEMA_FAIL`. Cross-tranche
callers in `spec-kitty` (CLI emission and `spec-kitty-saas` ingress) must update
emission to conform; the discovery and update is owned by Tranche A in
`spec-kitty`.

#### WPStatusChanged (StatusTransitionPayload)

Authoritative model: `StatusTransitionPayload` in
`src/spec_kitty_events/status.py` — **owned by WP01, not modified here**. Read
verbatim from the existing definition.

Canonical fields:

- `mission_slug: str` — Mission identifier.
- `wp_id: str` — Work-package identifier.
- `from_lane: Optional[Lane]` — Lane the WP is transitioning from
  (None for initial). Includes the new `Lane.IN_REVIEW` value from WP01.
- `to_lane: Lane` — Lane the WP is transitioning to. Includes
  `Lane.IN_REVIEW`.
- `actor: Union[str, Dict[str, Any]]` — Plain string identifier or a structured
  dict carrying `{role, profile, tool, model}`-style audit fields.
- `force: bool` — Whether this is a forced transition (default False).
- `reason: Optional[str]` — Required when `force=True`.
- `execution_mode: ExecutionMode` — `worktree` or `direct_repo`.
- `review_ref: Optional[str]` — Reference to an external review.
- `evidence: Optional[DoneEvidence]` — Required when `to_lane in {APPROVED, DONE}`.

Disposition: `extra='forbid'` is **already present** on the WP01-owned model
(verified by reading `status.py` line 211 from this WP's worktree without
modifying the file). No change is needed in `status.py`. The new
`Lane.IN_REVIEW` member is the WP01→WP04 handshake; the
`tests/test_payload_reconciliation.py::test_FR_004_status_transition_accepts_in_review_to_lane`
test pins it. Cross-tranche callers in `spec-kitty` Tranche A must accept and
emit `in_review` per WP01's `lane-vocabulary.md` contract.

#### MissionClosed

Authoritative model: `MissionClosedPayload` in
`src/spec_kitty_events/lifecycle.py`.

Canonical fields (after this WP):

- `mission_slug: str` — Canonical mission slug.
- `mission_number: int` — Canonical mission number (≥ 1).
- `mission_type: str` — Canonical mission workflow/template type.

Disposition: `extra='forbid'` is now enforced. The spec called out CLI-vs-library
disagreement; the canonical baseline above is the resolution. Speculative
historical fields such as `legacy_aggregate_id`, `closed_at`, and `closed_by`
are **not retained** in the canonical model — they must either be dropped at
the CLI emission site (Tranche A) or normalized away by the CLI canonicalizer
(Tranche B) before payloads cross the events-package boundary. The
`tests/test_payload_reconciliation.py::test_SC_004_mission_closed_rejects_historical_cli_shape`
test pins the SC-004 cross-shape evidence.

#### Schema regeneration

Ran `python -m spec_kitty_events.schemas.generate --check` after this WP's edits;
all 102 committed schemas matched the generator's deterministic output (no
drift). The three reconciled schemas
(`mission_created_payload.schema.json`, `mission_closed_payload.schema.json`,
`status_transition_payload.schema.json`) are in lockstep with their Pydantic
models. A `tests/test_payload_reconciliation.py` schema-drift test pins parity
going forward.
