# PyLLMKit

**Phase 3 / P3-G2 (2026-11-05): RESPONSE READY - GO technique avec reserves.** [PR #25](https://github.com/tawounfouet/pyllmkit/pull/25) integree sur [main SHA 783aa438](https://github.com/tawounfouet/pyllmkit/commit/783aa4381dc05a4b9bc431faab282f2bbe37d38d), [CI #42039312011 SUCCESS](https://github.com/tawounfouet/pyllmkit/actions/runs/42039312011): **545 tests / 94 %**, Python 3.11/3.12/3.13. [PV P3-G2](docs/quality/P3_G2_GATE_REVIEW.md), [API Response](docs/api/inference-response.md). L3.2 TextOutput/FinishReason/Usage/InferenceResponse qualifies, G3 Run a venir. **G3..M3 et publication 0.1.0a3 non qualifies; metadata 0.1.0a2 non publiee.**


**Phase 3 / P3-G1 (2026-11-05): REQUEST READY - TECHNICAL GO WITH RESERVATIONS.** L3.1 integrated by [PR #23](https://github.com/tawounfouet/pyllmkit/pull/23), [main SHA f1ef04b8](https://github.com/tawounfouet/pyllmkit/commit/f1ef04b8ff1bb52a1ee17defa0ec8b20f84ac9d3), [CI #42036557565 SUCCESS](https://github.com/tawounfouet/pyllmkit/actions/runs/42036557565): 432 tests, 93% coverage, Python 3.11/3.12/3.13. [P3-G1 gate](docs/quality/P3_G1_GATE_REVIEW.md) and [Request API](docs/api/inference-request.md). ADR-021 option A and P3-AC-001..007 qualified. **Next: L3.2 Response Domain. G2..M3 not qualified. Source metadata 0.1.0a2, unpublished.**


**Phase 3 / P3-G0 (2026-11-05): ARCHITECTURE GO WITH RESERVATIONS.** ADR-014..021 owner-accepted and merged via [PR #19](https://github.com/tawounfouet/pyllmkit/pull/19); exact integrated `main` SHA [`965311db`](https://github.com/tawounfouet/pyllmkit/commit/965311dbef527ad59222b7586f9c801bb713bead), [CI SUCCESS](https://github.com/tawounfouet/pyllmkit/actions/runs/42029448967) on Python 3.11/3.12/3.13. [Gate record](docs/quality/P3_G0_GATE_REVIEW.md). **Only architecture is qualified; L3.1..L3.5 and M3 are not implemented or qualified. Metadata remains `0.1.0a2`, unpublished; no `0.1.0a3` tag or release.**


**Status:** M1/G0/G1/G2/G3/G4 qualified on `main`. M2 = GO for source candidate on 2026-11-05. L2.4 strict Interaction JSON v1 is integrated, [CI SUCCESS](https://github.com/tawounfouet/pyllmkit/actions/runs/42015194077): 342 tests, 91% coverage. M2 source candidate [qualification](https://github.com/tawounfouet/pyllmkit/actions/runs/42015825424) is complete, with [M2 report](docs/quality/M2_GATE_REVIEW.md) pending archival PR qualification. Metadata `0.1.0a2` is a **repository alpha candidate**, not published. No Git tag, GitHub Release or PyPI upload.

PyLLMKit models provider-agnostic LLM primitives as typed Python domain objects, separate from model-serving providers, deployments and inference APIs.

**Phase 2 architecture (2026-11-05):** **P2-BOOT G0 = GO**. ADR-008..013 were accepted by the project owner and integrated in [PR #8](https://github.com/tawounfouet/pyllmkit/pull/8); the [G0 review](docs/quality/P2_BOOT_GATE_REVIEW.md) and [decision register](docs/quality/PHASE_2_ARCHITECTURE_DECISION_REGISTER.md) were archived via PR #9, and the integrated `main` CI passed. **L2.1/L2.2 and AC-006 are now implemented and G1 = GO on integrated main** ([CI #42008750610](https://github.com/tawounfouet/pyllmkit/actions/runs/42008750610): 204 tests, 90% coverage). **L2.3 and AC-007 now implemented, G2 = GO** ([CI #42011868937](https://github.com/tawounfouet/pyllmkit/actions/runs/42011868937): 252 tests, 90% coverage). L2.4 codec integrated and G3 GO ([CI #42015194077](https://github.com/tawounfouet/pyllmkit/actions/runs/42015194077), 342 tests, 91% coverage). G4 and technical M2 GO on `main` SHA `560d3a46c74cecebdf6a55301b2b8ca4e34331d4` ([CI #42015825424](https://github.com/tawounfouet/pyllmkit/actions/runs/42015825424)). No publication was performed. No release has been published.

## Phase 2 text/image interaction API (G2 GO)

```python
from pyllmkit.domain import Content, Message, Role, TextContent

message = Message(Role.USER, Content((TextContent("Bonjour PyLLMKit"),)))
assert message.content.parts[0].text == "Bonjour PyLLMKit"
```

- L2.2: `ContentPart`, `TextContent`, `Content` (immutable, ordered, strict).
- L2.1: `Role`, `Message` (five canonical roles; provider-agnostic, no required Conversation).
- [G1 Gate Review](docs/quality/P2_G1_GATE_REVIEW.md), [Interaction API](docs/api/interaction.md).
- L2.3: immutable `MediaSourceRef` and `ImageContent`, ordered mixed text/image Content, AC-007.
- [G2 Gate Review](docs/quality/P2_G2_GATE_REVIEW.md), [Media and Images](docs/concepts/media-and-images.md).
- L2.4 integrated: strict Interaction JSON mapping codec v1; [schema](docs/architecture/INTERACTION_JSON_SCHEMA_V1.md) and [G3 Gate Review](docs/quality/P2_G3_GATE_REVIEW.md). G3/G4 GO; [M2 GO report](docs/quality/M2_GATE_REVIEW.md). No alpha publication.

### AC-007 multimodal Message

```python
from pyllmkit.domain import Content, ImageContent, MediaSourceRef, Message, Role, TextContent

message = Message(
    Role.USER,
    Content((
        TextContent("Regarde : "),
        ImageContent(MediaSourceRef("asset", "image-123")),
        TextContent(" Que vois-tu ?"),
    )),
)
assert tuple(part.kind for part in message.content.parts) == ("text", "image", "text")
```

The domain does **not** resolve or download URLs. Accepted HTTP(S) URL syntax is not proof of SSRF safety; actual media access requires a future adapter's independent security controls.

### Interaction JSON v1 (L2.4 integrated, G3 GO)

```python
import json
from pyllmkit.domain import message_to_dict, message_from_dict

payload = json.loads(json.dumps(message_to_dict(message), ensure_ascii=False))
assert message_from_dict(payload) == message
```

This is a domain mapping schema, not a provider wire format. URL values are preserved verbatim as data; never log untrusted media URI payloads without redaction.

## What is implemented in Phase 1

- **L1.1:** Model, ModelId, ModelIdentity, ModelFamily, ModelVersion, ModelVariant, ModelRevision, ModelArchitecture, ModelLimits, ModelArtifact, typed provider alias, JSON codec.
- **L1.2:** Capability, CapabilitySupport, SupportLevel, CapabilityConstraint, CapabilitySet, Modality, ModalitySet; composed within Model.
- **L1.3:** offline tests and architecture fitness checks, reproducible examples, coverage reporting, typing, lint, isolated wheel and sdist installation, traceability and M1 review.

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
python examples/07_round_trip_interaction.py
python -m build
```

The domain core has no mandatory provider SDK dependencies. The tests remove common LLM credential environment variables and reject socket connection/bind attempts; the test fixture is not a machine-wide network sandbox.

## Domain example

```python
from pyllmkit.domain import (\n    Capability, CapabilityId, CapabilitySet, CapabilitySupport,\n    Model, ModelFamily, ModelId, ModelIdentity, Modality, ModalitySet, SupportLevel,\n)

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
- M1 decision: `docs/quality/M1_GATE_REVIEW.md` (GO, exact-SHA GitHub Actions evidence).
- ADR: `docs/adr/` (accepted for the Phase 1 alpha under delegated milestone authorization; future revisions require a new decision).

## Explicitly not included

No provider invocation, serving Deployment/Endpoint, registry, streaming, RAG, agent orchestration or tool-execution engine in Phase 1. The Python package is not a released, stable LLM client.

**License: MIT** (see `LICENSE` and ADR-007). Publication remains a separate decision after a successful M1 gate.
