"""Strict journal profile: a deterministic, structured envelope validator.

F1-T1 (7.0.0) publishes a *strict* profile over the existing canonical
envelope and lifecycle/WP contracts, opted into by new producers/readers
(the F2 journal, D1 projector, Z1 client) without changing :class:`Event`
itself — which stays lenient so today's local-CLI readers and the legacy
emitter keep working unchanged (decision 3, ``COMPATIBILITY.md``).

:func:`validate_strict_envelope` is the single public entry point. It is
pure (no I/O, no mutation), deterministic (same input -> byte-identical
output, same order every call), and *collect-all* for the checks that can
run independently, so a caller sees every defect in one pass rather than
one exception per submission.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Any, Literal, Mapping, Optional, Tuple

from pydantic import BaseModel, ConfigDict, Field
from pydantic import ValidationError as PydanticValidationError

from spec_kitty_events._iso8601 import normalize_iso8601_shape as _normalize_iso8601_shape
from spec_kitty_events.conformance.validators import validate_event
from spec_kitty_events.forbidden_keys import FORBIDDEN_LEGACY_KEYS, find_forbidden_keys
from spec_kitty_events.harness_observation import (
    FORBIDDEN_OBSERVATION_KEYS,
    HARNESS_OBSERVATION,
    ObservationKind,
    PAYLOAD_ID_BY_KIND,
)
from spec_kitty_events.lifecycle import MISSION_EVENT_TYPES
from spec_kitty_events.mission_next import (
    DECISION_INPUT_ANSWERED,
    DECISION_INPUT_REQUESTED,
    MISSION_RUN_COMPLETED,
    MISSION_RUN_STARTED,
    NEXT_STEP_AUTO_COMPLETED,
    NEXT_STEP_ISSUED,
)
from spec_kitty_events.models import Event
from spec_kitty_events.project_lifecycle import (
    PLAN_COMPLETED,
    PLAN_STARTED,
    PROJECT_INITIALIZED,
    SPECIFY_COMPLETED,
    SPECIFY_STARTED,
    TASKS_COMPLETED,
    TASKS_STARTED,
    WP_CREATED,
)
from spec_kitty_events.status import WP_STATUS_CHANGED
from spec_kitty_events.validation_errors import ValidationError, ValidationErrorCode

__all__ = [
    "STRICT_PROFILE_ID",
    "STRICT_ENVELOPE_KEYS",
    "STRICT_EVENT_TYPES",
    "STRICT_TIMESTAMP_RULES",
    "FORBIDDEN_LEGACY_AGGREGATE_NAMES",
    "validate_strict_envelope",
    "SupportRow",
    "SUPPORT_MATRIX",
    "support_matrix_digest",
]


STRICT_PROFILE_ID: str = "journal/v1"

# The 14 Event fields (models.py); ALL must be present under the strict
# profile — nullable ones (causation_id, project_slug) as explicit null,
# defaulted ones (schema_version, data_tier) explicit (draft §3.2, decision
# 13). One rule, no subset list to maintain.
STRICT_ENVELOPE_KEYS: frozenset[str] = frozenset(
    {
        "event_id",
        "event_type",
        "aggregate_id",
        "payload",
        "timestamp",
        "build_id",
        "node_id",
        "lamport_clock",
        "causation_id",
        "project_uuid",
        "project_slug",
        "correlation_id",
        "schema_version",
        "data_tier",
    }
)

# 9 mission + 6 mission-run (volatile, E2) + 1 WP-lane + 8 project/artifact
# + 1 observation = 25 (exhaustive; excluded names are listed in the draft's
# prose). ``NextStepPlanned`` stays excluded: its payload contract is
# reserved, so a strict envelope of that type could not be payload-validated.
STRICT_EVENT_TYPES: frozenset[str] = frozenset(
    MISSION_EVENT_TYPES
    | {
        MISSION_RUN_STARTED,
        NEXT_STEP_ISSUED,
        NEXT_STEP_AUTO_COMPLETED,
        DECISION_INPUT_REQUESTED,
        DECISION_INPUT_ANSWERED,
        MISSION_RUN_COMPLETED,
    }
    | {WP_STATUS_CHANGED}
    | {
        WP_CREATED,
        PROJECT_INITIALIZED,
        SPECIFY_STARTED,
        SPECIFY_COMPLETED,
        PLAN_STARTED,
        PLAN_COMPLETED,
        TASKS_STARTED,
        TASKS_COMPLETED,
    }
    | {HARNESS_OBSERVATION}
)

STRICT_TIMESTAMP_RULES: str = "iso8601-tz-aware"

# Legacy mission-domain aggregate names (issue #10): pre-cutover envelopes
# named their aggregate ``feature/<slug>`` or ``feature_catalog/<n>``;
# canonical ids are ``mission/...`` (and ``session/<id>`` for
# HarnessObservation). The prefix rule shipped with the deleted cutover
# artifact; 8.0.0 re-homes it onto this profile so every legacy surface it
# policed — keys, event names, aggregate names — fails closed on live paths
# again. Like FORBIDDEN_LEGACY_KEYS, membership changes are a contract
# change under contracts/versioning-and-compatibility.md.
FORBIDDEN_LEGACY_AGGREGATE_NAMES: frozenset[str] = frozenset({"feature", "feature_catalog"})

_REQUIRED_SCHEMA_VERSION = "3.0.0"

# E2 lands inside the same unreleased wave as epic E2's major bump
# (planning repo issue #3: delete sync/legacy/cutover, "new major; both
# consumers bump"). The mission-run rows are first strict-admitted by that
# release, not by 2.3.0 where their models appeared. Move this value with
# the release number if it changes.
_E2_STRICT_SINCE = "8.0.0"
_STRICT_PROFILE_MIN_CONSUMER_PACKAGE = "7.0.0"


# ── Support matrix (draft §3.4) ──────────────────────────────────────────────
#
# The machine-readable authority downstream candidates (F2-T1, F3-T1, D1-T1,
# Z1-T1) pin by digest in `declared_dependency_contracts` to know which
# payload IDs / event types this package supports. Published copy:
# `src/spec_kitty_events/support_matrix.json` (package data), generated by
# `schemas/generate.py` and covered by its `--check` drift gate.


class SupportRow(BaseModel):
    """One row of the machine-readable support matrix.

    E2 (volatile mission/WP vocabulary): the ``WPStatusChanged``,
    ``MissionCreated``, ``MissionClosed``, and ``PhaseEntered`` rows moved
    from ``journal`` to ``volatile`` durability, and the mission-run family
    (``mission_next``) joined as six new volatile rows — 14 journal + 16
    volatile = 30 rows, exactly six distinct payload IDs (the observation
    ones).
    """

    # populate_by_name=True: `schema_` is a Python-side rename (pydantic's
    # BaseModel already defines a deprecated `schema` classmethod, so a field
    # literally named `schema` shadows it and fails `mypy --strict`); the
    # `alias="schema"` plus `by_alias=True` on every dump/serialization below
    # keeps the wire/JSON contract at exactly `schema` per draft §3.4.
    model_config = ConfigDict(frozen=True, extra="forbid", populate_by_name=True)

    event_type: str
    kind: Optional[str] = None
    payload_id: Optional[str] = None
    family: Literal["lifecycle", "wp", "project", "mission_run", "harness"]
    durability: Literal["journal", "volatile"]
    model: str
    schema_: str = Field(alias="schema")
    strict: Literal[True] = True
    introduced_in: str
    strict_since: str
    status: Literal["supported", "reserved", "retired"]
    min_consumer_package: str


def _journal_row(
    *,
    event_type: str,
    family: Literal["lifecycle", "wp", "project"],
    model: str,
    schema: str,
    introduced_in: str,
    strict_since: Optional[str] = None,
) -> SupportRow:
    return SupportRow(
        event_type=event_type,
        kind=None,
        payload_id=None,
        family=family,
        durability="journal",
        model=model,
        schema=schema,
        strict=True,
        introduced_in=introduced_in,
        strict_since=strict_since or introduced_in,
        status="supported",
        min_consumer_package=_STRICT_PROFILE_MIN_CONSUMER_PACKAGE,
    )


def _volatile_row(
    *,
    event_type: str,
    family: Literal["lifecycle", "wp", "mission_run"],
    model: str,
    schema: str,
    introduced_in: str,
    strict_since: str | None = None,
) -> SupportRow:
    """A row of the ephemeral, broadcast-only vocabulary (E2).

    Volatile families are carried through each team's Zeitgeist relay as
    bounded attrs (``spec_kitty_events.zeitgeist_attrs``) and observed for
    the retention window only; they never form durable server-side state.
    """
    row_strict_since = strict_since or introduced_in
    return SupportRow(
        event_type=event_type,
        kind=None,
        payload_id=None,
        family=family,
        durability="volatile",
        model=model,
        schema=schema,
        strict=True,
        introduced_in=introduced_in,
        strict_since=row_strict_since,
        status="supported",
        min_consumer_package=strict_since or _STRICT_PROFILE_MIN_CONSUMER_PACKAGE,
    )


def _observation_row(kind: ObservationKind) -> SupportRow:
    return SupportRow(
        event_type=HARNESS_OBSERVATION,
        kind=kind.value,
        payload_id=PAYLOAD_ID_BY_KIND[kind],
        family="harness",
        durability="volatile",
        model="spec_kitty_events.harness_observation.HarnessObservationPayload",
        schema="harness_observation_payload.schema.json",
        strict=True,
        introduced_in="7.0.0",
        strict_since="7.0.0",
        status="supported",
        min_consumer_package=_STRICT_PROFILE_MIN_CONSUMER_PACKAGE,
    )


# introduced_in values are traced to the git commit that first added each
# model/constant and the pyproject.toml version at that commit (or, for
# commits landed between a release-harden commit and the next version-bump
# commit, the first *published* version containing them):
#   MissionCreated/MissionClosed  -> 3.0.0  (944166697, "land mission
#     contract cutover on main")
#   MissionStarted/MissionCompleted/MissionCancelled/PhaseEntered/
#     ReviewRollback               -> 0.3.0-alpha (2cbbcb8, "add lifecycle
#     payload models and MissionStatus enum")
#   WPStatusChanged                -> 0.2.0-alpha (d990b46, "Add enums,
#     evidence models, and public API for WP01")
#   MissionReopened/FollowUpRecorded -> 6.1.0 (CHANGELOG.md [6.1.0])
#   WPCreated/ProjectInitialized/Specify*/Plan*/Tasks* -> 5.1.0
#     (project_lifecycle.py added by 5155d0f, an ancestor of the 5.1.0
#     release commit e132d29 and a descendant of the 5.0.0 release-harden
#     commit 062dd97; CHANGELOG.md's 5.1.0 section does not mention this
#     module by name -- a pre-existing documentation gap, not introduced by
#     this row).
SUPPORT_MATRIX: Tuple[SupportRow, ...] = (
    # Volatile since E2 (Ephemeral Team Status): the mission/WP moment
    # vocabulary broadcasts through the team's Zeitgeist relay instead of
    # syncing into durable server-side state.
    _volatile_row(
        event_type="MissionCreated",
        family="lifecycle",
        model="spec_kitty_events.lifecycle.MissionCreatedPayload",
        schema="mission_created_payload.schema.json",
        introduced_in="3.0.0",
    ),
    _volatile_row(
        event_type="MissionClosed",
        family="lifecycle",
        model="spec_kitty_events.lifecycle.MissionClosedPayload",
        schema="mission_closed_payload.schema.json",
        introduced_in="3.0.0",
    ),
    _journal_row(
        event_type="MissionStarted",
        family="lifecycle",
        model="spec_kitty_events.lifecycle.MissionStartedPayload",
        schema="mission_started_payload.schema.json",
        introduced_in="0.3.0-alpha",
        strict_since="7.0.0",
    ),
    _journal_row(
        event_type="MissionCompleted",
        family="lifecycle",
        model="spec_kitty_events.lifecycle.MissionCompletedPayload",
        schema="mission_completed_payload.schema.json",
        introduced_in="0.3.0-alpha",
        strict_since="7.0.0",
    ),
    _journal_row(
        event_type="MissionCancelled",
        family="lifecycle",
        model="spec_kitty_events.lifecycle.MissionCancelledPayload",
        schema="mission_cancelled_payload.schema.json",
        introduced_in="0.3.0-alpha",
        strict_since="7.0.0",
    ),
    _volatile_row(
        event_type="PhaseEntered",
        family="lifecycle",
        model="spec_kitty_events.lifecycle.PhaseEnteredPayload",
        schema="phase_entered_payload.schema.json",
        introduced_in="0.3.0-alpha",
        strict_since="7.0.0",
    ),
    _journal_row(
        event_type="ReviewRollback",
        family="lifecycle",
        model="spec_kitty_events.lifecycle.ReviewRollbackPayload",
        schema="review_rollback_payload.schema.json",
        introduced_in="0.3.0-alpha",
        strict_since="7.0.0",
    ),
    _journal_row(
        event_type="MissionReopened",
        family="lifecycle",
        model="spec_kitty_events.lifecycle.MissionReopenedPayload",
        schema="mission_reopened_payload.schema.json",
        introduced_in="6.1.0",
    ),
    _journal_row(
        event_type="FollowUpRecorded",
        family="lifecycle",
        model="spec_kitty_events.lifecycle.FollowUpRecordedPayload",
        schema="follow_up_recorded_payload.schema.json",
        introduced_in="6.1.0",
    ),
    _volatile_row(
        event_type="WPStatusChanged",
        family="wp",
        model="spec_kitty_events.status.StatusTransitionPayload",
        schema="status_transition_payload.schema.json",
        introduced_in="0.2.0-alpha",
    ),
    _journal_row(
        event_type="WPCreated",
        family="project",
        model="spec_kitty_events.project_lifecycle.WPCreatedPayload",
        schema="wp_created_payload.schema.json",
        introduced_in="5.1.0",
    ),
    _journal_row(
        event_type="ProjectInitialized",
        family="project",
        model="spec_kitty_events.project_lifecycle.ProjectInitializedPayload",
        schema="project_initialized_payload.schema.json",
        introduced_in="5.1.0",
    ),
    _journal_row(
        event_type="SpecifyStarted",
        family="project",
        model="spec_kitty_events.project_lifecycle.SpecifyStartedPayload",
        schema="specify_started_payload.schema.json",
        introduced_in="5.1.0",
    ),
    _journal_row(
        event_type="SpecifyCompleted",
        family="project",
        model="spec_kitty_events.project_lifecycle.SpecifyCompletedPayload",
        schema="specify_completed_payload.schema.json",
        introduced_in="5.1.0",
    ),
    _journal_row(
        event_type="PlanStarted",
        family="project",
        model="spec_kitty_events.project_lifecycle.PlanStartedPayload",
        schema="plan_started_payload.schema.json",
        introduced_in="5.1.0",
    ),
    _journal_row(
        event_type="PlanCompleted",
        family="project",
        model="spec_kitty_events.project_lifecycle.PlanCompletedPayload",
        schema="plan_completed_payload.schema.json",
        introduced_in="5.1.0",
    ),
    _journal_row(
        event_type="TasksStarted",
        family="project",
        model="spec_kitty_events.project_lifecycle.TasksStartedPayload",
        schema="tasks_started_payload.schema.json",
        introduced_in="5.1.0",
    ),
    _journal_row(
        event_type="TasksCompleted",
        family="project",
        model="spec_kitty_events.project_lifecycle.TasksCompletedPayload",
        schema="tasks_completed_payload.schema.json",
        introduced_in="5.1.0",
    ),
    # Mission-run runtime family (mission_next), volatile since E2: run-scoped
    # execution moments broadcast with the rest of the ephemeral vocabulary.
    # ``NextStepPlanned`` has no row — its payload contract is reserved.
    _volatile_row(
        event_type=MISSION_RUN_STARTED,
        family="mission_run",
        model="spec_kitty_events.mission_next.MissionRunStartedPayload",
        schema="mission_run_started_payload.schema.json",
        introduced_in="2.3.0",
        strict_since=_E2_STRICT_SINCE,
    ),
    _volatile_row(
        event_type=NEXT_STEP_ISSUED,
        family="mission_run",
        model="spec_kitty_events.mission_next.NextStepIssuedPayload",
        schema="next_step_issued_payload.schema.json",
        introduced_in="2.3.0",
        strict_since=_E2_STRICT_SINCE,
    ),
    _volatile_row(
        event_type=NEXT_STEP_AUTO_COMPLETED,
        family="mission_run",
        model="spec_kitty_events.mission_next.NextStepAutoCompletedPayload",
        schema="next_step_auto_completed_payload.schema.json",
        introduced_in="2.3.0",
        strict_since=_E2_STRICT_SINCE,
    ),
    _volatile_row(
        event_type=DECISION_INPUT_REQUESTED,
        family="mission_run",
        model="spec_kitty_events.mission_next.DecisionInputRequestedPayload",
        schema="decision_input_requested_payload.schema.json",
        introduced_in="2.3.0",
        strict_since=_E2_STRICT_SINCE,
    ),
    _volatile_row(
        event_type=DECISION_INPUT_ANSWERED,
        family="mission_run",
        model="spec_kitty_events.mission_next.DecisionInputAnsweredPayload",
        schema="decision_input_answered_payload.schema.json",
        introduced_in="2.3.0",
        strict_since=_E2_STRICT_SINCE,
    ),
    _volatile_row(
        event_type=MISSION_RUN_COMPLETED,
        family="mission_run",
        model="spec_kitty_events.mission_next.MissionRunCompletedPayload",
        schema="mission_run_completed_payload.schema.json",
        introduced_in="2.3.0",
        strict_since=_E2_STRICT_SINCE,
    ),
    *(_observation_row(kind) for kind in ObservationKind),
)
"""30 rows: 14 journal + 16 volatile (draft §3.4 as amended by E2). Order is
fixed (source order above) so `support_matrix_digest()` and the generated
`support_matrix.json` are byte-stable across runs without an explicit sort."""


def _support_matrix_canonical_json() -> str:
    rows = [row.model_dump(mode="json", by_alias=True) for row in SUPPORT_MATRIX]
    return json.dumps(rows, indent=2, sort_keys=True) + "\n"


def support_matrix_digest() -> str:
    """SHA-256 digest of the canonical JSON serialization of SUPPORT_MATRIX.

    Deterministic and stable across generations in a clean runner (draft §4
    row C7) -- the input is a fixed tuple of frozen pydantic rows serialized
    with `sort_keys=True`, so process/interpreter-order artifacts cannot
    leak in. This is what downstream candidates pin in
    `declared_dependency_contracts` (draft §3.4).
    """
    canonical = _support_matrix_canonical_json().encode("utf-8")
    return f"sha256:{hashlib.sha256(canonical).hexdigest()}"


def _envelope_shape_error(**details: object) -> ValidationError:
    return ValidationError(
        code=ValidationErrorCode.ENVELOPE_SHAPE_INVALID,
        message="envelope shape invalid",
        path=[],
        details=dict(details),
    )


def _parse_iso8601(value: str) -> datetime | None:
    """Best-effort ISO-8601 parse. Returns None when unparsable.

    A well-formed value has at most one trailing ``Z``; a doubled/mixed-case
    trailing designator (e.g. ``...00ZZ``/``...00zZ``) is rejected by
    ``_normalize_iso8601_shape``'s case-folded residual guard before the
    reshape regex ever runs, so it is never laundered into something Python
    3.11+'s laxer ``fromisoformat`` would otherwise accept while 3.10 rejects
    it (spec-kitty-events#55/#107/#115/#122/#135).
    """
    try:
        return datetime.fromisoformat(_normalize_iso8601_shape(value))
    except ValueError:
        return None


def validate_strict_envelope(record: Any) -> Tuple[ValidationError, ...]:
    """Validate a raw JSON-shaped envelope against the strict journal profile.

    Deterministic, collect-all, pure. Empty tuple == accepted. Check order
    (fixed, each emits at most one error per finding):

    1. wrapper is a JSON object
    2. every STRICT_ENVELOPE_KEYS member present (explicit null counts)
    3. no key outside STRICT_ENVELOPE_KEYS
    4. forbidden keys anywhere (recursive walk; FORBIDDEN_LEGACY_KEYS,
       plus FORBIDDEN_OBSERVATION_KEYS when event_type == HarnessObservation)
    5. aggregate_id does not use a forbidden legacy name prefix
       (FORBIDDEN_LEGACY_AGGREGATE_NAMES)
    6. schema_version present, str, == "3.0.0"
    7. event_type in STRICT_EVENT_TYPES
    8. timestamp is str, ISO-8601, tz-aware

    Steps 1-8 all run (collect-all); steps 9-10 are skipped when any of 1-3
    or 6-7 failed (no cascading noise from a record already known to be
    unusable at the envelope/type level).

    9. Event.model_validate(record)
    10. validate_event(record, event_type, strict=False) model violations
    """
    errors: list[ValidationError] = []

    # Step 1: wrapper is a JSON object.
    if not isinstance(record, Mapping):
        errors.append(_envelope_shape_error(wrapper=type(record).__name__))
        return tuple(errors)

    # Step 2: every key present (explicit null counts as present).
    missing = sorted(key for key in STRICT_ENVELOPE_KEYS if key not in record)
    envelope_shape_failed = False
    if missing:
        errors.append(_envelope_shape_error(missing=missing))
        envelope_shape_failed = True

    # Step 3: no key outside the closed set.
    extra = sorted(key for key in record if key not in STRICT_ENVELOPE_KEYS)
    if extra:
        errors.append(_envelope_shape_error(extra=extra))
        envelope_shape_failed = True

    # Step 4: forbidden keys anywhere (recursive walk over the whole record).
    forbidden_set = FORBIDDEN_LEGACY_KEYS
    if record.get("event_type") == HARNESS_OBSERVATION:
        forbidden_set = FORBIDDEN_LEGACY_KEYS | FORBIDDEN_OBSERVATION_KEYS
    errors.extend(find_forbidden_keys(record, forbidden=forbidden_set))

    # Step 5: no forbidden legacy aggregate-name prefix (issue #10). Like
    # step 4, a hit here does not set envelope_shape_failed/type_failed —
    # the model layers below still run and may report further defects.
    aggregate_id = record.get("aggregate_id")
    if isinstance(aggregate_id, str):
        aggregate_name = aggregate_id.split("/", 1)[0]
        if aggregate_name in FORBIDDEN_LEGACY_AGGREGATE_NAMES:
            errors.append(
                ValidationError(
                    code=ValidationErrorCode.FORBIDDEN_AGGREGATE_NAME,
                    message=(
                        f"aggregate_id uses forbidden legacy aggregate name '{aggregate_name}'"
                    ),
                    path=["aggregate_id"],
                    details={"aggregate_name": aggregate_name},
                )
            )

    # Step 6: schema_version present, str, exact match.
    type_failed = False
    schema_version = record.get("schema_version")
    if not isinstance(schema_version, str) or schema_version != _REQUIRED_SCHEMA_VERSION:
        errors.append(
            ValidationError(
                code=ValidationErrorCode.UNSUPPORTED_SCHEMA_VERSION,
                message="unsupported schema_version for the strict journal profile",
                path=["schema_version"],
                details={"found": schema_version, "required": _REQUIRED_SCHEMA_VERSION},
            )
        )
        type_failed = True

    # Step 7: event_type admitted by the profile.
    event_type = record.get("event_type")
    if event_type not in STRICT_EVENT_TYPES:
        errors.append(
            ValidationError(
                code=ValidationErrorCode.UNKNOWN_EVENT_TYPE,
                message="event_type is not admitted by the strict journal profile",
                path=["event_type"],
                details={"event_type": event_type, "profile": STRICT_PROFILE_ID},
            )
        )
        type_failed = True

    # Step 8: timestamp shape (only when the key is present at all — its
    # absence is already reported by step 2 and we do not want a second,
    # confusing error about the same missing field).
    if "timestamp" in record:
        timestamp_value = record["timestamp"]
        if not isinstance(timestamp_value, str):
            errors.append(
                ValidationError(
                    code=ValidationErrorCode.ENVELOPE_SHAPE_INVALID,
                    message="timestamp must be an ISO-8601 string",
                    path=["timestamp"],
                    details={"reason": "not_string"},
                )
            )
        else:
            parsed = _parse_iso8601(timestamp_value)
            if parsed is None:
                errors.append(
                    ValidationError(
                        code=ValidationErrorCode.ENVELOPE_SHAPE_INVALID,
                        message="timestamp is not a parsable ISO-8601 value",
                        path=["timestamp"],
                        details={"reason": "unparsable"},
                    )
                )
            elif parsed.tzinfo is None:
                errors.append(
                    ValidationError(
                        code=ValidationErrorCode.ENVELOPE_SHAPE_INVALID,
                        message="timestamp must be timezone-aware",
                        path=["timestamp"],
                        details={"reason": "naive"},
                    )
                )

    if envelope_shape_failed or type_failed:
        # No cascading noise: a record already known unusable at the
        # envelope/type level is not also run through the (much more
        # detailed, and potentially misleading) model layers.
        return tuple(errors)

    # Step 9: Event.model_validate(record).
    try:
        Event.model_validate(dict(record))
    except PydanticValidationError as exc:
        for err in exc.errors():
            loc = list(err["loc"])
            if loc and loc[0] == "payload":
                errors.append(
                    ValidationError(
                        code=ValidationErrorCode.PAYLOAD_SCHEMA_FAIL,
                        message=err["msg"],
                        path=[str(part) for part in loc],
                        details={"type": err["type"]},
                    )
                )
            else:
                errors.append(
                    ValidationError(
                        code=ValidationErrorCode.ENVELOPE_SHAPE_INVALID,
                        message=err["msg"],
                        path=[str(part) for part in loc],
                        details={"type": err["type"]},
                    )
                )

    # Step 10: typed payload / semantic validation via the existing registry.
    # event_type is known to be a str member of STRICT_EVENT_TYPES here:
    # type_failed is False, so step 7 above confirmed membership.
    assert isinstance(event_type, str)
    result = validate_event(dict(record), event_type, strict=False)
    for violation in result.model_violations:
        if violation.violation_type == "transition_rule":
            errors.append(
                ValidationError(
                    code=ValidationErrorCode.UNKNOWN_LANE,
                    message=violation.message,
                    path=["payload"],
                    details={"violation_type": violation.violation_type},
                )
            )
        else:
            field_parts = [part for part in violation.field.split(".") if part]
            errors.append(
                ValidationError(
                    code=ValidationErrorCode.PAYLOAD_SCHEMA_FAIL,
                    message=violation.message,
                    path=["payload", *field_parts],
                    details={"violation_type": violation.violation_type},
                )
            )

    return tuple(errors)
