# PyLLMKit - P7 Provider Adapters - Architecture cible

- Date : 2026-11-06
- Statut : PROPOSED - P7-G0; aucun code provider implémenté par ce document
- Baseline : main@08a1cd5fc3d7a786e340727b446049c15c000ba7
- Invariants : Domain-First, DIP, ports/adapters, UNKNOWN != NATIVE, aucune release implicite.

## 1. Périmètre et ordre des lots

Le milestone technique P7/M7 poursuit le chantier fonctionnel historique « 6. Provider Adapters ». M6 est déjà le catalogue et la résolution descriptive offline. P7 ajoute, sans les confondre, les adapters exécutables, les connections explicites et les premières invocations Ollama, puis OpenAI Responses et Anthropic Messages. Streaming réel et qualité terminent M7.

| Incrément cible, non publié | Lots | Gate | Preuve |
|---|---|---|---|
| 0.2.0a1 | L7.1 ports/lifecycle, L7.2 sécurité/registry, L7.3 Ollama | P7-G1..G3 | Fake offline + smoke Ollama opt-in |
| 0.2.0a2 | L7.4 OpenAI, L7.5 Anthropic | P7-G4..G5 | Fixtures + smoke cloud opt-in budgété |
| 0.2.0a3 | L7.6 streaming, L7.7 resilience, L7.8 qualification | P7-G6..G8 | SSE/JSONL contract + CI + preuves live distinctes |

## 2. Topologie logique et responsabilités

1. Consumer: construit InferenceRequest (M3); ne connaît aucun SDK.
2. Application.InferenceService: valide messages/config, appelle DeploymentResolver (M6), calcule compatibilité et limites, vérifie le binding natif, crée RunId et InvocationContext, sélectionne l'adapter explicitement enregistré.
3. AdapterRegistryPort/composition: ProviderId -> factory contrôlée; distinct du ProviderCatalog M6. Pour Ollama local sans ProviderId, binding de runtime explicite et non déduction de l'identité d'un modèle.
4. Ports: InferencePort.invoke(PreparedInvocation), AsyncInferencePort.ainvoke(PreparedInvocation); ports StreamingPort/AsyncStreamingPort M5 préservés par instance bindée, sans mutation des signatures existantes.
5. Infrastructure: CredentialResolverPort, ProviderConnectionConfig, NetworkPolicy, retry/deadline, SDK optionnel.
6. Provider adapter: mappe DTO natif vers InferenceResponse ou StreamEvent typés; ne modifie ni la demande ni le domaine, n'exécute jamais un tool.
7. Run lifecycle: le service marque completed/failed/cancelled selon observation, pas selon l'intention du caller.

## 3. Séquence non-streaming proposée

Consumer -> InferenceService -> validate -> DeploymentResolver(M6) -> capability/limit -> explicit model alias -> AdapterRegistry -> NetworkPolicy/CredentialResolver -> adapter.invoke(prepared) -> provider -> strict mapping -> InferenceResponse(run_id) -> Run terminal.

Préconditions fail-closed : exactement un deployment, native model alias prouvé, adapter installé, URL approuvée, credentials requis présents, params supportés, timeout fini. Un EndpointTarget non bindé est refusé. Les objets de domaine ne reçoivent aucun token ou SDK.

## 4. Contrats d'application à figer lors de P7-G1

- InvocationContext: run_id, deployment_id, provider_id optionnel pour local, attempt_id, deadline, trace id opaque, execution policy.
- PreparedInvocation: request original inchangé, deployment résolu, native_model_alias, snapshot capacités/limites, invocation context; validation complète avant I/O.
- InvocationOptions: timeout fini, max_attempts=1 par défaut, opt-in retry, privacy policy, limites par provider.
- InferencePort et AsyncInferencePort partagent pré/postconditions, RunId et sémantique d'échec. RunId ne change pas entre tentatives du même run; attempt_id change.
- InferenceResponse.usage: inconnu ou partiel reste tel quel; jamais usage=0 inventé. finish_reason inconnu reste UNKNOWN avec native_reason assaini.
- Le binding streaming M5 peut être un objet construit avec PreparedInvocation; ses méthodes publiques gardent stream(request) / astream(request).

