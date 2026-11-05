# PyLLMKit

PyLLMKit est un framework Python de **primitives de domaine LLM agnostiques des fournisseurs**. Les modèles, capacités, contenus, demandes d'inférence, réponses et états d'exécution sont représentés par des objets Python validés, indépendamment de tout SDK ou service distant.

**État du dépôt (5 novembre 2026) :** M1 et M2 sont qualifiés, M3 a reçu un GO technique avec réserves. En Phase 4, les gates **P4-G0 à P4-G5** sont qualifiés avec réserves, y compris [P4-G4](docs/quality/P4_G4_GATE_REVIEW.md) sur le commit [main@ab0257a0](https://github.com/tawounfouet/pyllmkit/commit/ab0257a0a9a08f2320b580340ba84c92609bbfc0), [CI #42089506022](https://github.com/tawounfouet/pyllmkit/actions/runs/42089506022) (954 tests cumulatifs, couverture de branches 96 %, Python 3.11-3.13). Le lot **L4.5 - Integration & Quality est intégré** et **P4-G5 est qualifié** sur [main@aad2656c](https://github.com/tawounfouet/pyllmkit/commit/aad2656cbe1753dac709bb28b228ba22ecca44a2), [CI #42092202193 SUCCESS](https://github.com/tawounfouet/pyllmkit/actions/runs/42092202193) : 967 tests cumulatifs, 96 % de couverture et Python 3.11-3.13. La qualification M4 et la décision de publication demeurent distinctes. Le paquet source reste en version **0.1.0a2**, sans tag ni publication de version suivante. Les réserves [#22](https://github.com/tawounfouet/pyllmkit/issues/22), [#35](https://github.com/tawounfouet/pyllmkit/issues/35) et [#36](https://github.com/tawounfouet/pyllmkit/issues/36) restent ouvertes.

## Phase 4 : exemple complet hors ligne (P4-AC-036)

Les primitives de P4 représentent des déclarations, des appels d'outils **non exécutés**, leurs résultats observés et des formats structurés. Aucun SDK de fournisseur ni credential n'est requis. Cet exemple Python est vérifié par la CI et compose explicitement une requête M3 intacte avec un catalogue P4 :

```python
from pyllmkit.domain import (
    Content, InferenceRequest, Message, ModelId, ModelTarget, Role, TextContent,
)
from pyllmkit.domain.tooling import Tool, ToolChoice, ToolSchema
from pyllmkit.domain.tooling_inference import (
    ToolingInferenceIntent, intent_from_dict, intent_to_dict,
)

m3 = InferenceRequest(
    ModelTarget(ModelId("offline-example")),
    (Message(Role.USER, Content((TextContent("Weather in Paris?"),))),),
)
weather = Tool("get_weather", "Description only", ToolSchema({
    "type": "object",
    "properties": {"city": {"type": "string"}},
    "required": ["city"],
    "additionalProperties": False,
}))
p4_intent = ToolingInferenceIntent(
    m3, (weather,), ToolChoice.specific("get_weather"),
)
p4_wire = intent_to_dict(p4_intent)
p4_decoded = intent_from_dict(p4_wire)
assert p4_decoded.tools[0].name == "get_weather"
assert p4_wire["object_type"] == "tooling_inference_intent"
```

Pour le parcours complet tool -> call -> résultat illustratif -> sortie structurée -> JSON v1, exécuter `python examples/17_full_tooling_walkthrough.py`. Les résultats de cet exemple sont des **données de démonstration fournies localement**, pas une réponse réelle d'un modèle ou d'un outil.

Documentation Phase 4 : [Architecture](docs/architecture/PHASE_4_TOOLING_AND_STRUCTURED_OUTPUT_CONTRACTS.md), [Schéma Tooling JSON v1](docs/architecture/TOOLING_JSON_SCHEMA_V1.md), [Tool Definition](docs/concepts/tool-definition.md), [Tool Call](docs/concepts/tool-call.md), [Structured Output](docs/concepts/structured-output.md), [API Tooling](docs/api/tooling.md), [API Tool Calling](docs/api/tool-calling.md), [API Structured Output](docs/api/structured-output.md), [API Serialization](docs/api/tooling-serialization.md), [Traçabilité P4](docs/quality/PHASE_4_TRACEABILITY.md), [Précheck M4](docs/quality/M4_READINESS_PRECHECK.md).

## État de qualification

| Jalon | État | Preuve |
|---|---|---|
| M1 - Model Domain | GO technique | [PV M1](docs/quality/M1_GATE_REVIEW.md) |
| M2 - Interaction Domain | GO technique | [PV M2](docs/quality/M2_GATE_REVIEW.md) |
| P3-G0 - Architecture | GO avec réserves | [PV G0](docs/quality/P3_G0_GATE_REVIEW.md) |
| P3-G1 - Request | GO technique avec réserves | [PV G1](docs/quality/P3_G1_GATE_REVIEW.md) |
| P3-G2 - Response | GO technique avec réserves | [PV G2](docs/quality/P3_G2_GATE_REVIEW.md) |
| P3-G3 - Run | GO technique avec réserves | [PV G3](docs/quality/P3_G3_GATE_REVIEW.md) |
| P3-G4 - Inference JSON v1 | GO technique avec réserves | [PV G4](docs/quality/P3_G4_GATE_REVIEW.md), [CI main #42053906726](https://github.com/tawounfouet/pyllmkit/actions/runs/42053906726) |
| **P3-G5 - Integration & Packaging** | **GO technique avec réserves** | [PV G5](docs/quality/P3_G5_GATE_REVIEW.md), [CI #42059417894](https://github.com/tawounfouet/pyllmkit/actions/runs/42059417894) |
| **M3 - Inference Foundations (domaine hors ligne)** | **GO technique avec réserves** | [PV M3](docs/quality/M3_GATE_REVIEW.md), [CI #42069101048](https://github.com/tawounfouet/pyllmkit/actions/runs/42069101048) |
| **P4-G0 - Architecture** | GO technique avec réserves | [PV P4-G0](docs/quality/P4_G0_GATE_REVIEW.md) |
| **P4-G1 - Tool Declaration** | GO technique avec réserves | [PV P4-G1](docs/quality/P4_G1_GATE_REVIEW.md) |
| **P4-G2 - Tool Call** | GO technique avec réserves | [PV P4-G2](docs/quality/P4_G2_GATE_REVIEW.md) |
| **P4-G3 - Structured Output** | GO technique avec réserves | [PV P4-G3](docs/quality/P4_G3_GATE_REVIEW.md) |
| **P4-G4 - Composition & Serialization** | GO technique avec réserves | [PV P4-G4](docs/quality/P4_G4_GATE_REVIEW.md), [CI #42089506022](https://github.com/tawounfouet/pyllmkit/actions/runs/42089506022) |
| **P4-G5 - Integration & Quality** | **GO technique avec réserves** | [PV G5](docs/quality/P4_G5_GATE_REVIEW.md), [CI main #42092202193](https://github.com/tawounfouet/pyllmkit/actions/runs/42092202193) |
| **M4 - Tooling & Structured Output** | **Non qualifié** | [M4 Readiness Precheck](docs/quality/M4_READINESS_PRECHECK.md) |

Les preuves historiques ont été conservées dans les procès-verbaux, sans présenter les anciens statuts comme actuels. La dette M2 [#20](https://github.com/tawounfouet/pyllmkit/issues/20) est **résolue** par [PR #31](https://github.com/tawounfouet/pyllmkit/pull/31) ([CI main #42057132634](https://github.com/tawounfouet/pyllmkit/actions/runs/42057132634)). Les protections de `main` [#22](https://github.com/tawounfouet/pyllmkit/issues/22) restent **ouvertes**.

## Cloture Phase 3 et prochaines decisions

La Phase 3 est **techniquement integree et qualifiee sur P3-G0..G5**; [bilan post-implementation](docs/quality/P3_POST_IMPLEMENTATION_REVIEW.md). **M3 GO technique avec réserves**, [PV finale](docs/quality/M3_GATE_REVIEW.md), sans confondre qualite du domaine et publication.

Les cinq suites operationnelles sont documentees et auditablement separees :
- [Runbook de protection GitHub main](docs/governance/MAIN_BRANCH_PROTECTION_RUNBOOK.md) : issue [#22](https://github.com/tawounfouet/pyllmkit/issues/22) OPEN, aucune protection effective revendiquee.
- [Politique de versionnement et release 0.1.0a3](docs/governance/RELEASE_0_1_0a3_POLICY_AND_RUNBOOK.md) : aucune action de publication n'est autorisee par le gate M3.
- [Contrat de frontiere pour futurs adapters provider](docs/architecture/FUTURE_PROVIDER_BOUNDARY_CONTRACT.md) : parsing, limits, secrets, retries et transport hors Value Objects.
- [Cycle PyKit de delivery et d'apprentissage](docs/governance/PYKIT_DELIVERY_AND_LEARNING_LOOP.md) : exigences -> ADR -> code -> tests -> PR CI -> main CI -> PV.
- [Precheck M3](docs/quality/M3_READINESS_PRECHECK.md) : criteres de decision et limites.

## Phase 3 : exemple complet hors ligne (P3-AC-030)

Le script suivant **construit une réponse fictive en mémoire** : il ne contacte aucun modèle ni fournisseur. Il démontre les frontières Request, Run, Response et le round-trip JSON v1.

```python
import json
from datetime import UTC, datetime

from pyllmkit.domain import (
    Content, FinishReason, FinishReasonCode, GenerationConfig,
    InferenceRequest, InferenceResponse, InferenceRun, InferenceRunId,
    InferenceRunState, Message, ModelId, ModelTarget, Role, TextContent,
    TextOutput, Usage, run_from_dict, run_to_dict,
)

request = InferenceRequest(
    target=ModelTarget(ModelId("example/model")),
    messages=(Message(Role.USER, Content((TextContent("Bonjour"),))),),
    generation_config=GenerationConfig(temperature=0.0),
)
run = InferenceRun(InferenceRunId("offline-run-001"), request)
at = datetime(2026, 11, 5, 10, 0, tzinfo=UTC)
started = run.start(at)
synthetic_response = InferenceResponse(
    run_id=run.run_id,
    output=TextOutput("Bonjour, ceci est une démonstration hors ligne."),
    finish_reason=FinishReason(FinishReasonCode.STOP),
    usage=Usage(input_tokens=0, output_tokens=None),
)
completed = started.complete(synthetic_response, at)
wire = json.loads(json.dumps(run_to_dict(completed), allow_nan=False))
restored = run_from_dict(wire)
assert restored.state is InferenceRunState.COMPLETED
assert restored.response == synthetic_response
assert restored.started_at == at and restored.finished_at == at
```

- [API Request](docs/api/inference-request.md) : Target, GenerationConfig, support explicite.
- [API Response](docs/api/inference-response.md) : TextOutput, FinishReason et Usage observé.
- [API Run](docs/api/inference-run.md) : agrégat, horloge injectée, six états.
- [API JSON v1](docs/api/inference-json-v1.md) : formats stricts, sérialisation, absence de données inventées.
- [API consolidée](docs/api/inference.md) et [traçabilité P3](docs/quality/PHASE_3_TRACEABILITY.md).
- [Exemples hors ligne](examples/) : exemples 01 à 11 ; tous exécutés par la CI.

La représentation `STREAMING` dans le domaine n'est pas du streaming réseau. Les objets `InferenceResponse` et `InferenceRun` ne constituent pas un client LLM exécutable, un ordonnanceur ou une API fournisseur.

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
python examples/08_define_inference_request.py
python examples/09_define_inference_response.py
python examples/10_define_inference_run.py
python examples/11_round_trip_inference_json.py
python examples/12_full_inference_walkthrough.py
python -m build
```

The domain core has no mandatory provider SDK dependencies. The tests remove common LLM credential environment variables and reject socket connection/bind attempts; the test fixture is not a machine-wide network sandbox.

## Domain example

```python
from pyllmkit.domain import (
    Capability,
    CapabilityId,
    CapabilitySet,
    CapabilitySupport,
    Model,
    ModelFamily,
    ModelId,
    ModelIdentity,
    Modality,
    ModalitySet,
    SupportLevel,
)

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
