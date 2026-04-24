# Data Model — Decision Moment V1 Contract Freeze

Phase 1 output for mission `decision-moment-v1-contract-freeze-01KPWA0N`.

## Conventions

- All models are Pydantic v2 with `ConfigDict(frozen=True, extra="forbid")` unless noted.
- Tuples are used for immutable sequences on the wire (`Tuple[T, ...]`), matching existing module convention.
- Timestamps are `datetime` with tzinfo (ISO-8601 UTC strings on the wire).
- `decision_point_id`, `mission_id`, `run_id`, `participant_id`, and similar ID fields are `str` with `min_length=1` (ULID-like opaque strings; not parsed).
- All DecisionPoint-family events carry `origin_surface` (required on Opened/Widened/Discussing/Resolved; optional on Overridden) so every event is self-describing for replay.

## 1. Shared models (new or extended)

### 1.1 `ParticipantExternalRefs` (NEW)

Home: `src/spec_kitty_events/collaboration.py` (next to `ParticipantIdentity`).

```python
class ParticipantExternalRefs(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    slack_user_id: Optional[str] = Field(None, min_length=1)
    slack_team_id: Optional[str] = Field(None, min_length=1)
    teamspace_member_id: Optional[str] = Field(None, min_length=1)
```

Validation: at least one field must be present when the object is supplied (if a caller sets `external_refs={}` that is invalid and the schema rejects). Enforced via a root_validator that checks `any(value is not None for value in model_dump().values())`.

### 1.2 `ParticipantIdentity` (EXTEND)

Add optional `external_refs` field. No other changes.

```python
class ParticipantIdentity(BaseModel):
    model_config = ConfigDict(frozen=True)

    participant_id: str = Field(..., min_length=1)
    participant_type: Literal["human", "llm_context"] = Field(...)
    display_name: Optional[str] = None
    session_id: Optional[str] = None
    external_refs: Optional[ParticipantExternalRefs] = None   # NEW
```

Compatibility: existing 3.x consumers that do not set `external_refs` keep validating. Existing payloads that embed `ParticipantIdentity` (`ParticipantInvitedPayload`, `ParticipantJoinedPayload`, collaboration state) transparently gain the new optional field.

### 1.3 `SummaryBlock` (NEW)

Home: `src/spec_kitty_events/decisionpoint.py`.

```python
class SummarySource(str, Enum):
    SLACK_EXTRACTION = "slack_extraction"
    MANUAL = "manual"
    MISSION_OWNER_OVERRIDE = "mission_owner_override"


class SummaryBlock(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    text: str = Field(..., min_length=1)
    source: SummarySource
    extracted_at: Optional[datetime] = None
    candidate_answer: Optional[str] = None
```

### 1.4 `TeamspaceRef`, `DefaultChannelRef`, `ThreadRef`, `ClosureMessageRef` (NEW)

Home: `src/spec_kitty_events/decisionpoint.py`.

```python
class TeamspaceRef(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    teamspace_id: str = Field(..., min_length=1)
    name: Optional[str] = None


class DefaultChannelRef(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    channel_id: str = Field(..., min_length=1)
    name: Optional[str] = None


class ThreadRef(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    slack_team_id: Optional[str] = None
    channel_id: str = Field(..., min_length=1)
    thread_ts: str = Field(..., min_length=1)
    url: Optional[str] = None


class ClosureMessageRef(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    channel_id: str = Field(..., min_length=1)
    thread_ts: str = Field(..., min_length=1)
    message_ts: str = Field(..., min_length=1)
    url: Optional[str] = None
```

## 2. DecisionPoint event payload models

### 2.1 `OriginSurface` enum (NEW)

```python
class OriginSurface(str, Enum):
    ADR = "adr"
    PLANNING_INTERVIEW = "planning_interview"


class OriginFlow(str, Enum):
    CHARTER = "charter"
    SPECIFY = "specify"
    PLAN = "plan"
```

### 2.2 `DecisionPointOpenedPayload` — discriminated union

