# PyLLMKit - P3-G4 Inference JSON Codec & Quality - Proces-verbal de qualification

> **Date :** 2026-11-05
> **Phase :** P3 - Inference Primitives, candidate future `0.1.0a3`
> **Gate :** P3-G4 - Inference JSON Codec & Quality
> **VERDICT : GO TECHNIQUE AVEC RESERVES**
> **Autorite :** ADR-020 ACCEPTED et revue des preuves de CI sur le SHA integre
> **PR d'implementation :** [#29](https://github.com/tawounfouet/pyllmkit/pull/29)
> **Main qualifiant :** [`d72b1ce82a4a34c62888ad48b50bcf07537f83d1`](https://github.com/tawounfouet/pyllmkit/commit/d72b1ce82a4a34c62888ad48b50bcf07537f83d1)
> **CI push/main :** [GitHub Actions #42053906726](https://github.com/tawounfouet/pyllmkit/actions/runs/42053906726), `completed / success`, Python 3.11/3.12/3.13 : 3/3 SUCCESS
> **Version de package :** `0.1.0a2`, jamais publiee par cette transition
> **Publication `0.1.0a3` :** NON AUTORISEE

## 1. Decision de gate

Le codec Inference JSON v1, independant des codecs Model v1 et Interaction v1, est implemente et integre. La preuve de qualification G4 inclut la CI sur le SHA exact de `main` apres squash merge, avec tests de round-trip, negatives schemas, invariants des six etats, non-regression, imports et packaging.

**P3-G4 : GO technique avec reserves.** Cette decision autorise le chantier **L3.5 - Integration & Packaging**, mais ne vaut ni M3 GO ni approbation de release/production.

## 2. Perimetre et livrables

| Objet | Contrat |
|---|---|
| `INFERENCE_SCHEMA_VERSION = 1` | Espace de version distinct de Model v1 et Interaction v1 |
| `request_to_dict` / `request_from_dict` | Envelope `inference_request`, Target, messages Interaction v1, GenerationConfig |
| `response_to_dict` / `response_from_dict` | Envelope `inference_response`, TextOutput, FinishReason native/nullable, Usage |
| `run_to_dict` / `run_from_dict` | Envelope `inference_run` et six snapshots cohérents via constructeur Run |
| `docs/api/inference-json-v1.md` | Schema exact, nulls, timestamps et limitations parser |
| `examples/11_round_trip_inference_json.py` | Demo Request/Response/Run hors ligne |
| `tests/acceptance/test_p3_l34_inference_json_v1.py` | Scenarios P3-AC-021..028, six etats en JSON |
| `tests/unit/domain/inference/test_serialization_strict.py` | Negatives exhaustives et invariants de reconstitution |
| `tests/architecture/test_p3_l31_domain_boundaries.py` | Fitness domain no-SDK et module serialization reconnu |
| CI ` .github/workflows/ci.yml ` | Exemple 11, import/smoke codec depuis wheel et sdist propres |

Les nouvelles fonctions manipulent des **mappings JSON-compatibles**, non une API HTTP et non un protocole provider.

## 3. Matrice d'acceptation et preuves

| Cas | Description | Verdict |
|---|---|---|
| P3-AC-021 | Request -> dict -> JSON -> Request, contenus et ordre intacts | PASS |
| P3-AC-022 | Response -> dict -> JSON -> Response, Usage et FinishReason conserves | PASS |
| P3-AC-023 | Versions et champs inconnus refusés | PASS |
| P3-AC-024 | Model JSON v1 et Interaction JSON v1 inchanges | PASS, suite de non-regression + controles |
| P3-AC-025 | Construire/serialiser sans I/O reseau ou credentials | PASS, tests offline et exemple |
| P3-AC-026 | Imports root/subpackage depuis wheel/sdist isoles | PASS, smoke dans CI |
| P3-AC-027 | Pas de fuite de secret URI dans les erreurs | PASS, tests de non-divulgation |
| P3-AC-028 | ContentPart inconnue dans Interaction v1 emboite | PASS, rejet fail-closed |
| Complement | Six etats Run dans JSON roundtrip | PASS |
| Complement | Snapshots impossibles / horloges incoherentes / RunId mismatch | PASS |

Les 8 cas P3-AC-021..028 sont dans les tests dedies. Le numero 024 vise **une non-regression de comportement** et non une nouvelle version Model ou Interaction. Aucun changement silencieux de codec historique n'est revendique.

## 4. Preuves de CI exactes

| Controle | Resultat |
|---|---|
| Head final PR #29 | `9a97ac175692e48e912662c71c077de49643a2f1` |
| CI PR | [#42053634804](https://github.com/tawounfouet/pyllmkit/actions/runs/42053634804) : SUCCESS 3/3 |
| SHA main squash | `d72b1ce82a4a34c62888ad48b50bcf07537f83d1` |
| CI main | [#42053906726](https://github.com/tawounfouet/pyllmkit/actions/runs/42053906726) : completed / success |
| Python 3.11 | validate (3.11) SUCCESS |
| Python 3.12 | validate (3.12) SUCCESS |
| Python 3.13 | validate (3.13) SUCCESS |
| Pytest Python 3.11 | **779 passed** (2.94s) |
| Couverture globale avec branches | **95 %** : 1345 statements, 52 misses, 458 branches, 45 partial |
| Ruff | All checks passed |
| mypy | Success: no issues found in 39 source files |
| Offline examples | 01..11 PASS |
| Wheel/sdist et imports codecs dans environnements propres | PASS |
| Regression M1/M2/G1-G3 | PASS dans suite globale |

Baseline P3-G3 : **679 tests / 94 % coverage**. P3-G4 : **779 tests / 95 % coverage**. Il s'agit de la taille totale de la suite et non de 779 nouveaux tests.

## 5. Invariants seriels contractuels

1. L'enveloppe `schema_version=1` est un **int exact**, pas True. `object_type` est une valeur exacte, distincte pour Request/Response/Run.
2. Toute cle canonique est presente, y compris celles dont la valeur est `null`. Champs extras et cles manquantes sont refuses a tous les niveaux du codec.
3. Les messages imbriques sont des **enveloppes Interaction JSON v1 completes**, sans perte de l'ordre ni des repetitions des TextContent/ImageContent; aucune lecture de media.
4. Target `model`/`deployment`/`endpoint` conserve sa valeur opaque, sans resolver ni validation DNS/HTTP.
5. GenerationConfig conserve `None` / `0.0` / `[]` et les numeric stricts; NaN, Inf, int a la place de float et bool-as-int refuses.
6. Response conserve FinishReason UNKNOWN + native, ou `null` distinct, et Usage partiel sans total invente; pas de Pricing ni Cost.
7. Six etats Run tous lisibles : CREATED, RUNNING, STREAMING, COMPLETED, FAILED, CANCELLED. `run_from_dict` reutilise le constructeur Run pour rejet des payloads impossibles et RunId ne correspondant pas a response.
8. Horodatages timezone-aware ISO 8601, convertis en UTC a l'ecriture et en datetime aware UTC a la lecture. Pas de timestamp ajoute par le codec.
9. Echec de validation par `DomainValidationError` sans recopier le prompt, la valeur native d'URL, l'URI de media ou un secret dans le message d'erreur.
10. Le codec ne comporte **aucun client reseau**, flux operationnel, parser HTTP, fallback provider, retry ou event publisher.

## 6. Limites et reserves

- **R-01, parseur JSON texte :** `json.loads` standard peut perdre les **cles dupliquees** avant la reception du dict. ADR-020 attribue explicitement cette politique au caller : un parseur JSON strict au futur boundary HTTP devra verifier `object_pairs_hook` ou equivalent. Le codec ne promet pas de detecter les doublons deja perdus. De meme les extensions non standard `NaN/Infinity` du parser doivent etre filtrees par l'integration.
- **R-02, Mapping :** signature `Mapping[str, object]` mais le decoder Interaction v1 accepte des `dict` concrets. Dette PIR2-03 [issue #20](https://github.com/tawounfouet/pyllmkit/issues/20), toujours ouverte. L3.4 ne modifie pas le comportement historique des codecs.
- **R-03, protection de branche :** `main.protected=false` constate; issue [#22](https://github.com/tawounfouet/pyllmkit/issues/22) ouverte. Le SHA et la CI ne prouvent pas que les controles sont imposes par GitHub a tous les contributeurs.
- **R-04, revue independante :** pas de GitHub APPROVED review tierce revendiquee dans le dossier.
- **R-05, surface operationnelle :** les objets restent des donnees de domaine et non des invocations de modeles. Aucun appel distant, agent ou streaming reel.
- **R-06, publication :** version de package `0.1.0a2` et aucune release `0.1.0a3` autorisee.

Ces limites sont compatibles avec **G4 technique** mais devront etre traitées ou accepteées explicitement avant release.

## 7. Tableau de gates

| Gate | Etat |
|---|---|
| P3-G0 - Architecture Ready | GO avec reserves (previous) |
| P3-G1 - Request Ready | GO technique avec reserves (previous) |
| P3-G2 - Response Ready | GO technique avec reserves (previous) |
| P3-G3 - Run Lifecycle Ready | GO technique avec reserves (previous) |
| **P3-G4 - JSON Codec & Quality** | **GO technique avec reserves** |
| P3-G5 - Integration & Packaging | NOT STARTED |
| M3 - Inference Foundations Qualified | NOT QUALIFIED |
| Publication 0.1.0a3 | NOT AUTHORIZED |

**Prochain lot : L3.5 - Integration & Packaging** : documentation et snippets executables, audit transversal M1-M3, decisions de risques, tests packaging/regression et qualification G5. M3 devra encore recevoir un GO/NO-GO distinct.

## 8. Archivage sans circularite

Ce PV constate le GO technique sur le SHA `d72b1ce...` et la CI push/main #42053906726. Le commit d'archivage est un nouveau SHA a verifier avec sa propre CI. La preuve sera ajoutee en commentaire de la PR documentaire afin de ne pas anticiper une validation non encore executee.

---

**VERDICT FINAL : P3-G4 GO TECHNIQUE AVEC RESERVES. L3.5 AUTORISE. M3 ET RELEASE NON QUALIFIES.**
