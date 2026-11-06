# 0.3.0 - S0 Contract Audit & Baseline Freeze

> Date : 2026-11-06
> Gate : **G0 PRECHECK, qualification documentaire en cours**
> Source Git : `main@8dd97d5e33108c350e11b3a976926f2138f4e936`
> Version package : `0.1.0a2` ; **`0.3.0` est un jalon cible, pas une version publiee**.
> Aucun changement du code runtime dans S0.

## 1. Evidence de reference

- GitHub Actions `main` : [42211154597](https://github.com/tawounfouet/pyllmkit/actions/runs/42211154597) ;
  `validate (3.11)`, `validate (3.12)`, `validate (3.13)` SUCCESS.
- 1 890 tests generaux par environnement Python ; controle natif L7.6
  **90,87 %** branch coverage ; resilence L7.7 **100 %**.
- Le workflow comporte des controles Ruff, mypy strict, tests offline,
  exemples, wheel et sdist ; cette preuve n'etablit pas une execution live.
- [Rapport P7-G8](../../quality/P7_G8_INTEGRATED_GATE_REVIEW.md).
- A la verification S0 : pas de PR ouverte ; `main.protected=false`,
  aucun ruleset actif ; issues [#22](https://github.com/tawounfouet/pyllmkit/issues/22),
  [#35](https://github.com/tawounfouet/pyllmkit/issues/35),
  [#36](https://github.com/tawounfouet/pyllmkit/issues/36) non resolues.

## 2. Inventaire exact des contrats et des couches

| Surface | Point d'entree reel | Garantie S0 |
|---|---|---|
| Port synchrone | `protocols/inference.py:InferencePort.invoke(prepared)` | `InferenceResponse` |
| Port asynchrone | `AsyncInferencePort.ainvoke(prepared)` | `InferenceResponse` |
| Port native stream sync | `PreparedStreamingPort.stream_prepared(prepared)` | `Iterator[StreamEvent]` |
| Port native stream async | `AsyncPreparedStreamingPort.astream_prepared(prepared)` | `AsyncIterator[StreamEvent]` |
| Services applicatifs | `application/inference/service.py` | `InferenceService.invoke`, `AsyncInferenceService.ainvoke` |
| Sessions stream | `application/inference/streaming.py` | `open_stream`, `open_astream`, `cancel()` |
| Invocation | `application/inference/contracts.py` | `PreparedInvocation`, `InvocationContext`, `InvocationOptions` |
| Domaine | `domain/inference`, `domain/streaming` | Run, Response, Usage, FinishReason, M5 events |
| Composition | `adapters/inference/registry.py`, `routing.py` | Enregistrement explicite |
| Requete native HTTP | `cloud_http.py`, `openai_responses.py`, `anthropic_messages.py`, `ollama.py` | HTTPX optional et invocations opt-in |
| Streaming natif | `native_stream_transport.py`, `native_stream_mapping.py` | SSE/NDJSON, transport borne, fail-closed |
| Erreur | `application/inference/contracts.py:InvocationPortError`; `adapters/inference/errors.py:normalize_http_failure` | Codes courts, pas de payload brut |

Les modules `domain` ne doivent pas importer de SDK ou de transport HTTP.
Les Protocols P7 et le contrat M5 demeurent des interfaces **distinctes**.

## 3. Registre des 6 adapters natifs

| Provider | API native | Sync/async | Encoder | Decoder | Stream |
|---|---|---|---|---|---|
| OpenAI | Responses API | `OpenAIResponsesAdapter` / `AsyncOpenAIResponsesAdapter` | `encode_openai_responses_request` | `decode_openai_responses_response` | SSE |
| Anthropic | Messages API | `AnthropicMessagesAdapter` / `AsyncAnthropicMessagesAdapter` | `encode_anthropic_messages_request` | `decode_anthropic_messages_response` | SSE |
| Google | Gemini generateContent | `GoogleGeminiAdapter` / `AsyncGoogleGeminiAdapter` | `encode_gemini_request` | `decode_gemini_response` | SSE |
| xAI | Responses API | `XAIResponsesAdapter` / `AsyncXAIResponsesAdapter` | `encode_xai_responses_request` | `decode_xai_responses_response` | SSE |
| Mistral | Chat Completions | `MistralChatAdapter` / `AsyncMistralChatAdapter` | `encode_mistral_chat_request` | `decode_mistral_chat_response` | SSE |
| Ollama | Local /api/chat | `OllamaAdapter` / `AsyncOllamaAdapter` | `encode_ollama_request` | `decode_ollama_response` | NDJSON |

Le streaming utilise `NativeProviderStreamingAdapter` selon
`ProviderProfile`; ne pas inventer six classes de streaming distinctes.

## 4. Variations observees, non automatiquement des bugs

Le tableau de roles et parametres est deduit du **code des encodeurs a ce SHA**.
Il n'atteste pas que la plateforme distante accepte toutes les valeurs.

| Provider | Messages acceptes par le mapper | Parametres encodables explicitement |
|---|---|---|
| OpenAI | SYSTEM, DEVELOPER, USER, ASSISTANT | temperature, top_p, max_output_tokens |
| Anthropic | SYSTEM initial optionnel ; USER/ASSISTANT alternes ; dernier USER ; max_output_tokens obligatoire | max_output_tokens, temperature, top_p, top_k, stop_sequences |
| Gemini | SYSTEM initial optionnel ; USER/ASSISTANT alternes ; dernier USER | temperature, top_p, top_k, max_output_tokens, seed, stop_sequences, presence_penalty, frequency_penalty |
| xAI | SYSTEM, DEVELOPER, USER, ASSISTANT | temperature, top_p, max_output_tokens |
| Mistral | SYSTEM uniquement en tete ; USER/ASSISTANT ; dernier USER | temperature, top_p, top_k, max_output_tokens, seed, stop_sequences, presence_penalty, frequency_penalty |
| Ollama | SYSTEM, USER, ASSISTANT | temperature, top_p, top_k, max_output_tokens, seed, stop_sequences |

Tous les codecs text-only imposent une seule `TextContent` par message ;
les structures ou sorties non representables doivent echouer plutot
qu'etre converties en texte sans consentement explicite.
Certains adapters revérifient `SupportLevel.NATIVE` et d'autres se reposent
sur la validation de `_InvocationPipeline.prepare`. Ce decoupage
est a mettre sous test et non a modifier sans reproduction d'un ecart.

## 5. Carte invariants -> code -> tests -> lacunes

| Invariant | Code / preuves existantes | Lacune / owner |
|---|---|---|
| C-01/02 resolution, RunId, attempt_id | `service.py`, `contracts.py` ; `test_p7_l71_inference_kernel.py` | Tester six adapters natifs, S2 |
| C-03 generation strictement supportee | `compatibility.py`, six encoders | Cas croises NATIVE/UNKNOWN/UNSUPPORTED, S1/S4 |
| C-04/05/06 terminalite, finish, usage | `domain/inference`, six decoders | Projections sync/async sur memes fixtures, S2/S4 |
| C-07 erreurs publiques suretes | `errors.py`, `cloud_http.py` | Cross-mapping six providers et secrets, S3 |
| C-08/09 flux et EOF | `native_stream_mapping.py` ; L7.6 201 tests | Verifier matrice croisee unifiee, S5 |
| C-10 annulation locale | `streaming_resilience.py` ; L7.7 47 tests | Suspension/reprise et limites remote explicites, S5 |
| C-11 un attempt, aucun reroutage | `InvocationOptions(max_attempts=1)` ; tests P7 | Test compteur d'appels cross-provider, S2/S6 |
| C-12 import core sans HTTPX | smoke wheel / sdist P7 | Gate de compatibilite S7 |
| C-13 parite de projection sync/async | six paires de classes et tests par provider | Contrat de projection commun manquant, S2/S4 |
| C-14 egress et secrets | `security.py`, HTTPX transport | Peer DNS/TLS live non prouve, issue #36 |
| C-15 tailles/deadlines | `cloud_http.py`, `native_stream_transport.py` | Hard deadline sync live refuse ; S6/#81 |

Sources de comparaison : exigences FR-036, FR-037, FR-040 ;
invariants CAP-005..CAP-008, INT-006, INF-001.. ;
ADR-054 et ADR-055 ; programme de S0 dans le plan `0.3.0`.

## 6. Ecarts prioritaires / classification

| ID | Classe | Priorite | Constat prouve ou risque | Traitement |
|---|---|---|---|---|
| GAP-01 | TEST_COVERAGE | P0 | `test_p7_six_provider_registry.py` instancie des **fakes**, pas les six transports natifs | [#84](https://github.com/tawounfouet/pyllmkit/issues/84), S2 |
| GAP-02 | CONTRACT_DIFFERENCE | P0 | Restrictions de roles et exigences de `max_output_tokens` different entre codecs | [#83](https://github.com/tawounfouet/pyllmkit/issues/83), [#86](https://github.com/tawounfouet/pyllmkit/issues/86) |
| GAP-03 | VALIDATION_PARITY | P0 | Set de parametres natifs et methode de verification des snapshots different selon encoders | [#83](https://github.com/tawounfouet/pyllmkit/issues/83), [#86](https://github.com/tawounfouet/pyllmkit/issues/86) |
| GAP-04 | ERROR_TAXONOMY | P0 | `normalize_http_failure` existe ; equivalence des erreurs **tous** providers pas encore testee | [#85](https://github.com/tawounfouet/pyllmkit/issues/85) |
| GAP-05 | STREAMING | P0 | Le transport en streaming sync reel est refuse faute de deadline preemptive | [#87](https://github.com/tawounfouet/pyllmkit/issues/87), [#81](https://github.com/tawounfouet/pyllmkit/issues/81) |
| GAP-06 | SECURITY_GOVERNANCE | P0 | `main` non protegee et egress DNS/TLS live non atteste | [#22](https://github.com/tawounfouet/pyllmkit/issues/22), [#36](https://github.com/tawounfouet/pyllmkit/issues/36), [#81](https://github.com/tawounfouet/pyllmkit/issues/81) |
| GAP-07 | RELEASE_VERSION | P0 S9 | Package toujours `0.1.0a2` ; cible `0.3.0` non qualifiee | [#35](https://github.com/tawounfouet/pyllmkit/issues/35), S8/S9 |
| GAP-08 | EVIDENCE | P1 | Pas de rapport `provider x mode x scenario` sur SHA et Python exact | [#84](https://github.com/tawounfouet/pyllmkit/issues/84), S2/S8 |
| GAP-09 | CI_GATE | P0 | Une ancienne CI P7 verte signalait une couverture L7.6 sous seuil ; corrigee #80 | [PR #80](https://github.com/tawounfouet/pyllmkit/pull/80), suivi S8 |

Une divergence est **a investiguer**, pas necessairement un bug.
Ne pas creer de `PASS` transversaux a partir d'un inventaire de classes.

## 7. Reste a faire avant gate S0-G0

- [x] SHA et version de reference figes.
- [x] Six encoders et decoders identifies.
- [x] Protocols et surfaces publiques repertories.
- [x] Etat de la CI et limites de qualification archive.
- [x] Carte d'invariants et matrice de risques tracees.
- [x] Registre GitHub des gaps lie aux issues #22, #35, #36, #81, #83-#87 et PR #80.
- [x] Validation initiale sur PR #82 SHA `baf71e4609512f43dafaa99cd68ea977b85d9b2c` : [CI #42214251711](https://github.com/tawounfouet/pyllmkit/actions/runs/42214251711), Python 3.11-3.13 SUCCESS et **1 929 tests** chacun. Une revalidation du HEAD final reste necessaire.
- [ ] Revue independante de l'ADR-059 et du profil S1.
- [ ] Gate S0-G0 formellement prononce ; aucun GO release implicite.

**Decision preliminaire** : S0 peut passer en revue des preuves, pas encore
affirmer une certification multi-provider. Le prochain chantier code est
S1 - Contract Profile v1, suivi du harnais S2.
