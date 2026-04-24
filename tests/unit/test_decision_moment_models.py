"""Unit tests for Decision Moment V1 shared models and enums."""

from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from spec_kitty_events.decision_moment import (
    ClosureMessageRef,
    DefaultChannelRef,
    DiscussingSnapshotKind,
    OriginFlow,
    OriginSurface,
    SummaryBlock,
    SummarySource,
    TeamspaceRef,
    TerminalOutcome,
    ThreadRef,
    WideningChannel,
    WideningProjection,
)


# ── OriginSurface ─────────────────────────────────────────────────────────────


def test_origin_surface_values() -> None:
    assert OriginSurface.ADR.value == "adr"
    assert OriginSurface.PLANNING_INTERVIEW.value == "planning_interview"


def test_origin_surface_is_str_backed() -> None:
    assert isinstance(OriginSurface.ADR, str)
    assert isinstance(OriginSurface.PLANNING_INTERVIEW, str)


def test_origin_surface_has_exactly_two_members() -> None:
    assert len(list(OriginSurface)) == 2


# ── OriginFlow ────────────────────────────────────────────────────────────────


def test_origin_flow_values() -> None:
    assert OriginFlow.CHARTER.value == "charter"
    assert OriginFlow.SPECIFY.value == "specify"
    assert OriginFlow.PLAN.value == "plan"


def test_origin_flow_is_str_backed() -> None:
    assert isinstance(OriginFlow.CHARTER, str)
    assert isinstance(OriginFlow.SPECIFY, str)
    assert isinstance(OriginFlow.PLAN, str)


def test_origin_flow_has_exactly_three_members() -> None:
    assert len(list(OriginFlow)) == 3


# ── TerminalOutcome ───────────────────────────────────────────────────────────


def test_terminal_outcome_values() -> None:
    assert TerminalOutcome.RESOLVED.value == "resolved"
    assert TerminalOutcome.DEFERRED.value == "deferred"
    assert TerminalOutcome.CANCELED.value == "canceled"


def test_terminal_outcome_is_str_backed() -> None:
    assert isinstance(TerminalOutcome.RESOLVED, str)
    assert isinstance(TerminalOutcome.DEFERRED, str)
    assert isinstance(TerminalOutcome.CANCELED, str)


def test_terminal_outcome_has_exactly_three_members() -> None:
    assert len(list(TerminalOutcome)) == 3


# ── SummarySource ─────────────────────────────────────────────────────────────


def test_summary_source_values() -> None:
    assert SummarySource.SLACK_EXTRACTION.value == "slack_extraction"
    assert SummarySource.MANUAL.value == "manual"
    assert SummarySource.MISSION_OWNER_OVERRIDE.value == "mission_owner_override"


def test_summary_source_is_str_backed() -> None:
    assert isinstance(SummarySource.SLACK_EXTRACTION, str)
    assert isinstance(SummarySource.MANUAL, str)
    assert isinstance(SummarySource.MISSION_OWNER_OVERRIDE, str)


def test_summary_source_has_exactly_three_members() -> None:
    assert len(list(SummarySource)) == 3


# ── WideningChannel ───────────────────────────────────────────────────────────


def test_widening_channel_slack_only() -> None:
    members = list(WideningChannel)
    assert len(members) == 1
    assert WideningChannel.SLACK.value == "slack"
    assert isinstance(WideningChannel.SLACK, str)


# ── DiscussingSnapshotKind ────────────────────────────────────────────────────


def test_discussing_snapshot_kind_values() -> None:
    assert DiscussingSnapshotKind.PARTICIPANT_CONTRIBUTION.value == "participant_contribution"
    assert DiscussingSnapshotKind.DIGEST.value == "digest"
    assert DiscussingSnapshotKind.OWNER_NOTE.value == "owner_note"


def test_discussing_snapshot_kind_is_str_backed() -> None:
    assert isinstance(DiscussingSnapshotKind.PARTICIPANT_CONTRIBUTION, str)
    assert isinstance(DiscussingSnapshotKind.DIGEST, str)
    assert isinstance(DiscussingSnapshotKind.OWNER_NOTE, str)


def test_discussing_snapshot_kind_has_exactly_three_members() -> None:
    assert len(list(DiscussingSnapshotKind)) == 3


# ── SummaryBlock ──────────────────────────────────────────────────────────────