```python
class DecisionPointOpenedAdrPayload(BaseModel):
    """3.x-compatible ADR-style Opened payload."""

    model_config = ConfigDict(frozen=True, extra="forbid")
    origin_surface: Literal[OriginSurface.ADR] = Field(...)

    decision_point_id: str = Field(..., min_length=1)
    mission_id: str = Field(..., min_length=1)
    run_id: str = Field(..., min_length=1)
    mission_slug: str = Field(..., min_length=1)
    mission_type: str = Field(..., min_length=1)
    phase: str = Field(..., min_length=1)

    actor_id: str = Field(..., min_length=1)
    actor_type: Literal["human", "llm", "service"] = Field(...)
    authority_role: DecisionAuthorityRole
    mission_owner_authority_flag: bool
    mission_owner_authority_path: str

    rationale: str = Field(..., min_length=1)
    alternatives_considered: Tuple[str, ...] = Field(..., min_length=1)
    evidence_refs: Tuple[str, ...] = Field(..., min_length=1)

    state_entered_at: datetime
    recorded_at: datetime


class DecisionPointOpenedInterviewPayload(BaseModel):
    """V1 interview-origin Opened payload (ask-time)."""

    model_config = ConfigDict(frozen=True, extra="forbid")
    origin_surface: Literal[OriginSurface.PLANNING_INTERVIEW] = Field(...)

    decision_point_id: str = Field(..., min_length=1)
    mission_id: str = Field(..., min_length=1)
    run_id: str = Field(..., min_length=1)
    mission_slug: str = Field(..., min_length=1)
    mission_type: str = Field(..., min_length=1)
    phase: str = Field(..., min_length=1)

    origin_flow: OriginFlow = Field(...)
    question: str = Field(..., min_length=1)
    options: Tuple[str, ...] = Field(..., min_length=0)   # options MAY be empty (free-form only)
    input_key: str = Field(..., min_length=1)
    step_id: str = Field(..., min_length=1)

    actor_id: str = Field(..., min_length=1)              # who asked (usually the CLI process / mission owner session)
    actor_type: Literal["human", "llm", "service"] = Field(...)

    state_entered_at: datetime
    recorded_at: datetime


DecisionPointOpenedPayload = Annotated[
    Union[DecisionPointOpenedAdrPayload, DecisionPointOpenedInterviewPayload],
    Field(discriminator="origin_surface"),
]
```

### 2.3 `DecisionPointWidenedPayload` (NEW)

```python
class WideningChannel(str, Enum):
    SLACK = "slack"


class DecisionPointWidenedPayload(BaseModel):
    """V1-only: one Slack thread created for an interview-origin Decision Moment."""

    model_config = ConfigDict(frozen=True, extra="forbid")
    origin_surface: Literal[OriginSurface.PLANNING_INTERVIEW] = Field(...)

    decision_point_id: str = Field(..., min_length=1)
    mission_id: str = Field(..., min_length=1)
    run_id: str = Field(..., min_length=1)
    mission_slug: str = Field(..., min_length=1)
    mission_type: str = Field(..., min_length=1)

    channel: Literal[WideningChannel.SLACK] = Field(...)
    teamspace_ref: TeamspaceRef
    default_channel_ref: DefaultChannelRef
    thread_ref: ThreadRef
    invited_participants: Tuple[ParticipantIdentity, ...] = Field(..., min_length=0)

    widened_by: str = Field(..., min_length=1)            # participant_id of mission owner who confirmed widening
    widened_at: datetime
    recorded_at: datetime
```

### 2.4 `DecisionPointDiscussingPayload` — discriminated union

