# ADR-056 - SDK optionnels et compatibilité des distributions

- Date : 2026-11-06
- Statut : ACCEPTED FOR TECHNICAL P7-G0 BASELINE, sous autorisation de poursuite du propriétaire le 2026-11-06 ; revue humaine indépendante non constatée
- Milestone : P7 Provider Adapters / M7
- Baseline : main@08a1cd5fc3d7a786e340727b446049c15c000ba7
- Références : ADR-021, ADR-035, ADR-039..048, FUTURE_PROVIDER_BOUNDARY_CONTRACT et plan P7/M7.

## Décision proposée

Installation de base sans SDK fournisseur ni dépendance HTTP obligatoire. Extras indépendants openai, anthropic, ollama et agrégat providers. Imports SDK différés à l'instanciation des adapters; une dépendance manquante produit une exception sûre et actionnable. Versions/plages compatibles consignées avec fixture native et date de contrat au moment du lot correspondant.

## Conséquences et invariants

Conserver Python >=3.11 et les codecs v1 existants sans changement rétrocompatible caché. Tests wheel/sdist et installation propre sans extras, puis chaque extra séparément. Aucune importation réseau au chargement de pyllmkit.domain ou pyllmkit.protocols.

## Alternatives rejetées ou reportées

Ajouter les SDK comme dépendances obligatoires; imports top-level cassant le core; versions SDK non testées revendiquées compatibles.

## Vérification requise

P7-AC-011, 054, 057, 059, 061 et fixtures fournisseur versionnées.

## Gouvernance

La poursuite du chantier a été explicitement demandée après la présentation de P7-G0 le 2026-11-06. Ce statut accepte les décisions comme baseline de développement, sans prétendre à une revue humaine indépendante ni à une qualification post-merge déjà obtenue. Les contrôles de sécurité, CI sur SHA exact de main et gates de code demeurent obligatoires. Aucune publication ni test live payant n'est autorisé.