## 5. Table de traduction initiale (profil texte strict)

| Domaine | Ollama | OpenAI | Anthropic |
|---|---|---|---|
| API native | /api/chat | Responses API | Messages API |
| Modèle | alias local explicite | model API explicite | model API explicite |
| Dialogue | messages | input / instructions contrôlées | messages + system séparé |
| Max output | options.num_predict si supporté | max_output_tokens si supporté | max_tokens exigé |
| Texte | message.content | output text vérifié | content blocks text |
| Usage | prompt_eval_count / eval_count | input/output tokens natifs | input/output_tokens |
| Fin | done_reason si présent | status/finish native connue | stop_reason |
| Flux | JSONL | SSE Responses | SSE Messages |

Règle: aucune suppression silencieuse des tools, rôles, blocs non-textes, options inconnues ou paramètres non pris en charge. Rejeter explicitement jusqu'à extension documentée. Pour OpenAI, appliquer explicitement une politique store=false lorsque disponible; si incompatible avec l'API cible, refuser le profil plutôt que modifier silencieusement le contrat de confidentialité. Aucun contenu de raisonnement privé exposé.

## 6. Frontière sécurité

Cloud HTTPS vérifié, destinations officielles connues ou allowlist spécifique approuvée, sans redirection libre. Ollama local loopback 127.0.0.1 / ::1 seulement avec opt-in; DNS et IP finales vérifiés contre SSRF. Secrets référencés et résolus au dernier moment; jamais dans VO, repr, erreurs, snapshots ou logs. Timeouts connect/read/total finis et pool de connexions borné. Aucun réseau à l'import.

## 7. Erreurs et cycles de retry

Mapper statut fournisseur vers codes sûrs: invalid_request, authentication_failed, permission_denied, rate_limited, model_not_found, provider_overloaded, connection_failure, provider_timeout, unsupported_capability, stream_interrupted, user_cancelled. Cause native privée. Pas de retry 400/401/403. 429/5xx/timeout seulement si politique d'essai explicitement bornée et risque d'idempotence considéré. Désactiver retries automatiques SDK en présence de politique PyLLMKit. Aucun retry après premier delta.

## 8. Streaming M5 et fermeture

Mapper événements natifs SSE/JSONL vers ResponseStarted, TextDelta, UsageUpdated, ResponseCompleted, ResponseFailed et ResponseCancelled, en préservant run_id et sequence. En cas de disconnect ou de fermeture anticipée, ne jamais générer un completion fictif. close/aclose coopératifs, pas de promesse d'annulation distante.

## 9. Tests, CI et preuves

CI par défaut hermétique: fake ports, golden fixtures, échecs simulés, canaris secrets, SSRF/redirects, contrôle d'import, corpus M1-M6, JSON v1 inchangé; Python 3.11/12/13, Ruff, mypy strict, coverage branches >=95 % sur périmètre approuvé, wheel/sdist et extras isolés. Deux critères opt-in pour live, credentials non committés, budget cloud accepté, preuve distincte par fournisseur. Les 64 P7-AC-001..064 du plan sont proposés, 0 PASS avant run effectif.

## 10. Gouvernance et non-objectifs

G0 documentaire doit être accepté explicitement par le propriétaire et fusionné/qualifié sur SHA exact main avant L7.1. Pas de cache distribué, batch, embeddings, multimodalité live générale, orchestration agentique, failover intelligent, auto-exécution tools ni release implicite. Suivre #22 protection main, #35 release et #36 provider boundary. Revue humaine indépendante recommandée pour le réseau et la sécurité.
