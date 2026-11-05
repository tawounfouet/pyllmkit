# PyLLMKit - P3-G0 Architecture Review

> **Addendum apres revue (2026-11-05) :** Le proprietaire a ensuite autorise explicitement l'**adoption ADR-014..021** et choisi les **float stricts** ainsi que **l'option A ADR-021**. Voir [P3_G0_OWNER_ARCHITECTURE_APPROVAL.md](P3_G0_OWNER_ARCHITECTURE_APPROVAL.md). Les constats et le verdict ci-dessous sont l'etat de la **revue contradictoire pre-approbation**, conserves historiquement. Le GO formel reste conditionne a l'integration et la CI exacte sur main.


> **Date :** 2026-11-05
> **Phase / version candidate :** P3-BOOT / 0.1.0a3 - Inference Primitives
> **Revue :** contradictoire, technique, documentaire et pedagogique
> **Autorite de revue :** analyse assistee par Pythos / ChatGPT a la demande du proprietaire
> **Autorite d'adoption :** proprietaire du projet; aucune approbation des ADR attestee a cette etape
> **Verdict :** **TECHNICAL DESIGN RECOMMENDATION = CONDITIONAL GO**; **P3-G0 FORMAL = PENDING / NO-GO tant que les preuves et decisions obligatoires manquent**.
> **Release / publication :** NON AUTORISEE, NON REALISEE.
> **PR :** https://github.com/tawounfouet/pyllmkit/pull/19 (draft, pas de merge).

---

## 0. Synthese executif

La Phase 3 peut etre concue sans SDK LLM ni appel provider, en conservant la distinction fondamentale **InferenceRequest (Value Object) != InferenceRun (Aggregate Root) != InferenceResponse (Value Object)**. Le plan P3 et les documents fondateurs supportent ce positionnement. Les huit ADR proposees sont globalement compatibles avec cette architecture.

La revue a trouve **quatre fragilites de conception a traiter avant la qualification G0** :

1. **F-01 (majeur, traite dans la proposition)** : un run FAILED ne disposait pas d'un Failure P0 suffisamment explicite pour le contrat et la relecture JSON; une fin CANCELLED ne precisait pas la politique de timestamp.
2. **F-02 (majeur, traite dans la proposition)** : l'egalite par identite de snapshots immuables peut masquer une transition si les tests se contentent de comparer les instances. L'ADR-019 exige des assertions explicites d'etat et dates.
3. **F-03 (majeur, traite par un arbitrage ouvert)** : P3-AC-007 attend une evaluation de support de parametres, alors qu'ADR-021 peut differer le port et l'evaluator. Un test non implemente ne doit jamais etre revendique PASS.
4. **F-04 (moyen, arbitrage ouvert)** : le type float exact en GenerationConfig interdit l'entier 0 pour temperature malgre une intention numerique coherente. L'approche est defendable mais doit etre choisie consciemment.

**Aucun de ces constats ne remet en cause la qualification M2.** Les risques a3 ont ete precises dans les ADR revisees; le proprietaire doit encore trancher et accepter le contrat.

## 1. Preuves et methode

- **Baseline M2** : main acd6dfb76d73c260ccca523cf904be44ec249288; bilan M2 GO technique, 342 tests, 91 % de couverture, Python 3.11/3.12/3.13, CI finale M2 https://github.com/tawounfouet/pyllmkit/actions/runs/42016493260 selon le PIR Phase 2.
- **Revue documentaire** : expression du besoin 00, exigences 01, vision 02, architecture 03, domaine 04/05/06, invariants 07, commandes 08, evenements 09, plan P3, PIR M2, ADR 014..021 de PR #19.
- **Preuve CI avant revision** : commit 4ca6d76584499e59a9f94f5f000e935458381fb6; run https://github.com/tawounfouet/pyllmkit/actions/runs/42024327072 **SUCCESS** sur trois jobs Python. Cette CI **ne vaut pas qualification des commits de revue posterieurs**.
- **Controle des illustrations JSON** : les trois blocs JSON Request, Response et Run de l'ADR-020 revisee ont ete parsés avec JSON.parse; les cles, object_type et l'association run_id de l'exemple complet sont coherents. **Ce n'est pas un test du codec Python a3**, inexistant a ce stade.
- Aucune revision humaine independante, aucun benchmarking provider et aucune attestation de production ne sont revendiques.
- Le statut de protection de main signale non protege par le PIR M2 reste un risque de gouvernance, pas une preuve d'absence de fonctionnalite.

