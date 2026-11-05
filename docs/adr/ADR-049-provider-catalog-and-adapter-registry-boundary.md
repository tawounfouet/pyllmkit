# ADR-049 - Frontière catalogue et adaptateurs exécutables

- Date : 2026-11-06
- Statut : ACCEPTED FOR TECHNICAL P7-G0 BASELINE, sous autorisation de poursuite du propriétaire le 2026-11-06 ; revue humaine indépendante non constatée
- Milestone : P7 Provider Adapters / M7
- Baseline : main@08a1cd5fc3d7a786e340727b446049c15c000ba7
- Références : ADR-021, ADR-035, ADR-039..048, FUTURE_PROVIDER_BOUNDARY_CONTRACT et plan P7/M7.

## Décision proposée

Conserver ProviderCatalog/DeploymentRegistry de P6 comme sources descriptives, sans import ni instanciation de client externe. Introduire AdapterRegistryPort en couche composition, avec enregistrement explicite et résolution par ProviderId ou runtime local explicitement lié. Aucun enregistrement descriptif AVAILABLE ne crée automatiquement un adapter.

## Conséquences et invariants

Une entrée de catalogue et une capacité d'exécution attestent de faits différents. L'adapter ne modifie pas le catalogue pendant un appel. Une absence d'adapter produit adapter_not_registered avant toute connexion.

## Alternatives rejetées ou reportées

Enregistrement implicite depuis les noms du catalogue; découverte réseau à l'import; service universel qui importe les trois SDK.

## Vérification requise

Fitness test sans SDK dans le core; test P7-AC-009; doublons de registry P7-AC-010; zéro connexion à l'import P7-AC-054.

## Gouvernance

La poursuite du chantier a été explicitement demandée après la présentation de P7-G0 le 2026-11-06. Ce statut accepte les décisions comme baseline de développement, sans prétendre à une revue humaine indépendante ni à une qualification post-merge déjà obtenue. Les contrôles de sécurité, CI sur SHA exact de main et gates de code demeurent obligatoires. Aucune publication ni test live payant n'est autorisé.
