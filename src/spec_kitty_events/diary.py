"""Spec Kitty status diary (``status.events.jsonl``) contracts and reducer.

The *diary* is the append-only JSONL event log each Spec Kitty mission keeps
at ``kitty-specs/<mission>/status.events.jsonl``. Its wire format is part of
this package's contract: the CLI writes it, and the Team Kitty repo dossier
reduces it directly at a pushed commit instead of trusting the derived
``status.json`` (Repo Dossier decision D, planning issue
EXPERIMENTAL-spec-kitty-events#41).

This module is the canonical ``status.events.jsonl -> kanban state``
reducer. It was moved verbatim from the CLI
(``specify_cli/status/models.py`` + ``specify_cli/status/reducer.py`` +
the pure halves of ``specify_cli/status/store.py``, ``core/paths.py`` and
``mission_metadata.py``) so the CLI and Team Kitty share one implementation.
Behaviour-preserving adaptations are limited to:

* ``Lane`` is declared as ``(str, Enum)`` with an explicit ``__str__``
  instead of ``enum.StrEnum`` -- this package still supports Python 3.10,
  where ``StrEnum`` does not exist. The explicit ``__str__`` reproduces
  ``StrEnum``'s ``str(member) == member.value`` on every supported version,
  which the reducer's ``str(event.to_lane)`` snapshot slot relies on.
* The entry point takes raw wire rows (:func:`reduce`) rather than typed
  records; :func:`parse_diary` performs the row partition the CLI's
  ``store.read_event_stream`` performed, minus the filesystem I/O and the
  legacy ``meta.json`` mission_id back-fill (a dossier reader resolves
  identity from the rows it already has).
* ``State`` is the reduced snapshot. It carries every field the CLI's
  ``StatusSnapshot`` carries except ``retrospective``: that attachment is
  computed by the CLI's materialize step after reduction (it needs the
  CLI-side retrospective schema), never by :func:`reduce`.

Wire format (one JSON object per line)::

    {"event_id": "01HXYZ...", "mission_slug": "034-feature", "wp_id": "WP01",
     "from_lane": "planned", "to_lane": "claimed", "at": "2026-02-08T12:00:00Z",
     "actor": "claude", "force": false, "execution_mode": "worktree",
     "reason": null, "review_ref": null, "evidence": null}

Row partition rules (:func:`parse_diary`):

* ``kind == "annotation"`` decodes as an off-axis :class:`InnerStateChanged`
  runtime-state annotation and is folded by the reducer.
* A row carrying an unknown ``kind`` value fails loud
  (:class:`DiaryError`) -- silently skipping it would lose runtime state.
* Any other row carrying an ``event_type`` key (mission-level events from
  non-status emitters: Decision Point events and any future writer that
  shares this file) or a ``retrospective.*`` ``event_name`` is ignored in
  place -- descriptive lifecycle events, not lane transitions.
* Everything else must decode as a lane :class:`StatusEvent`; a malformed
  lane row raises :class:`DiaryError`.
"""

from __future__ import annotations

import logging
import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field, fields
from enum import Enum
from typing import Any, ClassVar, TypeAlias

from spec_kitty_events.models import SpecKittyEventsError

logger = logging.getLogger(__name__)

__all__ = [
    "ANNOTATION_KIND",
    "NON_DISPLAY_LANES",
    "SNAPSHOT_FILENAME",
    "ActorField",
    "DiaryError",
    "DoneEvidence",
    "EventStream",
    "InnerStateChanged",
    "Lane",
    "RepoEvidence",
    "ReviewApproval",
    "ReviewOverride",
    "ReviewResult",
    "State",
    "Status",
    "StatusEvent",
    "VerificationResult",
    "WPInnerStateDelta",
    "actor_identity_str",
    "assert_safe_path_segment",
    "decode_actor",
    "mission_identity_fields",
    "mission_number_from_slug",
    "parse_diary",
    "reduce",
    "reduce_parsed",
    "safe_mission_slug",
    "with_tracked_mission_slug_aliases",
]


class DiaryError(SpecKittyEventsError):
    """Raised when a status-diary row cannot be decoded.

    Fail-loud counterpart of the CLI store's ``StoreError``: a corrupted or
    structurally invalid lane/annotation row must never be silently skipped,
    because a silent skip loses runtime state while pretending to reduce.
    """


#: Wire discriminator for off-axis runtime-state annotation events
#: (:class:`InnerStateChanged`). These are surfaced to the reducer -- never
#: skip-and-dropped -- and are decoded by :meth:`InnerStateChanged.from_dict`,
#: never :meth:`StatusEvent.from_dict`.
ANNOTATION_KIND = "annotation"

#: Filename of the derived snapshot the CLI writes next to the diary. The
#: dossier read model reduces the diary itself; this constant names the
#: derived artifact it must no longer trust.
SNAPSHOT_FILENAME = "status.json"

ULID_PATTERN = re.compile(r"^[0-9A-HJKMNP-TV-Z]{26}$")


# ---------------------------------------------------------------------------
# Lane vocabulary
# ---------------------------------------------------------------------------


class Lane(str, Enum):
    """Canonical work package lifecycle states.

    ``GENESIS`` is the pre-finalize state of a work package that has been
    created (``WPCreated``) but not yet seeded into the lane lifecycle. It is
    distinct from ``PLANNED`` so that ``finalize-tasks`` seeds a real
    ``genesis -> planned`` transition instead of a no-op ``planned -> planned``
    self-transition, and so the lane-state readers never silently default an
    unfinalized WP to ``planned``.

    ``GENESIS`` is a *non-display* lane: it is never the current lane of a
    materialized WP (an unseeded WP has no lane events and so is absent from the
    snapshot; once seeded it is ``planned``). It therefore does not appear on
    the kanban board or in the board summary. The nine post-genesis states
    (``PLANNED``..``CANCELED``) are the active, displayed lifecycle lanes.

    ``UNINITIALIZED`` is a *non-display, non-transitionable read sentinel*
    for a WP that is **absent from the reduced snapshot** (no events yet) or
    whose only events are annotations. It is deliberately **distinct** from
    ``GENESIS``: ``GENESIS`` means "seeded WP on an unseeded lane", while
    ``UNINITIALIZED`` means "no lane events exist for this WP at all". It is
    never persisted to the event log, never appears as a ``from_lane``/
    ``to_lane`` in a transition, and never appears in a display summary --
    see :data:`NON_DISPLAY_LANES`, the single canonical authority for "which
    lanes never display."

    Declared as ``(str, Enum)`` rather than ``enum.StrEnum`` because this
    package supports Python 3.10; ``__str__`` reproduces ``StrEnum``'s
    ``str(member) == member.value`` so the reducer's snapshot slots stay
    plain strings on every supported interpreter.
    """

    GENESIS = "genesis"
    UNINITIALIZED = "uninitialized"
    PLANNED = "planned"
    CLAIMED = "claimed"
    IN_PROGRESS = "in_progress"
    FOR_REVIEW = "for_review"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    DONE = "done"
    BLOCKED = "blocked"
    CANCELED = "canceled"

    def __str__(self) -> str:
        return self.value


# Single canonical authority for "which lanes never display". Every
# display-filter site (reducer summaries, board roster builders, kanban
# grouping) MUST consume this constant instead of inlining an
# ``is not Lane.GENESIS``-style check, so a future non-display lane cannot
# silently leak into a summary from a forgotten site.
NON_DISPLAY_LANES: frozenset[Lane] = frozenset({Lane.GENESIS, Lane.UNINITIALIZED})


#: A subtask's completion status reuses the canonical lane/status enum
#: vocabulary (:class:`Lane`) rather than introducing a divergent string type.
#: A subtask is "done" when its status is ``Lane.DONE``.
Status: TypeAlias = Lane


# ---------------------------------------------------------------------------
# Actor decoding
# ---------------------------------------------------------------------------

