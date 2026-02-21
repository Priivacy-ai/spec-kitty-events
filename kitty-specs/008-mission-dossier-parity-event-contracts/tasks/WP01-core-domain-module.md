---
work_package_id: WP01
title: Core Domain Module (dossier.py)
lane: "doing"
dependencies: []
base_branch: main
base_commit: 3a7bc8bb5c9aa0e4a33d99e89bf59e2a7cf37bc0
created_at: '2026-02-21T14:14:14.569721+00:00'
subtasks:
- T001
- T002
- T003
- T004
- T005
- T006
phase: Phase 1 - Foundation
assignee: ''
agent: ''
shell_pid: "98594"
review_status: ''
reviewed_by: ''
history:
- timestamp: '2026-02-21T14:00:00Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP01 – Core Domain Module (dossier.py)

## ⚠️ IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above. If it says `has_feedback`, scroll to the **Review Feedback** section immediately.
- **You must address all feedback** before your work is complete.
- **Mark as acknowledged**: Update `review_status: acknowledged` when you begin addressing feedback.

---

## Review Feedback

*[Empty initially. Reviewers populate this section if work is returned.]*

---

## Markdown Formatting
Wrap HTML/XML tags in backticks. Use language identifiers in code blocks: ` ```python `, ` ```bash `.

---

## Objectives & Success Criteria

Implement `src/spec_kitty_events/dossier.py` — the single flat domain module that contains everything for the Mission Dossier contract: constants, exception, provenance value objects, four event payload models, reducer output models, and the `reduce_mission_dossier()` reducer.

**Acceptance gates**:
- [ ] `mypy --strict src/spec_kitty_events/dossier.py` exits 0 (zero errors)
- [ ] `python3.11 -m pytest tests/test_dossier_reducer.py -x` passes (written in WP04, but basic importability check can run here)
- [ ] `python -c "from spec_kitty_events.dossier import reduce_mission_dossier, NamespaceMixedStreamError"` succeeds
- [ ] `artifact_class` does NOT appear as a top-level field on any event payload model
- [ ] `manifest_version` does NOT appear as a field on any event payload model (only in `LocalNamespaceTuple`)
- [ ] Reducer sort key is `(lamport_clock, timestamp, event_id)` — three fields
- [ ] `NamespaceMixedStreamError` message contains both the expected and offending namespace strings

## Context & Constraints

- **Spec**: `kitty-specs/008-mission-dossier-parity-event-contracts/spec.md`
- **Plan**: `kitty-specs/008-mission-dossier-parity-event-contracts/plan.md`
- **Data model**: `kitty-specs/008-mission-dossier-parity-event-contracts/data-model.md`
- **Contract stub**: `kitty-specs/008-mission-dossier-parity-event-contracts/contracts/dossier_types.py` — use this as the authoritative field specification; it is NOT runnable but shows exact field names, types, and required/optional status.

**Pattern to follow**: `src/spec_kitty_events/mission_next.py` — the reducer uses the same six-section structure (constants, exception/value-objects, payload models, reducer output models, reducer). The section comments (`# ── Section N: ... ──`) aid navigation; keep them.

**Critical invariants** (from spec review findings):
1. `artifact_class` is defined ONLY in `ArtifactIdentity` — never as a top-level event payload field.
2. `manifest_version` is defined ONLY in `LocalNamespaceTuple` — never in event payload fields.
3. Sort key must be three-field: `(lamport_clock, timestamp, event_id)`. Import `status_event_sort_key` from `status.py` — do NOT define your own sort key.
4. `NamespaceMixedStreamError` must carry both namespaces in the message.

**Implementation command** (no dependencies):
```bash
spec-kitty implement WP01
```

## Subtasks & Detailed Guidance

### Subtask T001 – Event type constants and DOSSIER_EVENT_TYPES

- **Purpose**: Provide canonical string constants for the 4 new event types and a frozenset for fast membership testing in the reducer.
- **Steps**:
  1. Add at the top of `dossier.py` (Section 1):
     ```python
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
     ```
  2. Add the module docstring, imports, and `from __future__ import annotations` at the very top.
- **Files**: `src/spec_kitty_events/dossier.py` (new file)
- **Notes**: `FrozenSet` import comes from `typing`. The frozenset uses the constant variables (not raw strings) to avoid typo drift.

