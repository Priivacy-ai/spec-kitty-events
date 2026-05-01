"""Recursive forbidden-key validator and the canonical forbidden-key set.

This module is the single source of truth for the *legacy keys* that the
``spec_kitty_events`` contract package rejects anywhere in an envelope or
payload. It exposes:

* :data:`FORBIDDEN_LEGACY_KEYS` — a ``frozenset[str]`` containing every
  forbidden key (closed, named, versioned).
* :data:`FORBIDDEN_LEGACY_KEYS_VERSION` — bumped on any membership change
  (see ``contracts/versioning-and-compatibility.md``).
* :func:`find_forbidden_keys` — generator yielding every
  :class:`~spec_kitty_events.validation_errors.ValidationError` encountered
  during a deterministic depth-first walk.
* :func:`validate_no_forbidden_keys` — short-circuit helper returning the
  first ``ValidationError`` (or ``None`` when the input is clean).

Audit notes (T008)
------------------
The forbidden-key set is the union of the seeded keys plus the additions
justified by the audit below. Each entry cites a real source.

* **Seeded by spec**: ``feature_slug``, ``feature_number``, ``mission_key``
  are guaranteed-forbidden per the mission spec
  (``kitty-specs/teamspace-event-contract-foundation-01KQHDE4/spec.md``,
  FR-005) and the contract document at
  ``contracts/forbidden-key-validation.md``.

* **Epic #920 historical-row survey**
  (https://github.com/Priivacy-ai/spec-kitty/issues/920). The epic enumerates
  legacy keys observed across 6,155 historical status-event rows. The
  named keys are: ``feature_slug`` (2,772 rows), ``work_package_id`` (1,624
  rows), ``legacy_aggregate_id`` (424 rows), plus the seeded
  ``feature_number`` / ``mission_key``. We promote ``legacy_aggregate_id``
  into the forbidden set on first ship: it is unambiguously legacy and has
  no current legitimate frontmatter use anywhere in this repo.

* **``work_package_id`` is intentionally NOT forbidden.** A ripgrep audit
  inside this repository
  (``rg "work_package_id" --include='*.py'`` on
  ``spec-kitty-events/.worktrees/teamspace-event-contract-foundation-01KQHDE4-lane-a``)
  shows ``work_package_id`` is a *legitimate, current* frontmatter key used
  by ``.kittify/overrides/scripts/tasks/task_helpers.py``,
  ``tasks_cli.py``, and ``acceptance_support.py``. Adding it to the
  forbidden set today would make us reject our own envelopes. A follow-up
  audit work package can revisit this once the helpers migrate off the
  legacy key.

* **Sibling-repo audit (in-repo only)**: per the work package's "do NOT cd
  outside this repo" boundary, we did not crawl ``../spec-kitty-saas`` or
  ``../spec-kitty`` directly. A ripgrep inside ``spec-kitty-events`` for
  any pre-existing ``FORBIDDEN_LEGACY_KEYS`` constant or ``forbidden_keys``
  module returned no hits — there is no constant to reconcile against.
  WP06 / WP07 (compat doc + benchmark) can extend this audit if they
  surface additional legacy keys.

Final set on first ship (v1):
``feature_slug``, ``feature_number``, ``mission_key``, ``legacy_aggregate_id``.

Behaviour summary
-----------------
The validator inspects KEYS only. A string *value* equal to a forbidden key
name is accepted. The walk is depth-first with deterministic visit order
(dict keys in insertion order, then recurse into each value; array elements
in index order). Path entries use ``str`` for object keys and ``int`` for
array indices; ``[]`` denotes the envelope root.

Example — value-vs-key distinction:

.. code-block:: python

    from spec_kitty_events.forbidden_keys import validate_no_forbidden_keys

    # KEY hit: rejected.
    validate_no_forbidden_keys({"feature_slug": "x"})  # -> ValidationError

    # VALUE that *looks like* a forbidden key name: accepted.
    validate_no_forbidden_keys({"description": "see feature_slug docs"})  # -> None
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from spec_kitty_events.validation_errors import (
    ValidationError,
    ValidationErrorCode,
)

__all__ = [
    "FORBIDDEN_LEGACY_KEYS",
    "FORBIDDEN_LEGACY_KEYS_VERSION",
    "find_forbidden_keys",
    "validate_no_forbidden_keys",
]


FORBIDDEN_LEGACY_KEYS: frozenset[str] = frozenset(
    {
        # Seeded by spec FR-005 and contracts/forbidden-key-validation.md.
        "feature_slug",
        "feature_number",
        "mission_key",
        # Promoted from epic #920 historical-row survey (424 rows).
        # Unambiguously legacy; no legitimate current use in this repo.
        "legacy_aggregate_id",
    }
)
"""Closed, named set of forbidden legacy keys.

