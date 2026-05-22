# Data Model: Canonical Producer Contracts and Legacy Envelope Compatibility

This artifact captures the public types this mission ships. All models use pydantic 2.x with `ConfigDict(frozen=True, extra="forbid")` unless noted.

## Legacy normalizer types

### `NormalizedEnvelope`

Wraps a canonical envelope produced by promoting a named legacy shape.

| Field | Type | Description |
|-------|------|-------------|
| `canonical` | `dict` | Canonical-shape event ready for `validate_event(strict=True)`. |
| `raw` | `dict` | Original raw input retained for audit. |
| `legacy_shape` | `Literal["pre_3_0_envelope", "feature_keys_envelope", "awaiting_review_synonym"]` | Which named shape detector matched. |

### `UnnormalizableLegacyDiagnostic`

Structured diagnostic for legacy rows that cannot be promoted to canonical shape.

| Field | Type | Description |
|-------|------|-------------|
| `reason` | `str` | Machine-readable reason code (e.g. `"pre_3_0_envelope_missing_identity"`, `"unrecognized_legacy_shape"`). |
| `shape_hints` | `list[str]` | Free-form hints describing why detection or normalization failed (e.g. `["missing project_uuid", "missing node_id"]`). |
| `raw` | `dict` | Original raw input retained for audit. |

### `NormalizationResult`

```python
NormalizationResult = Union[NormalizedEnvelope, UnnormalizableLegacyDiagnostic]
```

Consumers pattern-match on `isinstance` (or `match`/`case` in 3.10+).

### `LegacyEnvelopeNormalizer`

Stateless class with one public method:

```python
def normalize(self, raw_event: dict) -> NormalizationResult: ...
```

Internally walks the ordered detector list (see `research.md` R2). First match wins; fallthrough emits `UnnormalizableLegacyDiagnostic(reason="unrecognized_legacy_shape", ...)`.

### Constants

| Name | Value |
|------|-------|
| `LEGACY_ENVELOPE_CONTRACT_NAME` | `"legacy_envelope_v1"` |
| `RECOGNIZED_LEGACY_SHAPES` | `frozenset({"pre_3_0_envelope", "feature_keys_envelope", "awaiting_review_synonym"})` |

## Seven previously-uncontracted payload models

Field shapes mirror the producer call sites audited in `research.md` R1.

### `WPAssignedPayload`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `wp_id` | `str` (min_length=1) | yes | Work-package identifier. |
| `agent_id` | `str` (min_length=1) | yes | Agent that picked up the WP. |
| `phase` | `str` (min_length=1) | yes | Phase of work (e.g. `"implement"`, `"review"`). |
| `retry_count` | `int` (ge=0, default=0) | no | Number of times the assignment has been retried. |

### `BuildRegisteredPayload`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `repo_slug` | `Optional[str]` (min_length=1) | no | Git repository slug. |
| `git_branch` | `Optional[str]` (min_length=1) | no | Active branch when build registered. |
| `head_commit_sha` | `Optional[str]` (min_length=1) | no | Head commit SHA when build registered. |

Note: build identity (`build_id`, `node_id`) lives on the envelope; this payload carries optional repo enrichment.

### `BuildHeartbeatPayload`

Inherits `BuildRegisteredPayload` semantics plus:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `remote_head` | `Optional[str]` (min_length=1) | no | Remote head commit SHA at heartbeat time. |
| `ahead_of_remote` | `Optional[int]` (ge=0) | no | Local commits ahead of remote. |
| `behind_remote` | `Optional[int]` (ge=0) | no | Local commits behind remote. |
| `recent_commits` | `Optional[list[str]]` | no | Recent local commit SHAs. |

### `HistoryAddedPayload`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `wp_id` | `str` (min_length=1) | yes | WP the history entry attaches to. |
| `entry_type` | `str` (min_length=1) | yes | Entry type code (e.g. `"note"`, `"decision"`). |
| `entry_content` | `str` (min_length=1) | yes | Entry body. |
| `author` | `str` (min_length=1) | yes | Who authored the entry. |

### `ErrorLoggedPayload`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `error_type` | `str` (min_length=1) | yes | Error class name or category. |
| `error_message` | `str` (min_length=1) | yes | Human-readable error message. |
| `wp_id` | `Optional[str]` (min_length=1) | no | WP context (when known). |
| `stack_trace` | `Optional[str]` | no | Stack trace text. |
| `agent_id` | `Optional[str]` (min_length=1) | no | Agent that observed the error. |

### `DependencyResolvedPayload`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `wp_id` | `str` (min_length=1) | yes | WP whose dependency resolved. |
| `dependency_wp_id` | `str` (min_length=1) | yes | The dependency WP that resolved. |
| `resolution_type` | `str` (min_length=1) | yes | How the dependency resolved (e.g. `"merged"`, `"skipped"`). |

### `MissionOriginBoundPayload`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `mission_slug` | `str` (min_length=1) | yes | Canonical mission slug. |
| `provider` | `str` (min_length=1) | yes | External tracker provider (e.g. `"github"`, `"linear"`). |
| `external_issue_id` | `str` (min_length=1) | yes | Provider-native issue id. |
| `external_issue_key` | `str` (min_length=1) | yes | Display key (e.g. `"PROJ-123"`). |
| `external_issue_url` | `str` (min_length=1) | yes | Browser URL. |
| `title` | `str` (min_length=1) | yes | External issue title. |
| `mission_id` | `Optional[str]` (min_length=1) | no | Canonical mission ULID. |

## `LOCAL_ONLY_EVENT_TYPES`

```python
LOCAL_ONLY_EVENT_TYPES: frozenset[str] = frozenset()
```

Empty in this mission. All seven previously-uncontracted events are SaaS-bound per the pre-mission audit. The surface is exported so Phase 2/3 have a stable place to add machine-readable local-only classifications without re-shipping a contract.

## Conformance ModelViolation surface (existing, unchanged)

The semantic validator pass synthesizes `ModelViolation` entries with:

| Field | Value |
|-------|-------|
| `field` | `"transition"` |
| `violation_type` | `"transition_rule"` |
| `message` | The exact string returned by `validate_transition()`, preserved verbatim so consumers can route on substrings `force=True` and `review-rejection`. |
| `input_value` | The payload dict the validator received. |

## Backward-compatibility guarantees

- No envelope-shape change.
- No existing payload field shape change.
- No `schema_version` bump.
- No new JSON Schema additions in this mission (existing schemas unchanged; Phase 5 may add schemas for the new types).
- No new pip dependencies.
- All additions are new public surfaces in the package; existing callers see no behavior change unless they pass a `WPStatusChanged` with an invalid review-rejection transition (which is the desired behavior change).
