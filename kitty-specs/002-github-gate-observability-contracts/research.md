# Research: GitHub Gate Observability Contracts
*Phase 0 output for feature 002*

## R1: GitHub Check Run Conclusion Values

**Decision**: Use the 8 documented conclusion values from the GitHub REST API.

**Rationale**: The GitHub API documentation defines these conclusion values for check runs:
- `success` — check passed
- `failure` — check failed
- `neutral` — informational, no pass/fail judgment
- `cancelled` — check was cancelled
- `timed_out` — check exceeded time limit
- `action_required` — manual intervention needed
- `stale` — check is outdated (superseded)
- `skipped` — check was skipped (conditional)

**Alternatives considered**:
- Scraping the GitHub OpenAPI spec for an exhaustive enum → rejected because the REST docs are the canonical source and the OpenAPI spec may lag.
- Including `startup_failure` → removed from scope after spec review. GitHub does not list this as a standard `check_run` conclusion in current API docs; it appears in some older references but is not reliably emitted.

**Mapping**:
| Conclusion        | Event Type     | Category    |
|-------------------|---------------|-------------|
| `success`         | `GatePassed`  | blocking    |
| `failure`         | `GateFailed`  | blocking    |
| `timed_out`       | `GateFailed`  | blocking    |
| `cancelled`       | `GateFailed`  | blocking    |
| `action_required` | `GateFailed`  | blocking    |
| `neutral`         | `None`        | ignored     |
| `skipped`         | `None`        | ignored     |
| `stale`           | `None`        | ignored     |

## R2: Pydantic v2 Payload Model Patterns

**Decision**: Use `BaseModel` with `ConfigDict(frozen=True)` for payload models, consistent with existing `Event` model.

**Rationale**: The existing codebase already uses this exact pattern. Pydantic v2's `model_dump()` / `model_validate()` methods provide serialization. Using `Literal` types for `gate_type` and `external_provider` provides compile-time constraints without custom validators.

**Alternatives considered**:
- `TypedDict` → rejected because it lacks runtime validation, which is the whole point of typed payloads.
- `dataclass` → rejected because the rest of the library uses Pydantic BaseModel; mixing would create inconsistency and lose validation features.
- `attrs` → rejected because it would add a new dependency.

## R3: URL Validation Approach

**Decision**: Use `Pydantic.AnyHttpUrl` for `check_run_url`.

**Rationale**: Pydantic v2 provides built-in URL validation via `AnyHttpUrl`. This validates structure (scheme, host) without network access. It's already available as a transitive dependency.

**Alternatives considered**:
- Plain `str` with regex → more fragile, harder to maintain.
- `pydantic.HttpUrl` (strict) → too strict; may reject valid GitHub URLs with uncommon characters in paths.

## R4: Error Type for Unknown Conclusions

**Decision**: Create `UnknownConclusionError(SpecKittyEventsError)` — a custom exception inheriting from the existing base.

**Rationale**: Follows the library's existing exception hierarchy (`SpecKittyEventsError` → `StorageError`, `ValidationError`, `CyclicDependencyError`). A dedicated exception type allows consumers to catch unknown conclusions specifically without catching unrelated validation errors.

**Alternatives considered**:
- Reuse `ValidationError` → rejected because unknown conclusions are a domain logic error (bad input from GitHub), not a schema validation error.
- Use `ValueError` → rejected because it doesn't integrate with the library's exception hierarchy and makes targeted error handling harder.

## R5: Logging Strategy for Ignored Conclusions

**Decision**: Use `logging.getLogger("spec_kitty_events.gates")` with `logger.info()` for ignored conclusions. Accept optional `on_ignored: Callable[[str, str], None]` callback.

**Rationale**: Stdlib logging is zero-dependency and follows Python best practices. The named logger allows consumers to configure log levels per-module. The callback parameter gives SaaS consumers a hook for structured metrics (e.g., StatsD, Prometheus counters) without coupling the library to any metrics framework.

**Alternatives considered**:
- Metrics-only (no logging) → rejected because logging is more universally useful for debugging.
- Structured logging (structlog) → rejected because it adds a dependency the library doesn't currently use.
