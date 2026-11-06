# PyLLMKit - P7 L7.3 - Ollama adapter & première invocation

- Date: 2026-11-06
- Statut: IMPLEMENTED IN STACKED PR #72, P7-G3 NOT YET SATISFIED
- Parents: PR #70 (L7.1), PR #71 (L7.2), toutes deux encore non fusionnées lors de l'ouverture
- Version PyPI: toujours `0.1.0a2`; `0.2.0a1` cible, non publiée
- Transport: HTTPX optionnel, profil local loopback et payload texte strict
- Documentation native: https://docs.ollama.com/api/chat

## Pourquoi ce lot

L7.1 prépare le Run et le port, L7.2 garantit l'enregistrement explicite
et la validation statique des destinations, L7.3 introduit un transport et
un mapping Ollama réellement codés. Le fait qu'une invocation puisse être
effectuée n'est pas une preuve qu'un démon Ollama est accessible, et une
réponse MockTransport ne vaut **jamais** un smoke live.

## Installer l'option de transport

```bash
python -m pip install -e '.[ollama]'
```

Le paquet principal garde zéro dépendance HTTP obligatoire. Le package
`httpx` est importé lors de l'appel, pas au chargement du domaine.

## Contrat Ollama texte strict

- `POST /api/chat` avec `model` alias explicitement configuré.
- `stream: false`, `think: false`, pas d'exécution d'outil.
- Un seul `TextContent` par `Message`; ordre préservé.
- Rôles autorisés : system, user, assistant. Developer et tool refusés.
- Mapping options : temperature, top_p, top_k, max_output_tokens ->
  num_predict, seed, stop_sequences -> stop.
- presence_penalty / frequency_penalty et autres options impossibles à
  mapper sont refusées, même si un snapshot extérieur les avait dites NATIVE.
- `done` doit être true, `message.role` doit être assistant, `content`
  doit être str. Thinking, tool_calls, images, logprobs non vides refusés.
- `done_reason` absent ou inconnu reste UNKNOWN, et son texte natif
  n'est conservé que s'il appartient à une forme sûre.
- `prompt_eval_count` et `eval_count` reflètent les observations natives;
  `Usage.total_tokens` reste None si non donné, jamais calculé.
- Taille requête max 1 MiB; réponse max 2 MiB; si dépassement, erreur sûre.

## Sécurité du transport et limitations

- `allow_live=False` par défaut sur `OllamaAdapter` et `AsyncOllamaAdapter`.
  Une tentative sans autorisation échoue sans ouverture de socket.
- Les seuls endpoints permis par L7.2 : http://127.0.0.1:<port>/api/chat
  et http://[::1]:<port>/api/chat, avec opt-in local.
- HTTPX instancié `trust_env=False` et `follow_redirects=False` :
  les proxys d'environnement ne sont pas utilisés et les 30x sont refusés.
- Les IP littérales évitent le recours à un hostname de destination
  modifiable et donc la classe de risques DNS rebinding à ce niveau.
- Une seule tentative, aucune reprise ni fallback vers un autre provider.
- Erreurs d'HTTP, timeout et connexion rendues en codes publics sûrs.
- Limitations actuelles : HTTPX fournit des timeouts par phase. Le service
  async applique une deadline murale supplémentaire avec `asyncio.timeout`;
  le sync ne garantit pas encore une deadline murale stricte en cas de réponse
  trickle infinie. NO-GO production avant remédiation et revue de sécurité.
- `_test_transport` est une injection réservée aux tests. Un transport
  fourni de l'extérieur n'est pas couvert par la preuve de destination et
  ne doit pas être utilisé en production.
- Les sorties natives privées ne sont jamais journalisées par le kit.
  Le serveur local et ses propres logs/paramètres restent sous la
  responsabilité du propriétaire.

## Démonstration CI sans réseau

```bash
python examples/31_ollama_mock_transport.py
```

Utilise `httpx.MockTransport`. Cela démontre le code d'inférence, pas
un contact réel avec le démon Ollama. Le CI standard se limite à ce mode.

## Première vraie invocation - opt-in manuel

À exécuter sur une machine où le démon Ollama est installé, démarré, où
un modèle a été téléchargé, et après décision de sécurité de l'opérateur :

```bash
export PYLLMKIT_LIVE_TESTS=1
export PYLLMKIT_LIVE_PROVIDER=ollama
export PYLLMKIT_ALLOW_LOCAL_LIVE=1
export PYLLMKIT_OLLAMA_MODEL='llama3.2:1b'
python examples/32_ollama_live_opt_in.py
```

Sans ces trois variables ou sans alias explicite, le script n'effectue
aucun appel. L'alias donné est indicatif : un modèle doit réellement être
installé sous ce nom. Le script ne journalise ni prompt ni réponse brute.
Aucun smoke live n'a été exécuté dans cette PR.

## Preuves exigées pour P7-G3

- P7-AC-017..024 exécutés et traçables, tests unitaires/acceptation offline.
- CI Python 3.11/3.12/3.13 sur HEAD exact de la PR puis post-merge main.
- Revues indépendantes de sécurité transport et de code.
- Smoke live local opt-in sur une machine explicitement autorisée, preuve
  assainie SHA / alias / date / RunId / statut, aucun prompt brut.
- Aucune release PyPI, aucune invocation cloud pendant L7.3.
- Précondition G1 et G2 satisfaites; #22, #35, #36 traitées ou
  réserves signées avant tout GO de fusion.
