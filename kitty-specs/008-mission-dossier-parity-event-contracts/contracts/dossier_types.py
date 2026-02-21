"""
Type stub / reference contract for dossier.py

This file shows the intended public surface for implementers.
It is NOT runnable — it is a specification aid only.
The real implementation lives in src/spec_kitty_events/dossier.py.

Section numbers match plan.md WP01 sections.
"""
from __future__ import annotations

from typing import Dict, FrozenSet, Literal, Optional, Sequence, Tuple
from pydantic import BaseModel, ConfigDict, Field

from spec_kitty_events.models import Event  # existing envelope

# ── Section 1: Event Type Constants ──────────────────────────────────────────

MISSION_DOSSIER_ARTIFACT_INDEXED: str = "MissionDossierArtifactIndexed"
MISSION_DOSSIER_ARTIFACT_MISSING: str = "MissionDossierArtifactMissing"
MISSION_DOSSIER_SNAPSHOT_COMPUTED: str = "MissionDossierSnapshotComputed"
MISSION_DOSSIER_PARITY_DRIFT_DETECTED: str = "MissionDossierParityDriftDetected"

DOSSIER_EVENT_TYPES: FrozenSet[str] = frozenset({
    MISSION_DOSSIER_ARTIFACT_INDEXED,
    MISSION_DOSSIER_ARTIFACT_MISSING,
    MISSION_DOSSIER_SNAPSHOT_COMPUTED,
    MISSION_DOSSIER_PARITY_DRIFT_DETECTED,
})

# ── Section 2: Exception ──────────────────────────────────────────────────────

class NamespaceMixedStreamError(ValueError):
    """Raised when reduce_mission_dossier() detects events from multiple namespaces.

    Message must include both the expected namespace (from the first dossier event)
    and the offending namespace (from the conflicting event), formatted as:
        "Namespace mismatch in dossier event stream. Expected: <ns>. Got: <ns>."
    """

# ── Section 3: Value Objects (provenance sub-types) ───────────────────────────

ArtifactClassT = Literal["input", "workflow", "output", "evidence", "policy", "runtime"]
DriftKindT = Literal[
    "artifact_added", "artifact_removed", "artifact_mutated",
    "anomaly_introduced", "anomaly_resolved", "manifest_version_changed",
]
AlgorithmT = Literal["sha256", "sha512", "md5"]
ParityStatusT = Literal["clean", "drifted", "unknown"]
ActorKindT = Literal["human", "llm", "system"]


class LocalNamespaceTuple(BaseModel):
    """Minimum collision-safe key for parity baseline scoping."""
    model_config = ConfigDict(frozen=True)

    project_uuid: str = Field(..., min_length=1)
    feature_slug: str = Field(..., min_length=1)
    target_branch: str = Field(..., min_length=1)
    mission_key: str = Field(..., min_length=1)
    manifest_version: str = Field(..., min_length=1)
    step_id: Optional[str] = Field(default=None)


class ArtifactIdentity(BaseModel):
    """Canonical identity for one artifact instance.

    artifact_class is the SINGLE source of truth for artifact taxonomy.
    Event payloads MUST NOT duplicate this field at the top level.
    """
    model_config = ConfigDict(frozen=True)

    mission_key: str = Field(..., min_length=1)
    path: str = Field(..., min_length=1, description="Repository-relative path")
    artifact_class: ArtifactClassT = Field(...)
    run_id: Optional[str] = Field(default=None)
    wp_id: Optional[str] = Field(default=None)


class ContentHashRef(BaseModel):
    """Content fingerprint with optional size and encoding metadata."""
    model_config = ConfigDict(frozen=True)

    hash: str = Field(..., min_length=1, description="Hex-encoded content hash")
    algorithm: AlgorithmT = Field(...)
    size_bytes: Optional[int] = Field(default=None, ge=0)
    encoding: Optional[str] = Field(default=None)


class ProvenanceRef(BaseModel):
    """Source trace connecting an artifact or event to its authoritative origin."""
    model_config = ConfigDict(frozen=True)

    source_event_ids: Optional[Tuple[str, ...]] = Field(default=None)
    git_sha: Optional[str] = Field(default=None)
    git_ref: Optional[str] = Field(default=None)
    actor_id: Optional[str] = Field(default=None)
    actor_kind: Optional[ActorKindT] = Field(default=None)
    revised_at: Optional[str] = Field(default=None, description="ISO 8601")

# ── Section 4: Payload Models ─────────────────────────────────────────────────

