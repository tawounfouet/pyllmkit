# PyLLMKit - M3 Inference Foundations Qualified - Proces-verbal GO/NO-GO

> **Date de decision technique :** 2026-11-05
> **Decision M3 : GO TECHNIQUE AVEC RESERVES** pour le **domaine d'inference hors ligne uniquement**
> **Decision versionnement / publication : NO-GO**, non autorisee, processus distinct
> **SHA de reference de la revue :** [`main@4900523f8999b7c42fb184d44a9ccc090e56f26a`](https://github.com/tawounfouet/pyllmkit/commit/4900523f8999b7c42fb184d44a9ccc090e56f26a)
> **CI qualifying ce SHA :** [GitHub Actions #42069101048](https://github.com/tawounfouet/pyllmkit/actions/runs/42069101048), `completed/success`, 3/3 versions Python
> **Portee et autorite :** revue technique assistee realisee sur instruction du proprietaire; **aucune APPROVED review GitHub tierce ni revue independante humaine revendiquee**
> **Version declaree :** `0.1.0a2` ; `0.1.0a3` non construite comme version releasable, non taguee, non publiee dans ce travail
> **Baselines :** M1/M2 qualifies, P3-G0..P3-G5 GO techniques avec reserves; revue M3 **independante**, non copie du verdict G5

## 1. Objet et definition du succes

La decision M3 porte strictement sur **Inference Foundations Qualified** tel que defini dans [le plan de Phase 3, §2.4 et §14](../03_PYLLMKIT_PHASE_3_IMPLEMENTATION_PLAN.md) : un consommateur sans cle API peut construire une Request, une Response normalisee et un Run, simuler ses transitions avec horloge injectee, serialiser et deserialiser les valeurs, et tester cette experience depuis une wheel ou un sdist isole.

**Hors champ du GO M3 :** requete reseau a un LLM reel, provider client, key management, streaming effectif, execution des tools, orchestration d'agents, facturation et production. La qualification d'un contrat de domaine n'est pas une attestation de securite, de disponibilite provider ou de readiness production.

## 2. Evidence revalidee apres la Phase 3

| Controle independant | Constat verifie | Preuve |
|---|---|---|
| Baseline SHA | `main@4900523f8999b7c42fb184d44a9ccc090e56f26a` | [Commit](https://github.com/tawounfouet/pyllmkit/commit/4900523f8999b7c42fb184d44a9ccc090e56f26a) |
| CI push/main | `completed / success` sur le SHA ci-dessus | [Actions #42069101048](https://github.com/tawounfouet/pyllmkit/actions/runs/42069101048) |
| Matrice | Python 3.11 / 3.12 / 3.13 : **3/3 jobs SUCCESS** | Jobs du workflow CI exact |
| Tests (Python 3.11) | **802 passed**, 0 failed (2.21s) | Logs `validate (3.11)` |
| Couverture globale branche incluse | **95 %**, 1345 statements / 52 misses, 458 branches / 45 partial | Logs `validate (3.11)` |
| Ruff | `All checks passed!` | Meme job |
| mypy strict | `Success: no issues found in 39 source files` | Meme job |
| Exemples | 01..12 executed offline | `.github/workflows/ci.yml` + CI success |
| Packaging | Wheel + sdist generes et installes en clean venv, full walkthrough 12 PASS | CI 3 versions |
| Runtime | `dependencies=[]`, pas de SDK provider obligatoire | `pyproject.toml` + test packaging |
| Versions de schemas | Model JSON v1, Interaction JSON v1, Inference JSON v1 | Tests d'API et de serialization |
| Controles de closeout | PR #34, quatre nouveaux tests de qualite docs | [PR #34](https://github.com/tawounfouet/pyllmkit/pull/34) + CI main |
| Tracabilite | P3-AC-001..030 tous couverts par une recette | [PHASE_3_TRACEABILITY.md](PHASE_3_TRACEABILITY.md) |

Ces 802 tests decrivent **la suite cumulative du depot**, non 802 tests propres a la Phase 3. La CI du commit d'archivage du present PV sera verifiee **apres** sa fusion et ajoutee a la PR sous forme d'attestation distincte.

## 3. Revue independante des onze criteres NO-GO obligatoires

La grille ci-dessous reprend **exactement les familles de refus** de [§14.1 du plan de Phase 3](../03_PYLLMKIT_PHASE_3_IMPLEMENTATION_PLAN.md), et les confronte a des preuves distinctes de la simple lecture du PV G5.

| # | Cause de NO-GO | Examen transversal et preuve | Resultat M3 |
|---|---|---|---|
| 1 | I/O ou SDK provider cache dans le Domain Core | `dependencies=[]`, tests architecture des domaines, imports wheel/sdist sans provider ni credentials, exemples offline | **NON CONSTATE** |
| 2 | Request/Run/Response fusionnes en objet mutable | Request et Response Value Objects immuables; Run Entity a ID stable et snapshots immuables, tests des invariants | **NON CONSTATE** |
| 3 | Defauts provider inventes ou parametres UNSUPPORTED perdus | GenerationConfig `None` distinct de `0.0`; snapshot de support explicite, `UNSUPPORTED` rejete et `UNKNOWN` non confirme | **NON CONSTATE** |
| 4 | `UNKNOWN` converti en NATIVE/STOP | Tests de `FinishReasonCode.UNKNOWN` et du rapport de compatibilite sans promotion arbitraire | **NON CONSTATE** |
| 5 | Usage manquante transformee en zero ou cout infere | `Usage` nullable/partielle, types exacts, aucun `Pricing` calcule par domaine, tests G2/G4 | **NON CONSTATE** |
| 6 | Run terminal reactivable ou Response d'autre ID attachee | Matrice a six etats, terminaux irreversibles, `response.run_id` corrige uniquement si identique, tests G3 | **NON CONSTATE** |
| 7 | JSON perd silencieusement champs/roles/ordre/parties | Clés v1 exhaustives, unknown fields/part kinds refuses, message order preserved, six runs round-trip, tests negatifs G4 | **NON CONSTATE** |
| 8 | Compatibilite Model v1/Interaction v1 rompue | Versions independantes, tests de regression M1/M2, correction `MappingProxyType` sans changer schema v1 | **NON CONSTATE** |
| 9 | Echec de CI bloquante, lint, mypy ou packaging sur SHA | [CI #42069101048](https://github.com/tawounfouet/pyllmkit/actions/runs/42069101048) SUCCESS, Python 3.11..3.13, 802 tests, 95 %, wheel/sdist | **NON CONSTATE** |
| 10 | Documentation promet provider ou release inexistante | README declare reponse synthetique et aucun provider; guides release signalent NO-GO; doc fitness tests | **NON CONSTATE** |
| 11 | ADR/preuves fabriquees ou liees a un autre SHA | ADR-014..021 dans Git, gates G0..G5 avec SHA, PR et CI distincts; G5 archive et PR #34 verifiees | **NON CONSTATE** |

**Portee de la conclusion :** ces causes de NO-GO ne sont **pas constatees dans le perimetre teste**. Un audit source/test ne garantit pas l'absence absolue de tout probleme futur ni de vulnerabilites de dependances tierces. Les risques exterieurs au domaine sont identifies sans les masquer.

## 4. Decomposition de la qualification par gates

| Gate | Verdict precedent | PV et qualification |
|---|---|---|
| P3-G0 - Architecture | GO avec reserves | [P3_G0_GATE_REVIEW.md](P3_G0_GATE_REVIEW.md), [CI #42029448967](https://github.com/tawounfouet/pyllmkit/actions/runs/42029448967) |
| P3-G1 - Request | GO technique avec reserves | [P3_G1_GATE_REVIEW.md](P3_G1_GATE_REVIEW.md), [CI #42036557565](https://github.com/tawounfouet/pyllmkit/actions/runs/42036557565) |
| P3-G2 - Response | GO technique avec reserves | [P3_G2_GATE_REVIEW.md](P3_G2_GATE_REVIEW.md), [CI #42039312011](https://github.com/tawounfouet/pyllmkit/actions/runs/42039312011) |
| P3-G3 - Run | GO technique avec reserves | [P3_G3_GATE_REVIEW.md](P3_G3_GATE_REVIEW.md), [CI #42044787119](https://github.com/tawounfouet/pyllmkit/actions/runs/42044787119) |
| P3-G4 - Codec & Quality | GO technique avec reserves | [P3_G4_GATE_REVIEW.md](P3_G4_GATE_REVIEW.md), [CI #42053906726](https://github.com/tawounfouet/pyllmkit/actions/runs/42053906726) |
| P3-G5 - Integration | GO technique avec reserves | [P3_G5_GATE_REVIEW.md](P3_G5_GATE_REVIEW.md), [CI #42059417894](https://github.com/tawounfouet/pyllmkit/actions/runs/42059417894) |

L'archivage du G5 lui-meme est couvert par [CI #42060508466](https://github.com/tawounfouet/pyllmkit/actions/runs/42060508466) sur `main@fc93200d...`. Le closeout des recommandations est integre par [PR #34](https://github.com/tawounfouet/pyllmkit/pull/34) et qualifie sur le SHA de reference M3 ci-dessus.

## 5. Registre des reserves examinees et arbitrage

| ID | Risque constate | Nature et effet sur decision |
|---|---|---|
| **M3-R01, gouvernance** | `main.protected=false`; `GET /rulesets=[]`; protection detaillee renvoie 403 pour le connecteur. [Issue #22](https://github.com/tawounfouet/pyllmkit/issues/22) **OPEN et assignee au proprietaire** | **Non bloquant pour un GO de domaine offline. Bloquant pour toute publication** jusqu'a preuve d'enforcement effectif |
| **M3-R02, revue tierce** | Pas de GitHub `APPROVED` review independante revendiquee | Reservation de gouvernance et release ; aucune validation tierce inventee |
| **M3-R03, parseur texte JSON** | `json.loads` standard peut conserver seulement la derniere cle dupliquee ; format mapping du domaine ne peut pas les detecter retroactivement | Specification future [Provider Boundary](../architecture/FUTURE_PROVIDER_BOUNDARY_CONTRACT.md), [issue #36](https://github.com/tawounfouet/pyllmkit/issues/36), non bloquant tant que hors scope |
| **M3-R04, release** | Source `0.1.0a2` seulement, pas de bump ou distribution autorisee | [Runbook release](../governance/RELEASE_0_1_0a3_POLICY_AND_RUNBOOK.md), [issue #35](https://github.com/tawounfouet/pyllmkit/issues/35), **RELEASE NO-GO** |
| **M3-R05, provider runtime** | Aucun provider SDK, execution distante ni streaming reel | Hors scope Phase 3 ; ne pas annoncer disponible |
| **M3-R06, securite et supply chain** | Pas de preuve d'une revue independante de la supply chain ou de la politique de publication | Verification de release distincte ; CI actuelle ne vaut pas certification de securite |

Ces reserves ne doivent pas etre effacees pour obtenir artificiellement un M3 GO. L'acceptation du risque est **limitee a la qualification technique du domaine hors ligne** et ne permet pas l'exploitation en production ni l'envoi de donnees a un provider.

## 6. Decision explicite et perimetre d'autorisation

| Decision | Verdict | Justification |
|---|---|---|
| **M3 - Inference Foundations Qualified (domain-only)** | **GO TECHNIQUE AVEC RESERVES** | 11 causes de NO-GO non constatees, G0..G5 qualifies, SHA exact et CI green, examples + wheel/sdist |
| Provider runtime, HTTP, streaming effectif, tools | **NON LIVRES / NON QUALIFIES** | Exclusions explicites, [issue #36](https://github.com/tawounfouet/pyllmkit/issues/36) |
| Gouvernance main pour release | **NO-GO** | Issue #22 ouverte ; protections non mises en place |
| Bump source vers `0.1.0a3` | **NON AUTORISE** | Decision de version candidate separee |
| Tag, GitHub Release, TestPyPI, PyPI | **NO-GO / AUCUNE PUBLICATION** | Prerequis governance, provenance artefact, reviewer et consentement release non satisfaits |

Le GO technique est rendu dans le cadre de la mission de **revue de M3** confiee a l'assistant. **Il ne simule pas une APPROVED review de GitHub par un humain independant**, ni une approbation de publication par le proprietaire. Les politiques de securite / branche restent hors d'acces en ecriture pour la connexion presente.

## 7. Suivi concret apres M3

1. [Issue #22](https://github.com/tawounfouet/pyllmkit/issues/22) - propriétaire GitHub : regler/activer `main` ruleset, PR requise, checks exacts, revue, zero bypass non approuve. Tester enforcement, attacher preuve et **seulement alors** cloturer.
2. [Issue #35](https://github.com/tawounfouet/pyllmkit/issues/35) - futur passage version `0.1.0a3` et decision release separee, hashes wheel/sdist, publication OIDC et rollback, jamais automatiquement.
3. [Issue #36](https://github.com/tawounfouet/pyllmkit/issues/36) - future ADR provider/application boundary sur parsing JSON texte, taille, secrets, erreur, retries, idempotence et SSRF.
4. [Convention d'apprentissage](../governance/PYKIT_DELIVERY_AND_LEARNING_LOOP.md) - conserver besoin -> invariants -> ADR -> code -> tests negatifs -> exemple -> CI PR -> CI main -> PV.
5. [Bilan P3](P3_POST_IMPLEMENTATION_REVIEW.md) - vue retrospective de la Phase 3, independante du present verdict.

## 8. Chaine de preuve et archivage

Ce PV qualifie le **commit d'integration deja construit** `main@4900523f8999b7c42fb184d44a9ccc090e56f26a` et [CI #42069101048](https://github.com/tawounfouet/pyllmkit/actions/runs/42069101048). Il est soumis dans une **PR documentaire distincte**. Son commit d'archive sera differente et devra avoir une **CI main propre** ; celle-ci sera attestee apres execution en commentaire de la PR pour eviter la circularite.

Le document ne cree pas de code provider et ne constitue aucune publication.

---

**VERDICT FINAL M3 : GO TECHNIQUE AVEC RESERVES, POUR LE DOMAINE HORS LIGNE.**
**VERDICT PUBLICATION 0.1.0a3 : NO-GO, NON AUTORISEE.**
