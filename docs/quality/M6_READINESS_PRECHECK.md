# PyLLMKit - M6 Registry & Discovery: précheck historique avant intégration

- **Document historique** : état antérieur à la fusion des PR #59..#66. Voir la qualification actualisée `PHASE_6_TRACEABILITY.md`, les PV `P6_G0_GATE_REVIEW.md` à `P6_G7_GATE_REVIEW.md`, puis la revue finale M6.
- Audit initial : 2026-11-05
- Baseline main vérifiée : `19cc1c9e1d5598711890ddc3e14f1da94c79ce70`, `protected=false`.
- Version source : `0.1.0a2`. Objectif `0.1.0b2` non publié et non autorisé.
- Périmètre : P6-G0 architecture et L6.1..L6.7, registre et découverte **hors réseau**.
- Verdict : **CANDIDATS TECHNIQUEMENT QUALIFIÉS SUR LEURS BRANCHES / NO-GO D'INTÉGRATION M6 À CE STADE**.

## Preuves GitHub consultées

| Gate candidat | PR | SHA head (abrégé) | CI push branche observée | État d'intégration |
|---|---|---|---|---|
| P6-G0 architecture | #59 | `62e2bced` | #42111176534 SUCCESS | Ouverte, non fusionnée |
| P6-G1 L6.1 | #60 | `cd4f1f46` | #42111495257 SUCCESS | Brouillon non fusionné |
| P6-G2 L6.2 | #61 | `ee014e68` | #42112968831 SUCCESS | Brouillon non fusionné |
| P6-G3 L6.3 | #62 | `717cb90d` | #42113796257 SUCCESS | Brouillon non fusionné |
| P6-G4 L6.4 | #63 | `0cee303b` | #42115352505 SUCCESS | Brouillon non fusionné |
| P6-G5 L6.5 | #64 | `48791e14` | #42116701724 SUCCESS | Brouillon non fusionné |
| P6-G6 L6.6 | #65 | `6f4c2323` | #42119596965 SUCCESS | Brouillon non fusionné |
| P6-G7 L6.7 | #66 | `4895152a` | #42120853512 SUCCESS | Brouillon non fusionné au moment de ce précheck |

Les CI ci-dessus sont des vérifications sur branches de travail, **pas des preuves de CI post-merge sur main**. Pour la candidature L6.7 : 1 188 tests cumulatifs, couverture avec branches `pyllmkit.domain` 96,61 %, 3/3 Python 3.11..3.13, Ruff/mypy et distributions wheel/sdist réussis au SHA `4895152a`. Ces preuves de CI sont historiques au moment de la rédaction ; toute nouvelle modification de la PR exige un nouveau contrôle au SHA final.

## Constats de gouvernance

- Les huit PR #59..#66 sont ouvertes et non fusionnées, la PR #59 n'étant pas un brouillon.
- Le connecteur GitHub renvoie **aucune review enregistrée** sur chacune de ces huit PR. Aucune approbation tierce ne peut être revendiquée.
- Le branchement main n'est pas protégé. La réussite des tests ne prouve pas une enforcement de reviews ni de checks obligatoires. Issue #22.
- Publication 0.1.0b2 non autorisée. Issue #35. Aucun tag ni release dans ce chantier.
- ProviderCatalog descriptif != AdapterRegistry exécutable ; services réseau et SDK hors P6. Issue #36.
- La matrice des 56 cas est traçable aux tests, mais sa formulation est issue de leurs noms ; le plan détaillé original est une référence distincte à rapprocher avant signature finale.

## Réserves techniques documentées

- L'atomicité L6.6 est une substitution de root snapshot en mémoire avec révision optimiste, pour un usage séquentiel. Pas de garantie transactionnelle multi-processus, cross-thread ou distribuée.
- `StaticDiscoverySource` accepte des objets déjà typés ; aucun parsing de fichiers arbitraires ni découverte en temps réel.
- Les capacités UNKNOWN, UNSUPPORTED, PARTIAL, EMULATED et NATIVE restent distinctes et les limites restrictives sont calculées à partir de preuves de déclarations, non de mesures provider.
- Une disponibilité AVAILABLE déclarée n'est pas un healthcheck. Aucun appel de modèle ni endpoint physique n'est qualifié.
- `repr=False` et absence de raw dans les diagnostics réduisent le risque d'affichage involontaire mais ne constituent pas une politique complète de confidentialité.

## Checklist avant décision finale M6

1. Obtenir l'approbation de conception ADR-039..048 et documenter les désaccords éventuels.
2. Intégrer PR #59 à main, vérifier CI push/main sur SHA exact et établir le PV P6-G0.
3. Réorienter/rebaser les PR empilées avec prudence ; intégrer successivement #60..#66, chaque gate nécessitant sa propre CI post-merge et un PV documenté.
4. Vérifier tests M1-M6, couverture >=95 %, Ruff, mypy strict, Python 3.11/3.12/3.13, examples 01..28, wheel/sdist, non-régression des codecs.
5. Faire une revue M6 GO/NO-GO distincte de P6-G7, avec audit du SHA main de clôture et contrôle des risques.
6. Traiter protection effective main, revue indépendante et gouvernance release ; une décision technique n'autorise pas automatiquement la publication.

**Décision actuelle : NO-GO de clôture M6 et NO-GO de release.** Le code de Phase 6 peut être revu et testé sur ses branches, sans pouvoir être présenté comme fusionné ou publié.