### Subtask T002 – NamespaceMixedStreamError

- **Purpose**: Provide a typed exception that callers can catch specifically when the reducer encounters events from multiple namespaces — a domain-critical invariant, not a generic validation error.
- **Steps**:
  1. Add Section 2 immediately after Section 1:
     ```python
     class NamespaceMixedStreamError(ValueError):
         """Raised when reduce_mission_dossier() receives events from multiple namespaces.

         Message format:
             "Namespace mismatch in dossier event stream.
              Expected: <expected_ns>. Got: <offending_ns>."
         """
     ```
  2. No additional fields or methods needed — inheriting from `ValueError` is sufficient.
- **Files**: `src/spec_kitty_events/dossier.py`
- **Notes**: Exported from `__init__.py` in WP02 (T011). The message carrying both namespaces is enforced at the raise site in T006.

### Subtask T003 – Value objects (provenance sub-types)

- **Purpose**: Define the four typed provenance payload sub-types used as fields within event payloads and reducer output.
- **Steps**: Add Section 3 with these four models. Follow exact field spec from `data-model.md §2`.

  **LocalNamespaceTuple** (all 5 required + 1 optional):
  ```python
  class LocalNamespaceTuple(BaseModel):
      model_config = ConfigDict(frozen=True)
      project_uuid: str = Field(..., min_length=1)
      feature_slug: str = Field(..., min_length=1)
      target_branch: str = Field(..., min_length=1)
      mission_key: str = Field(..., min_length=1)
      manifest_version: str = Field(..., min_length=1)
      step_id: Optional[str] = Field(default=None)
  ```

  **ArtifactIdentity** — `artifact_class` is a `Literal` with all 6 class values:
  ```python
  class ArtifactIdentity(BaseModel):
      model_config = ConfigDict(frozen=True)
      mission_key: str = Field(..., min_length=1)
      path: str = Field(..., min_length=1)
      artifact_class: Literal[
          "input", "workflow", "output", "evidence", "policy", "runtime"
      ] = Field(...)
      run_id: Optional[str] = Field(default=None)
      wp_id: Optional[str] = Field(default=None)
  ```

  **ContentHashRef**:
  ```python
  class ContentHashRef(BaseModel):
      model_config = ConfigDict(frozen=True)
      hash: str = Field(..., min_length=1)
      algorithm: Literal["sha256", "sha512", "md5"] = Field(...)
      size_bytes: Optional[int] = Field(default=None, ge=0)
      encoding: Optional[str] = Field(default=None)
  ```

  **ProvenanceRef** (all optional):
  ```python
  class ProvenanceRef(BaseModel):
      model_config = ConfigDict(frozen=True)
      source_event_ids: Optional[Tuple[str, ...]] = Field(default=None)
      git_sha: Optional[str] = Field(default=None)
      git_ref: Optional[str] = Field(default=None)
      actor_id: Optional[str] = Field(default=None)
      actor_kind: Optional[Literal["human", "llm", "system"]] = Field(default=None)
      revised_at: Optional[str] = Field(default=None)
  ```

- **Files**: `src/spec_kitty_events/dossier.py`
- **Parallel?**: Yes — can be written alongside T004 once T001/T002 are done.

### Subtask T004 – Four event payload models

