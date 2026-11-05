# Concepts PyLLMKit

PyLLMKit documente les primitives de domaine qui décrivent les modèles, les interactions, l'inférence et les outils LLM. Chaque module demeure indépendant d'un fournisseur et du réseau.

## Model et capacités (M1)

[Model](model.md) et [Capabilities & Modalities](capabilities-and-modalities.md).

## Interaction (M2)

[Messages](messages.md), [Content](content.md) et [Media & Images](media-and-images.md).

## Inference (M3)

[Inference Request](inference-request.md), [Inference Response](inference-response.md) et [Inference Run](inference-run.md).

## Tooling & Structured Output (P4)

[Tool Definition](tool-definition.md), [Tool Call](tool-call.md) et [Structured Output](structured-output.md).

Les contrats P4 sont aussi présentés dans l'[architecture P4](../architecture/PHASE_4_TOOLING_AND_STRUCTURED_OUTPUT_CONTRACTS.md), avec un [codec Tooling JSON v1](../architecture/TOOLING_JSON_SCHEMA_V1.md) indépendant du codec Inference JSON v1.

Aucun de ces objets ne lance des appels LLM ou exécute des outils. La version source déclarée reste 0.1.0a2; aucun jalon technique ne constitue une autorisation de publication.