#: The ``actor`` on a ``StatusEvent`` / ``InnerStateChanged`` is EITHER a plain
#: ``str`` identity (the common case) OR a ``{role, profile, tool, model}``
#: structured *resolved binding*. The dict form is the delivery vehicle that
#: lets the SaaS fan-out ride the transition's *resolved* identity;
#: ``spec_kitty_events.status.StatusTransitionPayload.actor`` accepts
#: ``Union[str, Dict]``, so both shapes ride the envelope uncorrupted.
ActorField: TypeAlias = str | dict[str, str | None]

_STRUCTURED_ACTOR_FIELDS = ("role", "profile", "tool", "model")


def decode_actor(value: Any) -> ActorField:
    """Decode a wire ``actor`` value, preserving a structured (dict) actor.

    A resolved-binding actor is a ``{role, profile, tool, model}`` dict that MUST
    survive the ``status.events.jsonl`` round-trip uncorrupted. The legacy
    ``from_dict`` decoders coerced *every* actor with ``str(...)`` -- silently
    flattening such a dict to its ``repr`` (``"{'role': …}"``) with **no**
    exception (the load-bearing silent-corruption trap). This decoder validates
    and copies the dict so only those four keys with ``str | None`` values can
    cross the persistence/fan-out boundary. Every other value is coerced to
    ``str`` (the legacy string-actor contract).
    """
    if isinstance(value, dict):
        expected = set(_STRUCTURED_ACTOR_FIELDS)
        actual = set(value)
        if actual != expected:
            raise ValueError(
                "structured actor must contain exactly "
                f"{sorted(expected)!r}; got {sorted(actual)!r}"
            )
        decoded: dict[str, str | None] = {}
        for field_name in _STRUCTURED_ACTOR_FIELDS:
            field_value = value[field_name]
            if field_value is not None and not isinstance(field_value, str):
                raise ValueError(
                    "structured actor fields must be strings or null; "
                    f"{field_name!r} was {type(field_value).__name__}"
                )
            decoded[field_name] = field_value
        return decoded
    return str(value)


def actor_identity_str(actor: ActorField) -> str:
    """Project an actor to its plain-string identity for guard / snapshot / display.

    A structured (dict) resolved-binding actor projects to its ``tool`` (the agent
    identity a plain-string actor already carries), falling back to ``role`` then
    ``""``. A ``str`` actor is returned verbatim. This keeps guard inputs and the
    reduced-snapshot ``actor`` slot ``str``-typed for the ``.strip()``/display
    consumers, while the dict itself still rides ``StatusEvent.actor`` to the
    SaaS fan-out untouched (the snapshot slot is a display identity, not the
    binding).
    """
    if isinstance(actor, dict):
        identity = actor.get("tool") or actor.get("role") or ""
        return str(identity)
    return actor


# ---------------------------------------------------------------------------
# Evidence models
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RepoEvidence:
    """Evidence of code changes in a repository."""

    repo: str
    branch: str
    commit: str  # 7-40 hex chars
    files_touched: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "repo": self.repo,
            "branch": self.branch,
            "commit": self.commit,
        }
        if self.files_touched:
            d["files_touched"] = list(self.files_touched)
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RepoEvidence:
        return cls(
            repo=data["repo"],
            branch=data["branch"],
            commit=data["commit"],
            files_touched=data.get("files_touched", []),
        )


@dataclass(frozen=True)
class VerificationResult:
    """Result of a verification command (test suite, linter, etc.)."""

    command: str
    result: str  # "pass", "fail", or "skip"
    summary: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "command": self.command,
            "result": self.result,
            "summary": self.summary,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> VerificationResult:
        return cls(
            command=data["command"],
            result=data["result"],
            summary=data["summary"],
        )


@dataclass(frozen=True)
class ReviewApproval:
    """Reviewer approval or change request record."""

    reviewer: str
    verdict: str  # "approved" or "changes_requested"
    reference: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "reviewer": self.reviewer,
            "verdict": self.verdict,
            "reference": self.reference,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ReviewApproval:
        return cls(
            reviewer=data["reviewer"],
            verdict=data["verdict"],
            reference=data["reference"],
        )


@dataclass(frozen=True)
class DoneEvidence:
    """Evidence payload required for done transitions."""

    review: ReviewApproval
    repos: list[RepoEvidence] = field(default_factory=list)
    verification: list[VerificationResult] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"review": self.review.to_dict()}
        if self.repos:
            d["repos"] = [r.to_dict() for r in self.repos]
        if self.verification:
            d["verification"] = [v.to_dict() for v in self.verification]
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DoneEvidence:
        return cls(
            review=ReviewApproval.from_dict(data["review"]),
            repos=[RepoEvidence.from_dict(r) for r in data.get("repos", [])],
            verification=[VerificationResult.from_dict(v) for v in data.get("verification", [])],
        )


@dataclass(frozen=True)
class ReviewResult:
    """Structured review outcome required for all outbound in_review transitions.

    Unifies the currently asymmetric approval (DoneEvidence.review: ReviewApproval)
    and rejection (review_ref: str) recording paths into a single typed contract.
    """

    reviewer: str
    verdict: str  # "approved" or "changes_requested"
    reference: str  # Approval ref or feedback:// URI
    feedback_path: str | None = None  # Resolved path to feedback file (rejection only)

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "reviewer": self.reviewer,
            "verdict": self.verdict,
            "reference": self.reference,
        }
        if self.feedback_path is not None:
            data["feedback_path"] = self.feedback_path
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ReviewResult:
        return cls(
            reviewer=data["reviewer"],
            verdict=data["verdict"],
            reference=data["reference"],
            feedback_path=data.get("feedback_path"),
        )


# ---------------------------------------------------------------------------
# Diary rows
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class StatusEvent:
    """Immutable record of a single lane transition.

    Each event is one line in status.events.jsonl.

    Wire-format evolution:
    - Legacy events: carry only ``mission_slug`` for mission identity.
    - Newer events carry both ``mission_slug`` AND ``mission_id`` (the ULID
      from meta.json). ``mission_id`` is the canonical machine-facing
      identity; ``mission_slug`` is retained for human readability and
      backward compatibility.
    """

    event_id: str  # ULID
    mission_slug: str  # e.g. "034-feature-name"
    wp_id: str  # e.g. "WP01"
    from_lane: Lane
    to_lane: Lane
    at: str  # ISO 8601 UTC
    # ``str`` identity OR a ``{role, profile, tool, model}`` structured
    # resolved binding; see :data:`ActorField` / :func:`decode_actor`.
    actor: ActorField
    force: bool
    execution_mode: str  # "worktree" or "direct_repo"
    reason: str | None = None
    review_ref: str | None = None
    evidence: DoneEvidence | None = None
    review_result: ReviewResult | None = None
    policy_metadata: dict[str, Any] | None = None
    # mission_id added later; None for legacy rows that pre-date it.
    mission_id: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "actor", decode_actor(self.actor))

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "event_id": self.event_id,
            "mission_slug": self.mission_slug,
            "wp_id": self.wp_id,
            "from_lane": str(self.from_lane),
            "to_lane": str(self.to_lane),
            "at": self.at,
            "actor": self.actor,
            "force": self.force,
            "execution_mode": self.execution_mode,
            "reason": self.reason,
            "review_ref": self.review_ref,
            "evidence": self.evidence.to_dict() if self.evidence else None,
            "policy_metadata": self.policy_metadata,
        }
        if self.review_result is not None:
            d["review_result"] = self.review_result.to_dict()
        if self.mission_id is not None:
            d["mission_id"] = self.mission_id
        return d

    # Legacy lane name aliases from older event log formats.
    # Note: "in_review" was formerly aliased to "for_review" but is now a
    # first-class Lane member.
    _LANE_ALIASES: ClassVar[dict[str, str]] = {}

    @classmethod
    def _coerce_lane(cls, value: str) -> Lane:
        return Lane(cls._LANE_ALIASES.get(value, value))

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> StatusEvent:
        evidence_data = data.get("evidence")
        review_result_data = data.get("review_result")
        return cls(
            event_id=data["event_id"],
            mission_slug=data.get("mission_slug") or data.get("feature_slug", ""),
            wp_id=data["wp_id"],
            from_lane=cls._coerce_lane(data["from_lane"]),
            to_lane=cls._coerce_lane(data["to_lane"]),
            at=data["at"],
            # Preserve a structured (dict) resolved-binding actor on read-back;
            # a scalar is coerced to ``str`` (decode_actor guards the trap).
            actor=decode_actor(data["actor"]),
            force=data["force"],
            execution_mode=data["execution_mode"],
            reason=data.get("reason"),
            review_ref=data.get("review_ref"),
            evidence=DoneEvidence.from_dict(evidence_data) if evidence_data else None,
            review_result=(
                ReviewResult.from_dict(review_result_data) if review_result_data else None
            ),
            policy_metadata=data.get("policy_metadata"),
            mission_id=data.get("mission_id"),  # None for legacy events
        )