- **Purpose**: Define the typed payload models for the four new domain events.
- **Steps**: Add Section 4 with these four models. Critical: `artifact_class` is NEVER at the top level — it lives in `ArtifactIdentity`; `manifest_version` is NEVER in payload — it lives in `LocalNamespaceTuple.manifest_version`.

  **MissionDossierArtifactIndexedPayload**:
  - Required: `namespace: LocalNamespaceTuple`, `artifact_id: ArtifactIdentity`, `content_ref: ContentHashRef`, `indexed_at: str`
  - Optional: `provenance`, `step_id`, `supersedes: Optional[ArtifactIdentity]`, `context_diagnostics: Optional[Dict[str, str]]`
  - Field doc on `namespace`: `"Carries manifest_version — not duplicated in payload"`
  - Field doc on `artifact_id`: `"Carries artifact_class — not duplicated at top level"`

  **MissionDossierArtifactMissingPayload**:
  - Required: `namespace`, `expected_identity: ArtifactIdentity`, `manifest_step: str` (min_length=1), `checked_at: str`
  - Optional: `last_known_ref: Optional[ProvenanceRef]`, `remediation_hint: Optional[str]`, `context_diagnostics`
  - Field doc on `expected_identity`: `"Carries path and artifact_class of missing artifact"`

  **MissionDossierSnapshotComputedPayload**:
  - Required: `namespace`, `snapshot_hash: str` (min_length=1), `artifact_count: int` (ge=0), `anomaly_count: int` (ge=0), `computed_at: str`
  - Optional: `algorithm: Optional[Literal["sha256", "sha512", "md5"]]`, `context_diagnostics`
  - Field doc: `"manifest_version NOT duplicated here — use namespace.manifest_version"`

  **MissionDossierParityDriftDetectedPayload**:
  - Required: `namespace`, `expected_hash: str` (min_length=1), `actual_hash: str` (min_length=1), `drift_kind: Literal["artifact_added", "artifact_removed", "artifact_mutated", "anomaly_introduced", "anomaly_resolved", "manifest_version_changed"]`, `detected_at: str`
  - Optional: `artifact_ids_changed: Optional[Tuple[ArtifactIdentity, ...]]`, `rebuild_hint: Optional[str]`, `context_diagnostics`

- **Files**: `src/spec_kitty_events/dossier.py`
- **Parallel?**: Yes — separate class definitions, can be written alongside T003.

### Subtask T005 – Reducer output models and MissionDossierState

- **Purpose**: Define the five frozen models that constitute the reducer's output projection.
- **Steps**: Add Section 5 with these models in dependency order:

  ```python
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
      model_config = ConfigDict(frozen=True)
      namespace: Optional[LocalNamespaceTuple] = None
      artifacts: Dict[str, ArtifactEntry] = Field(default_factory=dict)
      anomalies: Tuple[AnomalyEntry, ...] = Field(default_factory=tuple)
      latest_snapshot: Optional[SnapshotSummary] = None
      drift_history: Tuple[DriftRecord, ...] = Field(default_factory=tuple)
      parity_status: Literal["clean", "drifted", "unknown"] = "unknown"
      event_count: int = 0
  ```

- **Files**: `src/spec_kitty_events/dossier.py`
- **Notes**: `MissionDossierState` uses `Dict` (not `FrozenDict`) because Pydantic frozen=True prevents attribute reassignment, not dict mutation; the dict itself will be constructed once and returned.

### Subtask T006 – reduce_mission_dossier() reducer

