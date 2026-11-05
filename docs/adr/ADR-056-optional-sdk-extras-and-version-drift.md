# ADR-056 - SDK optionnels et compatibilité des distributions

- Date : 2026-11-06
- Statut : PROPOSED - P7-G0, non encore accepté par le propriétaire
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

Ce texte fixe une proposition de contrat, et non une preuve d'implémentation. L'acceptation requiert la décision explicite du propriétaire sur la PR documentaire P7-G0, une analyse de sécurité et la CI post-merge sur le SHA exact de main. Aucun code provider ni test réseau n'est autorisé par la seule création de l'ADR.