@dataclass(frozen=True)
class ReviewOverride:
    """Review-cycle override slot carried by an :class:`InnerStateChanged` delta.

    Pinned shape (do NOT reuse the review-result shape near the review-result
    slot and do NOT invent ``review_artifact_override_*`` fields): reference
    implementations pin these exact four fields and the :meth:`complete`
    predicate verbatim.
    """

    at: str
    actor: str
    wp_id: str
    reason: str

    @property
    def complete(self) -> bool:
        """True only when all four fields are non-empty."""
        return bool(self.at and self.actor and self.wp_id and self.reason)

    @property
    def is_release_sentinel(self) -> bool:
        """True only when ALL four fields are empty.

        This is the narrow "release" shape a ``--to planned`` rollback emits
        to explicitly clear a stale override (see the reducer's
        :func:`_apply_annotation_delta` docstring). It is deliberately
        narrower than ``not complete``: a *partially*-filled override (e.g.
        ``at``/``actor``/``wp_id`` present but a blank ``reason``) is
        incomplete but NOT a release sentinel -- it must still be persisted
        in the snapshot (so its non-completeness stays visible to gate
        consumers) rather than silently discarded as if no override attempt
        had ever been recorded.
        """
        return not (self.at or self.actor or self.wp_id or self.reason)

    def to_dict(self) -> dict[str, Any]:
        return {
            "at": self.at,
            "actor": self.actor,
            "wp_id": self.wp_id,
            "reason": self.reason,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> ReviewOverride:
        # Actor audit: the ``str(...)`` coercion is DELIBERATELY kept here.
        # ``ReviewOverride.actor`` is definitionally a scalar reviewer/agent
        # identity -- the resolved-binding dict actor is routed ONLY through
        # ``StatusEvent.actor`` (the transition) and the ``role``/
        # ``agent_profile``/``model``/``provider`` delta slots, NEVER through
        # a ``ReviewOverride``. A dict therefore never reaches this decoder,
        # so the coercion cannot flatten one.
        return cls(
            at=str(data["at"]),
            actor=str(data["actor"]),
            wp_id=str(data["wp_id"]),
            reason=str(data["reason"]),
        )


@dataclass(frozen=True)
class WPInnerStateDelta:
    """Typed partial runtime-state payload for an :class:`InnerStateChanged` event.

    Every field is optional; an absent (``None``) field leaves the
    corresponding reduced-snapshot slot untouched. This is deliberately a
    typed dataclass rather than a free ``dict[str, Any]``.

    ``tracker_refs`` is the *additive* channel (unions into the snapshot slot);
    ``tracker_refs_replace`` is the *replace* channel (wholesale-replaces the
    slot) so a replace does not resurrect stale refs. Both are delta inputs;
    the reduced snapshot exposes a single ``tracker_refs`` slot.

    **Resolved-binding group**: ``role``, ``agent_profile``,
    ``agent_profile_version``, ``model``, ``provider`` carry the *actual*
    runtime identity that resolved and ran a WP. They are event-sourced and
    folded latest-wins by the reducer -- a later pick-up/reassign replaces
    them. These are the **resolved actual**, deliberately distinct from the
    **authored recommendation** in frontmatter: never conflate "what ran"
    with "what was designed to run". Absence is valid -- a never-reclaimed WP
    leaves these slots ``None``.

    **Single-source-of-truth field list**: the plain ``str | None`` scalar
    fields are enumerated once in :data:`_SCALAR_FIELDS`, which backs both
    ``to_dict`` and ``from_dict``; ``is_empty`` iterates the dataclass fields
    directly. Adding a scalar slot is one field declaration plus one
    ``_SCALAR_FIELDS`` entry -- no method carries a hand-maintained field
    list. ``shell_pid`` (int coercion) and the container/typed fields
    (``subtasks``/``note``/``tracker_refs``/``tracker_refs_replace``/
    ``review``) are genuinely non-scalar and stay explicit.
    """

    shell_pid: int | None = None
    shell_pid_created_at: str | None = None
    subtasks: Mapping[str, Status] | None = None
    note: str | None = None
    tracker_refs: list[str] | None = None
    tracker_refs_replace: list[str] | None = None
    agent: str | None = None
    assignee: str | None = None
    review: ReviewOverride | None = None
    # Resolved-binding actuals -- pure ``str | None`` scalar slots folded
    # latest-wins by the reducer. Picked up automatically by _SCALAR_FIELDS /
    # is_empty.
    role: str | None = None
    agent_profile: str | None = None
    agent_profile_version: str | None = None
    model: str | None = None
    provider: str | None = None
    # Explicit claim-release marker. A bare ``agent=""`` (or any blank
    # scalar) is, by design, a NO-OP over the reducer's blank-protection
    # guard -- it must never clobber a real recorded value. But a legitimate
    # claim RELEASE (e.g. ``move-task --to planned``) needs a way to say
    # "clear the claim triple for real", which a per-field string sentinel
    # cannot express cleanly because the group is mixed-type (``shell_pid``
    # is ``int | None``, not ``str | None``). When ``True`` the reducer clears
    # ``agent``/``shell_pid``/``shell_pid_created_at`` (the claim triple) to
    # falsy, distinct from -- and unaffected by -- the bare empty-string
    # no-op guard. Not a member of ``_SCALAR_FIELDS`` (it is not a
    # ``str | None`` scalar) and not folded through ``_REPLACE_SLOTS`` -- it
    # is applied as its own explicit step in ``_apply_annotation_delta``.
    release_runtime_claim: bool = False

    #: Single authoritative list of the pure ``str | None`` scalar fields that
    #: round-trip trivially on the wire. Backs ``to_dict``/``from_dict`` (one
    #: source of truth). A new scalar slot is added here once; the two
    #: serializers pick it up as data. NOT a dataclass field (``ClassVar``).
    #: ``release_runtime_claim`` is deliberately EXCLUDED: it is a ``bool``,
    #: not a ``str | None`` scalar, and it must never be routed through the
    #: ``""`` -> ``None`` blank-protection normalization below (a ``bool``
    #: has no ``""`` state to normalize).
    _SCALAR_FIELDS: ClassVar[tuple[str, ...]] = (
        "shell_pid_created_at",
        "agent",
        "assignee",
        "role",
        "agent_profile",
        "agent_profile_version",
        "model",
        "provider",
    )

    def __post_init__(self) -> None:
        """Write-boundary normalization.

        An empty-string scalar runtime slot is meaningless -- it carries no
        attribution. Normalize ``""`` -> ``None`` for every ``str | None``
        scalar field so the append-only log **never records a blanking
        delta**: a stray ``agent: ""`` (or any blank scalar) can no longer
        clobber a real recorded value when the reducer folds it. This is the
        durable net; the reducer's empty-string no-op guard is the read-side
        belt-and-braces for logs written before this normalization existed.
        """
        for name in self._SCALAR_FIELDS:
            if getattr(self, name) == "":
                object.__setattr__(self, name, None)

    def is_empty(self) -> bool:
        """True when the delta touches no slot (all fields ``None``).

        Iterates the dataclass fields directly, so a newly-added optional
        field is covered automatically with no hand-maintained list to keep
        in sync.

        ``release_runtime_claim`` is the one field this scan does NOT apply
        the ``is None`` check to: it is a ``bool`` (default ``False``, never
        ``None``), so it is checked separately -- ``True`` alone makes the
        delta non-empty (a real claim-release request must actually be
        emitted); the default ``False`` never manufactures a non-empty delta
        on its own.
        """
        if self.release_runtime_claim:
            return False
        return all(
            getattr(self, f.name) is None for f in fields(self) if f.name != "release_runtime_claim"
        )

    def to_dict(self) -> dict[str, Any]:
        """Emit only present fields so the reducer's "absent leaves slot
        untouched" rule is unambiguous on the wire.

        Scalar fields are emitted by iterating the single ``_SCALAR_FIELDS``
        list; the non-scalar fields (``shell_pid`` int, ``subtasks``,
        ``note``, ``tracker_refs*``, ``review``) are handled explicitly.
        """
        d: dict[str, Any] = {}
        if self.shell_pid is not None:
            d["shell_pid"] = self.shell_pid
        if self.subtasks is not None:
            d["subtasks"] = {sid: str(status) for sid, status in self.subtasks.items()}
        if self.note is not None:
            d["note"] = self.note
        if self.tracker_refs is not None:
            d["tracker_refs"] = list(self.tracker_refs)
        if self.tracker_refs_replace is not None:
            d["tracker_refs_replace"] = list(self.tracker_refs_replace)
        if self.review is not None:
            d["review"] = self.review.to_dict()
        for name in self._SCALAR_FIELDS:
            value = getattr(self, name)
            if value is not None:
                d[name] = value
        if self.release_runtime_claim:
            d["release_runtime_claim"] = True
        return d

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> WPInnerStateDelta:
        subtasks_raw = data.get("subtasks")
        subtasks: dict[str, Status] | None = None
        if subtasks_raw is not None:
            subtasks = {str(sid): Status(value) for sid, value in subtasks_raw.items()}
        review_raw = data.get("review")
        review = ReviewOverride.from_dict(review_raw) if review_raw is not None else None
        shell_pid_raw = data.get("shell_pid")
        tracker_refs_raw = data.get("tracker_refs")
        tracker_refs_replace_raw = data.get("tracker_refs_replace")
        scalars: dict[str, Any] = {name: data.get(name) for name in cls._SCALAR_FIELDS}
        return cls(
            shell_pid=int(shell_pid_raw) if shell_pid_raw is not None else None,
            subtasks=subtasks,
            note=data.get("note"),
            tracker_refs=list(tracker_refs_raw) if tracker_refs_raw is not None else None,
            tracker_refs_replace=(
                list(tracker_refs_replace_raw) if tracker_refs_replace_raw is not None else None
            ),
            review=review,
            release_runtime_claim=bool(data.get("release_runtime_claim", False)),
            **scalars,
        )


@dataclass(frozen=True)
class InnerStateChanged:
    """Off-axis (non-transition) runtime-state annotation event.

    Shares the append-only ``status.events.jsonl`` file with
    :class:`StatusEvent` but carries **no** ``from_lane``/``to_lane`` and can
    never traverse the FSM: it bypasses transition validation and never
    increments ``force_count``. The reducer folds its typed
    :class:`WPInnerStateDelta` into the per-WP runtime slots in a dedicated
    post-transition pass.
    """

    event_id: str  # ULID
    wp_id: str
    at: str  # ISO 8601 UTC
    # Widened to accept a structured resolved-binding actor for parity with
    # ``StatusEvent.actor``; ``decode_actor`` guards the ``from_dict``
    # round-trip against the ``str(dict)`` flattening trap.
    actor: ActorField
    delta: WPInnerStateDelta
    kind: str = ANNOTATION_KIND

    def __post_init__(self) -> None:
        object.__setattr__(self, "actor", decode_actor(self.actor))

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "kind": self.kind,
            "wp_id": self.wp_id,
            "at": self.at,
            "actor": self.actor,
            "delta": self.delta.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> InnerStateChanged:
        """Decode an annotation dict.

        Distinct from :meth:`StatusEvent.from_dict` (which hard-requires the
        ``from_lane``/``to_lane`` keys). Validates ``event_id`` against
        ``ULID_PATTERN`` and requires ``kind == "annotation"``.
        """
        event_id = data["event_id"]
        if not isinstance(event_id, str) or not ULID_PATTERN.match(event_id):
            raise ValueError(f"InnerStateChanged.event_id is not a valid ULID: {event_id!r}")
        kind = data.get("kind")
        if kind != ANNOTATION_KIND:
            raise ValueError(
                f"InnerStateChanged requires kind == '{ANNOTATION_KIND}', got {kind!r}"
            )
        delta_raw = data["delta"]
        return cls(
            event_id=event_id,
            kind=kind,
            wp_id=str(data["wp_id"]),
            at=str(data["at"]),
            # decode_actor: a dict resolved-binding actor round-trips
            # uncorrupted; a scalar is ``str``-coerced.
            actor=decode_actor(data["actor"]),
            delta=WPInnerStateDelta.from_dict(delta_raw),
        )


@dataclass(frozen=True)
class EventStream:
    """Read-shape container partitioning the event log by kind.

    :func:`parse_diary` surfaces both lane ``transitions`` and off-axis
    ``annotations`` to the reducer without changing the on-disk file.
    """

    transitions: list[StatusEvent] = field(default_factory=list)
    annotations: list[InnerStateChanged] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Mission slug safety (moved from specify_cli.core.paths)
# ---------------------------------------------------------------------------

# Grammar decision: interior-dot-allowed form so real mission-slug values
# (full 26-char ULIDs, ``<slug>-<mid8>`` directory names, numeric-prefix slugs,
# bare mid8, mission_id/mid8 values) survive without change.
#
# Rejects: empty/whitespace, ".", "..", any "/" or "\", non-ASCII, leading
# ".", and any value whose stripped form contains ".." as a substring.
_SAFE_PATH_SEGMENT_RE: re.Pattern[str] = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


def assert_safe_path_segment(value: str) -> str:
    """Return ``value`` if it is a single safe path segment; else raise ValueError.

    Rejects empty/whitespace-only, ``"."``, ``".."``, any ``"/"`` or ``"\\"``
    (path separators), non-ASCII input, values beginning with ``"."``
    (hidden-file style -- leading-dot rejected as traversal risk), and any
    value whose stripped form contains ``".."`` as a substring (dotted-
    traversal guard: ``"..foo"``, ``"foo.."``, ``"a..b"`` -- a grammar that
    only special-cases the two literal tokens would wrongly accept these).

    This is a **general safe-segment validator** (not slug-only): it also
    validates ``mission_id`` and ``mid8`` values, which carry the same format
    constraints.

    Raises:
        ValueError: When ``value`` is not a safe single path segment.
    """
    stripped = value.strip() if value else value

    # Reject empty or whitespace-only
    if not stripped:
        raise ValueError(
            f"Not a safe path segment: {value!r} — value must not be empty or whitespace-only."
        )

    # Reject leading or trailing whitespace — a value that differs from its
    # stripped form is ambiguous and would silently produce wrong path segments.
    if value != stripped:
        raise ValueError(
            f"Not a safe path segment: {value!r} — value must not contain leading or trailing whitespace."
        )

    # Reject any ".." substring (covers ..foo, foo.., a..b, and literal ..)
    if ".." in stripped:
        raise ValueError(
            f"Not a safe path segment: {value!r} — value must not contain '..' (traversal guard)."
        )

    # Reject leading dot (covers .hidden, .dot-only, etc.)
    if stripped.startswith("."):
        raise ValueError(
            f"Not a safe path segment: {value!r} — value must not begin with '.' (traversal guard)."
        )

    # Reject path separators (/ and \) — catches a/b, a\b, /absolute, trailing/
    if "/" in stripped or "\\" in stripped:
        raise ValueError(
            f"Not a safe path segment: {value!r} — value must not contain path separators."
        )

    # Reject non-ASCII and enforce the segment grammar
    if not _SAFE_PATH_SEGMENT_RE.fullmatch(stripped):
        raise ValueError(
            f"Not a safe path segment: {value!r} — value must match the canonical segment grammar "
            f"(ASCII alphanumerics, hyphens, underscores, and interior dots only; "
            f"must begin with an alphanumeric character)."
        )

    return value


def safe_mission_slug(slug: str | None, fallback: str) -> str:
    """Return *slug* when it is a safe single path segment, else *fallback*.

    The mission slug carried on a status snapshot originates from UNTRUSTED
    event-record content (``StatusEvent.mission_slug``, copied verbatim from a
    ``status.events.jsonl`` row). Any sink that joins that slug into a path
    and creates/writes a directory (the ``derived/<slug>/`` view writers)
    must never let a crafted ``"../../../../tmp/evil"`` slug escape the
    derived root.

    This is the fail-closed chokepoint: an unsafe slug downgrades to
    *fallback*, logging a warning. The downgrade is display-only -- the slug
    is used solely as a path segment and a display label, so substituting
    the trusted directory name has no correctness cost.

    Args:
        slug: The candidate slug (may be ``None`` or empty).
        fallback: The trusted replacement (e.g. ``feature_dir.name``).

    Returns:
        ``slug`` when valid; otherwise ``fallback``.
    """
    if not slug:
        return fallback
    try:
        assert_safe_path_segment(slug)
    except ValueError as exc:
        logger.warning(
            "Refusing to use unsafe mission_slug %r as a path segment (traversal guard); "
            "falling back to trusted %r: %s",
            slug,
            fallback,
            exc,
        )
        return fallback
    return slug


# ---------------------------------------------------------------------------
# Mission identity fields (moved from specify_cli.mission_metadata /
# specify_cli.identity.aliases)
# ---------------------------------------------------------------------------

_MISSION_NUMBER_PATTERN = re.compile(r"^(?P<number>\d+)-")


def mission_number_from_slug(mission_slug: str) -> int | None:
    """Extract the numeric mission prefix from a mission slug when present.

    Returns the prefix as an ``int`` if the slug starts with ``NNN-``,
    or ``None`` if no numeric prefix is found.

    Examples:
        "083-foo-bar" -> 83
        "foo-bar"     -> None
    """
    match = _MISSION_NUMBER_PATTERN.match(str(mission_slug).strip())
    if match is None:
        return None
    return int(match.group("number"))


def mission_identity_fields(
    mission_slug: str,
    mission_number: int | str | None = None,
    mission_type: str | None = None,
) -> dict[str, str]:
    """Normalize canonical mission identity fields for machine-facing payloads.

    Converts ``mission_number`` to a display string at the payload boundary.
    ``None`` becomes ``""``; integers are formatted as their decimal string
    representation (no leading-zero padding -- that is display-layer choice).
    """
    resolved_slug = str(mission_slug).strip()
    # Stringify mission_number at the display boundary
    if isinstance(mission_number, int):
        resolved_number: str = str(mission_number)
    else:
        resolved_number = str(mission_number or "").strip()
    # Fall back to slug-derived prefix if no number provided
    if not resolved_number:
        slug_number = mission_number_from_slug(resolved_slug)
        resolved_number = str(slug_number) if slug_number is not None else ""
    resolved_type = str(mission_type or "").strip() or "software-dev"
    return {
        "mission_slug": resolved_slug,
        "mission_number": resolved_number,
        "mission_type": resolved_type,
    }


def with_tracked_mission_slug_aliases(payload: dict[str, Any]) -> dict[str, Any]:
    """Backfill ``mission_slug`` from legacy ``feature_slug`` if missing.

    Read-compat only: ensures payloads originating from old serialised data
    (which used ``feature_slug``) are normalised to the canonical
    ``mission_slug`` key before use. The legacy ``feature_slug`` key is
    intentionally *not* re-injected into output payloads -- callers that
    serialise to disk produce ``mission_slug``-only output going forward.
    """

    enriched = dict(payload)

    if enriched.get("mission_slug") is None and enriched.get("feature_slug") is not None:
        enriched["mission_slug"] = enriched["feature_slug"]

    return enriched


# ---------------------------------------------------------------------------
# Reducer (moved verbatim from specify_cli.status.reducer)
# ---------------------------------------------------------------------------

#: Per-WP runtime slots carried forward across lane transitions (per-field
#: independence). A transition updates ``lane``/``actor``/… and MUST preserve
#: these -- the pre-mission reducer rebuilt the dict carrying forward only
#: ``force_count``, which would erase runtime state on the next transition
#: (the reducer replace-dict hazard).
#:
#: The resolved-binding actuals (``role``/``agent_profile``/
#: ``agent_profile_version``/``model``/``provider``) are runtime slots too: an
#: implement-claim annotation's binding survives every later lane transition
#: until a review-claim annotation replaces it (latest-wins).
_RUNTIME_SLOTS: tuple[str, ...] = (
    "shell_pid",
    "shell_pid_created_at",
    "subtasks",
    "notes",
    "tracker_refs",
    "agent",
    "assignee",
    "review",
    "role",
    "agent_profile",
    "agent_profile_version",
    "model",
    "provider",
)

#: Data-driven **replace slots** for :func:`_apply_annotation_delta`: fields
#: whose fold rule is exactly "if the delta field is present, replace the
#: snapshot slot of the same name". Iterating this table (instead of a flat
#: if-chain) keeps the annotation fold under the complexity ceiling as
#: resolved-binding slots are added -- the five resolved actuals are pure
#: replace slots, so they are data here, not new branches. The non-replace
#: fields (``subtasks`` per-subtask merge, ``note`` -> ``notes`` append,
#: ``tracker_refs``/``tracker_refs_replace`` union/replace, ``review``) are
#: handled explicitly and are NOT members of this table.
_REPLACE_SLOTS: tuple[str, ...] = (
    "shell_pid",
    "shell_pid_created_at",
    "agent",
    "assignee",
    "role",
    "agent_profile",
    "agent_profile_version",
    "model",
    "provider",
)

#: The "claim triple" released by an explicit
#: ``WPInnerStateDelta.release_runtime_claim`` marker. Deliberately narrower
#: than :data:`_REPLACE_SLOTS`: ``assignee`` and the resolved-binding actuals
#: (``role``/``agent_profile``/``agent_profile_version``/``model``/
#: ``provider``) are NOT part of "the claim" and are left untouched by a
#: release -- only the runtime-claim identity (who/what process holds the WP)
#: is cleared. See :func:`_apply_annotation_delta`.
_CLAIM_RELEASE_SLOTS: tuple[str, ...] = ("agent", "shell_pid", "shell_pid_created_at")


def _is_rollback_event(event: StatusEvent) -> bool:
    """Check if an event represents a reviewer rollback.

    Current review rejection rolls back from in_review to in_progress.
    Legacy logs represented the same outcome as for_review to in_progress
    with a review reference.
    """
    if event.to_lane != Lane.IN_PROGRESS:
        return False
    if event.from_lane == Lane.IN_REVIEW:
        return True
    return event.from_lane == Lane.FOR_REVIEW and event.review_ref is not None


def _wp_state_from_event(
    event: StatusEvent,
    previous: dict[str, Any] | None,
) -> dict[str, Any]:
    """Build a WP state dict from a lane transition.

    Carries forward ``force_count`` **and** every untouched runtime slot from
    ``previous`` (per-field independence) so a later transition never
    silently erases ``shell_pid``/``subtasks``/``notes``/``tracker_refs``/…
    (the reducer replace-dict hazard).

    The ``planned -> claimed`` transition is the only transition that writes a
    runtime slot: it extracts ``shell_pid``/``shell_pid_created_at``/``agent``
    from its ``policy_metadata`` sidecar into the snapshot slots.
    ``policy_metadata`` may be ``None`` -- read defensively.

    **``review_result``** is a second, analogous exception, but its trigger is
    WIDER than "outbound from ``in_review``" alone. Emitters apply no
    ``from_lane`` filter of their own: callers thread an operator-supplied
    ``review_result`` onto the event verbatim, regardless of ``from_lane``.
    ``in_progress -> approved`` is a legal edge gated on evidence, not on
    ``from_lane`` -- so a single-hop transition carrying both ``evidence`` and
    a populated ``ReviewResult`` is constructible and persistable without ever
    passing through ``in_review``. A trigger keyed SOLELY on
    ``from_lane == IN_REVIEW`` would silently drop that verdict (and, on a
    later unrelated transition, resurrect whatever stale value a prior
    ``in_review`` cycle had carried forward) -- exactly the multi-authority
    bug this rule exists to close. The rule is therefore: **any event carrying
    a populated ``ReviewResult`` populates the slot with it, full stop**; the
    ``from_lane == IN_REVIEW`` leg exists ADDITIONALLY to capture the
    forced-null case the guard bypass creates (a forced exit from
    ``in_review`` supplying no ``ReviewResult`` still must land an explicit
    ``None`` -- an event with no ``review_result`` and ``from_lane !=
    IN_REVIEW`` has no such guarantee to make, so it only carries forward).
    Deliberately NOT a ``_RUNTIME_SLOTS`` row. The slot being written to
    ``None`` is distinct from the slot being entirely ABSENT for a WP that has
    never carried a verdict or exited ``in_review`` (the un-migrated/
    never-reviewed compatibility case).
    """
    prior_force_count = 0
    if previous is not None:
        prior_force_count = previous.get("force_count", 0)

    state: dict[str, Any] = {
        "lane": str(event.to_lane),
        # Project a structured (dict) resolved-binding actor to its string
        # identity for the SNAPSHOT slot: the reduced ``actor`` is a display
        # identity consumed by ``str(actor).strip()`` sinks, so it stays
        # ``str``-typed. The dict binding still rides the in-memory event to
        # the SaaS fan-out and round-trips the event LOG uncorrupted.
        "actor": actor_identity_str(event.actor),
        "last_transition_at": event.at,
        "last_event_id": event.event_id,
        "force_count": prior_force_count + (1 if event.force else 0),
    }

    # Preserve untouched runtime slots across the transition.
    if previous is not None:
        for slot in _RUNTIME_SLOTS:
            if slot in previous:
                state[slot] = previous[slot]

    # Claim exception: the only transition that writes a runtime slot.
    if event.from_lane == Lane.PLANNED and event.to_lane == Lane.CLAIMED:
        meta = event.policy_metadata or {}
        shell_pid = meta.get("shell_pid")
        if shell_pid is not None:
            state["shell_pid"] = shell_pid
        shell_pid_created_at = meta.get("shell_pid_created_at")
        if shell_pid_created_at is not None:
            state["shell_pid_created_at"] = shell_pid_created_at
        agent = meta.get("agent")
        # Truthiness, not ``is not None``: an empty ``agent`` sidecar is a
        # no-op, never a blank written over a real slot.
        if agent:
            state["agent"] = agent

    # review_result exception: see the docstring above. Trigger is "the event
    # carries a verdict" OR "outbound-from-in_review" (NOT from_lane ==
    # IN_REVIEW alone -- emit applies no from_lane filter, so a single-hop
    # in_progress -> approved carrying evidence + review_result is a real,
    # reachable event shape the narrower trigger would silently drop). Either
    # way the slot is OVERRIDDEN (not carry-forward-merged): a populated
    # ReviewResult always lands as itself, and a forced in_review exit with no
    # ReviewResult still lands an explicit ``None``. Any other transition
    # carries the slot forward verbatim (sticky) from ``previous`` so it is
    # never silently erased.
    if event.review_result is not None or event.from_lane == Lane.IN_REVIEW:
        state["review_result"] = (
            event.review_result.to_dict() if event.review_result is not None else None
        )
    elif previous is not None and "review_result" in previous:
        state["review_result"] = previous["review_result"]

    return state


def _apply_annotation_delta(state: dict[str, Any], delta: WPInnerStateDelta) -> None:
    """Fold a typed :class:`WPInnerStateDelta` into a per-WP snapshot dict.

    **Claim release (``release_runtime_claim``) is applied FIRST, before the
    replace-slot loop below.** A corrupted/blanking delta can never clobber a
    real recorded value (blank scalars normalize away at the write boundary
    and the replace-slot loop no-ops on a stray blank), but that protection is
    correctly indiscriminate: it cannot tell a corruption-shaped blank from a
    *legitimate* claim release (e.g. ``move-task --to planned`` releasing a
    stale ``agent``/``shell_pid`` on rollback), because both look identical on
    the wire (an absent/empty scalar). ``release_runtime_claim`` is the
    explicit, unambiguous signal that disambiguates the two: when ``True`` it
    clears :data:`_CLAIM_RELEASE_SLOTS` (``agent``/``shell_pid``/
    ``shell_pid_created_at``) to falsy -- a REAL clear, not a no-op -- while a
    bare ``agent=""`` with ``release_runtime_claim`` absent/``False`` remains
    a no-op. Applying the release BEFORE the replace-slot loop lets a concrete
    value carried in the SAME delta (e.g. an explicit ``--agent`` replant on
    the same rollback move) win over the release: the loop below overwrites
    whatever the release just cleared whenever the delta also carries a
    present, non-empty value for that slot.

    Per-field merge rules (only present delta fields are applied; absent
    fields leave the slot untouched):

    - **Replace slots** (:data:`_REPLACE_SLOTS`, data-driven): ``shell_pid`` /
      ``shell_pid_created_at`` / ``agent`` / ``assignee`` and the resolved-
      binding actuals ``role`` / ``agent_profile`` / ``agent_profile_version``
      / ``model`` / ``provider``. Each folds **latest-wins** -- a present
      value replaces the same-named slot; the most-recent annotation's actual
      wins across the lifecycle.
    - ``subtasks``: **per-subtask replace** (merge by subtask id).
    - ``note``: **append** to the ``notes`` list (field/slot name mismatch:
      delta ``note`` -> snapshot ``notes``, so it is NOT a replace slot).
    - ``tracker_refs`` (additive) **unions** into the ``tracker_refs`` slot;
      ``tracker_refs_replace`` (present) **wholesale-replaces** the slot
      (dedup-preserving order) and takes precedence when both are present --
      the replace channel is what lets a ``--replace`` drop stale refs rather
      than resurrect them.
    - ``review``: **replace** with ``ReviewOverride.to_dict()``, UNLESS the
      delta is the all-empty **release sentinel**
      (:attr:`ReviewOverride.is_release_sentinel` -- every field empty, the
      shape a ``--to planned`` rollback emits), in which case the slot is a
      deliberate **clear** instead: it drops back to ``None`` rather than
      persisting an empty dict, so a stale "superseded by approval" record
      left by an earlier review-artifact override does not survive onto a WP
      that has since rolled back to ``planned`` with a fresh rejection. A
      *partially*-filled override (some but not all fields present, e.g. a
      blank ``reason``) is a DIFFERENT case from the release sentinel: it is
      still persisted (so its presence remains visible), just not
      :attr:`ReviewOverride.complete`.

    **Precedence vs. ``review_result``**: ``review`` (this slot, written here)
    and ``review_result`` (written in :func:`_wp_state_from_event` on an
    outbound-from-``in_review`` transition) are two DIFFERENT facts and are
    never collapsed into one -- ``review`` is the arbiter's override decision,
    ``review_result`` is the reviewer's own verdict. Both may be populated
    simultaneously for the same WP (an override recorded after a standing
    rejection, for instance). Precedence between them for GATE purposes is
    applied by each consumer, never by overwriting either slot here.

    Never increments ``force_count``.
    """
    if delta.release_runtime_claim:
        for name in _CLAIM_RELEASE_SLOTS:
            state[name] = None
    for name in _REPLACE_SLOTS:
        value = getattr(delta, name)
        # Empty strings are a no-op for string replace-slots: ``""`` must
        # never clobber a real recorded value. ``value != ""`` keeps the
        # non-string slots intact (e.g. ``shell_pid == 0`` still folds).
        if value is not None and value != "":
            state[name] = value
    if delta.subtasks is not None:
        current_subtasks: dict[str, str] = dict(state.get("subtasks") or {})
        for subtask_id, status in delta.subtasks.items():
            current_subtasks[subtask_id] = str(status)
        state["subtasks"] = current_subtasks
    if delta.note is not None:
        notes: list[str] = list(state.get("notes") or [])
        notes.append(delta.note)
        state["notes"] = notes
    if delta.tracker_refs_replace is not None:
        state["tracker_refs"] = _dedup_preserve_order(delta.tracker_refs_replace)
    elif delta.tracker_refs is not None:
        merged: list[str] = list(state.get("tracker_refs") or [])
        for ref in delta.tracker_refs:
            if ref not in merged:
                merged.append(ref)
        state["tracker_refs"] = merged
    if delta.review is not None:
        state["review"] = None if delta.review.is_release_sentinel else delta.review.to_dict()


def _dedup_preserve_order(refs: list[str]) -> list[str]:
    """Return ``refs`` with duplicates removed, preserving first-seen order."""
    seen: set[str] = set()
    result: list[str] = []
    for ref in refs:
        if ref not in seen:
            seen.add(ref)
            result.append(ref)
    return result


def _should_apply_event(
    current_state: dict[str, Any] | None,
    new_event: StatusEvent,
    all_events: list[StatusEvent],
) -> bool:
    """Determine whether new_event should be applied given the current state.

    Implements rollback-aware precedence: if the current state was set by
    a forward transition and a concurrent rollback event exists for the
    same WP, the rollback wins.

    If there is no current state, the event always applies.
    If events are not concurrent (different timestamps), the later one
    wins naturally through sort order.
    """
    if current_state is None:
        return True

    current_event_id = current_state.get("last_event_id")
    current_timestamp = current_state.get("last_transition_at")

    # If this event has the same timestamp as the current state's event,
    # they are concurrent. Check rollback precedence.
    if current_timestamp == new_event.at:
        # If the new event is a rollback, it beats a forward transition
        if _is_rollback_event(new_event):
            # Check if the current state was set by a non-rollback event
            current_setter = None
            for ev in all_events:
                if ev.event_id == current_event_id:
                    current_setter = ev
                    break
            if current_setter is not None and not _is_rollback_event(current_setter):
                return True  # Rollback beats forward

        # If the current state was set by a rollback, don't let a
        # concurrent forward event override it
        if current_event_id is not None:
            current_setter = None
            for ev in all_events:
                if ev.event_id == current_event_id:
                    current_setter = ev
                    break
            if (
                current_setter is not None
                and _is_rollback_event(current_setter)
                and not _is_rollback_event(new_event)
            ):
                return False  # Forward does not beat rollback

    # Default: apply the event (later in sort order wins)
    return True


def _runtime_only_wp_state(actor: ActorField) -> dict[str, Any]:
    """Seed a per-WP snapshot entry for an annotation with no prior transition.

    Such a WP never traversed the FSM, so it has no display lane -- it sits in
    the non-display ``UNINITIALIZED`` lane and is therefore excluded from the
    board summary. The annotation delta then folds its runtime slots on top.

    The ``actor`` is projected to its string identity for the snapshot slot
    (parity with :func:`_wp_state_from_event`), so a structured annotation
    actor never lands as a raw dict in a display sink.
    """
    return {
        "lane": str(Lane.UNINITIALIZED),
        "actor": actor_identity_str(actor),
        "last_transition_at": None,
        "last_event_id": None,
        "force_count": 0,
    }


# ---------------------------------------------------------------------------
# Reduced state + public entry points
# ---------------------------------------------------------------------------


@dataclass
class State:
    """Materialized kanban state of all WPs in a mission (derived from the diary).

    Produced by :func:`reduce` / :func:`reduce_parsed`. Serializes with
    :meth:`to_dict` to exactly the shape the CLI writes as ``status.json``
    (minus the CLI-side ``retrospective`` attachment, which is computed after
    reduction by the CLI's materialize step).
    """

    mission_slug: str
    materialized_at: str  # ISO 8601 UTC
    event_count: int
    last_event_id: str | None
    work_packages: dict[str, dict[str, Any]]  # WP ID -> WP state
    summary: dict[str, int]  # lane -> count
    mission_number: str | None = None
    mission_type: str | None = None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            **mission_identity_fields(
                self.mission_slug,
                self.mission_number,
                self.mission_type,
            ),
            "materialized_at": self.materialized_at,
            "event_count": self.event_count,
            "last_event_id": self.last_event_id,
            "work_packages": self.work_packages,
            "summary": self.summary,
        }
        result: dict[str, Any] = with_tracked_mission_slug_aliases(d)
        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> State:
        feature_slug = data.get("mission_slug") or data.get("feature_slug")
        if feature_slug is None:
            raise KeyError("mission_slug")
        return cls(
            mission_slug=feature_slug,
            materialized_at=data["materialized_at"],
            event_count=data["event_count"],
            last_event_id=data.get("last_event_id"),
            work_packages=data["work_packages"],
            summary=data["summary"],
            mission_number=data.get("mission_number"),
            mission_type=data.get("mission_type"),
        )


