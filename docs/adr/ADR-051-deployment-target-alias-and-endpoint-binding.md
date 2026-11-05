# ADR-051 - Résolution de cible et binding explicite

- Date : 2026-11-06
- Statut : ACCEPTED FOR TECHNICAL P7-G0 BASELINE, sous autorisation de poursuite du propriétaire le 2026-11-06 ; revue humaine indépendante non constatée
- Milestone : P7 Provider Adapters / M7
- Baseline : main@08a1cd5fc3d7a786e340727b446049c15c000ba7
- Références : ADR-021, ADR-035, ADR-039..048, FUTURE_PROVIDER_BOUNDARY_CONTRACT et plan P7/M7.

## Décision proposée

Le service réutilise DeploymentResolver P6 et exige exactement un deployment admissible. DeploymentTarget exact ne peut jamais être redirigé. ProviderModelRef ou binding de composition détermine le model alias natif; aucun alias n'est inféré de ModelId. EndpointTarget ne contient pas une URL : refuser target_not_routable tant qu'un binding sûr, vérifiable et explicitement approuvé n'existe pas.

## Conséquences et invariants

Vérifier l'identité du deployment, provider/runtime, alias, capacité et limite avant adaptation. ModelTarget 0/N candidats produit erreur explicite sans contact réseau. Le provider id ne peut être déduit du seul protocole OpenAI-compatible.

## Alternatives rejetées ou reportées

Routage heuristique et sélection arbitraire du premier candidat; traitement de EndpointId comme URL; fallback implicite multi-provider.

## Vérification requise

P7-AC-005..007, P7-AC-021, P7-AC-027 et P7-AC-036; tests cible exacte et zéro requête après échec.

## Gouvernance

La poursuite du chantier a été explicitement demandée après la présentation de P7-G0 le 2026-11-06. Ce statut accepte les décisions comme baseline de développement, sans prétendre à une revue humaine indépendante ni à une qualification post-merge déjà obtenue. Les contrôles de sécurité, CI sur SHA exact de main et gates de code demeurent obligatoires. Aucune publication ni test live payant n'est autorisé.