Membership changes are a contract change governed by
``contracts/versioning-and-compatibility.md``; bump
:data:`FORBIDDEN_LEGACY_KEYS_VERSION` whenever this set changes.
"""


FORBIDDEN_LEGACY_KEYS_VERSION: str = "v1"
"""Bump on any membership change to :data:`FORBIDDEN_LEGACY_KEYS`."""


def find_forbidden_keys(
    data: Any,
    *,
    forbidden: frozenset[str] = FORBIDDEN_LEGACY_KEYS,
    _path: list[str | int] | None = None,
) -> Iterator[ValidationError]:
    """Yield a ``ValidationError(FORBIDDEN_KEY)`` for each forbidden key found.

    Walks objects (dicts) by their *keys*; never inspects values for
    matching strings. Recurses into nested objects and into elements of
    arrays. Visit order is deterministic: dict keys in insertion order,
    then recurse into each value; array elements in index order;
    depth-first.

    Args:
        data: Arbitrary JSON-shaped input. ``dict`` and ``list`` nodes are
            traversed; primitives (``str``, ``int``, ``float``, ``bool``,
            ``None``) are leaves.
        forbidden: The forbidden-key set. Defaults to
            :data:`FORBIDDEN_LEGACY_KEYS`. Override for tests or for
            consumer-specific stricter sets.
        _path: Internal accumulator for the JSON-pointer-like path. Callers
            should not pass this.

    Yields:
        ``ValidationError`` instances with ``code=FORBIDDEN_KEY``,
        ``path`` describing the location of the offending key, and
        ``details={"key": <key>}``.
    """

    path: list[str | int] = list(_path) if _path is not None else []

    if isinstance(data, dict):
        for key, value in data.items():
            key_path: list[str | int] = path + [key]
            if isinstance(key, str) and key in forbidden:
                yield ValidationError(
                    code=ValidationErrorCode.FORBIDDEN_KEY,
                    message=f"Forbidden legacy key '{key}' is not allowed",
                    path=key_path,
                    details={"key": key},
                )
            yield from find_forbidden_keys(
                value, forbidden=forbidden, _path=key_path
            )
    elif isinstance(data, list):
        for index, element in enumerate(data):
            yield from find_forbidden_keys(
                element, forbidden=forbidden, _path=path + [index]
            )
    # Primitives (str, int, float, bool, None, anything else): no-op.


def validate_no_forbidden_keys(
    data: Any,
    *,
    forbidden: frozenset[str] = FORBIDDEN_LEGACY_KEYS,
) -> ValidationError | None:
    """Return the first ``ValidationError`` found, or ``None`` if input is clean.

    This is the short-circuit form of :func:`find_forbidden_keys`. It stops
    walking on the first hit. Consumers needing every error can call
    ``list(find_forbidden_keys(data))`` instead.

    Args:
        data: Arbitrary JSON-shaped input.
        forbidden: The forbidden-key set. Defaults to
            :data:`FORBIDDEN_LEGACY_KEYS`.

    Returns:
        The first ``ValidationError`` (in deterministic visit order) or
        ``None`` when no forbidden key is present.
    """

    iterator = find_forbidden_keys(data, forbidden=forbidden)
    return next(iterator, None)