_RETROSPECTIVE_EVENT_NAME_PREFIX = "retrospective."

# Registration point: any new non-lane lifecycle event that uses the "type"
# envelope shape MUST be added here, or this row will hit StatusEvent.from_dict
# and raise as a malformed lane-transition row. Ported from the CLI's
# `_RETROSPECTIVE_LIFECYCLE_EVENT_TYPES` (specify_cli/status/store.py).
_RETROSPECTIVE_LIFECYCLE_EVENT_TYPES: frozenset[str] = frozenset(
    {
        "RetrospectiveCaptured",
        "RetrospectiveCaptureFailed",
        "RetrospectiveSkipped",
    }
)


def _is_retrospective_lifecycle_event(obj: dict[str, Any]) -> bool:
    """Return True for retrospective lifecycle rows using the ``type`` envelope.

    These rows are written to status.events.jsonl by design and read back by
    retrospective consumers; they are descriptive lifecycle events, not lane
    transitions, and must be skipped in place — never removed.
    """
    event_type = obj.get("type")
    return isinstance(event_type, str) and event_type in _RETROSPECTIVE_LIFECYCLE_EVENT_TYPES


def _is_non_lane_row(obj: dict[str, Any]) -> bool:
    """Return True for diary rows that are ignored in place, never fatal.

    These are rows written into ``status.events.jsonl`` by subsystems other
    than the status emitter:

    - retrospective.* diary entries (``event_name`` key);
    - the three canonical retrospective lifecycle events which use a ``type``
      field instead of ``event_name`` (RetrospectiveCaptured/CaptureFailed/
      Skipped);
    - mission-level events carrying a top-level ``event_type`` key
      (DecisionPointOpened/Resolved/Deferred/Canceled/Widened and any future
      event-type written by a non-status-emitter subsystem). Two cooperating
      subsystems write to this file with incompatible schemas: the status
      emitter writes lane-transition events (carrying wp_id, from_lane,
      to_lane), while mission-level protocols write events with a top-level
      ``event_type`` field instead. Discriminating on event_type PRESENCE
      (not a specific value allowlist) is future-proof AND preserves the
      fail-loud contract for malformed lane events: a corrupted lane event
      missing wp_id but ALSO missing event_type still hits
      :meth:`StatusEvent.from_dict` below and raises as today.

    InnerStateChanged annotations are NOT skip-and-dropped: they are surfaced
    to the reducer via the annotation read path (handled before this check).
    """
    event_name = obj.get("event_name")
    if isinstance(event_name, str) and event_name.startswith(_RETROSPECTIVE_EVENT_NAME_PREFIX):
        return True
    if _is_retrospective_lifecycle_event(obj):
        return True
    return "event_type" in obj


