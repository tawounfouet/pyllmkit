# PyLLMKit

**Status:** Phase 1 - foundational domain implementation in stacked **draft PRs**. The metadata version `0.1.0a1` is a **candidate**, not a published release. Milestone M1 has **not** been approved.

PyLLMKit models provider-agnostic LLM primitives as typed Python domain objects, separate from model-serving providers, deployments and inference APIs.

## What is implemented in Phase 1

- **L1.1:** Model, ModelId, ModelIdentity, ModelFamily, ModelVersion, ModelVariant, ModelRevision, ModelArchitecture, ModelLimits, ModelArtifact, typed provider alias, JSON codec.
- **L1.2:** Capability, CapabilitySupport, SupportLevel, CapabilityConstraint, CapabilitySet, Modality, ModalitySet; composed within Model.
- **L1.3 (proposed):** offline tests and architecture fitness checks, reproducible examples, coverage reporting, typing, lint, isolated wheel and sdist installation, traceability and M1 review.

## Quick start

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
python -m ruff check .
python -m mypy src/pyllmkit
python -m pytest -q --cov=pyllmkit.domain --cov-branch --cov-report=term-missing
python examples/01_define_model.py
python examples/02_define_artifacts.py
python examples/03_define_capabilities.py
python -m build
```

The domain core has no mandatory provider SDK dependencies. The tests remove common LLM credential environment variables and reject socket connection/bind attempts; the test fixture is not a machine-wide network sandbox.

## Domain example

```python
from pyllmkit.domain.models import Model, ModelFamily, ModelId, ModelIdentity
from pyllmkit.domain.capabilities import Capability, CapabilityId, CapabilitySet, CapabilitySupport, SupportLevel
from pyllmkit.domain.modalities import Modality, ModalitySet

model = Model(
    id=ModelId("example/vision"),
    identity=ModelIdentity(ModelFamily("example")),
    capabilities=CapabilitySet((
        Capability(CapabilityId("vision"), CapabilitySupport(SupportLevel.NATIVE)),
    )),
    modalities=ModalitySet(
        input_modalities=frozenset({Modality("text"), Modality("image")}),
        output_modalities=frozenset({Modality("text")}),
    ),
)
assert model.supports(CapabilityId("vision"))
assert model.modalities.can_output(Modality("image")) is False
```

## Architecture & documentation

```text
Applications -> Facade -> Application Services -> Ports/Protocols
                                 |                    ^
                                 v                    |
                             Domain Core <---------- Adapters
```

**This is a conceptual invocation view**, not a Python import graph. The Domain Core does not depend on facade, adapters, SDKs, network or credentials. Capabilities and Modalities must not depend on the Model Entity. For source-code rules see `docs/architecture/dependencies.md`.

- Domain reference: `docs/api/domain.md`.
- Test coverage and qualification: `docs/quality/P1_L13_QUALIFICATION.md`.
- Acceptance mapping: `docs/quality/PHASE_1_TRACEABILITY.md`.
- M1 decision: `docs/quality/M1_GATE_REVIEW.md`.
- ADR: `docs/adr/` (all proposals pending approval).

## Explicitly not included

No provider invocation, serving Deployment/Endpoint, registry, streaming, RAG, agent orchestration or tool-execution engine in Phase 1. The Python package is not a released, stable LLM client.

The license has not been selected. Before any publication, confirm licensing, architecture decisions, release notes and the M1 GO/NO-GO gate.
