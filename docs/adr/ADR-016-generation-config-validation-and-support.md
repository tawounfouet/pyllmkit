# ADR-016 - GenerationConfig, valeurs absentes et validation

- Statut : **PROPOSED** (P3-BOOT, 2026-11-05).
- Sources : plan Phase 3 section 5.2, FR-016/017, INF-001..005, SER-004.

## Contexte

Les fournisseurs n'ont pas les memes options de generation. Une configuration generique doit decrire l'intention, sans supposer support, coercition ou bornes propres a une API.

## Decision proposee

1. **GenerationConfig** est un Value Object frozen/slots, sans valeur par defaut universelle de generation. Chaque parametre non fourni vaut **None**.
2. Champs P0 : temperature, top_p, top_k, max_output_tokens, seed, stop_sequences, presence_penalty, frequency_penalty. Le nom **max_output_tokens** est propose en remplacement du terme conceptuel max_tokens, sous reserve de G0.
3. Les champs decimaux acceptent un vrai float fini (ni bool ni NaN/Infinity); les entiers acceptent un int exact sauf bool. Aucune coercition implicite.
4. Contraintes generiques proposees : temperature >= 0.0; 0.0 < top_p <= 1.0; top_k >= 1; max_output_tokens >= 1; seed est un entier explicite sans borne commune arbitraire; presence_penalty/frequency_penalty sont finis, sans limite specifique inventee.
5. **stop_sequences** vaut None ou un tuple de strings exactes non vides; tuple vide explicite autorise et distinct de None. Ordre et repetitions preserves.
6. **0.0**, **0**, **False**, **()**, None et UNKNOWN ne sont jamais fusionnes. False n'est jamais un int valide pour les compteurs.
7. La validation **structurelle** reside dans le domaine; la validation du **support effectif** utilise un resolver ou une policy externe quand des capacites de la cible sont effectivement connues.
8. Les options natives provider restent hors GenerationConfig. Pas de fourre-tout mutable ou de dict arbitraire dans le contrat P0.

## Alternatives examinees

- Defaults copies d'OpenAI, Anthropic ou Google : rejetes.
- Accepter silencieusement tout type ou tronquer les bornes : rejete.
- Sentinelle UNSET : envisageable si None devient semantiquement insuffisant; non retenue dans a3.
- Verification effective dans le constructeur : rejetee en absence de cible resolue.

## Conditions d'acceptation

- Tests exhaustifs: None, 0.0, entier/bool, Nan/Inf, bornes, tuple vide, duplicates, mauvais types.
- Aucune assertion de support provider en l'absence de snapshot de compatibilite.
- Round-trip JSON sans defaults ajoutes.
- Tests P3-AC-004..007, P3-AC-021.