def test_summary_block_minimal() -> None:
    sb = SummaryBlock(text="A decision was made", source=SummarySource.MANUAL)
    assert sb.text == "A decision was made"
    assert sb.source == SummarySource.MANUAL
    assert sb.extracted_at is None
    assert sb.candidate_answer is None


def test_summary_block_full() -> None:
    now = datetime(2026, 4, 23, 12, 0, 0, tzinfo=timezone.utc)
    sb = SummaryBlock(
        text="Summary of discussion",
        source=SummarySource.SLACK_EXTRACTION,
        extracted_at=now,
        candidate_answer="Option B",
    )
    assert sb.text == "Summary of discussion"
    assert sb.source == SummarySource.SLACK_EXTRACTION
    assert sb.extracted_at == now
    assert sb.candidate_answer == "Option B"


def test_summary_block_rejects_empty_text() -> None:
    with pytest.raises(ValidationError):
        SummaryBlock(text="", source=SummarySource.MANUAL)


def test_summary_block_frozen() -> None:
    sb = SummaryBlock(text="Some text", source=SummarySource.MANUAL)
    with pytest.raises(ValidationError):
        sb.text = "changed"  # type: ignore[misc]


def test_summary_block_extra_fields_rejected() -> None:
    with pytest.raises(ValidationError):
        SummaryBlock(text="ok", source=SummarySource.MANUAL, unknown_field="x")  # type: ignore[call-arg]


@pytest.mark.parametrize("source", list(SummarySource))
def test_summary_block_each_source_roundtrips(source: SummarySource) -> None:
    sb = SummaryBlock(text="Roundtrip test", source=source)
    json_str = sb.model_dump_json()
    data = json.loads(json_str)
    restored = SummaryBlock.model_validate(data)
    assert restored == sb
    assert restored.source == source


def test_summary_block_extracted_at_roundtrips_via_json() -> None:
    now = datetime(2026, 4, 23, 9, 0, 0, tzinfo=timezone.utc)
    sb = SummaryBlock(
        text="Extracted summary",
        source=SummarySource.SLACK_EXTRACTION,
        extracted_at=now,
    )
    json_str = sb.model_dump_json()
    restored = SummaryBlock.model_validate_json(json_str)
    assert restored.extracted_at == now


# ── TeamspaceRef ──────────────────────────────────────────────────────────────


def test_teamspace_ref_minimal() -> None:
    ref = TeamspaceRef(teamspace_id="ts-001")
    assert ref.teamspace_id == "ts-001"
    assert ref.name is None


def test_teamspace_ref_with_name() -> None:
    ref = TeamspaceRef(teamspace_id="ts-001", name="Engineering Team")
    assert ref.name == "Engineering Team"


def test_teamspace_ref_rejects_empty_id() -> None:
    with pytest.raises(ValidationError):
        TeamspaceRef(teamspace_id="")


def test_teamspace_ref_extra_fields_rejected() -> None:
    with pytest.raises(ValidationError):
        TeamspaceRef(teamspace_id="ts-001", extra_key="x")  # type: ignore[call-arg]


def test_teamspace_ref_frozen() -> None:
    ref = TeamspaceRef(teamspace_id="ts-001")
    with pytest.raises(ValidationError):
        ref.teamspace_id = "changed"  # type: ignore[misc]


# ── DefaultChannelRef ─────────────────────────────────────────────────────────


def test_default_channel_ref_minimal() -> None:
    ref = DefaultChannelRef(channel_id="C012345")
    assert ref.channel_id == "C012345"
    assert ref.name is None


def test_default_channel_ref_with_name() -> None:
    ref = DefaultChannelRef(channel_id="C012345", name="#general")
    assert ref.name == "#general"


def test_default_channel_ref_rejects_empty_id() -> None:
    with pytest.raises(ValidationError):
        DefaultChannelRef(channel_id="")


def test_default_channel_ref_extra_fields_rejected() -> None:
    with pytest.raises(ValidationError):
        DefaultChannelRef(channel_id="C123", extra="x")  # type: ignore[call-arg]


# ── ThreadRef ─────────────────────────────────────────────────────────────────


def test_thread_ref_minimal() -> None:
    ref = ThreadRef(channel_id="C012345", thread_ts="1234567890.123456")
    assert ref.channel_id == "C012345"
    assert ref.thread_ts == "1234567890.123456"
    assert ref.slack_team_id is None
    assert ref.url is None


