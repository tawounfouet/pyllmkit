# PyLLMKit - Politique de versionnement et procedure de release 0.1.0a3

> Date : 2026-11-05
> Statut : **POLITIQUE PROPOSEE, AUCUNE EXECUTION DE RELEASE AUTORISEE**.
> Baseline source : `0.1.0a2`, `pyproject.toml`. Jalon M3 et release sont **deux autorisations distinctes**.

## 1. Autorites de decision

| Transition | Autorisation | Preuve necessaire |
|---|---|---|
| Source apres P3 | P3-G0..G5 GO techniques avec reserves | PV de gates, CI SHA main |
| **M3 GO/NO-GO** | Revue technique specifique et PV `M3_GATE_REVIEW.md` | CI, invariants, risques et limites |
| Passage `0.1.0a2` -> `0.1.0a3` | **Decision de version candidate** distincte | PR de version et changelog, CI SHA main |
| Release GitHub/tag | **Decision de publication** distincte | CI, governance #22, approbation responsable |
| PyPI/TestPyPI | **Decision de distribution** explicite | hash d'artefacts, authentication OIDC/publisher, procedure de rollback |

Un `M3 GO` ne lance **aucune** de ces etapes automatiquement.

## 2. Prerequis de release (hard stop)

- M3 GO enregistre sur SHA exact, PR archivee, et CI main post-archivage SUCCESS sur trois versions Python.
- [Issue #22](https://github.com/tawounfouet/pyllmkit/issues/22) **CLOSED avec preuve d'enforcement** et politique de review approuvee; pas de waiver implicite.
- Aucune erreur Ruff, mypy strict, pytest, negative tests, exemple offline, wheel ou sdist.
- Inventaire des dependances et licence MIT, `py.typed`, README/changelog/release notes concordants.
- Versions Model/Interaction/Inference JSON v1 independantes et compatibilite tracee.
- Provenance des artefacts liee au **commit exact du tag**; SHA256 et inspection contenus.
- Secret scanning et eventuels audits de securite necessaires documentes, notamment review du pipeline de publication.
- Validation du responsable projet pour bump, tag, release et PyPI. La presence d'une authentification ne remplace pas l'autorisation.

## 3. Procedure future de version candidate (non executee)

1. Creer une branche `release/0.1.0a3-candidate` depuis le SHA main **qualifie et protege**.
2. Changer `pyproject.toml`, `src/pyllmkit/__init__.py` si necessaire, les tests actuellement ancres sur `0.1.0a2`, CHANGELOG/README et guides.
3. Mettre a jour les tests qui verifient volontairement `0.1.0a2` (ne pas supprimer le garde-fou sans remplacement).
4. CI de PR : Python 3.11/3.12/3.13, coverage, Ruff, mypy strict, examples et wheel/sdist.
5. Review independante et merge PR apres required checks et preuve du ruleset.
6. Verifier CI du **nouveau SHA main**, sans supposer que le SHA PR reste le meme apres squash.

## 4. Procedure de construction et verification d'artefacts

Exemple **documentaire et manuel**, a effectuer dans un environnement propre a partir du commit **approuve** :

```bash
python -m venv .venv-release
. .venv-release/bin/activate
python -m pip install --upgrade pip
python -m pip install build twine
rm -rf dist/ build/
python -m build
python -m twine check dist/*
sha256sum dist/*
python -m zipfile -l dist/*.whl
tar -tzf dist/*.tar.gz
```

Avant de decider la distribution, construire les deux artefacts **du meme SHA** et verifier qu'ils contiennent les packages attendus, la licence, README et `py.typed`, sans `.env`, tokens ou fichiers privés. L'installation isolee doit fonctionner sans SDK fournisseur. Archiver le commit SHA, le job/workflow run, la version normalisee et les hashes SHA256 dans les notes de release.

`python -m build` et `twine check` n'impliquent **aucun upload**.

## 5. Version, tag, GitHub Release et publication

Seulement **apres autorisation explicite** et revues validees :
1. Choisir un tag de version non ambigu (`v0.1.0a3`), lie au SHA d'un commit qualifie; exiger un tag signe si la politique projet le permet.
2. Creer les release notes : scope réel, API, exigences Python, compatibilite M1/M2, limites sans provider et risques acceptes.
3. Joindre wheel/sdist et leurs hashes a la release GitHub ; verifier qu'ils proviennent du tag et non d'une branche mutable.
4. Pour TestPyPI/PyPI, privilegier **Trusted Publishing OIDC** avec environnement restreint, droits minimaux et approbation manuelle; ne pas introduire de token PyPI dans le depot.
5. Verifier installation depuis l'index vise dans un environnement isole et test imports offline.
6. Archiver les liens vers la distribution, les attestations disponibles et les logs des checks.

**Aucune de ces etapes n'est lancee dans le chantier M3.**

## 6. Strategie de rollback, retrait et incident

Les versions publiees sur PyPI ne sont **pas ecrasables** sous le meme numero. Pour un defaut :
- Arreter toute nouvelle publication/promotion, enregistrer un incident et identifier le tag/SHA/artefacts touches.
- Selon gravite et politique de l'index, **yank** (marquer comme deconseillee) la version affectee, avec decision documentee. Le yank ne desinstalle pas ce qui existe.
- Preparer une nouvelle version corrective avec **un nouveau numero de version**, CI et revue completes; ne pas reutiliser `0.1.0a3`.
- Publier une note de correction ou de securite et des consignes pour consommateurs.
- Si une GitHub Release est incorrecte, annoter/suspendre sa promotion et conserver la preuve historique; eviter d'effacer des artefacts sans proces d'incident.

## 7. Checklist de consentement avant toute publication

- [ ] M3 GO/NO-GO PV valide
- [ ] #22 gouvernance main CLOSED avec enforcement
- [ ] Approbation review independante constatable
- [ ] PR version candidate et CI main SHA vertes
- [ ] Metadata 0.1.0a3 coherente et tests adaptes
- [ ] Artefacts wheel/sdist inspectes + hashes conserves
- [ ] Notes de version et limites approuvees
- [ ] Proprietaire release donne accord explicite pour chaque canal
- [ ] Plan incident / rollback documente
- [ ] Aucune credentielle de publication en clair

**Etat actuel : aucune autorisation de version bump, tag, GitHub Release ou upload.**
