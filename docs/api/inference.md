# API publique Inference Domain - PyLLMKit P3

> Source candidate `0.1.0a2` avec primitives P3 developpees et G1..G4 qualifiees; G5/M3 et publication independants.
> API de **domaine pur**, pas un SDK fournisseur ni une API d'invocation.

## Points d'entree

Les symbols ci-dessous sont disponibles depuis `pyllmkit.domain.inference` **et** reexportes par `pyllmkit.domain`.

| Famille | Public API |
|---|---|
| Target | `ModelTarget`, `DeploymentTarget`, `EndpointTarget`, `DeploymentId`, `EndpointId`, `InferenceTarget` |
| Request | `GenerationConfig`, `InferenceRequest` |
| Support | `GenerationSupportSnapshot`, `ParameterSupport`, `ParameterAssessment`, `CompatibilityReport`, `evaluate_request_support`, `validate_request_support` |
| Response | `InferenceRunId`, `TextOutput`, `InferenceOutput`, `FinishReason`, `FinishReasonCode`, `Usage`, `InferenceResponse` |
| Run | `InferenceRun`, `InferenceRunState`, `InferenceFailure` |
| JSON v1 | `INFERENCE_SCHEMA_VERSION`, `request_to_dict`, `request_from_dict`, `response_to_dict`, `response_from_dict`, `run_to_dict`, `run_from_dict` |

Pour le modele logique et les messages, importer `ModelId`, `Message`, `Content`, `Role`, `TextContent`, `ImageContent`, `MediaSourceRef` depuis les modules M1/M2 ou la racine `pyllmkit.domain`.

## Constructeurs Python

```python
from pyllmkit.domain import (
    Content, InferenceRequest, InferenceResponse, InferenceRun,
    InferenceRunId, Message, ModelId, ModelTarget, Role,
    TextContent, TextOutput,
)

request = InferenceRequest(
    target=ModelTarget(ModelId("example/model")),
    messages=(Message(Role.USER, Content((TextContent("Bonjour"),))),),
)
run = InferenceRun(InferenceRunId("run-1"), request)
response = InferenceResponse(run.run_id, TextOutput("test hors ligne"))
```

Pour faire evoluer un Run, injecter une `datetime` timezone-aware a `run.start(at)`, puis `begin_stream(at)`, `complete(response, at)`, `fail(failure, at)` ou `cancel(at, reason_code)` selon les transitions permises. Construire un Response ne complete **pas** automatiquement le Run.

## Fonctions de codec v1

```python
from pyllmkit.domain import request_to_dict, request_from_dict

snapshot = request_to_dict(request)
assert request_from_dict(snapshot) == request
```

Ces fonctions acceptent/renvoient des mappings JSON-compatibles, et les cles canoniques restent obligatoires, y compris les nulls. `json.dumps` et `json.loads` appartiennent au caller. Il n'existe pas de parseur HTTP, de gestion des cles dupliquees dans le texte JSON ni de codec wire OpenAI/Anthropic.

## Erreurs et limites

Les erreurs structurelles de l'API Inference utilisent `DomainValidationError` (ex. cible invalide, horodatage naive, mauvais RunId, champ JSON inconnu, support explicitement UNSUPPORTED). Elles ne sont pas des exceptions reseau. Les appels sont offline et ne valident pas la disponibilite d'un modele.

- Pas de `Client`, `InferencePort` operationnel, provider plugin, scheduler, streaming, tools, pricing ou RAG.
- Les trois schemas Model/Interaction/Inference v1 restent dans des namespaces independants.
- Une version du code sur `main` ne constitue pas automatiquement une release PyPI.

## References

[Concept Request](../concepts/inference-request.md) | [Concept Response](../concepts/inference-response.md) | [Concept Run](../concepts/inference-run.md) | [Schema JSON v1](../architecture/INFERENCE_JSON_SCHEMA_V1.md) | [PV G4](../quality/P3_G4_GATE_REVIEW.md).
