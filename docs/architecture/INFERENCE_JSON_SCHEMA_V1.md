# Inference JSON Schema v1 - Contrat de mapping de domaine

> `INFERENCE_SCHEMA_VERSION = 1`, defini dans `pyllmkit.domain.inference.serialization`.
> ADR-020 ACCEPTED; code P3-G4 qualifie, futur M3 non encore qualifie.
> Independamment de `Model JSON v1` et `Interaction JSON v1`.

## Enveloppes obligatoires

| Envelope | Champs exactement requis |
|---|---|
| `inference_request` | `schema_version`, `object_type`, `target`, `messages`, `generation_config` |
| `inference_response` | `schema_version`, `object_type`, `run_id`, `output`, `finish_reason`, `usage` |
| `inference_run` | `schema_version`, `object_type`, `run_id`, `request`, `attempt`, `state`, `started_at`, `streaming_started_at`, `finished_at`, `response`, `failure`, `cancellation_reason_code` |

Toutes les cles doivent etre **presentes**. Une valeur nullable absente n'est pas equivalente a la cle presente avec `null`. Les cles extras et variantes inconnues sont refusees.

## Request v1

```json
{
  "schema_version": 1,
  "object_type": "inference_request",
  "target": {"kind": "model", "value": "example/model"},
  "messages": [
    {
      "schema_version": 1,
      "object_type": "message",
      "role": "user",
      "content": {"parts": [{"kind": "text", "text": "Bonjour"}]}
    }
  ],
  "generation_config": null
}
```

- `target.kind` appartient a `model`, `deployment`, `endpoint`; `value` est un ID opaque, jamais un client reseau.
- `messages` doit etre un tableau non vide d'enveloppes **Interaction JSON v1 completes**, sans perte de l'ordre, des repetitions ou des media references.
- Config non nulle : exactement `temperature`, `top_p`, `top_k`, `max_output_tokens`, `seed`, `stop_sequences`, `presence_penalty`, `frequency_penalty`. Champs non renseignes avec `null`; `stop_sequences=[]` autorise, distinct de `null`.
- Les champs reels utilisent le type Python `float` exact et fini (`0.0` et non `0`) et les entiers sont des `int` exacts (pas `True`). Les bornes viennent des Value Objects.

## Response v1

```json
{
  "schema_version": 1,
  "object_type": "inference_response",
  "run_id": "run-001",
  "output": {"kind": "text", "text": ""},
  "finish_reason": {"code": "unknown", "native_reason": "provider_specific"},
  "usage": {
    "input_tokens": 8,
    "output_tokens": null,
    "total_tokens": null,
    "reasoning_tokens": null,
    "cached_input_tokens": 0
  }
}
```

`output.kind="text"` est le seul variant. `finish_reason` nullable est distinct de `code="unknown"`. Une Usage non nulle possede cinq cles obligatoires, chacune un entier non negatif ou `null`. **Jamais de somme ou de cout invente**.

## Run v1

```json
{
  "schema_version": 1,
  "object_type": "inference_run",
  "run_id": "run-001",
  "request": {
    "schema_version": 1,
    "object_type": "inference_request",
    "target": {"kind": "model", "value": "example/model"},
    "messages": [
      {
        "schema_version": 1,
        "object_type": "message",
        "role": "user",
        "content": {"parts": [{"kind": "text", "text": "Bonjour"}]}
      }
    ],
    "generation_config": null
  },
  "attempt": 1,
  "state": "completed",
  "started_at": "2026-11-05T10:00:00+00:00",
  "streaming_started_at": null,
  "finished_at": "2026-11-05T10:00:02+00:00",
  "response": {
    "schema_version": 1,
    "object_type": "inference_response",
    "run_id": "run-001",
    "output": {"kind": "text", "text": "Bonjour !"},
    "finish_reason": {"code": "stop", "native_reason": null},
    "usage": null
  },
  "failure": null,
  "cancellation_reason_code": null
}
```

Six etats : `created`, `running`, `streaming`, `completed`, `failed`, `cancelled`. Les etats `completed`, `failed` et `cancelled` ont `started_at` et `finished_at`. Pour `failed`, `response=null` et `failure={"code":"normalized_code"}`; pour `cancelled`, ni response ni failure. Le constructeur de `InferenceRun` rejette les incoherences, meme si le mapping satisfait les cles.

Les dates sont des ISO 8601 aware avec offset explicite; le codec les convertit en UTC lors de l'ecriture. Aucune date n'est calculee implicitement.

## API de transformation

```python
import json
from pyllmkit.domain import request_to_dict, request_from_dict

wire = json.dumps(request_to_dict(request), allow_nan=False)
restored = request_from_dict(json.loads(wire))
```

L'objet `request` est suppose construit dans le code appelant. Les fonctions en elles-memes n'acceptent que des mappings JSON-compatible. Elles **ne sont pas** un parseur JSON texte ni un codec OpenAI/Anthropic.

## Limites explicites

- Le parseur standard `json.loads` ne garantit pas le refus des cles dupliquees; le caller doit appliquer la politique `object_pairs_hook` ou equivalente au boundary.
- Le parseur standard peut accepter `NaN` et `Infinity` en texte avant validation; le boundary doit assurer le comportement strict attendu.
- Les structures `Mapping` read-only sont gerees par le codec Interaction apres PIR2-03; aucun appel provider ni envoi reseau n'est implique.
- Pas de migration v2, extensions arbitraires, tarification, role provider-specific ou ToolCall dans ce schema.

Voir [ADR-020](../adr/ADR-020-inference-json-v1-codec.md), [API codec](../api/inference-json-v1.md), [tests L3.4](../../tests/acceptance/test_p3_l34_inference_json_v1.py) et [PV G4](../quality/P3_G4_GATE_REVIEW.md).