def parse_diary(rows: Iterable[dict[str, Any]]) -> EventStream:
    """Partition raw diary rows into lane transitions and annotations.

    Pure function over already-decoded rows (one JSON object per
    ``status.events.jsonl`` line). See the module docstring for the exact
    partition rules. Raises :class:`DiaryError` for a non-object row, a
    malformed lane/annotation row, or an unknown ``kind`` discriminator.
    """
    transitions: list[StatusEvent] = []
    annotations: list[InnerStateChanged] = []
    for row in rows:
        if not isinstance(row, dict):
            raise DiaryError(f"Invalid diary row: expected JSON object, got {type(row).__name__}")

        kind = row.get("kind")
        if kind is not None:
            if kind == ANNOTATION_KIND:
                try:
                    annotations.append(InnerStateChanged.from_dict(row))
                except (KeyError, ValueError, TypeError) as exc:
                    raise DiaryError(f"Invalid annotation row: {exc}") from exc
                continue
            # An unknown kind is never silently skipped — fail loud.
            raise DiaryError(f"Unknown event kind {kind!r}")

        if _is_non_lane_row(row):
            continue

        try:
            transitions.append(StatusEvent.from_dict(row))
        except (KeyError, ValueError, TypeError) as exc:
            raise DiaryError(f"Invalid lane-transition row: {exc}") from exc
    return EventStream(transitions=transitions, annotations=annotations)