## 2. Decision technique par ADR

| ADR | Evaluation de la revue | Recommandation | Statut de decision |
|---|---|---|---|
| 014 - Request / Run / Response | **Favorable** | Maintenir Request/Response VO, Run Aggregate, request chat 1..* | PROPOSED |
| 015 - Target | **Favorable** | Trois variantes Model/Deployment/Endpoint; identites opaques distinctes, aucune resolution | PROPOSED |
| 016 - GenerationConfig | **Favorable avec arbitrage** | Validation structurelle stricte, None distinct de zero; decider float exact vs nombres reels | REVISED / PROPOSED |
| 017 - Output et FinishReason | **Favorable** | TextOutput meme vide, motif natif facultatif, UNKNOWN ≠ absent, aucun tool operationnel | PROPOSED |
| 018 - Usage | **Favorable** | Compteurs observes optionnels, total non fabrique, aucune deduction Pricing/Cost | PROPOSED |
| 019 - Run Lifecycle | **Favorable apres revision** | Snapshots immuables, equality identity-based, InferenceFailure, finished_at terminal et six etats | REVISED / PROPOSED |
| 020 - JSON Inference v1 | **Favorable apres revision** | Three schema envelopes, full Interaction JSON v1, six Run states, datetime aware, validation stricte | REVISED / PROPOSED |
| 021 - Port et compatibilite | **Decision ouverte** | Port public differe; option A evaluator pur avec snapshot (conseillee), ou option B AC-007 DEFERRED | REVISED / PROPOSED |

Aucune ADR ne passe de PROPOSED a ACCEPTED par la seule presente revue. Les decisions de conception recommandees ne sont pas encore des contrats publics normatifs.

## 3. Frontieres DDD et dependances

~~~text
          M1 Model            M2 Interaction
             |                      |
             +----------+-----------+
                        v
                 InferenceRequest
                 (immutable VO)
                        |
                     * runs
                        v
                   InferenceRun
                 (Aggregate Root)
                        |
                        v
                 InferenceResponse
                 (immutable VO)
                   |     |     |
                Output Finish  Usage?
~~~

- Aucun Provider SDK, Client HTTP, Endpoint concret, Agent Runtime, Workflow ou Storage dans le core.
- Aucun registry ni changement de Model JSON v1 / Interaction JSON v1.
- Message != Request; Request != Run != Response; Usage != Pricing != Cost.
- Les identites Model, Deployment, Endpoint sont distinctes; target ne prouve ni availability ni capabilities effectives.
- Les extensions tools, structured output, streaming operationnel et adapters sont maintenues hors a3.

## 4. Decisions d'architecture a confirmer explicitement

| ID | Decision proposee | Justification |
|---|---|---|
| D-01 | Trois variantes de Target; identifiants opaques non resolus | INF-008, separation Serving |
| D-02 | Request chat P0 non vide (1..* Message), mais domaine futur non contraint globalement | Plan 4.2 et INT-001..003 |
| D-03 | Snapshots Run immuables, equality par RunId, comparisons d'etat separees | DDD identity + testabilite |
| D-04 | Failure minimal code-only, annulation code optionnel et finished_at pour tous terminaux | FAILED/CANCELLED serialisables |
| D-05 | GenerationConfig None pour non specifie; **choisir** types float stricts | Explicit over Implicit vs ergonomie |
| D-06 | FinishReason absent None, UNKNOWN si motif inconnu; TextOutput vide permis | Unknown Must Remain Unknown |
| D-07 | Usage optionnel; total_tokens non calcule implicitement | USG-002/003 et heterogeneite |
| D-08 | Inference JSON v1 : 3 enveloppes, null explicites, snapshots a six etats | Round-trip, version independante |
| D-09 | ADR-021 option A : evaluator pur sur snapshot explicite pour AC-007, sans InferencePort | Respecter cas d'acceptation sans faux provider |
| D-10 | Events documentes uniquement; pas d'event bus, streaming ni execution distante | YAGNI et boundaries |

