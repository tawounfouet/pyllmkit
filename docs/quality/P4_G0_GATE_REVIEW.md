# PyLLMKit - P4-G0 Architecture Ready - Proces-verbal GO

> **Date de decision :** 2026-11-05
> **Verdict : GO TECHNIQUE AVEC RESERVES** pour lancer L4.1 Tool Domain.
> **SHA qualifiant exact de main :** [b66e94e3bcfec9b84fc77fd5e2860612f55827eb](https://github.com/tawounfouet/pyllmkit/commit/b66e94e3bcfec9b84fc77fd5e2860612f55827eb).
> **CI main qualifiante :** [GitHub Actions #42079191595](https://github.com/tawounfouet/pyllmkit/actions/runs/42079191595), event=push, completed/success.
> **Autorite :** proprietaire de PyLLMKit (demande explicite du 5 novembre 2026); revue technique assistee, aucune review GitHub independante presentee comme acquise.
> **Publication : NO-GO** - decision distincte, issues #22 et #35 non resolues.

## 1. Objet et limites du verdict

Le gate P4-G0 statue sur les **contrats et arbitrages d'architecture**, pas sur du code P4 ou sur un M4 livre. Il autorise uniquement le demarrage de L4.1, sur une nouvelle branche et avec une PR propre. Aucun outil n'est executable dans le noyau; aucune API provider, streaming operationnel, release ou bump de version n'est autorise.

## 2. Chaine de preuve verifiee

| Controle | Resultat | Preuve |
|---|---|---|
| Baseline M3 | PASS | main initial 3d5ffc811c33ae6dabf392b2c7d24f7ec2a27dc6, M3_GATE_REVIEW |
| Approbation owner | PASS | [P4_G0_OWNER_ARCHITECTURE_APPROVAL.md](P4_G0_OWNER_ARCHITECTURE_APPROVAL.md) |
| Huit decisions | ACCEPTED | ADR-022..029, registre P4 |
| Revue contradictoire | PASS | [P4_G0_ARCHITECTURE_REVIEW.md](P4_G0_ARCHITECTURE_REVIEW.md) |
| PR architecture | MERGED | [PR #38](https://github.com/tawounfouet/pyllmkit/pull/38), squash sur main |
| CI branche P4-G0 | SUCCESS | Run #42079019478 et #42079009256, SHA 4da00861c8500f81e8a4c206ca47d91d1483dd09 |
| Commit qualifiant main | PASS | b66e94e3bcfec9b84fc77fd5e2860612f55827eb |
| CI push/main du SHA qualifiant | SUCCESS | [Run #42079191595](https://github.com/tawounfouet/pyllmkit/actions/runs/42079191595) |
| Python 3.11 | SUCCESS | Job 127427424417 |
| Python 3.12 | SUCCESS | Job 127427424250 |
| Python 3.13 | SUCCESS | Job 127427423737 |
| Tests Python 3.11 | **802 passed**, 0 fail | Logs job 127427424417 |
| Couverture branches Python 3.11 | **95 %** | 1345 statements, 52 misses; 458 branches, 45 partial |
| Ruff et mypy strict | PASS | Logs du meme job, aucun probleme |
| Exemples et packaging | SUCCESS | Workflow complet incluant wheel/sdist |
| Protection main | NON EFFECTIVE | API branche main protected=false, rulesets [], issue #22 |
| Revue GitHub tierce | ABSENTE | Pas de revue soumise sur PR #38 |
| Publication | INTERDITE | Issue #35, decision future distincte |

Les 802 tests sont la suite **cumulative M1-M3**, pas des tests P4. La CI ne prouve aucune implementation P4.

## 3. Decisions contractuelles et arbitrages

- **ADR-022 :** Tool descriptif, aucun executor ni credential.
- **ADR-023 :** ToolCallId explicite, correlation locale et au plus un resultat final.
- **ADR-024 :** profil de validation schema **P4-JSON-1** documente, borne et hors reseau.
- **ADR-025 :** JSON profondement immutable, raw/parsed/ABSENT distincts, VALID uniquement apres preuve.
- **ADR-026 :** ToolChoice AUTO/NONE/REQUIRED/SPECIFIC, capability UNKNOWN conservee.
- **ADR-027 :** formats Text/Json/Schema, validation explicite VALID/INVALID/UNKNOWN.
- **ADR-028 :** **Option B** : composition P4 separee, contrats et codecs M3 inchanges.
- **ADR-029 :** Tooling JSON v1 autonome; Inference JSON v2 differe si nouvelle ADR.

## 4. Reserves non bloquantes pour le seul demarrage L4.1

1. **Issue #22 :** main protected=false. La validation systematique par PR/CI est une discipline observee, pas une protection enforcee. Ne pas publier.
2. **Issue #35 :** absence d'approbation release 0.1.0a3/0.1.0a4. Ne pas bump/tag/releaser.
3. **Issue #36 :** la frontiere des futurs providers reste a approuver; ne pas introduire les SDK dans le domaine.
4. **Revue par pair :** aucune APPROVED review tierce; validation du proprietaire en conversation explicite et enregistree.

## 5. Decision et suite

**P4-G0 = GO TECHNIQUE AVEC RESERVES**, sur le SHA exact ci-dessus. Autoriser la branche `feat/p4-l41-tool-domain`, les objets ToolSchema/Tool/ToolChoice, les validateurs purs, des tests P4-AC-001..008, l'exemple 13 et la documentation.

P4-G1 reste **NON QUALIFIE** tant qu'une PR d'implementation, ses tests et sa CI sur le SHA de main n'ont pas ete verifies. M4 reste NON QUALIFIE.

## 6. Archivage

Le present PV est archive dans une PR documentaire **apres** verification du SHA qualifiant b66e94e3. La CI du commit d'archivage doit etre suivie separement, sans pretendre etre la preuve retrospective de b66e94e3.
