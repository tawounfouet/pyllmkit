# ADR-055 - Streaming, annulation et fermeture des ressources

- Date : 2026-11-06
- Statut : PROPOSED - P7-G0, non encore accepté par le propriétaire
- Milestone : P7 Provider Adapters / M7
- Baseline : main@08a1cd5fc3d7a786e340727b446049c15c000ba7
- Références : ADR-021, ADR-035, ADR-039..048, FUTURE_PROVIDER_BOUNDARY_CONTRACT et plan P7/M7.

## Décision proposée

Réutiliser les événements typés M5, leur séquencement et leurs terminaux. Adaptateurs propriétaires de SSE OpenAI Responses, SSE Anthropic Messages et JSONL Ollama; mapper en StreamEvent M5 ordonnés, avec même RunId. Respecter StreamingPort.stream(request) et AsyncStreamingPort.astream(request) via instance bindée à une PreparedInvocation, plutôt que changer les Protocol existants.

## Conséquences et invariants

Une interruption après premier delta produit échec explicite, jamais ResponseCompleted fictif, jamais replay implicite. La fermeture iterator/async iterator ferme la réponse HTTP et les clients possédés; l'annulation distante reste non garantie. Backpressure native des itérateurs; pas de buffering illimité.

## Alternatives rejetées ou reportées

Faire passer le streaming pour Iterator[str]; terminer un flux clos prématurément en succès; retry post-delta; renommer ou casser M5.

## Vérification requise

P7-AC-041..048, cas early close, erreur en plein SSE, cancellation sync/async et tests de fuite de ressources.

## Gouvernance

Ce texte fixe une proposition de contrat, et non une preuve d'implémentation. L'acceptation requiert la décision explicite du propriétaire sur la PR documentaire P7-G0, une analyse de sécurité et la CI post-merge sur le SHA exact de main. Aucun code provider ni test réseau n'est autorisé par la seule création de l'ADR.
