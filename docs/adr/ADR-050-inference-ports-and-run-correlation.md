# ADR-050 - Ports d'inférence et corrélation des runs

- Date : 2026-11-06
- Statut : PROPOSED - P7-G0, non encore accepté par le propriétaire
- Milestone : P7 Provider Adapters / M7
- Baseline : main@08a1cd5fc3d7a786e340727b446049c15c000ba7
- Références : ADR-021, ADR-035, ADR-039..048, FUTURE_PROVIDER_BOUNDARY_CONTRACT et plan P7/M7.

## Décision proposée

Définir InferencePort.invoke(prepared: PreparedInvocation) et AsyncInferencePort.ainvoke(prepared) pour l'exécution texte. PreparedInvocation est un objet immuable de frontière application, construit après résolution, contenant InferenceRequest original, deployment, alias fournisseur explicite, snapshot de compatibilité et InvocationContext. RunId créé une seule fois par service, avant le transport; AttemptId change pour chaque tentative réseau.

## Conséquences et invariants

Le service application reste propriétaire du cycle Run: created -> running -> completed/failed/cancelled après observation. L'adapter retourne InferenceResponse avec le même InferenceRunId. Les ports M5 streaming existants gardent stream(request) et astream(request); une instance de streaming bindée au contexte sera utilisée, sans rupture de signature.

## Alternatives rejetées ou reportées

Ajouter un run_id à InferenceRequest; modifier les codecs v1; laisser un SDK inventer les run ids; créer de nouvelles APIs streaming incompatibles.

## Vérification requise

Fake sync/async; P7-AC-001..004 et 008; tests de parité sync/async; invariance du codec Inference v1; cleanup M5.

## Gouvernance

Ce texte fixe une proposition de contrat, et non une preuve d'implémentation. L'acceptation requiert la décision explicite du propriétaire sur la PR documentaire P7-G0, une analyse de sécurité et la CI post-merge sur le SHA exact de main. Aucun code provider ni test réseau n'est autorisé par la seule création de l'ADR.
