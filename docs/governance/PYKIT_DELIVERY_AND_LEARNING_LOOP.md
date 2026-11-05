# PyKit - Cycle de conception, execution et apprentissage logiciel

> Date : 2026-11-05
> Statut : **convention de travail** applicable aux futures phases et packages Py*Kit, a adapter aux exigences propres de chaque projet.
> But : rendre chaque livrable **auditables, explicable, reproductible** et pedagogiquement exploitable.

## 1. Chaine de valeur

```text
Besoin -> Cas d'usage / exigences -> Modele et invariants
      -> ADR / arbitrages -> Architecture et contrats
      -> Implementation minimale -> Tests positifs ET negatifs
      -> Exemple copiable -> CI sur PR -> Revue
      -> Merge par SHA attendu -> CI sur main SHA exact
      -> PV de gate -> Revue jalon -> Release separee
```

## 2. Definition of Done par etape

| Etape | Livrable | Question d'apprentissage | Preuve requise |
|---|---|---|---|
| Besoin | Expression du besoin et contraintes | Quel probleme et quel acteur ? | Exigence source et exclusions |
| Domaine | Ubiquitous Language, VO/Entity, invariants | Pourquoi cet aggregate, quelles transitions ? | Tests de domain invalides |
| ADR | Alternatives, couts, compromis, decision | Pourquoi ce choix, qu'avons-nous refuse ? | ADR acceptee par owner |
| Architecture | Dependances, ports et adapters | Quelles frontieres SoC/DIP ? | Fitness tests, aucune fuite SDK |
| Code | Solution Python simple et idiomatique | Quel pattern, pourquoi SOLID/KISS ? | Source typée, erreurs explicites |
| Tests | Unit + acceptance + negatives + regression | Quel comportement refuse-t-on ? | Cas nommes et reproductibles |
| Exemple | Script offline execute en CI | Peut-on comprendre et copier ? | Exemple non fictif ou explicitement synthetique |
| PR | Difference petite et revue | Quels risques introduits ? | PR, checklists, review et tests |
| CI PR/main | Matrice, couverture branches, packaging | Quelle preuve est liee a quel SHA ? | URLs, SHA, 3/3 jobs |
| Gate | GO/NO-GO motive | Quelles limites restent ? | PV sur un SHA exact |
| Jalon | Revue transversale | Etait-ce la bonne abstraction ? | Bilan et registre de risques |
| Publication | Autorisation distincte | Comment retirer une version problematique ? | Runbook, hashes, provenance |

## 3. Distinction des actes

- **Propose :** architecture, documentation, recommandations non encore acceptees.
- **Implemente :** code/source presente sur une branche; pas une preuve de CI.
- **Teste sur PR :** CI associee au SHA de branche / merge-ref, non le SHA final `main`.
- **Integre :** commit/merge sur `main`, statut de CI a verifier separement.
- **Qualifie :** gate avec preuves liees au **SHA exact de main**, limites et reservations.
- **Publie :** tag/release/index verifies, via autorisation explicite et preuve de distribution.

Ne jamais ecrire `GO` si le gate n'est pas effectue, ni `published` si seul un wheel local existe.

## 4. Checklists reutilisables

### Avant une PR
- [ ] Exigences et exclusions identifiees.
- [ ] Invariants/alternatives/ADR traces.
- [ ] API publique versionnee et typage strict, erreurs normalisees.
- [ ] Tests positifs, negatifs et d'architecture.
- [ ] Exemple executable dans CI, docs avec chemins valides.
- [ ] Aucun secret, schema casse ou fonction provider non testee.

### Avant merge
- [ ] CI PR Ruff, mypy, pytest/branches, Python supportes et packaging SUCCESS.
- [ ] Review requise selon protections effectives, aucun APPROVED invente.
- [ ] PR HEAD exact verifie et merge sans force push.

### Apres merge
- [ ] Lire `main` SHA reel.
- [ ] Chercher GitHub Actions **sur ce SHA**, complet et SUCCESS pour toutes les versions.
- [ ] Produire PV sur preuves, puis archiver en PR documentaire.
- [ ] Verifier la CI sur le SHA de l'archive et commenter ce resultat pour eviter la circularite.

### Apres gate
- [ ] Bilan post-implementation, enseignements et dette.
- [ ] Mettre a jour roadmap, matrices, index.
- [ ] Ouvrir issues uniquement pour travaux restants clairement assignables.
- [ ] Revue du jalon entier avant choix d'une release.

## 5. Frontieres de responsabilite humain / compagnon IA

- Le compagnon IA peut **proposer, concevoir, implementer, verifier et documenter**.
- Les decisions sensibles (acceptation de risques, gouvernance des acces, credentials et publication) restent sous **autorite humaine explicite**.
- L'IA distingue les commandes executees des commandes proposees, les donnees verifiees des hypotheses, et les blocages réels.
- Un agent proactif n'est pas une autorite de release, et une CI verte ne represente ni une audit securite complet ni une revue humaine independante.

## 6. Registre de preuves minimum

Pour chaque gate ou PR conserver : date, base SHA, head SHA, merge SHA, PR URL, CI PR URL et etat, CI main URL et etat, nombres de tests et couverture relus sur logs, liste des ADR, decisions de risques, responsable de validation, absence de publication le cas echeant.

Les notes de conception peuvent etre riches, mais chaque affirmation de qualite doit etre **verifiable sur les artefacts**.

## 7. Adaptation au monde Py*Kit

Reprendre cette convention pour un nouveau Py*Kit seulement apres avoir defini : nature du domaine, mode de distribution, dependances inter-kits, exigences de securite, rythme de version et responsabilites des agents. Le squelette est reutilisable, **les invariants ne sont pas copiables sans analyse**.
