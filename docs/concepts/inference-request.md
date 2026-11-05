# InferenceRequest - une intention, pas une invocation

> Statut : implementee et qualifiee techniquement en P3-G1 (ADR-014/015/016/021).
> Implementation : `pyllmkit.domain.inference.request`, `targets`, `config`, `compatibility`.

## Qu'est-ce qu'une requete d'inference ?

`InferenceRequest` est un **Value Object** immuable qui assemble une cible typee, un tuple non vide de messages M2 et une `GenerationConfig` optionnelle. Elle represente ce que l'appelant souhaite obtenir, sans executer ce souhait.

```python
from pyllmkit.domain import (
    Content, GenerationConfig, InferenceRequest, Message,
    ModelId, ModelTarget, Role, TextContent,
)

request = InferenceRequest(
    ModelTarget(ModelId("example/model")),
    (Message(Role.USER, Content((TextContent("Bonjour"),))),),
    GenerationConfig(temperature=0.0, max_output_tokens=100),
)
assert request.target.kind == "model"
```

### Trois cibles disjointes

`ModelTarget(ModelId)`, `DeploymentTarget(DeploymentId)` et `EndpointTarget(EndpointId)` ne resolvent ni noms de providers, ni DNS, ni credentials. Un `EndpointId` n'est pas une URL de connexion implicite.

### Configuration explicite

Tous les huit champs sont initialement `None`. Les floats exigent le type `float` exact et une valeur finie; `0.0` differe de `0`. Les entiers ne prennent pas `bool`. `stop_sequences=()` est une information exprimee et distincte d'une absence `None`.

### Support effectif : ADR-021 option A

`evaluate_request_support(request, snapshot)` et `validate_request_support(request, snapshot)` inspectent **seulement** le `GenerationSupportSnapshot` explicitement fourni pour une cible identique. Une capacite absente est `UNKNOWN`, jamais `NATIVE`; `UNSUPPORTED` provoque un rejet. Aucun snapshot n'est recupere automatiquement aupres d'un fournisseur.

## Invariants

- Les `Message` M2 sont preserves dans leur ordre et leur contenu, y compris texte/image et repetitions.
- Aucun appel LLM, aucun `RunId`, aucune `Conversation`, aucun streaming ni ToolCall.
- Une requete structurellement valide ne garantit ni disponibilite d'un modele, ni une capacite vision effective.
- La serialisation canonique est `request_to_dict/from_dict` (Inference JSON v1).

Voir [API Request](../api/inference-request.md), [schema JSON](../architecture/INFERENCE_JSON_SCHEMA_V1.md), [PV G1](../quality/P3_G1_GATE_REVIEW.md).
