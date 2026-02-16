"""Glossary semantic integrity event contracts for Feature 007.

Defines event type constants, value objects, payload models,
reducer output models, and the glossary reducer for
mission-level semantic integrity enforcement.
"""

from __future__ import annotations

from typing import Dict, FrozenSet, List, Literal, Optional, Sequence, Tuple

from pydantic import BaseModel, ConfigDict, Field

from spec_kitty_events.models import SpecKittyEventsError

# ── Section 1: Constants ─────────────────────────────────────────────────────

GLOSSARY_SCOPE_ACTIVATED: str = "GlossaryScopeActivated"
TERM_CANDIDATE_OBSERVED: str = "TermCandidateObserved"
SEMANTIC_CHECK_EVALUATED: str = "SemanticCheckEvaluated"
GLOSSARY_CLARIFICATION_REQUESTED: str = "GlossaryClarificationRequested"
GLOSSARY_CLARIFICATION_RESOLVED: str = "GlossaryClarificationResolved"
GLOSSARY_SENSE_UPDATED: str = "GlossarySenseUpdated"
GENERATION_BLOCKED_BY_SEMANTIC_CONFLICT: str = "GenerationBlockedBySemanticConflict"
GLOSSARY_STRICTNESS_SET: str = "GlossaryStrictnessSet"

GLOSSARY_EVENT_TYPES: FrozenSet[str] = frozenset({
    GLOSSARY_SCOPE_ACTIVATED,
    TERM_CANDIDATE_OBSERVED,
    SEMANTIC_CHECK_EVALUATED,
    GLOSSARY_CLARIFICATION_REQUESTED,
    GLOSSARY_CLARIFICATION_RESOLVED,
    GLOSSARY_SENSE_UPDATED,
    GENERATION_BLOCKED_BY_SEMANTIC_CONFLICT,
    GLOSSARY_STRICTNESS_SET,
})

# ── Section 2: Value Objects ─────────────────────────────────────────────────

# ── Section 3: Payload Models ────────────────────────────────────────────────

# ── Section 4: Reducer Output Models ─────────────────────────────────────────

# ── Section 5: Glossary Reducer ──────────────────────────────────────────────
