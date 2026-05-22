"""Build-aggregate event contracts.

Defines canonical pydantic payload models for build-lifecycle events emitted
by the spec-kitty CLI: ``BuildRegistered`` and ``BuildHeartbeat``. Build
identity (``build_id``, ``node_id``) lives on the canonical Event envelope;
these payloads carry only repo enrichment and (for BuildHeartbeat) sync
state vs the remote.

Aggregate type: ``Build``.

Shipped with mission ``canonical-producer-contracts-legacy-envelope-01KS7JM3``.
"""

from __future__ import annotations

from typing import FrozenSet, List, Optional

from pydantic import BaseModel, ConfigDict, Field

# Event type string constants
BUILD_REGISTERED: str = "BuildRegistered"
BUILD_HEARTBEAT: str = "BuildHeartbeat"

BUILD_LIFECYCLE_EVENT_TYPES: FrozenSet[str] = frozenset({
    BUILD_REGISTERED,
    BUILD_HEARTBEAT,
})


class BuildRegisteredPayload(BaseModel):
    """Typed payload for ``BuildRegistered`` events.

    Emitted once per build identity startup. Identity itself (``build_id``,
    ``node_id``) is on the envelope; this payload carries optional repo
    enrichment so consumers can correlate builds with git context.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    repo_slug: Optional[str] = Field(
        None, min_length=1, description="Git repository slug (e.g. 'org/repo')."
    )
    git_branch: Optional[str] = Field(
        None, min_length=1, description="Active git branch when the build registered."
    )
    head_commit_sha: Optional[str] = Field(
        None, min_length=1, description="Head commit SHA when the build registered."
    )


class BuildHeartbeatPayload(BaseModel):
    """Typed payload for ``BuildHeartbeat`` events.

    Emitted periodically by an active build. Carries repo enrichment plus
    optional sync state vs the remote so observers can detect divergence.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    repo_slug: Optional[str] = Field(
        None, min_length=1, description="Git repository slug."
    )
    git_branch: Optional[str] = Field(
        None, min_length=1, description="Active git branch at heartbeat time."
    )
    head_commit_sha: Optional[str] = Field(
        None, min_length=1, description="Head commit SHA at heartbeat time."
    )
    remote_head: Optional[str] = Field(
        None, min_length=1, description="Remote head commit SHA at heartbeat time."
    )
    ahead_of_remote: Optional[int] = Field(
        None, ge=0, description="Local commits ahead of the remote."
    )
    behind_remote: Optional[int] = Field(
        None, ge=0, description="Local commits behind the remote."
    )
    recent_commits: Optional[List[str]] = Field(
        None, description="Recent local commit SHAs (most-recent-first)."
    )


__all__ = [
    "BUILD_REGISTERED",
    "BUILD_HEARTBEAT",
    "BUILD_LIFECYCLE_EVENT_TYPES",
    "BuildRegisteredPayload",
    "BuildHeartbeatPayload",
]