- **Purpose**: Implement the pure, deterministic reducer that folds a sequence of `Event` envelope objects into a `MissionDossierState`.
- **Steps**: Add Section 6 with the reducer function. Pipeline:

  ```python
  def reduce_mission_dossier(events: Sequence[Event]) -> MissionDossierState:
      from spec_kitty_events.status import dedup_events, status_event_sort_key

      # 1. Filter to dossier event types
      dossier_events = [e for e in events if e.event_type in DOSSIER_EVENT_TYPES]
      if not dossier_events:
          return MissionDossierState()

      # 2. Sort by (lamport_clock, timestamp, event_id)
      sorted_events = sorted(dossier_events, key=status_event_sort_key)

      # 3. Deduplicate by event_id
      unique_events = dedup_events(sorted_events)

      # 4. Validate single-namespace invariant
      first_namespace = _extract_namespace(unique_events[0])
      for event in unique_events[1:]:
          ns = _extract_namespace(event)
          if ns != first_namespace:
              raise NamespaceMixedStreamError(
                  f"Namespace mismatch in dossier event stream. "
                  f"Expected: {first_namespace}. Got: {ns}."
              )

      # 5. Fold events into mutable intermediates
      namespace = first_namespace
      artifacts: Dict[str, ArtifactEntry] = {}
      anomalies: List[AnomalyEntry] = []
      latest_snapshot: Optional[SnapshotSummary] = None
      drift_history: List[DriftRecord] = []
      parity_status = "unknown"

      for event in unique_events:
          etype = event.event_type
          if etype == MISSION_DOSSIER_ARTIFACT_INDEXED:
              # parse payload, upsert artifacts dict, mark superseded if needed
              ...
          elif etype == MISSION_DOSSIER_ARTIFACT_MISSING:
              # parse payload, add/update AnomalyEntry
              ...
          elif etype == MISSION_DOSSIER_SNAPSHOT_COMPUTED:
              # parse payload, set latest_snapshot, update parity_status
              ...
          elif etype == MISSION_DOSSIER_PARITY_DRIFT_DETECTED:
              # parse payload, append DriftRecord, set parity_status="drifted"
              ...

      # 6. Assemble frozen state
      return MissionDossierState(
          namespace=namespace,
          artifacts=artifacts,
          anomalies=tuple(anomalies),
          latest_snapshot=latest_snapshot,
          drift_history=tuple(drift_history),
          parity_status=parity_status,
          event_count=len(unique_events),
      )
  ```

  **Reducer logic details**:

  - **ARTIFACT_INDEXED**: Parse `MissionDossierArtifactIndexedPayload(**event.payload)`. If `supersedes` is set and the superseded `path` exists in `artifacts`, mark its entry `superseded=True`. Upsert `artifacts[payload.artifact_id.path]` with new `ArtifactEntry`.
  - **ARTIFACT_MISSING**: Parse `MissionDossierArtifactMissingPayload(**event.payload)`. Append `AnomalyEntry` to anomalies list (allow duplicate missing anomalies for same path if re-checked).
  - **SNAPSHOT_COMPUTED**: Parse `MissionDossierSnapshotComputedPayload(**event.payload)`. Set `latest_snapshot`. If `anomaly_count == 0` and no drift records, set `parity_status = "clean"`.
  - **PARITY_DRIFT_DETECTED**: Parse `MissionDossierParityDriftDetectedPayload(**event.payload)`. Append `DriftRecord`. Set `parity_status = "drifted"`.

  **parity_status derivation** (after full fold):
  - If `drift_history` is non-empty → `"drifted"`
  - Else if `latest_snapshot` is not None → `"clean"`
  - Else → `"unknown"`

  **Helper**:
  ```python
  def _extract_namespace(event: Event) -> Optional[LocalNamespaceTuple]:
      """Extract namespace from a dossier event's payload dict."""
      ns_dict = event.payload.get("namespace")
      if ns_dict is None:
          return None
      try:
          return LocalNamespaceTuple(**ns_dict)
      except Exception:
          return None
  ```
  Compare namespace objects by value (Pydantic frozen models support `==`).

  **Unknown event types**: The filter in step 1 ensures only dossier event types reach the fold loop; no explicit skip needed inside the loop.

  **Payload parse failures**: If `Model(**event.payload)` raises, skip the event silently (analogous to `mission_next.py` anomaly handling). Do not propagate payload parse errors as exceptions.

- **Files**: `src/spec_kitty_events/dossier.py`
- **Notes**: Use distinct variable names per type branch (e.g., `payload_indexed`, `payload_missing`) to satisfy mypy strict's no-reuse-across-branches rule.

## Risks & Mitigations

- **mypy strict + `from __future__ import annotations`**: if a `Literal` type is used as a default value, mypy may complain. Use `Field(default="unknown")` rather than bare `= "unknown"` where type narrowing matters.
- **`Optional[Dict[str, str]]`** for `context_diagnostics`: Pydantic v2 handles `Dict` fine; no need for `dict[str, str]` lowercase form (keep `Dict` from `typing` for 3.10 compat with `from __future__ import annotations`).
- **`_extract_namespace` vs direct dict access**: The `payload` field on `Event` is `Dict[str, Any]`, so `.get("namespace")` is safe. Always wrap in `try/except` for resilience.

## Review Guidance

1. Run `mypy --strict src/spec_kitty_events/dossier.py` — must exit 0.
2. Confirm `artifact_class` does NOT appear at top-level in any payload model class body.
3. Confirm `manifest_version` does NOT appear in any event payload model class body.
4. Check that the reducer's sort call uses `status_event_sort_key` from `status.py`, not a lambda.
5. Check that `NamespaceMixedStreamError` is raised with a message containing both namespace repr strings.
6. Confirm `parity_status` derivation is done AFTER the full fold loop (not inside the loop).
7. Check `MissionDossierState.artifacts` key is `artifact_id.path` (string), not the full `ArtifactIdentity` object.

## Activity Log

- 2026-02-21T14:00:00Z – system – lane=planned – Prompt created.
