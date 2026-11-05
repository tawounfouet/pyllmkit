# ADR-054 - Mapping natif et profil texte strict

- Date : 2026-11-06
- Statut : ACCEPTED FOR TECHNICAL P7-G0 BASELINE, sous autorisation de poursuite du propriétaire le 2026-11-06 ; revue humaine indépendante non constatée
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

La poursuite du chantier a été explicitement demandée après la présentation de P7-G0 le 2026-11-06. Ce statut accepte les décisions comme baseline de développement, sans prétendre à une revue humaine indépendante ni à une qualification post-merge déjà obtenue. Les contrôles de sécurité, CI sur SHA exact de main et gates de code demeurent obligatoires. Aucune publication ni test live payant n'est autorisé.