class MissionDossierArtifactIndexedPayload(BaseModel):
    model_config = ConfigDict(frozen=True)

    namespace: LocalNamespaceTuple = Field(...)
    artifact_id: ArtifactIdentity = Field(...)        # artifact_class lives here only
    content_ref: ContentHashRef = Field(...)
    indexed_at: str = Field(..., description="ISO 8601")
    provenance: Optional[ProvenanceRef] = Field(default=None)
    step_id: Optional[str] = Field(default=None)
    supersedes: Optional[ArtifactIdentity] = Field(default=None)
    context_diagnostics: Optional[Dict[str, str]] = Field(default=None)
    # NOTE: manifest_version NOT duplicated here — use namespace.manifest_version


class MissionDossierArtifactMissingPayload(BaseModel):
    model_config = ConfigDict(frozen=True)

    namespace: LocalNamespaceTuple = Field(...)
    expected_identity: ArtifactIdentity = Field(...)  # artifact_class lives here only
    manifest_step: str = Field(..., min_length=1, description='"required_always" or step_id')
    checked_at: str = Field(..., description="ISO 8601")
    last_known_ref: Optional[ProvenanceRef] = Field(default=None)
    remediation_hint: Optional[str] = Field(default=None)
    context_diagnostics: Optional[Dict[str, str]] = Field(default=None)


class MissionDossierSnapshotComputedPayload(BaseModel):
    model_config = ConfigDict(frozen=True)

    namespace: LocalNamespaceTuple = Field(...)       # manifest_version lives here only
    snapshot_hash: str = Field(..., min_length=1, description="Hex-encoded deterministic hash")
    artifact_count: int = Field(..., ge=0)
    anomaly_count: int = Field(..., ge=0)
    computed_at: str = Field(..., description="ISO 8601")
    algorithm: Optional[AlgorithmT] = Field(default=None)
    context_diagnostics: Optional[Dict[str, str]] = Field(default=None)
    # NOTE: manifest_version NOT duplicated here — use namespace.manifest_version


class MissionDossierParityDriftDetectedPayload(BaseModel):
    model_config = ConfigDict(frozen=True)

    namespace: LocalNamespaceTuple = Field(...)
    expected_hash: str = Field(..., min_length=1)
    actual_hash: str = Field(..., min_length=1)
    drift_kind: DriftKindT = Field(...)
    detected_at: str = Field(..., description="ISO 8601")
    artifact_ids_changed: Optional[Tuple[ArtifactIdentity, ...]] = Field(default=None)
    rebuild_hint: Optional[str] = Field(default=None)
    context_diagnostics: Optional[Dict[str, str]] = Field(default=None)

# ── Section 5: Reducer Output Models ─────────────────────────────────────────

class ArtifactEntry(BaseModel):
    model_config = ConfigDict(frozen=True)
    identity: ArtifactIdentity
    content_ref: ContentHashRef
    indexed_at: str
    provenance: Optional[ProvenanceRef] = None
    superseded: bool = False
    step_id: Optional[str] = None


class AnomalyEntry(BaseModel):
    model_config = ConfigDict(frozen=True)
    anomaly_type: Literal["missing_artifact"] = "missing_artifact"
    expected_identity: ArtifactIdentity
    manifest_step: str
    checked_at: str
    remediation_hint: Optional[str] = None


class SnapshotSummary(BaseModel):
    model_config = ConfigDict(frozen=True)
    snapshot_hash: str
    artifact_count: int
    anomaly_count: int
    computed_at: str
    algorithm: str = "sha256"


class DriftRecord(BaseModel):
    model_config = ConfigDict(frozen=True)
    expected_hash: str
    actual_hash: str
    drift_kind: str
    detected_at: str


class MissionDossierState(BaseModel):
    """Deterministic projection output of reduce_mission_dossier()."""
    model_config = ConfigDict(frozen=True)

    namespace: Optional[LocalNamespaceTuple] = None
    artifacts: Dict[str, ArtifactEntry] = Field(default_factory=dict)
    anomalies: Tuple[AnomalyEntry, ...] = Field(default_factory=tuple)
    latest_snapshot: Optional[SnapshotSummary] = None
    drift_history: Tuple[DriftRecord, ...] = Field(default_factory=tuple)
    parity_status: ParityStatusT = "unknown"
    event_count: int = 0

# ── Section 6: Reducer Signature ──────────────────────────────────────────────

def reduce_mission_dossier(events: Sequence[Event]) -> MissionDossierState:
    """Fold dossier events into deterministic MissionDossierState.

    Pipeline:
    1. Filter to DOSSIER_EVENT_TYPES
    2. Sort by (lamport_clock, timestamp, event_id) via status_event_sort_key
    3. Deduplicate by event_id via dedup_events
    4. Validate namespace consistency — raise NamespaceMixedStreamError on mismatch
    5. Fold each event into mutable intermediates
    6. Assemble and return frozen MissionDossierState

    Raises:
        NamespaceMixedStreamError: If events span multiple namespace tuples.

    Pure function. No I/O. No global state. Deterministic.
    """
    ...
