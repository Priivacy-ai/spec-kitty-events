"""Lock the reconciled payload contracts for MissionCreated, WPStatusChanged,
and MissionClosed.

These tests pin three reconciliation guarantees from WP04:

1. Each canonical payload model rejects unknown fields with Pydantic's
   ``ValidationError`` (covering FR-003, C-002).
2. Each canonical payload model accepts a known-good baseline shape
   (covering FR-004, the canonical baseline for downstream tranches).
3. ``WPStatusChanged`` accepts ``Lane.IN_REVIEW`` as ``to_lane`` (the
   handshake to WP01's lane-vocabulary expansion).
4. The committed JSON Schemas match what ``schemas.generate`` produces (a
   schema-drift sentinel) and a known-good canonical instance validates
   against the regenerated schema (FR-003, schema parity).
5. ``MissionClosedPayload`` rejects historical-shape envelopes carrying
   speculative legacy fields (the SC-004 cross-shape evidence).

Refs: FR-003, FR-004, C-002, C-004, SC-004 of mission
``teamspace-event-contract-foundation-01KQHDE4``.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

import pytest
from jsonschema import Draft202012Validator
from pydantic import ValidationError as PydanticValidationError

from spec_kitty_events.lifecycle import (
    MissionClosedPayload,
    MissionCreatedPayload,
)
from spec_kitty_events.schemas import generate as schema_gen
from spec_kitty_events.status import Lane, StatusTransitionPayload


SCHEMA_DIR = Path(schema_gen.__file__).parent


# ---------------------------------------------------------------------------
# Canonical baseline shapes
# ---------------------------------------------------------------------------


def _baseline_mission_created() -> Dict[str, Any]:
    """Known-good MissionCreatedPayload shape."""
    return {
        "mission_id": "01KQHDE4ABCDEF0123456789AB",
        "mission_slug": "demo-mission-01KQHDE4",
        "mission_number": 42,
        "mission_type": "software-dev",
        "target_branch": "main",
        "wp_count": 7,
        "friendly_name": "Demo Mission",
        "purpose_tldr": "Demonstrate the canonical MissionCreated payload.",
        "purpose_context": "WP04 reconciliation test fixture.",
        "created_at": "2026-05-01T10:00:00Z",
    }


def _baseline_mission_closed() -> Dict[str, Any]:
    """Known-good MissionClosedPayload shape."""
    return {
        "mission_slug": "demo-mission-01KQHDE4",
        "mission_number": 42,
        "mission_type": "software-dev",
    }


def _baseline_status_transition() -> Dict[str, Any]:
    """Known-good StatusTransitionPayload shape (FOR_REVIEW → IN_REVIEW)."""
    return {
        "mission_slug": "demo-mission-01KQHDE4",
        "wp_id": "WP01",
        "from_lane": Lane.FOR_REVIEW.value,
        "to_lane": Lane.IN_REVIEW.value,
        "actor": "claude",
        "force": False,
        "reason": None,
        "execution_mode": "worktree",
        "review_ref": None,
        "evidence": None,
    }


# ---------------------------------------------------------------------------
# 1. Each model accepts the canonical baseline.
# ---------------------------------------------------------------------------


def test_FR_004_mission_created_accepts_canonical_baseline() -> None:
    payload = MissionCreatedPayload(**_baseline_mission_created())
    assert payload.mission_slug == "demo-mission-01KQHDE4"
    assert payload.mission_number == 42


def test_FR_004_mission_closed_accepts_canonical_baseline() -> None:
    payload = MissionClosedPayload(**_baseline_mission_closed())
    assert payload.mission_slug == "demo-mission-01KQHDE4"
    assert payload.mission_type == "software-dev"


def test_FR_004_status_transition_accepts_canonical_baseline() -> None:
    payload = StatusTransitionPayload(**_baseline_status_transition())
    assert payload.to_lane == Lane.IN_REVIEW
    assert payload.from_lane == Lane.FOR_REVIEW


# ---------------------------------------------------------------------------
# 2. Each model rejects unknown fields (extra='forbid').
# ---------------------------------------------------------------------------


def test_FR_003_mission_created_rejects_extra_fields() -> None:
    bad = _baseline_mission_created()
    bad["legacy_aggregate_id"] = "legacy-123"
    with pytest.raises(PydanticValidationError) as exc_info:
        MissionCreatedPayload(**bad)
    assert "legacy_aggregate_id" in str(exc_info.value)


def test_FR_003_mission_closed_rejects_extra_fields() -> None:
    bad = _baseline_mission_closed()
    bad["legacy_aggregate_id"] = "legacy-123"
    bad["closed_by"] = "user"
    with pytest.raises(PydanticValidationError) as exc_info:
        MissionClosedPayload(**bad)
    msg = str(exc_info.value)
    # Pydantic surfaces extra-field violations; either of the bogus keys is fine.
    assert "legacy_aggregate_id" in msg or "closed_by" in msg


def test_FR_003_status_transition_rejects_extra_fields() -> None:
    bad = _baseline_status_transition()
    bad["legacy_payload_version"] = "v0"
    with pytest.raises(PydanticValidationError) as exc_info:
        StatusTransitionPayload(**bad)
    assert "legacy_payload_version" in str(exc_info.value)


# ---------------------------------------------------------------------------
# 3. WPStatusChanged accepts Lane.IN_REVIEW (handshake to WP01).
# ---------------------------------------------------------------------------


def test_FR_004_status_transition_accepts_in_review_to_lane() -> None:
    """WP01 added Lane.IN_REVIEW to the canonical vocabulary; this test
    pins that the WPStatusChanged model accepts it as ``to_lane`` from
    FOR_REVIEW (and, separately, as a transition out of IN_PROGRESS via
    FOR_REVIEW first — see status.py LANE_TRANSITIONS).
    """
    raw = _baseline_status_transition()
    raw["from_lane"] = Lane.FOR_REVIEW.value
    raw["to_lane"] = Lane.IN_REVIEW.value
    payload = StatusTransitionPayload(**raw)
    assert payload.to_lane is Lane.IN_REVIEW


def test_FR_004_status_transition_accepts_in_review_from_lane() -> None:
    """A transition out of IN_REVIEW (e.g. back to PLANNED on rollback)."""
    raw = _baseline_status_transition()
    raw["from_lane"] = Lane.IN_REVIEW.value
    raw["to_lane"] = Lane.PLANNED.value
    payload = StatusTransitionPayload(**raw)
    assert payload.from_lane is Lane.IN_REVIEW
    assert payload.to_lane is Lane.PLANNED


# ---------------------------------------------------------------------------
# 4. Schema-drift parity: regenerated schemas match committed files, and a
#    canonical instance validates against the schema.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "schema_name",
    [
        "mission_created_payload",
        "mission_closed_payload",
        "status_transition_payload",
    ],
)
def test_C_004_committed_schema_matches_generator_output(schema_name: str) -> None:
    """The committed *.schema.json must equal what generate.py produces."""
    schemas = schema_gen.generate_all_schemas()
    expected = schema_gen.schema_to_json(schemas[schema_name])
    actual = (SCHEMA_DIR / f"{schema_name}.schema.json").read_text(encoding="utf-8")
    assert actual == expected, f"Schema drift detected in {schema_name}"


def test_C_004_mission_created_baseline_validates_against_committed_schema() -> None:
    schema = json.loads(
        (SCHEMA_DIR / "mission_created_payload.schema.json").read_text(encoding="utf-8")
    )
    Draft202012Validator(schema).validate(_baseline_mission_created())


def test_C_004_mission_closed_baseline_validates_against_committed_schema() -> None:
    schema = json.loads(
        (SCHEMA_DIR / "mission_closed_payload.schema.json").read_text(encoding="utf-8")
    )
    Draft202012Validator(schema).validate(_baseline_mission_closed())


def test_C_004_status_transition_baseline_validates_against_committed_schema() -> None:
    schema = json.loads(
        (SCHEMA_DIR / "status_transition_payload.schema.json").read_text(encoding="utf-8")
    )
    # Drop None fields that the schema may not accept under default JSON shapes.
    instance = {
        k: v for k, v in _baseline_status_transition().items() if v is not None
    }
    Draft202012Validator(schema).validate(instance)


# ---------------------------------------------------------------------------
# 5. SC-004 cross-shape evidence: MissionClosed rejects historical-shape
#    envelopes that carry speculative legacy fields.
# ---------------------------------------------------------------------------


def test_SC_004_mission_closed_rejects_historical_cli_shape() -> None:
    """The spec called out CLI-vs-library disagreement for MissionClosed.

    This test mimics a hypothetical historical CLI emission carrying
    fields the canonical model does not declare (e.g. ``legacy_aggregate_id``,
    ``closed_at``, ``closed_by``). Under ``extra='forbid'`` the canonical
    model must reject it. Producers are expected to be normalized by the
    CLI canonicalizer before hitting the canonical model.
    """
    historical = {
        **_baseline_mission_closed(),
        "legacy_aggregate_id": "legacy-99",
        "closed_at": "2026-05-01T11:22:33Z",
        "closed_by": "ci-bot",
    }
    with pytest.raises(PydanticValidationError):
        MissionClosedPayload(**historical)


def test_SC_004_mission_created_rejects_historical_cli_shape() -> None:
    """Mirror of the MissionClosed cross-shape test for MissionCreated."""
    historical = {
        **_baseline_mission_created(),
        "legacy_workflow_kind": "research",
        "raw_envelope": {"foo": "bar"},
    }
    with pytest.raises(PydanticValidationError):
        MissionCreatedPayload(**historical)