def reduce_parsed(
    transitions: list[StatusEvent],
    annotations: list[InnerStateChanged] | None = None,
) -> State:
    """Deterministically reduce parsed events (+ annotations) into a :class:`State`.

    The fold itself, for callers that already hold parsed
    :class:`StatusEvent`/:class:`InnerStateChanged` records (e.g. a reader
    that resolves legacy ``mission_id`` values against ``meta.json`` before
    folding). Most consumers want :func:`reduce`.

    Event-kind partition fold (NOT a timestamp-interleaved single pass):

    1. Deduplicate transitions by event_id (keep first occurrence)
    2. Sort transitions by (at, event_id) ascending
    3. Fold all transitions with rollback-aware precedence, preserving each
       WP's untouched runtime slots (and folding the ``planned -> claimed``
       ``policy_metadata`` sidecar into the snapshot slots)
    4. Fold **all annotations** in a dedicated post-transition pass, applying
       the per-field ``WPInnerStateDelta`` merge. A same-``at`` transition can
       never clobber an annotation slot; annotations never bump ``force_count``.
       This pass is a single O(annotations) walk keyed by ``wp_id`` -- it does
       NOT re-scan the transition list.
    5. Build summary counts for the active/display lanes (lanes in
       ``NON_DISPLAY_LANES`` -- currently ``GENESIS`` and ``UNINITIALIZED`` --
       are excluded; neither ever appears as the current lane of a
       materialised WP)

    ``annotations`` defaults to ``None`` (treated as empty). An
    annotation-only stream materialises a runtime-only WP entry.

    An empty stream (no transitions and no annotations) returns a state with
    ``mission_slug=""``, all zero counts, and no work packages.
    """
    annotations = annotations or []
    if not transitions and not annotations:
        return State(
            mission_slug="",
            materialized_at="",  # No events → no last-event timestamp; stable empty string
            event_count=0,
            last_event_id=None,
            work_packages={},
            summary={lane.value: 0 for lane in Lane if lane not in NON_DISPLAY_LANES},
        )

    # Step 1: Deduplicate by event_id (keep first occurrence)
    seen_ids: set[str] = set()
    unique_events: list[StatusEvent] = []
    for event in transitions:
        if event.event_id not in seen_ids:
            seen_ids.add(event.event_id)
            unique_events.append(event)

    # Step 2: Sort by (at, event_id) ascending
    sorted_events = sorted(unique_events, key=lambda e: (e.at, e.event_id))

    # Step 3 & 4: Iterate and apply events with rollback-aware precedence
    wp_states: dict[str, dict[str, Any]] = {}
    # The event's mission_slug is UNTRUSTED (verbatim from a status.events.jsonl
    # row). Sanitize it HERE -- the single seam where the snapshot's slug is set --
    # so a crafted traversal slug (e.g. "../../../../tmp/evil") is downgraded to
    # "" at the source. Every derived-view writer already falls back to the
    # trusted feature_dir.name when the slug is empty (`slug or feature_dir.name`),
    # so this one chokepoint fail-closes all current and future path sinks.
    # An annotation-only stream has no transition to source the slug from.
    mission_slug = safe_mission_slug(sorted_events[0].mission_slug, "") if sorted_events else ""

    for event in sorted_events:
        current = wp_states.get(event.wp_id)
        if _should_apply_event(current, event, sorted_events):
            wp_states[event.wp_id] = _wp_state_from_event(event, current)

    # Step 4: Annotation post-pass (event-kind partition -- folded AFTER every
    # transition, never interleaved by timestamp). A single O(annotations) walk
    # keyed by wp_id; it does NOT re-scan the transition list. An annotation for
    # a wp_id with no prior transition materialises a runtime-only WP entry.
    #
    # Sort by ``(at, event_id)`` -- the SAME key as the transition pass (Step 2) --
    # so two annotations touching the same field resolve by timestamp, not by
    # merge/file order. Without this, a parallel-worktree merge that interleaves
    # the rows non-deterministically would flip the winner (#2684 determinism).
    sorted_annotations = sorted(annotations, key=lambda a: (a.at, a.event_id))
    for annotation in sorted_annotations:
        wp_state = wp_states.get(annotation.wp_id)
        if wp_state is None:
            wp_state = _runtime_only_wp_state(annotation.actor)
            wp_states[annotation.wp_id] = wp_state
        _apply_annotation_delta(wp_state, annotation.delta)

    # Step 5: Build summary counts for the active/display lanes.
    # Lanes in NON_DISPLAY_LANES (GENESIS, UNINITIALIZED) are excluded --
    # neither is ever the current lane of a materialised WP (post-finalize
    # there are none).
    summary: dict[str, int] = {lane.value: 0 for lane in Lane if lane not in NON_DISPLAY_LANES}
    for wp_state in wp_states.values():
        lane_val = wp_state["lane"]
        if lane_val in summary:
            summary[lane_val] += 1

    # ``materialized_at``/``last_event_id`` derive from the last transition
    # (deterministic). Annotations are off-axis and do not move these markers.
    last_transition = sorted_events[-1] if sorted_events else None
    return State(
        mission_slug=mission_slug,
        materialized_at=last_transition.at if last_transition is not None else "",
        event_count=len(sorted_events),
        last_event_id=last_transition.event_id if last_transition is not None else None,
        work_packages=wp_states,
        summary=summary,
    )


def reduce(events: Iterable[dict[str, Any]]) -> State:
    """Reduce raw status-diary rows into the kanban :class:`State`.

    Args:
        events: Raw ``status.events.jsonl`` rows -- one decoded JSON object
            per log line, in any order. Accepts any iterable (a generator is
            consumed once).

    Returns:
        The deterministic reduced :class:`State`. Deterministic for any
        permutation of the same row multiset.

    Raises:
        DiaryError: On a malformed lane/annotation row or an unknown ``kind``
            discriminator. Non-lane rows (unknown ``event_type`` writers,
            ``retrospective.*`` entries) are ignored, not fatal.
    """
    stream = parse_diary(events)
    return reduce_parsed(stream.transitions, stream.annotations)
