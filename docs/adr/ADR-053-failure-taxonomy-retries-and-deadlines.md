# ADR-053 - Erreurs, retries et deadlines

- Date : 2026-11-06
- Statut : PROPOSED - P7-G0, non encore accepté par le propriétaire
- Milestone : P7 Provider Adapters / M7
- Baseline : main@08a1cd5fc3d7a786e340727b446049c15c000ba7
- Références : ADR-021, ADR-035, ADR-039..048, FUTURE_PROVIDER_BOUNDARY_CONTRACT et plan P7/M7.

## Décision proposée

Les exceptions SDK et statuts HTTP sont traduits en codes sûrs: invalid_request, unsupported_capability, authentication_failed, permission_denied, model_not_found, rate_limited, provider_overloaded, provider_timeout, connection_failure, stream_interrupted, user_cancelled. La cause native reste privée; aucun body/token n'entre dans le message public. Par défaut max_attempts=1; retries optionnels bornés par deadline et budget explicites.

## Conséquences et invariants

Une politique de retry unique gouverne le transport: max_retries=0 dans les SDK si PyLLMKit gère les retries. Pas de retry automatique des 400/401/403, ni après premier delta. 429 et erreurs transitoires seulement si budget et risque d'idempotence acceptés; Retry-After plafonné; chaque tentative a un AttemptId unique sans changer RunId. Timeout n'atteste pas que le fournisseur n'a pas traité ou facturé l'appel.

## Alternatives rejetées ou reportées

Empiler les retries SDK/framework; retries illimités; masquer un traitement partiel par un deuxième appel.

## Vérification requise

P7-AC-015..016, 030, 038..039 et 049..051; fake clock, fault injection et preuve du nombre de tentatives.

## Gouvernance

Ce texte fixe une proposition de contrat, et non une preuve d'implémentation. L'acceptation requiert la décision explicite du propriétaire sur la PR documentaire P7-G0, une analyse de sécurité et la CI post-merge sur le SHA exact de main. Aucun code provider ni test réseau n'est autorisé par la seule création de l'ADR.
