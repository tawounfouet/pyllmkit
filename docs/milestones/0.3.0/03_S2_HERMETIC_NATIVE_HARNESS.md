# 0.3.0 - S2 Hermetic Native Adapter Harness (first slice)

> Statut : **IN PROGRESS - S2/G2 partial**.
> Base : S1 PR #88, S0 PR #82.
> Ticket : [#84](https://github.com/tawounfouet/pyllmkit/issues/84).
> Runtime PyLLMKit : aucun changement.

## Factory unique `tests/conformance/providers.py`

- Six fournisseurs natifs nommes : OpenAI, Anthropic, Gemini, xAI,
  Mistral, Ollama.
- Fabrique un `PreparedInvocation` canonique en memoire.
- Cree les **vraies classes** de transport sync ou async.
- Injecte exclusivement `httpx.MockTransport`.
- Secret synthetique fourni par `EnvCredentialResolver` a partir d'un
  mapping in-memory ; ne lit pas les vraies variables d'environnement.
- Teste `allow_live=False` par absence de contact, y compris mock.

## Scenarios P0 executes

| ID | Combinaisons | Oracle |
|---|---|---|
| S2-ERR-001..009 | 9 statuts x 6 providers x 2 modes = 108 | Codes HTTP normalises sans fuite |
| S2-SEC-001 | 6 providers x 2 modes = 12 | `allow_live=False` bloque avant toute connexion |
| Total | **120 cas parametres** | Zero socket externe, 0/1 appel mock |

Les statuts HTTP : 400, 401, 403, 404, 408, 429, 500, 503 et
504. Chaque execution doit constater `InvocationPortError(code)`,
pas de `exception` native ni de corps de reponse. Le nombre de
requêtes mock doit etre **exactement un** lors d'un echec HTTP et
**zero** avec `allow_live=False`.

## Preuves et limites

- La suite n'est pas une preuve TLS, DNS, peer-IP ni publication.
- Les six paths de transport sont reels mais la reponse HTTP est
  **synthetique**. Les tests nominaux de decoding/Usage/FinishReason,
  le streaming natif, les MIME/tailles, les capabilities et les fixtures
  provenancees restent a completer dans S2-S6.
- Les champs natifs comme les roles ne doivent pas etre supprimes pour
  obtenir un rapport vert.

## Gate S2-G2

- [x] Structure `tests/conformance` et factories explicites.
- [x] Scenarios partages contre six vrais adapters sync et async.
- [ ] CI HEAD Python 3.11/3.12/3.13 et audit codes de sortie.
- [ ] Fixtures de reponse nominale pour six providers et projections
  de `InferenceResponse`.
- [ ] Reporter JSON/Markdown par SHA/Python/fixture.
- [ ] Streaming SSE/NDJSON, cancellations, limites completes.
- [ ] Revue independante et PV G2.

**S2-G2 n'est pas ferme par ce premier lot.**
