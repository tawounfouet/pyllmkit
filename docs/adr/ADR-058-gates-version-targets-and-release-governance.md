# ADR-058 - Gates, versions cibles et gouvernance de release

- Date : 2026-11-06
- Statut : PROPOSED - P7-G0, non encore accepté par le propriétaire
- Milestone : P7 Provider Adapters / M7
- Baseline : main@08a1cd5fc3d7a786e340727b446049c15c000ba7
- Références : ADR-021, ADR-035, ADR-039..048, FUTURE_PROVIDER_BOUNDARY_CONTRACT et plan P7/M7.

## Décision proposée

P7-G0 est une PR documentaire avec ADR-049..058, architecture, threat model et précheck, à approuver explicitement avant tout code d'adapter. P7-G1..G8 suivent les lots L7.1..L7.8 en PR séquentielles, chaque gate exige CI sur HEAD puis sur SHA exact de main après merge. M7 final est une revue distincte de G8.

## Conséquences et invariants

Les étiquettes 0.2.0a1, 0.2.0a2 et 0.2.0a3 sont uniquement des cibles fonctionnelles: aucun bump, tag, release GitHub ni publication PyPI sans arbitrage séparé de version et autorisation propriétaire. Réserves #22, #35, #36 maintenues visibles, et absence de revue tierce jamais présentée comme approbation indépendante.

## Alternatives rejetées ou reportées

Déclarer GO sur simple capture d'écran/PR verte; inférer autorisation de release depuis GO technique; fusionner des gates en parallèle.

## Vérification requise

P7-AC-057..064; registre des CI SHA, 64 AC traçables, PV P7_Gn_GATE_REVIEW et M7_GATE_REVIEW final.

## Gouvernance

Ce texte fixe une proposition de contrat, et non une preuve d'implémentation. L'acceptation requiert la décision explicite du propriétaire sur la PR documentaire P7-G0, une analyse de sécurité et la CI post-merge sur le SHA exact de main. Aucun code provider ni test réseau n'est autorisé par la seule création de l'ADR.
