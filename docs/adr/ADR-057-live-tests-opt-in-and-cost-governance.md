# ADR-057 - Essais live, budgets et preuves

- Date : 2026-11-06
- Statut : PROPOSED - P7-G0, non encore accepté par le propriétaire
- Milestone : P7 Provider Adapters / M7
- Baseline : main@08a1cd5fc3d7a786e340727b446049c15c000ba7
- Références : ADR-021, ADR-035, ADR-039..048, FUTURE_PROVIDER_BOUNDARY_CONTRACT et plan P7/M7.

## Décision proposée

Tous les tests réseau sont doublement opt-in: PYLLMKIT_LIVE_TESTS=1 et provider choisi, environnement/contexte explicitement fourni. Les tests cloud exigent autorisation du propriétaire, credentials externes, plafond de tokens, deadline, nombre d'appels et budget monétaire défini; sinon skip/bloqué, jamais pass. CI standard reste hermétique et sans secrets.

## Conséquences et invariants

Capturer une attestation assainie par fournisseur: date UTC, SHA, nom du modèle/alias autorisé, résultat/succès réel, identifiant de run non sensible, durée, tokens connus, statut de dépense; ne pas consigner prompts/réponses brutes ni clés. Un mock ne constitue jamais une preuve de connexion.

## Alternatives rejetées ou reportées

Tests live déclenchés sur PR externe; secrets dans artefacts; déclarer Ollama/OpenAI/Anthropic 3/3 live à partir de fixtures.

## Vérification requise

P7-AC-017..018, 024, 032, 040, 048, 060; preuves par provider vérifiables et CI offline inchangée.

## Gouvernance

Ce texte fixe une proposition de contrat, et non une preuve d'implémentation. L'acceptation requiert la décision explicite du propriétaire sur la PR documentaire P7-G0, une analyse de sécurité et la CI post-merge sur le SHA exact de main. Aucun code provider ni test réseau n'est autorisé par la seule création de l'ADR.
