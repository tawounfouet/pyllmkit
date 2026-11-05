# PyLLMKit - P3-G0 Architecture Ready - Proces-verbal de qualification

> **Date de qualification :** 2026-11-05
> **Phase :** P3 - Inference Primitives
> **Version candidate visee :** `0.1.0a3` (non implementee, non publiee)
> **Gate :** P3-G0 - Architecture Ready
> **VERDICT : GO ARCHITECTURE AVEC RESERVES**
> **Nature :** qualification des contrats et de leur integration; aucun GO G1/M3, aucune publication.
> **Autorite :** proprietaire du projet (instruction explicite d'adopter, integrer, verifier main et rediger PV).
> **Revue :** revue technique documentaire assistee; **aucune GitHub APPROVED review tierce**.
> **SHA de qualification :** [`965311dbef527ad59222b7586f9c801bb713bead`](https://github.com/tawounfouet/pyllmkit/commit/965311dbef527ad59222b7586f9c801bb713bead)
> **CI de qualification sur `main` :** [GitHub Actions #42029448967](https://github.com/tawounfouet/pyllmkit/actions/runs/42029448967) - `push`, **completed / success**.
> **PR d'adoption integree :** [#19](https://github.com/tawounfouet/pyllmkit/pull/19) - merge squash par GitHub avec expected head SHA.
> **PV :** document archive sur PR distincte, afin de ne pas attribuer par anticipation une CI a son propre commit.

---

## 1. Objet du gate

P3-G0 verifie que les **contrats de domaine** des futures primitives d'inference sont suffisamment explicites, testes au niveau CI documentaire/non-regression M1/M2 et approuves pour permettre le lancement du lot L3.1. Il ne teste ni l'existence des classes Python a3, ni l'invocation d'un modele.

L'invariant fondateur reste :

```text
InferenceRequest (Value Object)
        !=
InferenceRun (Entity / Aggregate Root)
        !=
InferenceResponse (Value Object)
```

Les SDK providers, HTTP, routing, streaming operationnel et agents sont hors de la Phase 3 a3.

## 2. Chaine de preuves

| Controle | Resultat | Preuve |
|---|---|---|
| Baseline M2 identifiee | PASS | `main` initial `acd6dfb76d73c260ccca523cf904be44ec249288` ; M2 Gate Review |
| Revue contradictoire | PASS | [P3_G0_ARCHITECTURE_REVIEW](P3_G0_ARCHITECTURE_REVIEW.md) et constats F-01..04 |
| Adoption owner | PASS | [P3_G0_OWNER_ARCHITECTURE_APPROVAL](P3_G0_OWNER_ARCHITECTURE_APPROVAL.md), D-01..D-10 |
| ADR-014..020 | ACCEPTED | Fichiers ADR dans `docs/adr/`; contrats domain-first |
| ADR-021 | OPTION A ACCEPTED | Evaluateur pur de support sur snapshot caller; AC-007 REQUIRED |
| Perimetre acceptance | APPROVED FOR IMPLEMENTATION | P3-AC-001..030 restent des cibles de test, **aucun PASS a3 revendique** |
| Dette M2 | ISOLATED, OPEN | [Issue #20](https://github.com/tawounfouet/pyllmkit/issues/20), PIR2-01/02/03 |
| PR de preparation et adoption | MERGED | [#19](https://github.com/tawounfouet/pyllmkit/pull/19) |
| Branche qualifiante | MAIN EXACT SHA | `965311dbef527ad59222b7586f9c801bb713bead` |
| CI sur main | SUCCESS | [run #42029448967](https://github.com/tawounfouet/pyllmkit/actions/runs/42029448967) |
| Python 3.11 | SUCCESS | Job `validate (3.11)`, run #42029448967 |
| Python 3.12 | SUCCESS | Job `validate (3.12)`, run #42029448967 |
| Python 3.13 | SUCCESS | Job `validate (3.13)`, run #42029448967 |
| Protection main | NON VERIFIABLE PAR CONNECTEUR | Endpoint /branches/main/protection refuse HTTP 403, droits administration manquants |
| Rulesets accessibles | AUCUN RETOURNE | GET /repos/tawounfouet/pyllmkit/rulesets renvoie [] au moment du controle |
| Revue GitHub independante | AUCUNE | La PR #19 ne porte pas de reviews submittees, l'approbation est celle du proprietaire en conversation |
| Release / PyPI | NON AUTORISE | Aucune publication ne decoule de ce GO |

**Resultat exact** : la CI sur le SHA `965311...` est une run **push/main** achevee `success` et les trois jobs `validate` ont chacun `conclusion=success`. Le workflow `.github/workflows/ci.yml` execute lint Ruff, mypy, pytest --cov-branch, exemples offline, wheel et sdist, puis smoke tests propres. **Le total de tests 342 / 91 % appartient a la baseline M2**, et n'est pas presente ici comme un nouveau comptage independant de la CI G0.

## 3. Arbitrages adoptes

| ADR | Decision | Implication |
|---|---|---|
| 014 | Request/Response VOs, Run Entity avec identite | Architecture DDD et separation d'intention/execution |
| 015 | Trois Targets typed Model/Deployment/Endpoint | Aucune inference de provider ni resolution implicite |
| 016 | Floats stricts finis, entiers stricts, None != zero | A couvrir par tests L3.1 |
| 017 | TextOutput y compris vide, FinishReason natif/UNKNOWN | Pas d'execution Tool en a3 |
| 018 | Usage rapporte ou absent, sans total invente | Usage != Pricing != Cost |
| 019 | Snapshots Run immuables, RunId stable, finished_at terminal, Failure minimal | Six etats, tests de transitions L3.3 |
| 020 | Codec Inference JSON v1 strict, independent M1/M2 | Trois enveloppes et six etats, tests L3.4 |
| 021 | **Option A** : evaluator de compatibilite pur sur snapshot explicite | AC-007 **obligatoire**, sans InferencePort executable |

Le port d'invocation provider et le streaming reel ne sont pas inclus dans ce jalon; leur absence n'est pas une anomalie de G0.

## 4. Reservations et risques acceptes pour ce gate

### R-01 - Protection de `main` non attestee

Le connecteur retourne **403** sur l'endpoint de branch protection. Aucun ruleset accessible n'a ete retourne. **Ne pas conclure que main est protegee**, ni extrapoler que des politiques de revue ou de CI sont imposees. Risque de gouvernance maintenu comme priorite **avant toute publication**; a recontroler avec des droits administratifs adaptes.

### R-02 - Aucune review GitHub independante

L'autorisation a ete donnee explicitement en conversation par le proprietaire; elle est tracee dans le registre et les ADR. **Elle ne remplace pas une revue GitHub externe ni un audit de securite.**

### R-03 - Dette M2 ouverte

PIR2-01/02/03 sont isolees dans [issue #20](https://github.com/tawounfouet/pyllmkit/issues/20). Leur resolution est suivie en PR separee, sans alteration silencieuse de M1/M2. Les autres PIR2 restent dans le registre du bilan M2.

### R-04 - API et tests a3 non livres

Les 51 taches et 30 scenarios d'acceptation du plan sont la **cible des lots L3.1..L3.5**, non des travaux deja termines. Le GO G0 n'atteste **aucune** nouvelle primitive Python, aucun test a3, aucune performance, aucune communication reseau.

Ces reservations sont compatibles avec un **GO pour conception/implementation L3.1**, mais **pas** avec un GO de production, release ou M3.

## 5. Tableau de decision des gates

| Gate | Statut apres ce PV | Condition de progression |
|---|---|---|
| P3-G0 - Architecture Ready | **GO AVEC RESERVES** | Contrats adoptes, integres, CI main exacte SUCCESS |
| P3-G1 - Request Ready | NOT STARTED | L3.1, tests Target/Config/Request, AC-007 sur snapshot |
| P3-G2 - Response Ready | NOT STARTED | L3.2, FinishReason/Usage/Response |
| P3-G3 - Run Ready | NOT STARTED | L3.3, etats, horloge, identity et terminalite |
| P3-G4 - Quality Ready | NOT STARTED | L3.4, codec JSON v1 et non-regression M1/M2 |
| P3-G5 - Integration Ready | NOT STARTED | L3.5, packaging et CI finale |
| M3 - Inference Foundations Qualified | NOT STARTED | GO/NO-GO autonome et distinct |
| Publication `0.1.0a3` | NOT AUTHORIZED | Decision future explicite |

## 6. Prochaine action

**Autoriser l'ouverture du lot L3.1 - Inference Request Domain**, dans une branche de fonctionnalite et PR distinctes :

1. Implementer Target et identifiants typed selon ADR-015.
2. Implementer GenerationConfig stricte selon ADR-016.
3. Implementer InferenceRequest comme VO de chat ordonne et non vide selon ADR-014.
4. Implementer l'evaluator pur sur snapshot explicite pour AC-007 (ADR-021 option A), sans adapter fournisseur.
5. Ajouter tests positifs/negatifs et exemples offline; maintenir la regression M1/M2.
6. Qualifier P3-G1 **uniquement** apres preuve CI sur SHA exact integre.

## 7. Politique d'archivage

Ce PV constate le GO **sur le commit integration deja controle** `965311dbef...`. Son propre commit d'archivage modifie `main` et necessite une verification CI de ce **nouveau SHA**. Cette preuve peut etre jointe a la PR d'archivage comme commentaire horodate, afin d'eviter une chaine infinie de commits qui referencent leur propre validation. Aucun SHA futur n'est pre-qualifie ici.

---

**VERDICT FINAL : P3-G0 = GO POUR LES CONTRATS D'ARCHITECTURE, AVEC RESERVES EXPLICITES.**  
**L3.1 est autorise a demarrer. M3 et la publication restent non qualifies et non autorises.**
