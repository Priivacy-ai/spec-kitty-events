# Phase 0 Research: Canonical Producer Contracts and Legacy Envelope Compatibility

## Method

This mission was scoped from a complete brief (`spec.md` Assumptions section captures the pre-mission audit). No `[NEEDS CLARIFICATION]` markers remain. The three research items below capture the field-shape, contract-shape, and dispatch-shape decisions made during pre-audit.

## R1: Field shapes for the seven uncontracted SaaS-bound event types

**Source audit**: `spec-kitty/src/specify_cli/sync/emitter.py` at commit `43305c12c`, lines 720–1431. Each of the seven event types is constructed by an `emit_*` method whose body directly assembles a `payload: dict[str, Any]` and routes it through `self._emit(event_type=<name>, aggregate_id=<id>, aggregate_type=<type>, payload=payload, ...)`. Because `_emit()` is the SaaS-bound central path (durable outbox + drain to SaaS), every one of these events is SaaS-bound by definition.

| Event type | Emit fn | Aggregate type | Required fields | Optional fields | Producer-call-site line |
|------------|---------|---------------|-----------------|-----------------|------------------------|
| `WPAssigned` | `emit_wp_assigned` | `WorkPackage` | `wp_id`, `agent_id`, `phase`, `retry_count` (default `0`) | — | 879 |
| `BuildRegistered` | `emit_build_registered` | `Build` | (envelope identity carries `build_id`, `node_id`) | `repo_slug`, `git_branch`, `head_commit_sha` (assembled via `_build_lifecycle_payload()`) | 722 |
| `BuildHeartbeat` | `emit_build_heartbeat` | `Build` | (same as BuildRegistered) | `remote_head`, `ahead_of_remote`, `behind_remote`, `recent_commits`, `repo_slug`, `git_branch`, `head_commit_sha` | 738 |
| `HistoryAdded` | `emit_history_added` | `WorkPackage` | `wp_id`, `entry_type`, `entry_content`, `author` (default `"user"`) | — | 1320 |
| `ErrorLogged` | `emit_error_logged` | `WorkPackage` or `Mission` | `error_type`, `error_message` | `wp_id`, `stack_trace`, `agent_id` | 1339 |
| `DependencyResolved` | `emit_dependency_resolved` | `WorkPackage` | `wp_id`, `dependency_wp_id`, `resolution_type` | — | 1370 |
| `MissionOriginBound` | `emit_mission_origin_bound` | `Mission` | `mission_slug`, `provider`, `external_issue_id`, `external_issue_key`, `external_issue_url`, `title` | `mission_id` | 1391 |

**Decision**: The seven payload models mirror these field shapes exactly. `ConfigDict(frozen=True, extra="forbid")` for all (matches conventions in `project_lifecycle.py`).

**Classification**: All seven SaaS-bound (route through `_emit()`). `LOCAL_ONLY_EVENT_TYPES` is shipped empty but the surface is published so Phase 2/3 have a place to put future local-only events without re-shipping a contract.

**Risk**: If the CLI emitter changes a field shape between this mission and Phase 2's refactor, the new pydantic model will reject the new shape. Mitigation: Phase 2 must update both the CLI emit and (if needed) the pydantic model in lockstep; this is the desired property — drift becomes a hard error at the contract boundary, not a silent SaaS materializer failure.

## R2: Legacy envelope shapes for `legacy_envelope_v1`

**Source audit**: existing fixtures under `src/spec_kitty_events/conformance/fixtures/class_taxonomy/envelope_valid_historical_synthesized/` and `class_taxonomy/historical_row_raw/`. Three historical envelope shapes appear in the fixture corpus:

1. **`pre_3_0_envelope`** — fixtures: `from_pre30_envelope.json`. Pre-3.0 wire envelopes that lack `project_uuid` but carry `event_type`, `payload`, `event_id`, `timestamp`, `node_id`, `build_id`. The synthetic canonical envelope is constructed by minting `project_uuid = uuid.uuid5(NAMESPACE_URL, f"spec-kitty-events/legacy/{node_id}/{build_id}")` and adding `schema_version = "3.0.0"`, `correlation_id = event_id` if absent.

2. **`feature_keys_envelope`** — fixtures: `from_envelope_with_legacy_keys.json`. Envelopes carrying retired top-level keys `feature_slug` and `feature_number`. Map `feature_slug → mission_slug`, `feature_number → mission_number`. Recursively strip if same keys appear in `payload`.

3. **`awaiting_review_synonym`** — fixtures: `from_in_review_legacy_synonym.json`. Envelopes whose `payload.to_lane == "awaiting-review"`. Map to canonical `payload.to_lane = "in_review"`. (The canonical lane has been `in_review` since 3.0; pre-3.0 producers used `awaiting-review`.)

**Decision**: Ship these three shapes in `legacy_envelope_v1`. Document the contract as named and frozen — any future additions (other legacy synonyms, schema-version bumps) ship as `legacy_envelope_v2` with both contracts coexisting for a deprecation window.

**Alternatives considered**:
- A wider initial catalog — rejected to keep the contract small and auditable.
- A discriminated tagged union for `NormalizationResult` — rejected; `isinstance` pattern is simpler and Python 3.10+ supports structural pattern matching for consumers.
- Embedding normalization inside `validate_event()` — rejected because that conflates conformance checking with shape repair. Phase 3 needs to keep the legacy normalization step explicit so un-normalizable rows are visible diagnostics, not silent passes.

## R3: Semantic validator dispatch shape

**Question**: Where does the call from `validate_event()` to `validate_transition()` live, and how does it stay extensible?

**Decision**: A module-level registry `_SEMANTIC_VALIDATORS: Dict[str, Callable[[BaseModel, dict], Tuple[ModelViolation, ...]]]` in `conformance/validators.py`. Initial entry: `"WPStatusChanged"` → `_semantic_validate_wp_status_changed`. The validator parses the payload dict into `StatusTransitionPayload`, calls `validate_transition()`, wraps each violation string in a `ModelViolation` with `field="transition"`, `violation_type="transition_rule"`. `validate_event()` invokes the dispatch only when the shape-validation pass returned no model violations (avoids double-faulting on malformed shape).

**Rationale**: Mirrors the existing `_EVENT_TYPE_TO_MODEL` / `_EVENT_TYPE_TO_SCHEMA` registry pattern in the same file. Future event types with semantic rules (e.g. terminal-lane exit checks) plug in with one line.

**Alternatives considered**:
- `@model_validator(mode="after")` on `StatusTransitionPayload` — rejected; would couple business-rule validation to model construction and break tests that construct payloads to test transitions in isolation.
- A second public function `validate_event_strict()` — rejected; would create a forking public surface and require every downstream consumer to choose which to call. The dispatch keeps the single public surface.

## Conclusion

All Phase 0 questions are resolved. No remaining `[NEEDS CLARIFICATION]` markers. Phase 1 design follows directly from R1–R3.
