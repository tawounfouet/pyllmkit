# ADR-054 - Mapping natif et profil texte strict

- Date : 2026-11-06
- Statut : PROPOSED - P7-G0, non encore accepté par le propriétaire
- Milestone : P7 Provider Adapters / M7
- Baseline : main@08a1cd5fc3d7a786e340727b446049c15c000ba7
- Références : ADR-021, ADR-035, ADR-039..048, FUTURE_PROVIDER_BOUNDARY_CONTRACT et plan P7/M7.

## Décision proposée

Premier profil d'exécution: chat textuel avec rôles et ContentPart texte connus, options de génération démontrées compatibles, TextOutput et Usage partiel. OpenAI utilise Responses API, Anthropic Messages API et Ollama /api/chat. Le mapping explicite conserve ordre, rôle, alias de modèle, native finish reason assainie, tokens réellement reçus; UNKNOWN reste UNKNOWN et absence de usage reste None.

## Conséquences et invariants

System/developer sont mappés selon la sémantique du fournisseur; si l'équivalence ne peut être garantie, refuser. Tools, outputs non textuels, reasoning privé, image, structured output et options incompatibles sont refusés plutôt que supprimés. Anthropic exige max_tokens fourni et validé. OpenAI store=false est imposé dans le profil de confidentialité initial lorsque le contrat endpoint le permet; refus explicite si la politique ne peut être satisfaite.

## Alternatives rejetées ou reportées

Un dict universel qui efface les différences; conversion de finish reason inconnue en STOP; inventer usage, prix ou coût.

## Vérification requise

P7-AC-019,021..023, 025..031, 033..038; golden fixtures et canaris pour blocs non supportés.

## Gouvernance

Ce texte fixe une proposition de contrat, et non une preuve d'implémentation. L'acceptation requiert la décision explicite du propriétaire sur la PR documentaire P7-G0, une analyse de sécurité et la CI post-merge sur le SHA exact de main. Aucun code provider ni test réseau n'est autorisé par la seule création de l'ADR.
