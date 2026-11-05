# ADR-020 - Inference JSON v1, objets et snapshots
> **Decision owner P3-G0 (2026-11-05)** : `ACCEPTED`, sous autorite du proprietaire dans la conversation du projet. Cette autorisation concerne les contrats et leur integration, **pas** une GitHub review externe ni la publication d'un package. 
> **Arbitrage retenu :** Independent strict INFERENCE_SCHEMA_VERSION=1; Request/Response/Run envelopes and six valid Run snapshots, timestamps UTC, full Interaction JSON v1 nested, preserve null.


- **Statut : ACCEPTED** - adoption explicite par le proprietaire pour P3-G0 le 2026-11-05. Contrat de conception adopte, implementation Python non commencee.
- **Sources :** plan Phase 3 section 8; ADR-004, ADR-012, ADR-014..019, SER-001..006, PIR2-03/04/06.
- **Portee :** mapping JSON de domaine, pas payload provider ni parser HTTP.

## Decision proposee

1. **INFERENCE_SCHEMA_VERSION = 1** est propre au namespace Inference. Model v1 et Interaction v1 restent inchanges.
2. Trois enveloppes canoniques : **inference_request**, **inference_response**, **inference_run**. Chacune contient schema_version entier exact 1 (bool exclu) et object_type exact.
3. Request : target (kind: model/deployment/endpoint, value: id), liste non vide de messages **Interaction JSON v1 complets**, generation_config (objet P0 avec les 8 champs ou null).
4. Response : run_id non vide, output = discriminant **text** et texte exact (vide autorise), finish_reason et usage nullable. FinishReason contient code normalise et native_reason nullable; UNKNOWN ne signifie pas STOP.
5. Run : run_id, request emboitee, attempt, state, started_at, streaming_started_at, finished_at, response, failure et cancellation_reason_code. Les six etats et toutes leurs contraintes de dates et payload terminal sont revalides a la lecture (ADR-019).
6. **InferenceFailure** P0 = objet avec **code** non vide. Le failure n'est pas une exception ni un raw provider error; l'absence de details doit rester absente.
7. **Presence obligatoire de toutes les cles canoniques**, y compris les champs nullable qui valent null, dans chaque enveloppe v1. Dans GenerationConfig non-nulle et Usage non-nul, tous les champs P0 sont explicitement presents et nullable. Aucune valeur par defaut n'est produite silencieusement.
8. Rejeter a toutes les profondeurs les cles inconnues/manquantes, les variantes inconnues, les types incorrects, booleens utilises comme entiers et NaN/Inf. Echec par DomainValidationError ou sous-type valide, sans echo de prompt, URI, token ou raw data.
9. Les timestamps sont des strings ISO 8601 timezone-aware canoniques, normalises en UTC a l'ecriture. Le decodage restitue un datetime aware de la meme valeur temporelle; le fuseau d'origine n'est **pas** un champ du contrat. Aucun now() en cours de parsing.
10. Les appels request_to_dict/from_dict, response_to_dict/from_dict et run_to_dict/from_dict sont des fonctions pures. json.dumps/json.loads restent a la frontiere caller. La validation des cles dupliquees dans le **texte JSON** n'est pas garantie par json.loads standard.
11. Conserver ordre et doublons des messages/ContentParts, ainsi que les references media (sans fetch); aucun cast provider, aucun Message v2, pas de migration automatique.
12. Pour tout schema non valide : refus deterministe, **jamais** un best effort qui perd des informations.

## Exemple Request complet (illustration a approuver)

~~~json
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
~~~

Si generation_config est un objet, ses 8 cles sont : temperature, top_p, top_k, max_output_tokens, seed, stop_sequences, presence_penalty et frequency_penalty. stop_sequences vaut null ou un tableau JSON (vide autorise).

## Exemple Response complet (illustration a approuver)

~~~json
{
  "schema_version": 1,
  "object_type": "inference_response",
  "run_id": "run-001",
  "output": {"kind": "text", "text": ""},
  "finish_reason": {"code": "unknown", "native_reason": "some_provider_reason"},
  "usage": {
    "input_tokens": 8,
    "output_tokens": null,
    "total_tokens": null,
    "reasoning_tokens": null,
    "cached_input_tokens": 0
  }
}
~~~

Le reason code et le compteur cached_input_tokens sont illustratifs, non inventes lors d'un decodage de production.

## Exemple Run COMPLETED complet (illustration a approuver)

~~~json
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
~~~

Pour FAILED, response=null et failure={"code":"inference_failed"} ; pour CANCELLED, response=null et failure=null, cancellation_reason_code=null ou code non vide. CREATED et RUNNING respectent les combinaisons de dates de l'ADR-019. Aucun timestamp terminal n'est invente.

## Alternatives et compromis

- Reutiliser Model/Interaction codec pour une enveloppe Inference : rejete.
- Mapper directement un wire format OpenAI/Anthropic : rejete.
- Ommettre les nullable ou leur donner des defaults silencieux : rejete dans v1.
- Conserver le fuseau source d'un datetime : reporte, inutile pour le suivi d'instant.
- Decoder un objet incoherent en contournant le constructeur : rejete.

## Verification avant G4

- Payloads canoniques revus et fixtures testees.
- Round-trip pour Request, Response et chacun des **six** etats Run.
- Tests de negative schema, dates incoherentes, run_id differents, failure illegal, null/zero, ordre, doublons, Unicode, NaN/Inf.
- Non-regression M1/M2 et controle de fuite d'informations dans les exceptions.
- Policy future de parseur strict a la frontiere HTTP (PIR2-04), sans le revendiquer comme disponible aujourd'hui.

**Statut : ACCEPTED pour la conception P3.** L'implementation des symboles reste a realiser.
