"""Structured validation error vocabulary.

This module defines the canonical, structured rejection shape used across the
``spec_kitty_events`` contract package: :class:`ValidationError` (a Pydantic
model) and :class:`ValidationErrorCode` (a closed string enum).

The vocabulary is *layered on top* of the existing typed exceptions in
``status.py`` (``TransitionError``) and any future lifecycle exceptions: code
that already raises and catches the typed exceptions keeps working unchanged,
while new consumers can convert any rejection into a deterministic, structured
:class:`ValidationError` for transport, comparison, or fixture pinning.

Cross-file note (WP02 ownership boundary)
----------------------------------------
``status.py`` and ``lifecycle.py`` are owned by sibling work packages (WP01 /
WP04). To avoid ownership conflicts, this WP intentionally does *not* attach an
``as_validation_error()`` method to those exception classes directly. Instead,
this module exposes free helper functions:

* :func:`transition_error_to_validation_error`
* :func:`lifecycle_error_to_validation_error`

Sibling work packages can later call into these helpers from a thin wrapper
method on the exception class itself (e.g.
``def as_validation_error(self): return transition_error_to_validation_error(self)``).

Closed-enum discipline
----------------------
:class:`ValidationErrorCode` is a *closed* set of codes. Helpers in this module
*never* invent a new code as a fallback. If a typed exception cannot be cleanly
mapped to one of the existing codes the helper raises :class:`ValueError`,
forcing the caller to either widen the enum (a contract change) or fix the
mapping at the call site.
"""

from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, ConfigDict

if TYPE_CHECKING:  # pragma: no cover - import only used for type checking
    from spec_kitty_events.status import TransitionError


__all__ = [
    "ValidationError",
    "ValidationErrorCode",
    "transition_error_to_validation_error",
    "lifecycle_error_to_validation_error",
]


class ValidationErrorCode(str, Enum):
    """Closed set of validation error codes.

    The set is *closed* for this release. Adding a new member is a contract
    change subject to the same review and version-bump process as a schema
    bump (see ``contracts/validation-error-shape.md``).
    """

    FORBIDDEN_KEY = "FORBIDDEN_KEY"
    UNKNOWN_LANE = "UNKNOWN_LANE"
    PAYLOAD_SCHEMA_FAIL = "PAYLOAD_SCHEMA_FAIL"
    ENVELOPE_SHAPE_INVALID = "ENVELOPE_SHAPE_INVALID"
    RAW_HISTORICAL_ROW = "RAW_HISTORICAL_ROW"


class ValidationError(BaseModel):
    """Structured rejection produced by the contract package.

    The model is ``frozen`` (instances are immutable / hashable) and
    ``extra='forbid'`` (unknown fields raise on construction). These choices
    support determinism (NFR-001) — two ``ValidationError`` instances built
    from identical inputs must serialize to byte-identical JSON.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    code: ValidationErrorCode
    message: str
    path: list[str | int] = []
    details: dict[str, Any] = {}


# ---------------------------------------------------------------------------
# Helper conversion functions
# ---------------------------------------------------------------------------


def transition_error_to_validation_error(err: "TransitionError") -> ValidationError:
    """Convert a :class:`TransitionError` into a structured ``ValidationError``.

    A ``TransitionError`` carries a tuple of human-readable violation strings.
    Every violation produced by ``validate_transition`` in ``status.py`` is a
    statement about either:

    * an illegal lane move (e.g. "Transition X -> Y is not allowed"), or
    * a guard condition tied to lane semantics (terminal lane exit without
      ``force``, missing ``review_ref``, missing ``reason``).

    All of these are lane-vocabulary violations; the closed-enum mapping is
    therefore :data:`ValidationErrorCode.UNKNOWN_LANE`.

    Raises:
        ValueError: if ``err`` carries no violations to summarize. The closed
            enum has no "generic" bucket, so an empty error cannot be mapped.
    """

    violations = getattr(err, "violations", None)
    if not violations:
        raise ValueError(
            "TransitionError has no violations; cannot map to a closed "
            "ValidationErrorCode (would require inventing a fallback code)."
        )

    return ValidationError(
        code=ValidationErrorCode.UNKNOWN_LANE,
        message=str(err),
        path=[],
        details={"violations": list(violations)},
    )


def lifecycle_error_to_validation_error(err: Exception) -> ValidationError:
    """Convert a lifecycle-layer exception into a structured ``ValidationError``.

    The lifecycle module currently does not define typed exceptions of its
    own; once it does (WP04), each will be mapped here. Until then, this
    helper supports two well-known failure shapes encountered on the
    lifecycle/envelope boundary:

    * **Envelope shape failures.** Pydantic ``ValidationError`` instances
      (or any exception whose class name contains ``"Validation"``) raised
      while parsing an envelope wrapper map to
      :data:`ValidationErrorCode.ENVELOPE_SHAPE_INVALID`. The ``details``
      payload carries the original error string under ``"errors"``.
    * **Raw historical row failures.** Exceptions whose message identifies a
      historical local-status-row shape map to
      :data:`ValidationErrorCode.RAW_HISTORICAL_ROW`.

    Anything else raises ``ValueError`` — the closed enum has no generic
    fallback, so unmapped exceptions must be addressed at the call site.

    Raises:
        ValueError: if ``err`` cannot be mapped to a closed code.
    """

    msg = str(err)
    cls_name = type(err).__name__

    if "historical" in msg.lower() and "row" in msg.lower():
        return ValidationError(
            code=ValidationErrorCode.RAW_HISTORICAL_ROW,
            message=msg or "raw historical row detected",
            path=[],
            details={"detected_shape": "local_status_row"},
        )

    if "Validation" in cls_name or "envelope" in msg.lower():
        return ValidationError(
            code=ValidationErrorCode.ENVELOPE_SHAPE_INVALID,
            message=msg or "envelope shape invalid",
            path=[],
            details={"errors": [msg]},
        )

    raise ValueError(
        f"Cannot map exception of type {cls_name!r} to a closed "
        f"ValidationErrorCode; widen the enum or fix the mapping."
    )
