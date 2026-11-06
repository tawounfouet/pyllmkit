# PyLLMKit v0.3.0 - S2 Native Streaming Conformance & Evidence

> Date : 2026-11-06
> Statut : **S2/G2 EN COURS**, qualification de la seconde tranche en cours
> Branche : `v030/s2-native-streaming-evidence`, empilee sur S2 PR #89
> Principe : six fournisseurs, deux modes, observables normalises, aucune requete live
> Sources : ADR-059, profil `text_only_v1`, P7-G6/G7, issue #84

## 1. Objet

La premiere tranche S2 (#89) verifie les transports HTTP natifs en mode
`invoke/ainvoke` sur des erreurs normalisees et des reponses textuelles.
Cette tranche complete **les memes axes de conformite** pour le streaming :

- OpenAI Responses, Anthropic Messages, Google Gemini, xAI Responses,
  Mistral Chat : `text/event-stream` SSE.
- Ollama `/api/chat` : JSONL/NDJSON.
- Synchrone avec un `httpx.MockTransport` injecte, jamais avec un vrai socket.
- Asynchrone avec un `httpx.MockTransport` injecte, aucune API payante.
- `StreamingSession` et `AsyncStreamingSession` conservent l'identite
  `InferenceRunId`, les sequences et un terminal unique.

## 2. Fixture provenance et differences non masquees

Le module `tests/conformance/stream_fixtures.py` fournit une source
**synthetique, versionnee** `v030-s2-stream-v1` inspiree des fixtures
P7 L7.6. Aucune capture reseau ou promesse de compatibilite avec un
service distant au jour du test. Le payload terminal et le MIME
sont choisis selon les regles natives de chaque fournisseur.

**Difference observee a documenter** : le streaming Ollama accepte
`application/x-ndjson` et `application/json`, tandis que les cinq
profils SSE exigent `text/event-stream`. Un test de MIME invalide
doit employer `text/plain` pour ne pas assimiler une variante native
licite a une defaillance.

## 3. Matrice de scenarios implementes

| Scenario | Providers | Modes | Cas | Oracle |
|---|---:|---:|---:|---|
| `complete` | 6 | 2 | 12 | Started, deux deltas, usage final reel, Completed |
| `truncated` | 6 | 2 | 12 | EOF sans completion => Failed(`provider_not_completed`) |
| `malformed` | 6 | 2 | 12 | JSON invalide => Failed(`provider_protocol_error`) |
| `bad_mime` | 6 | 2 | 12 | MIME `text/plain` => Failed(`provider_protocol_error`) |
| `rate_limited` | 6 | 2 | 12 | HTTP 429 => Failed(`rate_limited`) |
| `pre_cancelled` | 6 | 2 | 12 | Annulation locale, aucun transport contacte |
| **Total** | | | **72** | Protocoles M5 et fail-closed |

Les events doivent toujours utiliser le RunId de la session et des
sequences contigues commencant a zero. La suite refuse toute
`ResponseCompleted` sur les scenarios d'echec.

## 4. Reporter reproductible et preuves CI

`tools/v030_conformance_report.py` execute uniquement
`tests/conformance` avec pytest, analyse le fichier JUnit local puis
ecrit `conformance.json` et `conformance.md` contenant :

- version de schema `v030-conformance-evidence-v1`, Python, date UTC,
  SHA exact du code teste et SHA HEAD de la PR ;
- identifiant de scenario, fournisseur, mode, operation, fixture et
  resultat (PASS/FAIL/BLOCKED) **observe** ;
- verification de la completude de huit familles de scenarios
  couvrant les six fournisseurs ;
- refus de tout resultat FAIL, BLOCKED, SKIP ou suite incomplete ;
- absence de prompts, secrets, corps HTTP, logs d'erreur ou traces
  JUnit persistants dans les artefacts distribues.

Le rapport prend les cinq statuts contractuels :
`PASS`, `FAIL`, `NOT_APPLICABLE`, `UNSUPPORTED`, `BLOCKED`.
Dans cette campagne ciblee, tout cas collecte doit etre `PASS`.
Les deux statuts `NOT_APPLICABLE` et `UNSUPPORTED` seront utilises
pour les axes non communs lorsqu'un oracle et une justification seront
definis en S3/S4 ; ils ne servent pas a cacher un test en echec.

Le workflow `.github/workflows/ci.yml` doit executer le reporter sur
Python 3.11, 3.12, 3.13 et archiver un artefact par version via
`actions/upload-artifact@v4`. Un check vert ne suffit pas sans
la presence et l'integrite des artefacts.

## 5. Périmetre de cette tranche et sorties attendues

- [x] Six fixtures SSE/NDJSON documentees et versionnees.
- [x] Tests de complétion, EOF, MIME, JSON, 429, pre-annulation.
- [x] Reporter de resultats hors ligne (code et workflow).
- [ ] Verifier CI SHA exact et trois artefacts JSON/MD non vides.
- [ ] Verifier la coherence `tested_sha` / `head_sha` / matrix Python.
- [ ] Ajouter les scenarios de cancellation pendant stream et
  `Task.cancel()` en conditions de transport simulées.
- [ ] Attester les seuils taille/frames et redaction cross-provider.
- [ ] Revue independante de l'ADR-059 et du registre de risques.
- [ ] Exclure toute declaration de conformite live sans vrais canaris
  autorises avec budget, connexions et DNS/TLS controles.

## 6. Gate

**GO pour l'execution des tests offline de cette tranche seulement,
PENDING pour S2-G2 complet.**

Aucune modification de version `pyproject.toml`, aucun merge automatique,
aucun test payant ni publication sont autorises par ce document.
