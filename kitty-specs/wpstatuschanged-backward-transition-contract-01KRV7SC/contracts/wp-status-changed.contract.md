# Superseded Contract: WPStatusChanged Event Semantics

**Status**: Superseded by mission `force-required-review-rejection-01KRWWVJ`.
**Owners**: `spec-kitty-events` maintainers.
**Consumers**: `spec-kitty` CLI, `spec-kitty-saas` materializer, `spec-kitty-saas` durable drain worker.
**Binding artefacts**: Historical reference only. The current binding contract is the `src/spec_kitty_events/status.py` review-rejection family docstring, `validate_transition()` behavior, `docs/consumer-contract-dossier-v2.4.0.md` review-rejection section, and the registered conformance fixtures.

> This artifact is no longer canonical. The superseding doctrine requires `force=true` plus a non-empty `reason` for the four review-rejection family pairs into `planned`: `in_progress -> planned`, `for_review -> planned`, `in_review -> planned`, and `approved -> planned`. `review_ref` is optional/recommended for those forced family members.

---

## 1. Event shape

`WPStatusChanged` wraps a `StatusTransitionPayload` (`src/spec_kitty_events/status.py`):

| Field | Type | Required | Notes |
|---|---|---|---|
| `mission_slug` | str (non-empty) | yes | |
| `wp_id` | str (non-empty) | yes | |
| `from_lane` | `Lane \| null` | no | `null` allowed only for the canonical bootstrap transition `(null → planned)` with `force=true`. |
| `to_lane` | `Lane` | yes | |
| `actor` | str \| dict | yes | Audit-only. **Does not modify validation.** See §4. |
| `force` | bool | yes (default `false`) | See §3 for the exact cases that require `force=true`. |
| `reason` | str \| null | conditional | Required when `force=true` (non-empty). Required when `from_lane=in_progress` and `to_lane=planned` (non-empty). |
| `execution_mode` | `ExecutionMode` | yes | |
| `review_ref` | str \| null | optional/conditional | Optional/recommended for forced review-rejection family members into `planned`; still required for older non-planned review-rollback paths such as `for_review -> in_progress`. |
| `evidence` | `DoneEvidence \| null` | conditional | Required when `to_lane in {approved, done}`. |

The wire envelope adds `event_id` (ULID), `event_type` (`"WPStatusChanged"`), and standard envelope metadata. `event_id` is treated as the canonical replay key (§6).

## 2. Lane set and the allowed-transition matrix

The `Lane` enum has these values: `planned`, `claimed`, `in_progress`, `for_review`, `in_review`, `approved`, `done`, `blocked`, `canceled`.

The historical transition matrix is the frozenset literal in `src/spec_kitty_events/status.py`. The four review-rejection family pairs into `planned` remain in the matrix for forced acceptance, but the explicit family guard rejects them unless `force=true`.

| from_lane | to_lane | Notes |
|---|---|---|
| `null` | `planned` | Bootstrap (also requires `force=true`; see §3) |
| `planned` | `claimed` | Forward |
| `claimed` | `in_progress` | Forward |
| `in_progress` | `for_review` | Forward |
| `in_progress` | `approved` | Forward (uncommon) |
| `for_review` | `in_review` | Forward |
| `for_review` | `approved` | Forward |
| `for_review` | `done` | Forward |
| `in_review` | `approved` | Forward |
| `in_review` | `done` | Forward |
| `approved` | `done` | Forward |
| `for_review` | `in_progress` | **Review rollback** — requires `review_ref` (§3.3) |
| `for_review` | `planned` | **Review-rejection family** — requires `force=true` + non-empty `reason`; `review_ref` optional/recommended |
| `in_review` | `in_progress` | **Review rollback** — requires `review_ref` |
| `in_review` | `for_review` | **Review rollback** |
| `in_review` | `planned` | **Review-rejection family** — requires `force=true` + non-empty `reason`; `review_ref` optional/recommended |
| `approved` | `in_progress` | **Review rollback** — requires `review_ref` |
| `approved` | `planned` | **Review-rejection family** — requires `force=true` + non-empty `reason`; `review_ref` optional/recommended |
| `in_progress` | `planned` | **Review-rejection family** — requires `force=true` + non-empty `reason`; `review_ref` optional/recommended |
| `blocked` | `in_progress` | Unblock |

Plus the always-allowed sinks:
- `* → blocked` from any non-terminal lane.
- `* → canceled` from any non-terminal lane.

`done` and `canceled` are **terminal**. Exiting either requires `force=true` (§3.1).

## 3. When `force=true` is required

### 3.1 Terminal exit

Any transition where `from_lane in {done, canceled}` requires `force=true` AND a non-empty `reason`. There is no exception.

### 3.2 Outside-matrix transitions

Any `(from_lane, to_lane)` pair not in §2 requires `force=true` (and the same `reason` requirement). Examples: `done → done`, `planned → done` (sketch flows skip lanes), etc.

### 3.3 Review-rejection family requires `force=true`

This section supersedes the original locked decision from this historical mission.

> **Review-rejection family transitions** — `in_progress -> planned`, `for_review -> planned`, `in_review -> planned`, and `approved -> planned` — MUST NOT be accepted unless `force=true` and `reason` is non-empty.

A consumer that accepts an unforced review-rejection family transition is non-conformant with the superseding contract. The correct validator violation contains both `force=True` and `review-rejection`.

### 3.4 Reason field

`reason` is required (non-empty) in these cases:
- `force=true` (always).
- Any review-rejection family member into `planned`, because those transitions require `force=true`.

`reason` is optional otherwise. Producers MAY set `reason` for clarity even when not required.

## 4. `actor` is audit-only

