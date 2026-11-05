# ADR-053 - Erreurs, retries et deadlines

- Date : 2026-11-06
- Statut : ACCEPTED FOR TECHNICAL P7-G0 BASELINE, sous autorisation de poursuite du propriétaire le 2026-11-06 ; revue humaine indépendante non constatée
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

La poursuite du chantier a été explicitement demandée après la présentation de P7-G0 le 2026-11-06. Ce statut accepte les décisions comme baseline de développement, sans prétendre à une revue humaine indépendante ni à une qualification post-merge déjà obtenue. Les contrôles de sécurité, CI sur SHA exact de main et gates de code demeurent obligatoires. Aucune publication ni test live payant n'est autorisé.
