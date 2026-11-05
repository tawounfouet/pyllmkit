# PyLLMKit - P7 Provider Adapters - Référentiel d'implémentation

- Date: 2026-11-06
- Statut: PROPOSED - P7-G0 non qualifié
- Source: plan P7/M7 fourni par le propriétaire le 2026-11-06
- Baseline: main@08a1cd5fc3d7a786e340727b446049c15c000ba7
- Version déclarée: 0.1.0a2; 0.2.0a1..a3 cibles et non releases.

## Gates et branches

| Étape | Branche recommandée | Contenu |
|---|---|---|
| P7-G0 | p7/g0-provider-architecture | ADR 049..058, architecture, threat model, précheck |
| P7-G1 / L7.1 | p7/l71-inference-ports | sync/async, PreparedInvocation, RunId, fake |
| P7-G2 / L7.2 | p7/l72-secure-provider-registry | registry, credentials, réseau, erreurs, extras |
| P7-G3 / L7.3 | p7/l73-ollama-first-invocation | Ollama, tests offline + smoke local opt-in |
| P7-G4 / L7.4 | p7/l74-openai-responses-adapter | OpenAI Responses, fixtures + cloud opt-in |
| P7-G5 / L7.5 | p7/l75-anthropic-messages-adapter | Anthropic Messages, fixtures + cloud opt-in |
| P7-G6 / L7.6 | p7/l76-network-streaming | SSE/JSONL, M5, cancellation |
| P7-G7 / L7.7 | p7/l77-reliability-security | retries, SSRF, observabilité |
| P7-G8 / L7.8 | p7/l78-integration-quality | CI, exemples, packaging, AC, revue |
| M7 final | p7/m7-final-review | Bilan M7 indépendant |

## Contrats d'acceptation

64 cas proposés P7-AC-001..064, 8 par lot L7.1..L7.8. Ils doivent être tracés vers des tests effectivement exécutés. P7-G0 documentaire n'en valide aucun automatiquement. Ne pas annoncer de PASS d'invocation réelle à partir de mock/fixture. Les tests bloquants restent sans réseau; les tests live nécessitent opt-in explicite et budget approuvé.

## Règle de fusion

Pour chaque gate: PR -> revue -> CI sur HEAD -> décision du propriétaire -> merge -> CI push/main sur SHA exact -> procès-verbal. Pas de merge ou publication autorisés par ce document. La protection main (#22), la release (#35) et la boundary (#36) restent ouvertes.

## Sécurité / exclusion

Aucun SDK dans domain; pas de tools automatiquement exécutés, ni routage auto, embeddings, batch, multimodalité générale, ou proxy enterprise dans M7. SDKs en extras; secrets hors code; endpoints sûrs; unknown/unsupported refusés; aucune promesse de disponibilité réelle d'un provider par son seul statut descriptif AVAILABLE.