```python
class DecisionPointDiscussingAdrPayload(BaseModel):
    """3.x-compatible ADR-style Discussing payload (unchanged field set)."""

    model_config = ConfigDict(frozen=True, extra="forbid")
    origin_surface: Literal[OriginSurface.ADR] = Field(...)

    decision_point_id: str = Field(..., min_length=1)
    mission_id: str = Field(..., min_length=1)
    run_id: str = Field(..., min_length=1)
    mission_slug: str = Field(..., min_length=1)
    mission_type: str = Field(..., min_length=1)
    phase: str = Field(..., min_length=1)

    actor_id: str = Field(..., min_length=1)
    actor_type: Literal["human", "llm", "service"] = Field(...)
    authority_role: DecisionAuthorityRole
    mission_owner_authority_flag: bool
    mission_owner_authority_path: str

    rationale: str = Field(..., min_length=1)
    alternatives_considered: Tuple[str, ...] = Field(..., min_length=1)
    evidence_refs: Tuple[str, ...] = Field(..., min_length=1)

    state_entered_at: datetime
    recorded_at: datetime


class DiscussingSnapshotKind(str, Enum):
    PARTICIPANT_CONTRIBUTION = "participant_contribution"
    DIGEST = "digest"
    OWNER_NOTE = "owner_note"


class DecisionPointDiscussingInterviewPayload(BaseModel):
    """V1: synthesized contribution snapshot for interview-origin discussion."""

    model_config = ConfigDict(frozen=True, extra="forbid")
    origin_surface: Literal[OriginSurface.PLANNING_INTERVIEW] = Field(...)

    decision_point_id: str = Field(..., min_length=1)
    mission_id: str = Field(..., min_length=1)
    run_id: str = Field(..., min_length=1)
    mission_slug: str = Field(..., min_length=1)
    mission_type: str = Field(..., min_length=1)

    snapshot_kind: DiscussingSnapshotKind
    contributions: Tuple[str, ...] = Field(default_factory=tuple)   # synthesized summary lines, not raw Slack messages
    actor_id: str = Field(..., min_length=1)                        # who authored the snapshot (usually SaaS)
    actor_type: Literal["human", "llm", "service"] = Field(...)

    state_entered_at: datetime
    recorded_at: datetime


DecisionPointDiscussingPayload = Annotated[
    Union[DecisionPointDiscussingAdrPayload, DecisionPointDiscussingInterviewPayload],
    Field(discriminator="origin_surface"),
]
```

### 2.5 `DecisionPointResolvedPayload` — discriminated union

```python
class TerminalOutcome(str, Enum):
    RESOLVED = "resolved"
    DEFERRED = "deferred"
    CANCELED = "canceled"


class DecisionPointResolvedAdrPayload(BaseModel):
    """3.x-compatible ADR-style Resolved payload (unchanged field set)."""

    model_config = ConfigDict(frozen=True, extra="forbid")
    origin_surface: Literal[OriginSurface.ADR] = Field(...)

    decision_point_id: str = Field(..., min_length=1)
    mission_id: str = Field(..., min_length=1)
    run_id: str = Field(..., min_length=1)
    mission_slug: str = Field(..., min_length=1)
    mission_type: str = Field(..., min_length=1)
    phase: str = Field(..., min_length=1)

    actor_id: str = Field(..., min_length=1)
    actor_type: Literal["human", "llm", "service"] = Field(...)
    authority_role: DecisionAuthorityRole
    mission_owner_authority_flag: bool
    mission_owner_authority_path: str

    rationale: str = Field(..., min_length=1)
    alternatives_considered: Tuple[str, ...] = Field(..., min_length=1)
    evidence_refs: Tuple[str, ...] = Field(..., min_length=1)

    state_entered_at: datetime
    recorded_at: datetime


class DecisionPointResolvedInterviewPayload(BaseModel):
    """V1 interview-origin Resolved payload."""

    model_config = ConfigDict(frozen=True, extra="forbid")
    origin_surface: Literal[OriginSurface.PLANNING_INTERVIEW] = Field(...)

    decision_point_id: str = Field(..., min_length=1)
    mission_id: str = Field(..., min_length=1)
    run_id: str = Field(..., min_length=1)
    mission_slug: str = Field(..., min_length=1)
    mission_type: str = Field(..., min_length=1)

    terminal_outcome: TerminalOutcome = Field(...)
    final_answer: Optional[str] = None                    # REQUIRED when terminal_outcome=resolved; FORBIDDEN otherwise
    other_answer: bool = False                            # True when final_answer is free-text (Other path)
    rationale: Optional[str] = None                       # REQUIRED when terminal_outcome in {deferred, canceled}
    summary: Optional[SummaryBlock] = None                # REQUIRED when a prior DecisionPointWidened exists (enforced by reducer + fixture)
    actual_participants: Tuple[ParticipantIdentity, ...] = Field(default_factory=tuple)

    resolved_by: str = Field(..., min_length=1)           # participant_id of mission owner
    closed_locally_while_widened: bool = False
    closure_message: Optional[ClosureMessageRef] = None

    state_entered_at: datetime
    recorded_at: datetime

    @model_validator(mode="after")
    def _enforce_outcome_fields(self) -> "DecisionPointResolvedInterviewPayload":
        if self.terminal_outcome == TerminalOutcome.RESOLVED:
            if self.final_answer is None or len(self.final_answer) == 0:
                raise ValueError("final_answer is required when terminal_outcome=resolved")
        else:
            if self.final_answer is not None:
                raise ValueError(
                    f"final_answer must be absent when terminal_outcome={self.terminal_outcome.value}"
                )
            if self.rationale is None or len(self.rationale) == 0:
                raise ValueError(
                    f"rationale is required when terminal_outcome={self.terminal_outcome.value}"
                )
            if self.other_answer:
                raise ValueError(
                    f"other_answer must be False when terminal_outcome={self.terminal_outcome.value}"
                )
        return self


DecisionPointResolvedPayload = Annotated[
    Union[DecisionPointResolvedAdrPayload, DecisionPointResolvedInterviewPayload],
    Field(discriminator="origin_surface"),
]
```