def test_thread_ref_full() -> None:
    ref = ThreadRef(
        slack_team_id="T012345",
        channel_id="C012345",
        thread_ts="1234567890.123456",
        url="https://slack.com/archives/C012345/p1234567890123456",
    )
    assert ref.slack_team_id == "T012345"
    assert ref.url == "https://slack.com/archives/C012345/p1234567890123456"


def test_thread_ref_rejects_empty_channel_id() -> None:
    with pytest.raises(ValidationError):
        ThreadRef(channel_id="", thread_ts="1234567890.123456")


def test_thread_ref_rejects_empty_thread_ts() -> None:
    with pytest.raises(ValidationError):
        ThreadRef(channel_id="C012345", thread_ts="")


def test_thread_ref_extra_fields_rejected() -> None:
    with pytest.raises(ValidationError):
        ThreadRef(channel_id="C123", thread_ts="123.456", extra="x")  # type: ignore[call-arg]


def test_thread_ref_frozen() -> None:
    ref = ThreadRef(channel_id="C012345", thread_ts="1234567890.123456")
    with pytest.raises(ValidationError):
        ref.channel_id = "changed"  # type: ignore[misc]


# ── ClosureMessageRef ─────────────────────────────────────────────────────────


def test_closure_message_ref_minimal() -> None:
    ref = ClosureMessageRef(
        channel_id="C012345",
        thread_ts="1234567890.123456",
        message_ts="1234567899.999999",
    )
    assert ref.channel_id == "C012345"
    assert ref.thread_ts == "1234567890.123456"
    assert ref.message_ts == "1234567899.999999"
    assert ref.url is None


def test_closure_message_ref_rejects_empty_channel_id() -> None:
    with pytest.raises(ValidationError):
        ClosureMessageRef(channel_id="", thread_ts="123.456", message_ts="123.789")


def test_closure_message_ref_rejects_empty_thread_ts() -> None:
    with pytest.raises(ValidationError):
        ClosureMessageRef(channel_id="C123", thread_ts="", message_ts="123.789")


def test_closure_message_ref_rejects_empty_message_ts() -> None:
    with pytest.raises(ValidationError):
        ClosureMessageRef(channel_id="C123", thread_ts="123.456", message_ts="")


def test_closure_message_ref_extra_fields_rejected() -> None:
    with pytest.raises(ValidationError):
        ClosureMessageRef(  # type: ignore[call-arg]
            channel_id="C123",
            thread_ts="123.456",
            message_ts="123.789",
            extra="x",
        )


# ── WideningProjection ────────────────────────────────────────────────────────


def _make_widening_projection(**kwargs: object) -> WideningProjection:
    """Helper: build a minimal WideningProjection with overridable fields."""
    defaults: dict[str, object] = dict(
        channel=WideningChannel.SLACK,
        teamspace_ref=TeamspaceRef(teamspace_id="ts-1"),
        default_channel_ref=DefaultChannelRef(channel_id="C-1"),
        thread_ref=ThreadRef(channel_id="C-1", thread_ts="111.222"),
        invited_participants=(),
        widened_by="p-owner",
        widened_at=datetime(2026, 4, 23, 12, 0, 0, tzinfo=timezone.utc),
    )
    defaults.update(kwargs)
    return WideningProjection(**defaults)  # type: ignore[arg-type]


def test_widening_projection_constructs_with_empty_participants() -> None:
    wp = _make_widening_projection(invited_participants=())
    assert wp.invited_participants == ()


def test_widening_projection_serializes_channel_as_slack() -> None:
    wp = _make_widening_projection()
    dumped = wp.model_dump(mode="json")
    assert dumped["channel"] == "slack"


def test_widening_projection_frozen() -> None:
    wp = _make_widening_projection()
    with pytest.raises(ValidationError):
        wp.widened_by = "changed"  # type: ignore[misc]


def test_widening_projection_extra_fields_rejected() -> None:
    with pytest.raises(ValidationError):
        _make_widening_projection(unknown="x")  # type: ignore[call-arg]


def test_widening_projection_rejects_empty_widened_by() -> None:
    with pytest.raises(ValidationError):
        _make_widening_projection(widened_by="")


def test_widening_projection_with_invited_participants() -> None:
    from spec_kitty_events.collaboration import ParticipantIdentity

    participant = ParticipantIdentity(
        participant_id="p-001",
        participant_type="human",
    )
    wp = _make_widening_projection(invited_participants=(participant,))
    assert len(wp.invited_participants) == 1
    assert wp.invited_participants[0].participant_id == "p-001"
