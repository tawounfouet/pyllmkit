# Phase 1 - Public API and schema v1 contract

**Decision:** M1 architecture closure, 2026-10-28.
**Status:** Pre-release alpha; breaking API changes may occur in later alpha versions with explicit change logs.

## Public import surface

Both of these imports are supported and tested:

```python
from pyllmkit.domain import Model, ModelId, ModelIdentity, ModelFamily
from pyllmkit.domain.models import Model as ModelFromSubpackage

assert Model is ModelFromSubpackage
```

`pyllmkit.domain` exposes explicit aliases to the stable Phase 1 *concept classes* at the alpha boundary. `pyllmkit.domain.models`, `capabilities`, `modalities` and `errors` retain their dedicated import paths. No provider SDK import occurs in the facade. A version number is only metadata; `0.1.0a1` has not been published by passing M1.

## Schema v1 guarantee and limitations

- The `0.1.0a1` alpha freezes the **current** shape of `schema_version=1` emitted by `model_to_dict` and `artifact_to_dict`.
- The current decoder accepts earlier development-time v1 Model snapshots without `capabilities` and `modalities`.
- Conversely, a strict older developer-time decoder that did not recognize those keys **cannot** read the current emitted v1 snapshots. No claim of bidirectional compatibility is made.
- Explicit `None` represents unknown descriptor information. Unknown keys are errors to prevent silent data loss, not a forward-compatible extension bag.
- Future incompatible changes require a new `schema_version` (and an explicit migration strategy before consumers depend on it). Additive changes to the frozen writer are not permitted under v1 without documenting backward/forward support and an approved ADR.
- Schema version is separate from Python package `0.1.0a1`.

## Governance

The architectural decision is **provisionally accepted for the alpha**, based on the owner's request to complete M1; this is no independent architect's or legal counsel's signature. Publishing requires a separate authorized step.
