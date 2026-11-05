# ADR-018 - Usage, granularite et valeurs manquantes
> **Decision owner P3-G0 (2026-11-05)** : `ACCEPTED`, sous autorite du proprietaire dans la conversation du projet. Cette autorisation concerne les contrats et leur integration, **pas** une GitHub review externe ni la publication d'un package. 
> **Arbitrage retenu :** Nullable observed token counters, no defaults as 0, total_tokens is provider observation only; no Pricing/Cost in Usage.


- **Statut : ACCEPTED** - adoption explicite par le proprietaire pour P3-G0 le 2026-11-05. Contrat de conception adopte, implementation Python non commencee.
- Sources : plan Phase 3 section 6.3, FR-030, INV-008, USG-001..006.

## Contexte

Les fournisseurs exposent des metriques variables, parfois incompletes et parfois non comparables. Usage doit decrire des observations techniques, sans deduction de prix ni fausses mesures.

## Decision proposee

1. **Usage** est un Value Object immuable optionnel dans InferenceResponse.
2. Champs canoniques P0 optionnels : **input_tokens**, **output_tokens**, **total_tokens**, **reasoning_tokens**, **cached_input_tokens**. Chacun est un **int exact >= 0 ou None**. Le booleen est refuse.
3. **None != 0**. Aucune metrique absente n'est completee automatiquement.
4. **total_tokens** conserve une valeur rapportee par la source, sans imposer total = input + output ni calculer une somme tacite. Une fonction de calcul future exigerait une convention de provenance explicite.
5. **reasoning_tokens** et **cached_input_tokens** sont des sous-comptages optionnels. Ils ne sont pas deduits d'un solde ou de la longueur du texte.
6. **Usage != Pricing != Cost**. Aucune multiplication par un prix ni facture n'appartient a ce VO.
7. Les metriques propres aux providers sont differees dans une extension namespacee et immuable; aucun dict arbitraire n'est ajoute au contrat P0.
8. Si la source ne rapporte aucun usage, la response porte **usage=None** plutot qu'un Usage avec des zeros. Un Usage partiel reste representable.
9. Une coherence non garantie entre compteurs fournis n'est ni silencieusement corrigee ni presentee comme une estimation certifiee.

## Alternatives

- Calculer automatiquement total_tokens : rejete dans le constructeur par risque de semantique heterogene.
- Remplir les absences par zero : rejete.
- Stocker un prix dans Usage : rejete, melange domaine technique et economics.

## Tests / gate

- None, zero, donnees partielles, valeurs negatives, float et bool, absence d'usage complet.
- Aucun champ de pricing ou cost dans le contrat.
- Round-trip P3-AC-010..013, P3-AC-022 sans fabrication de champs.
