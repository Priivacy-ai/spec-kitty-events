# Research: Event Model Project Identity

**Feature**: 001-event-model-project-identity
**Date**: 2026-02-07

## Decision 1: UUID Field Type

**Decision**: Use `uuid.UUID` (Python stdlib) as the Pydantic field type.

**Rationale**: Pydantic v2 has first-class `uuid.UUID` support. It accepts strings on input, stores as `uuid.UUID` internally, and serializes to standard UUID strings in JSON output via `model_dump()`. This gives type safety without losing wire compatibility.

**Alternatives considered**:
- `str` with `@field_validator`: Loses type safety, requires manual validation regex. Rejected because Pydantic already handles this.
- Custom `UUID4` type alias: Over-constraining. Spec says any valid UUID version is acceptable (CLI may use v4, but library shouldn't enforce version).

## Decision 2: Backward Compatibility

**Decision**: `project_uuid` is required (not optional). No backward compatibility.

**Rationale**: User confirmed all three teams (CLI, events, SaaS) are updating simultaneously. Making it optional would create a risk of events reaching SaaS without project identity, which defeats the purpose. Breaking change is acceptable since this is pre-1.0 alpha.

**Alternatives considered**:
- Optional with deprecation warning: Adds complexity for a coordinated release where it's not needed. Rejected.
- Optional with validation-on-presence: Half-measure that doesn't guarantee identity on every event. Rejected.

## Decision 3: Version Bump Strategy

**Decision**: Bump to `0.1.1-alpha` (patch within alpha).

**Rationale**: User selected this option. The change is additive (new fields) with a breaking contract change (required field), but within alpha the audience is small and coordinated. A patch bump signals "update available" without implying major new functionality.

**Alternatives considered**:
- `0.2.0-alpha`: Would signal new functionality tier. Rejected by user — scope is too small.
- `0.2.0` (drop alpha): Premature — the library isn't production-ready yet. Rejected.

## Decision 4: Serialization Approach

**Decision**: Use Pydantic's `model_dump()` for `to_dict()` — Pydantic v2 serializes `uuid.UUID` to string by default in `mode='python'`, but we need to ensure `to_dict()` returns JSON-compatible types.

**Rationale**: The current `to_dict()` calls `self.model_dump()`. Pydantic v2's `model_dump()` returns `uuid.UUID` objects by default. For JSON-compatible serialization, `to_dict()` should use `model_dump(mode='json')` which converts UUIDs to strings. However, the current `to_dict()` uses plain `model_dump()` which serializes `datetime` as `datetime` objects (not ISO strings). This means existing consumers already handle Python-native types in dicts. To stay consistent, `to_dict()` should continue using `model_dump()` (Python mode), and `uuid.UUID` objects in the dict are fine — they're handled by JSON encoders downstream and by `from_dict()` on rehydration.

**Alternatives considered**:
- Switch to `model_dump(mode='json')`: Would change existing behavior (datetime → ISO string). Rejected as out of scope.
- Manual serialization in `to_dict()`: Unnecessary — Pydantic handles it.

## Decision 5: project_slug Validation

**Decision**: No format validation on `project_slug`. Accept any string or `None`.

**Rationale**: Slug format enforcement is the CLI's responsibility. The events library is a transport/storage layer and should not impose business rules about slug format. The library stores whatever string the CLI provides.

**Alternatives considered**:
- Regex validation (kebab-case only): Over-constraining for a library. Different teams might have different slug conventions. Rejected.
- `min_length=1` when present: Unnecessary — an empty string slug is a CLI concern, not a library concern. Rejected.