### 2.6 `DecisionPointOverriddenPayload` — unchanged behaviour + optional `origin_surface`

```python
class DecisionPointOverriddenPayload(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    # (existing 3.x fields unchanged)

    origin_surface: Optional[OriginSurface] = None        # NEW (optional; for replay context)
    # ... rest unchanged
```

## 3. Event-type → payload mapping

```python
_EVENT_TO_PAYLOAD: dict[str, Any] = {
    DECISION_POINT_OPENED:      DecisionPointOpenedPayload,      # discriminated union
    DECISION_POINT_WIDENED:     DecisionPointWidenedPayload,     # NEW, single model
    DECISION_POINT_DISCUSSING:  DecisionPointDiscussingPayload,  # discriminated union
    DECISION_POINT_RESOLVED:    DecisionPointResolvedPayload,    # discriminated union
    DECISION_POINT_OVERRIDDEN:  DecisionPointOverriddenPayload,
}
```

## 4. State machine

```
                        ┌──────────────────────┐
                        │        (start)       │
                        └────────────┬─────────┘
                                     │ DecisionPointOpened
                                     ▼
                              ┌────────────┐
                              │    OPEN    │
                              └─────┬──────┘
                 DecisionPointWidened │  │ DecisionPointResolved (interview, never widened)
                                   ▼  │  ▼
                              ┌─────────┐  (TERMINAL)
                              │ WIDENED │
                              └────┬────┘
                  DecisionPointDiscussing │
                                   ▼  │
                              ┌────────────┐
                              │ DISCUSSING │──► DecisionPointResolved (terminal_outcome + closed_locally_while_widened)
                              └─────┬──────┘
                                    │
          DecisionPointResolved (adr path) ─► RESOLVED ─► DecisionPointOverridden ─► OVERRIDDEN (terminal)
```

Transition table, by event type (target state):

| From          | `Opened` | `Widened`                     | `Discussing`  | `Resolved` | `Overridden` |
|---------------|----------|-------------------------------|---------------|------------|--------------|
| `None`        | `OPEN`   | anomaly (`invalid_transition`)| anomaly       | anomaly    | anomaly      |
| `OPEN`        | anomaly  | `WIDENED`                     | `DISCUSSING`  | `RESOLVED` | anomaly      |
| `WIDENED`     | anomaly  | `WIDENED` (idempotent no-op)  | `DISCUSSING`  | `RESOLVED` | anomaly      |
| `DISCUSSING`  | anomaly  | anomaly (already widened)     | `DISCUSSING`  | `RESOLVED` | anomaly      |
| `RESOLVED`    | anomaly  | anomaly                       | anomaly       | anomaly    | `OVERRIDDEN` |
| `OVERRIDDEN`  | anomaly  | anomaly                       | anomaly       | anomaly    | terminal     |

Notes:

- `WIDENED` exists only for `origin_surface="planning_interview"` events. An ADR event stream can never enter `WIDENED` in V1 (schema-rejected: Widened payload requires `origin_surface=planning_interview`).
- A duplicate `DecisionPointWidened` for the same `decision_point_id` collapses into a no-op on widening state: the reducer ignores the second occurrence rather than raising an anomaly (idempotency per FR-014).
- `closed_locally_while_widened=true` is only legal on `Resolved` when a prior `DecisionPointWidened` exists for the same `decision_point_id`. Reducer logs `DecisionPointAnomaly(kind="invalid_transition")` otherwise.
- Origin mismatch across events for the same `decision_point_id` produces `DecisionPointAnomaly(kind="origin_mismatch")` — events are still applied in arrival order, but downstream consumers are signalled.

## 5. `ReducedDecisionPointState` (extended)

```python
class ReducedDecisionPointState(BaseModel):
    model_config = ConfigDict(frozen=True)

    # 3.x fields (preserved, unchanged semantics)
    state: Optional[DecisionPointState] = None            # enum extended with WIDENED below
    decision_point_id: Optional[str] = None
    mission_id: Optional[str] = None
    run_id: Optional[str] = None
    mission_slug: Optional[str] = None
    mission_type: Optional[str] = None
    phase: Optional[str] = None
    last_actor_id: Optional[str] = None
    last_actor_type: Optional[str] = None
    last_authority_role: Optional[DecisionAuthorityRole] = None
    last_rationale: Optional[str] = None
    last_alternatives_considered: Optional[Tuple[str, ...]] = None
    last_evidence_refs: Optional[Tuple[str, ...]] = None
    last_state_entered_at: Optional[datetime] = None
    anomalies: Tuple[DecisionPointAnomaly, ...] = ()
    event_count: int = 0

    # V1 projection fields (NEW)
    origin_surface: Optional[OriginSurface] = None
    origin_flow: Optional[OriginFlow] = None
    question: Optional[str] = None
    options: Optional[Tuple[str, ...]] = None
    input_key: Optional[str] = None
    step_id: Optional[str] = None

    widening: Optional[WideningProjection] = None         # populated on Widened
    terminal_outcome: Optional[TerminalOutcome] = None
    final_answer: Optional[str] = None
    other_answer: bool = False
    summary: Optional[SummaryBlock] = None
    actual_participants: Tuple[ParticipantIdentity, ...] = ()
    resolved_by: Optional[str] = None
    closed_locally_while_widened: bool = False
    closure_message: Optional[ClosureMessageRef] = None


class DecisionPointState(str, Enum):
    OPEN = "open"
    WIDENED = "widened"        # NEW
    DISCUSSING = "discussing"
    RESOLVED = "resolved"
    OVERRIDDEN = "overridden"


class WideningProjection(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    channel: WideningChannel
    teamspace_ref: TeamspaceRef
    default_channel_ref: DefaultChannelRef
    thread_ref: ThreadRef
    invited_participants: Tuple[ParticipantIdentity, ...]
    widened_by: str
    widened_at: datetime
```

## 6. `DecisionInputRequested` / `DecisionInputAnswered`

**Unchanged for 3.x compatibility.** Constraint C-004 allows adding *optional* fields if future needs arise, but this mission adds none.

**Behavior rule** (documented in CHANGELOG + COMPATIBILITY): `DecisionInputAnswered` is emitted only when a real final answer is written back. It is *not* emitted when `terminal_outcome ∈ {deferred, canceled}`, because no input was actually answered.

## 7. JSON Schema expectations

Regenerated (via `schemas/generate.py`) files:

- `decision_point_opened_payload.schema.json` — `oneOf` of the two Opened variants, discriminated by `origin_surface`.
- `decision_point_widened_payload.schema.json` — NEW, single schema.
- `decision_point_discussing_payload.schema.json` — `oneOf` of the two Discussing variants.
- `decision_point_resolved_payload.schema.json` — `oneOf` of the two Resolved variants with cross-field constraints on `final_answer`/`rationale`/`other_answer` encoded via `allOf` + `if/then`.
- `decision_point_overridden_payload.schema.json` — adds optional `origin_surface` property.
- NEW shared: `participant_identity.schema.json` (canonical extracted), `participant_external_refs.schema.json`, `summary_block.schema.json`, `teamspace_ref.schema.json`, `default_channel_ref.schema.json`, `thread_ref.schema.json`, `closure_message_ref.schema.json`.