`actor` is a free-form audit-identity field. It may be a non-empty string (e.g. `"user"`, `"claude"`, `"codex"`, `"migration"`) or a non-empty dict (e.g. `{"role": "reviewer", "profile": "python-pedro"}`).

**`actor` MUST NOT modify validation.** Specifically:

- `actor="user"` is NOT an implicit `force=true`. A consumer that sees a backward transition with `actor="user"` MUST evaluate the same matrix + guards as for any other actor.
- `actor="migration"` is NOT a policy escape hatch. Migration code that needs to bypass the matrix MUST set `force=true` explicitly and provide a non-empty `reason`.
- Future structured-actor schemes (`{"profile": …, "role": …}`) MUST NOT be wired into validation. They are observability only.

## 5. `from_lane` mismatch and reconciliation

A consumer maintains a projection of the current lane for each `wp_id`. When a `WPStatusChanged` event arrives with `from_lane != projection`, the consumer MUST treat the event as a reconciliation case, NOT as an infra failure.

Two sub-cases distinguished by `reason_code` (closed enum; see §7):

### 5.1 `from_lane_mismatch_replay`

The event's `from_lane` matches a prior projection state that the consumer has already advanced past (i.e. the event has effectively already been applied via a subsequent event). The consumer SHOULD:

1. Emit a `ReconciliationDiagnostic` with `reason_code=from_lane_mismatch_replay`.
2. SKIP re-application of the event.
3. NOT count the event toward infra failures.

### 5.2 `from_lane_mismatch_drift`

The event's `from_lane` does not match any prior projection state in the consumer's event log for that `wp_id`. The consumer MUST:

1. Emit a `ReconciliationDiagnostic` with `reason_code=from_lane_mismatch_drift`.
2. HOLD the event (do not apply, do not retry, do not infra-fail).
3. Surface the diagnostic on a dedicated drift surface (see §9) for operator review.

## 6. Replay

### 6.1 Detection

Replay is detected at the consumer BEFORE invoking `validate_transition`. The replay key is:

1. `event_id` (preferred; present on every emitted event today).
2. `(mission_slug, wp_id, sequence)` (fallback, used only if `event_id` is missing).

A replay hit is logged at debug level and produces no `ReconciliationDiagnostic`.

### 6.2 Terminal replay

A `terminal replay` is the special case where an event targets a terminal lane (`done`, `canceled`) that the projection is already in. Consumers MAY emit a `ReconciliationDiagnostic` with `reason_code=terminal_replay_skipped` for visibility, but MUST NOT infra-fail and MUST NOT apply the event a second time.

## 7. `ReconciliationDiagnostic` shape

The Pydantic model is defined in `src/spec_kitty_events/status.py` and its JSON Schema in `src/spec_kitty_events/schemas/reconciliation_diagnostic.schema.json`. See [data-model.md](../data-model.md) for the full field set. The `reason_code` field is a closed enum:

| Code | Meaning |
|---|---|
| `from_lane_mismatch_replay` | The event was effectively already applied; consumer skipped re-application. |
| `from_lane_mismatch_drift` | The event's `from_lane` does not match any prior projection state. Held for operator review. |
| `terminal_replay_skipped` | Optional diagnostic when a replay targets a terminal lane the projection is already in. |
| `unforced_rollback_without_review_ref` | Historical compatibility code for older review-rollback handling; the superseding review-rejection family violation names missing `force=True`. |

Adding a new `reason_code` REQUIRES updating this document AND adding at least one conformance fixture (D-6 / FR-013).

## 8. Consumer responsibilities

| Consumer | Responsibility | Mission/issue |
|---|---|---|
| `spec-kitty` CLI (producer) | Emit review-rejection family events with `force=true` and a non-empty `reason`; include `review_ref` when a feedback artifact exists. Emit terminal-exit events with `force=true` and `reason`. Never emit a backward transition with `actor` carrying policy intent. | spec-kitty#1089, spec-kitty#1087 |
| `spec-kitty-saas` materializer | Reject unforced review-rejection family events per §3.3. Detect replay per §6 and emit `ReconciliationDiagnostic` per §5/§6 instead of `terminal_failed`. | spec-kitty-saas#205 |
| `spec-kitty-saas` durable drain worker | Classify `ReconciliationDiagnostic` outcomes as reconciliation, not as infra terminal failure. Report on a separate drift/diagnostic surface from infra readiness. | spec-kitty-saas#204, spec-kitty-saas#206 |

## 9. Diagnostic surface separation

`ReconciliationDiagnostic` events MUST be reported on a SEPARATE health surface from infra-failure events. Conflating reconciliation with infra failure (as the 2026-05-17 incident did) is the failure mode this contract exists to prevent.

Specifically:

- `/health/ready/` (or equivalent) MUST report `reconciliation_pending` count separately from `infra_terminal_failed` count.
- A non-zero `reconciliation_pending` count is operator-actionable but does NOT degrade readiness.
- A non-zero `infra_terminal_failed` count MAY degrade readiness per the consumer's policy.

This requirement is the contract-side floor that `spec-kitty-saas#204` and `spec-kitty-saas#206` consume.

## 10. Conformance

The binding artefact is the fixture set at `src/spec_kitty_events/conformance/fixtures/wp_status_changed/` plus the manifest entries in `src/spec_kitty_events/conformance/fixtures/manifest.json`.

A consumer claims conformance by exercising every fixture and producing the declared `outcome` and (where applicable) `reason_code`. Conformance is a single binary: any deviation on any fixture is non-conformance.

## 11. Versioning

This contract is versioned with the `spec-kitty-events` package. Backward-incompatible changes to this contract MUST bump the package major version and provide a migration runbook for consumers.