**Attention :** les D-01..D-10 sont des recommandations, et non un proces-verbal d'approbation du proprietaire.

## 5. Traceabilite et tests

| Lot | Preuve requise apres G0 | Points de vigilance |
|---|---|---|
| L3.1 / G1 | Targets + Config + Request; types, ordre, no-I/O; AC-001..006 | AC-007 conditionnel a D-09 |
| L3.2 / G2 | TextOutput + FinishReason + Usage + Response; AC-008..013 | None/UNKNOWN/0/texte vide |
| L3.3 / G3 | Six etats + dates + RunId + Failure; AC-014..020/029 | Interdictions terminales, identity != snapshot state |
| L3.4 / G4 | JSON v1 Round-trips, schemas stricts, negatives, M1/M2 regression; AC-021..028 | JSON duplicate keys restent frontiere parser |
| L3.5 / G5 | wheel, sdist, README, examples offline, CI main; AC-026/030 | Aucun publish sans decision distincte |

Les **30 cas P3-AC du plan sont proposes**, pas encore executes. Si l'option B de D-09 est retenue, **P3-AC-007 est DEFERRED**, et aucun rapport M3 ne doit annoncer 30/30 PASS.

## 6. Dette M2 isolee et securite

Issue [#20](https://github.com/tawounfouet/pyllmkit/issues/20) ouverte pour **PIR2-01..03** :
- en-tetes d'ADR M2 historiques non requalifies ;
- exemple README avec newlines litteraux ;
- contrat Mapping annonce, dict runtime uniquement.

Ces points sont **ISOLATED / OPEN, pas corriges**. L'issue doit etre suivie avant G1/G5 selon la nature du correctif; elle ne doit pas masquer un test de regression casse. Les autres PIR2-04..13 restent dans le registre du PIR et doivent etre surveilles selon leurs dependances, notamment SSRF avant fetch reseau, redaction avant logs, protection de main avant release.

## 7. Critere formel GO / NO-GO

| Condition | Statut au moment de la revue |
|---|---|
| Baseline M2 identifiee et sourcée | OUI |
| ADR-014..021 ecrites et contradictoirement revues | OUI |
| Revisions F-01 et F-02 documentees | OUI, **proposees** |
| F-03 compatibilite AC-007 tranche | NON |
| F-04 types float arbitre | NON |
| Toutes ADR adoptees par le proprietaire | NON |
| Dette M2 suivie | OUI, issue #20, **non resolue** |
| PR revue avec CI sur le SHA final | A VERIFIER apres les revisions |
| Integration main et CI sur SHA exact | NON (PR draft, non fusionnee) |
| Autorisation de release | NON |

**Verdict : favorable a la validation des contrats revisees sous reserve d'arbitrage; G0 formel reste PENDING / NO-GO.** Ne pas annoncer G0 GO avant (1) decisions explicites du proprietaire, (2) integration volontaire, (3) preuves CI sur main et (4) proces-verbal gate avec SHA et eventuelles reserves.

## 8. Actions suivantes

1. Proprietaire : adopter/reviser ADR-014..020; choisir ADR-021 option A ou B; valider D-01..D-10.
2. Suite a la decision : ajuster signatures, fixtures et matrice P3-AC sans requalifier retroactivement les exigences fondateurs.
3. Traiter l'issue #20 sur PR separee, avec tests cibles.
4. Controler les nouveaux commits de PR #19 et, apres decision explicite de merge, archiver la CI sur le SHA exact de main.
5. Rediger le proces-verbal P3-G0 seulement apres adoption et integration; ne lancer L3.1 que lorsque le gate est decide.

---

**Le present document est une revue d'architecture proposee, pas une implementation, pas un GO M3 et pas une autorisation de publication.**
