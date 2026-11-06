# 0.3.0 - Multi-provider Contract Profile v1 (draft S0)

> Statut : **DRAFT, a ratifier en S1-G1**. Aucun endpoint live certifie.
> Decision liee : [ADR-059](../../adr/ADR-059-multi-provider-conformance-boundary.md).
> Source : `main@8dd97d5e33108c350e11b3a976926f2138f4e936`.

## 1. Profil et limites

`text_only_v1` stabilise les **observables et la securite**, pas les
chaines generees. Pour une requete compatible avec un provider donne :

- Texte uniquement, un `TextContent` par message; l'ordre est conserve.
- Deployment, provider et alias resolus explicitement, pas de routage tacite.
- Support natif prouve pour toute option de generation fournie.
- Reponse canonique `InferenceResponse`; identite RunId inchangee.
- `Usage` partiel/absent non complete artificiellement.
- `FinishReason.UNKNOWN` conserve pour raison native inconnue.
- Flux M5 a sequences ordonnees et terminal unique.
- Refus des contenus/tool/reasoning impossibles a representer.
- Echec observable par code sur, sans secrets ni payload brut.
- Opt-in strict pour reseau, un seul attempt; zero fallback.
- Aucune promesse de cancellation de la requete distante.

Le profil ne declare pas le support uniforme de `SYSTEM`,
`DEVELOPER`, `top_k`, `stop_sequences` ou autres options
propres a un fournisseur. Il impose leur compatibilite explicite.

## 2. Signatures gelées pour S0

```python
# pyllmkit.protocols.inference
InferencePort.invoke(self, prepared: PreparedInvocation) -> InferenceResponse
AsyncInferencePort.ainvoke(self, prepared: PreparedInvocation) -> InferenceResponse
PreparedStreamingPort.stream_prepared(self, prepared: PreparedInvocation) -> Iterator[StreamEvent]
AsyncPreparedStreamingPort.astream_prepared(self, prepared: PreparedInvocation) -> AsyncIterator[StreamEvent]

# pyllmkit.application.inference
InferenceService.invoke(self, request: InferenceRequest, support_snapshot=None) -> InferenceExecution
AsyncInferenceService.ainvoke(self, request: InferenceRequest, support_snapshot=None) -> InferenceExecution
StreamingInferenceService.open_stream(self, request: InferenceRequest, support_snapshot=None) -> StreamingSession
AsyncStreamingInferenceService.open_astream(self, request: InferenceRequest, support_snapshot=None) -> AsyncStreamingSession
```

Le port historique M5 `stream(request)` /`astream(request)` reste
separe du port natif `stream_prepared(prepared)` /
`astream_prepared(prepared)`. Toute modification exige un ADR et un
plan de migration.

## 3. Oracle de conformite v1

| ID | Famille | Entree | Observation attendue |
|---|---|---|---|
| ID-01 | Identification | Requete resolue | RunId, deployment, provider et alias coherents |
| ID-02 | Tentative | Appel unique | AttemptId distinct du RunId, pas de retry |
| INPUT-01 | Role simple | Un message USER texte | Message native non perdu |
| INPUT-02 | Role incompatible | DEVELOPER non mappe ou ordre invalide | Refus explicite et zero HTTP |
| INPUT-03 | Multi-part | Deux TextContent dans un meme message | `unsupported_content_structure` |
| GEN-01 | Parametre absent | None | Pas de valeur native inventee |
| GEN-02 | Parametre NATIVE | Valeur explicite et snapshot correspondant | Encodage identique semantiquement |
| GEN-03 | Parametre inconnu | Snapshot absent/UNKNOWN | Refus avant l'HTTP |
| GEN-04 | Parametre non encode | Champ non representable nativement | Refus, pas d'omission |
| RESP-01 | Response valide | Payload provider reconnu | Type canonique et RunId correct |
| RESP-02 | Usage absent | Donnees sans comptage | Valeur absente ou partielle preservee |
| RESP-03 | Finish inconnu | Raison native sans mapping sur | `FinishReasonCode.UNKNOWN` |
| ERR-01 | HTTP auth | 401/403 | `authentication_failed` / `permission_denied` |
| ERR-02 | HTTP timeout | 408/504 | `provider_timeout` |
| ERR-03 | HTTP rate limit | 429 | `rate_limited` |
| ERR-04 | HTTP upstream | 5xx | `provider_overloaded` |
| ERR-05 | Native malformee | JSON invalide/duplique/interdit | `provider_protocol_error` ou rejet explicite |
| STR-01 | Stream nominal | Frames natifs complets | M5 started, deltas, terminal unique |
| STR-02 | EOF premature | Pas de terminal provider | `ResponseFailed(provider_not_completed)` |
| STR-03 | Cancellation | Signal local | `ResponseCancelled` et cleanup a reprise |
| STR-04 | Impossible a decoder | Tools/reasoning non representables | Echec fail-closed |
| SEC-01 | Live non autorise | `allow_live=False` | Aucun secret resolu, aucun reseau |
| SEC-02 | Taille/deadline | Seuil depasse | Refus et nettoyage des ressources |
| SYNC-01 | Parite metier | Fixtures sync + async equivalentes | Meme projection sans comparer timing |

## 4. Grille de compatibilite

Les cinq issues de scenarios admises sont `PASS`, `FAIL`,
`NOT_APPLICABLE`, `UNSUPPORTED` et `BLOCKED`. Un scenario
`UNSUPPORTED` doit justifier pourquoi la fonction n'entre pas
dans la promesse du provider, pas couvrir une erreur de test.
Aucun `pytest.skip` ou `xfail` non documente.

Exemple d'enregistrement de preuve :

```yaml
scenario_id: ERR-03
provider: google
operation: ainvoke
mode: async
profile: text_only_v1
fixture_id: google/http_rate_limit_v1
source_kind: synthetic_fixture
expected: rate_limited
observed: rate_limited
status: PASS
commit_sha: "<HEAD_SHA>"
python_version: "3.12"
network_calls: 0
```

Le resultat de cet exemple est **illustratif**, non un PASS constate.
Les fixtures natives et le reporting automatique seront implementes
dans S2, pas dans le profil documentaire de S0.

## 5. Qualite / securite

- Main non protegee actuellement : issue #22.
- Frontiere DNS/TLS/SSRF live non certifiee : #36 et #81.
- Politique de release et publication non autorisee : #35.
- L'usage de `httpx.MockTransport` est une preuve hermetique
  et non une preuve live TLS.
- Streaming synchrone live : reste fail-closed en l'absence de
  deadline globale et preemptive.
- `0.1.0a2` reste la version source declaree; `0.3.0a1`
  n'est qu'une future candidate apres gates et versioning explicite.

## 6. Sorties attendues des gates suivants

- **S1/G1** : faire ratifier les oracles et la politique de compatibilite,
  classer chaque scenario selon les providers.
- **S2/G2** : fixtures natives effectives, tests parametres six providers,
  preuves par mode sur SHA/Python exact.
- **S3/G3** : normalisation d'erreurs avec negatifs redaction.
- **S4/G4** : tests de roles, de parametres, de finish et de usage.
- **S5/G5** : flux M5, EOF, post-terminal et cancellation.
- **S8/G8** : rapport GO/NO-GO technique independant de S9 release.

**Decision** : ce profil est une base de tests **proposee**,
pas une API finale ratifiee ni une release.
