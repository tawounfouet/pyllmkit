# ADR-051 - Résolution de cible et binding explicite

- Date : 2026-11-06
- Statut : PROPOSED - P7-G0, non encore accepté par le propriétaire
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

Ce texte fixe une proposition de contrat, et non une preuve d'implémentation. L'acceptation requiert la décision explicite du propriétaire sur la PR documentaire P7-G0, une analyse de sécurité et la CI post-merge sur le SHA exact de main. Aucun code provider ni test réseau n'est autorisé par la seule création de l'ADR.
