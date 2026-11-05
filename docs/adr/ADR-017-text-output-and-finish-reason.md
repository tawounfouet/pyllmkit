# ADR-017 - TextOutput et FinishReason normalise
> **Decision owner P3-G0 (2026-11-05)** : `ACCEPTED`, sous autorite du proprietaire dans la conversation du projet. Cette autorisation concerne les contrats et leur integration, **pas** une GitHub review externe ni la publication d'un package. 
> **Arbitrage retenu :** TextOutput including empty text, absent FinishReason distinct from UNKNOWN; normalized code plus optional native reason; no Tool execution.


- **Statut : ACCEPTED** - adoption explicite par le proprietaire pour P3-G0 le 2026-11-05. Contrat de conception adopte, implementation Python non commencee.
- Sources : plan Phase 3 section 6, FR-019/021, INF-022..026, architecture Inference.

## Contexte

Les resultats fournisseurs ne se reduisent pas toujours a du texte; leur raison de fin peut etre absente ou non reconnue. Le domaine doit conserver cette heterogeneite sans donner l'illusion que les tools et sorties structurees sont deja operationnels.

## Decision adoptee

1. **InferenceOutput** est le contrat conceptuel extensible. Le seul type concret de a3 est **TextOutput(text: str)**, immuable et strict.
2. Une string vide est un output textuel valide et reste distincte de l'absence d'un output. InferenceResponse exige toujours un output non nul en a3.
3. **FinishReasonCode** represente STOP, LENGTH, TOOL_CALL, CONTENT_FILTER, CANCELLED, ERROR, UNKNOWN; **FinishReason** est un Value Object avec code normalise et **native_reason: str | None**.
4. L'absence complete de finish_reason reste **None**; un motif natif inconnu, lorsqu'il est fourni, devient **UNKNOWN** en conservant la valeur native. Ne jamais convertir UNKNOWN en STOP.
5. Une raison de fin n'est pas un etat du Run: CANCELLED sur une raison et CANCELLED sur un run ne sont pas interchangeables.
6. TOOL_CALL peut etre decrit comme cause de fin mais n'implemente ni ToolCallOutput, ni execution d'outils dans a3.
7. Pas d'output JSON structure, image, audio, embeddings ou raw provider dans le P0. Leur ajout necessite un contrat de variante et une evolution de codec explicite.

## Alternatives

- Retourner directement une string au lieu d'un output typé : rejete, compromet la famille Output.
- Enum unique et fermee sans native_reason : rejete, perd les informations inconnues.
- Produire STOP en l'absence de signal : rejete, invente une observation.

## Acceptance

- TextOutput: Unicode, vide, mauvais types, equality et hash.
- FinishReason: codes canoniques, UNKNOWN avec provenance, None sans source, refus de types invalides.
- Response ne confond pas output et reason ni response et etat.
- Tests P3-AC-008/009, P3-AC-022.
