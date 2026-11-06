# PyLLMKit - P7 L7.5 - Anthropic Messages Adapter

- Date: 2026-11-06
- Statut: IMPLEMENTED IN PR #74; G5 NOT YET CLOSED
- Dépend de: PR #70 (G1), #71 (G2), #72 (G3), #73 (G4)
- Baseline: PR #73 HEAD `654fa2831021daa8b5e78aad5b68029901998424`
- Version du package: `0.1.0a2`. `0.2.0a2` est une cible non publiée.
- API documentée: https://platform.claude.com/docs/en/api/http/messages
- Authentification actuelle: https://platform.claude.com/docs/en/manage-claude/authentication
- Gestion des raisons de fin: https://platform.claude.com/docs/en/build-with-claude/handling-stop-reasons

## 1. Architecture et composition

`AnthropicMessagesAdapter` et `AsyncAnthropicMessagesAdapter` implémentent
respectivement `InferencePort` et `AsyncInferencePort` au travers de
`RegisteredInferencePort` et `RegisteredAsyncInferencePort`.

Le registre d'exécution P7 demeure distinct du catalogue descriptif P6.
Un deployment `AVAILABLE` ne déclenche pas une invocation. Il faut un
binding explicite `AdapterKey(provider_id="anthropic", runtime="cloud")`,
une `ProviderConnectionConfig.anthropic(CredentialRef(...))`, un
`CredentialResolverPort`, un alias de modèle natif et une invocation
réellement autorisée. `InferenceRunId` est créé dans l'application et reste
identique de la requête à la réponse.

L'extra `pyllmkit[anthropic]` installe HTTPX, pas le SDK officiel Anthropic.
HTTPX n'est pas importé par le domaine ni au moment de la construction
de l'adapter. L'usage d'un transport filaire direct impose une revue de
compatibilité en cas de changement de la version d'API.

## 2. Profil Messages textuel et fail-closed

- `POST https://api.anthropic.com/v1/messages` uniquement.
- `anthropic-version: 2026-10-21` épinglé au contrat de cette PR.
- `Authorization: Bearer ...`, clé opaque résolue au dernier moment.
- `stream: false`; aucun tool, prompt cache explicite, multimodalité,
  extended thinking ou output structuré dans le MVP.
- Le premier message SYSTEM est mappé en paramètre `system` comme bloc
  textuel. Aucun autre SYSTEM n'est accepté, et DEVELOPER et TOOL sont
  refusés car leur sémantique ne peut pas être transposée identiquement.
- Les rôles USER/ASSISTANT doivent alterner, débuter et se terminer par USER.
  C'est un profil strict de conservation de la structure, pas une règle
  générale imposée par tous les appels Anthropic.
- Un seul `TextContent` par message. Aucun collage silencieux de parts.
- `GenerationConfig.max_output_tokens` est obligatoire, mappé à
  `max_tokens`, et doit disposer d'un `GenerationSupportSnapshot`
  explicitement NATIVE sur la cible de la requête. Pas de valeur par défaut
  inventée. Il faut aussi respecter le plafond réel du modèle.
- `temperature`, `top_p`, `top_k`, `stop_sequences` possibles si leur
  support NATIVE est attesté par modèle. `seed` et les pénalités sont
  explicitement rejetés au lieu d'être perdus.
- Les modèles Claude peuvent ne pas supporter certaines combinaisons
  de paramètres. La déclaration des capacités reste un prérequis.

## 3. Réponses

Un seul bloc `{"type":"text","text":"..."}` est accepté. Les blocs de
raisonnement, tool_use, citations non vides, refus natifs, sorties
multi-blocs ou de type inconnu sont refusés; aucun outil n'est exécuté.

Les `stop_reason` sont interprétés sans inventer une fin naturelle:

| Stop reason natif | FinishReasonCode / erreur |
|---|---|
| `end_turn`, `stop_sequence` | STOP, raison native conservée |
| `max_tokens`, `model_context_window_exceeded` | LENGTH |
| `tool_use` | Erreur `unsupported_provider_output` |
| `refusal` | Erreur `provider_refusal` |
| `pause_turn` | Erreur `provider_not_completed` |
| Valeur future non reconnue | UNKNOWN + raison native assainie |

Les métriques `input_tokens`, `output_tokens`,
`cache_read_input_tokens` et `output_tokens_details.thinking_tokens`
sont copiées si observées. `Usage.total_tokens` n'est pas calculé, car
les sous-compteurs Anthropic n'ont pas tous la même signification
(les lectures/créations cache sont comptabilisées séparément).
Une création de cache non nulle est refusée dans ce premier profil,
car `Usage` ne peut pas représenter ce compteur sans perte.

## 4. Sécurité et confidentialité

- L'URL officielle est exigée. HTTPS avec certificat vérifié,
  `trust_env=False` et `follow_redirects=False`.
- Aucun retry implicite, un seul essai réseau. HTTP 4xx/5xx devient un code
  d'erreur sûr sans exposer le corps de la réponse ou une exception native.
- Limites locales: requête 1 MiB, réponse 2 MiB, timeout de transport fini,
  vérification de la deadline avant l'appel.
- L'async utilise `asyncio.timeout` comme deadline murale locale.
  L'appel sync n'est pas garanti contre un serveur qui renvoie
  indéfiniment de minuscules morceaux, malgré le timeout HTTPX par phase.
  NO-GO production sans remédiation et revue.
- `allow_live=False` par défaut. Construction, import et CI offline
  n'ouvrent aucun socket. L'injection `_test_transport` n'a une valeur
  de preuve que pour les tests déterministes, jamais pour la sécurité
  d'une connexion réelle.
- Aucune promesse de rétention nulle chez Anthropic. Les règles de
  protection et rétention de données du fournisseur s'appliquent.
- Les secrets Python ne sont pas effacés physiquement de la mémoire,
  même si `SecretValue.__repr__` les masque.
- Aucun budget cloud exécutoire n'est implémenté dans ce lot. Les
  tests live restent NO-GO, même si la bibliothèque a un flag d'opt-in.

## 5. Exemple CI non connecté

```bash
python -m pip install -e '.[dev,anthropic]'
python examples/34_anthropic_messages_mock.py
python -m pytest -q tests/acceptance/test_p7_l75_anthropic_messages.py
```

L'exemple utilise `httpx.MockTransport` et une fausse clé de démonstration.
Aucun accès au service Anthropic réel, aucune dépense, aucun secret réel.

## 6. Gate

P7-AC-033..040 documentés et testés offline; CI du SHA final sur Python
3.11/3.12/3.13, Ruff, mypy strict, wheel/sdist et couverture branchée à
vérifier dans le précheck. Un PASS de mock n'est pas une preuve live.

P7-G5 n'est pas clôturé tant que les dépendances G1-G4, revues humaines,
protection de main, budget réel, qualification du transport et smoke
cloud explicitement autorisé ne sont pas réglés. Pas de tag ni PyPI.