The schema-drift integration test (`tests/integration/test_schema_drift.py`) regenerates and diffs against the committed files; a diff fails CI.

## 8. Conformance fixtures (new/extended)

### 8.1 Valid

Under `src/spec_kitty_events/conformance/fixtures/decisionpoint/valid/`:

- `v1_opened_interview.json` — one-event fixture of `DecisionPointOpened` interview variant.
- `v1_opened_adr.json` — one-event fixture of `DecisionPointOpened` ADR variant (verifies 3.x compatibility).
- `v1_widened.json` — one-event fixture of `DecisionPointWidened`.
- `v1_resolved_interview_resolved.json` — Resolved interview variant with `terminal_outcome=resolved`, `final_answer`, `other_answer=false`.
- `v1_resolved_interview_resolved_other.json` — same but `other_answer=true`, free-text `final_answer`.
- `v1_resolved_interview_deferred.json` — `terminal_outcome=deferred`, no `final_answer`, `rationale` required.
- `v1_resolved_interview_canceled.json` — `terminal_outcome=canceled`, no `final_answer`, `rationale` required.
- `v1_resolved_interview_closed_locally.json` — `closed_locally_while_widened=true`, `summary.source=manual` or `mission_owner_override`.
- `v1_discussing_interview.json` — interview discussing snapshot.
- `v1_participant_identity_with_external_refs.json` — shared fixture used by ParticipantInvited/Joined tests.

### 8.2 Invalid

Under `src/spec_kitty_events/conformance/fixtures/decisionpoint/invalid/`:

- `v1_resolved_missing_terminal_outcome.json` — fails schema (discriminated-interview variant missing `terminal_outcome`).
- `v1_widened_missing_thread_ref.json` — fails schema.
- `v1_opened_interview_missing_origin_flow.json` — fails schema when `origin_surface=planning_interview` and `origin_flow` absent.
- `v1_participant_identity_empty_external_refs.json` — fails schema because `external_refs` supplied with all-null fields.
- `v1_resolved_interview_deferred_with_final_answer.json` — fails cross-field validator (Pydantic `model_validator`; conformance test calls `payload_cls.model_validate` to exercise).

### 8.3 Golden replay fixtures

Under `tests/fixtures/decisionpoint_golden/` (mirrored into `src/spec_kitty_events/conformance/fixtures/decisionpoint/replay/`):

| Name                                            | Event sequence                                                                 |
|-------------------------------------------------|--------------------------------------------------------------------------------|
| `replay_interview_local_only_resolved`          | Opened(interview) → Resolved(interview, terminal=resolved, closed_locally=false) |
| `replay_interview_widened_resolved`             | Opened(interview) → Widened → Discussing(interview) → Resolved(interview, terminal=resolved, summary.source=slack_extraction) |
| `replay_interview_widened_closed_locally`       | Opened(interview) → Widened → Resolved(interview, terminal=resolved, closed_locally=true, summary.source=manual, closure_message populated) |
| `replay_interview_deferred`                     | Opened(interview) → (optional Widened) → Resolved(interview, terminal=deferred, rationale populated) |
| `replay_interview_canceled`                     | Opened(interview) → Resolved(interview, terminal=canceled, rationale populated) |
| `replay_interview_resolved_other`               | Opened(interview, options=[A,B,C,Other]) → Resolved(interview, terminal=resolved, other_answer=true, final_answer="custom text") |

Each fixture is a `.jsonl` of events + a paired `_output.json` capturing the expected `ReducedDecisionPointState` with sorted-key serialization.

## 9. Migration notes

- Existing 3.x ADR `DecisionPointOpened` producers add `origin_surface="adr"` to payloads. No other changes required for ADR producers.
- Existing 3.x `DecisionInputRequested` / `DecisionInputAnswered` producers: no changes required.
- Internal `DECISIONPOINT_SCHEMA_VERSION` constant bumps from `2.6.0` to `3.0.0` (domain-schema version), independent of package version `4.0.0`.
