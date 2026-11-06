# PyLLMKit - P7 L7.4 - OpenAI Responses Adapter

- Date: 2026-11-06
- Statut: IMPLEMENTATION EN PR #73, P7-G4 NON CLOTURE
- Baseline de la branche: P7 L7.3 / PR #72, dépend de #71 et #70
- Version déclarée: `0.1.0a2`. `0.2.0a2` reste un objectif non publié.
- Références contractuelles: ADR-050, ADR-052, ADR-054, ADR-056 et P7-AC-025..032
- Source API: https://developers.openai.com/api/reference/resources/responses/methods/create

## 1. Positionnement

L7.4 apporte un adapter *wire-level* pour `POST https://api.openai.com/v1/responses`.
Il utilise HTTPX pour les contrats sync et async, sans dépendre du SDK officiel
`openai`. Ce choix réduit les dépendances obligatoires mais impose une revue
des changements de protocole. L'extra `pyllmkit[openai]` installe HTTPX seulement.

Le coeur PyLLMKit reste dépourvu de tout SDK fournisseur. Les imports HTTP
sont différés jusqu'au moment de l'invocation. Les noms de modèles ne sont ni
découverts ni modifiés; le modèle natif doit être lié explicitement à un
DeploymentId et confirmé par une réponse portant exactement le même alias.
Un modèle dont la réponse est canoniquement renvoyée avec un autre nom est
refusé dans ce premier profil, en attendant des bindings d'alias attestés.

## 2. Payload non-streaming strict

Le message conserve l'ordre et le rôle system/developer/user/assistant.
Un seul `TextContent` par message; rôles TOOL et contenus multimodaux refusés.
Un `GenerationSupportSnapshot` externe doit attester chaque paramètre natif.
Seuls `temperature`, `top_p` et `max_output_tokens` sont mappés dans
ce lot; seed, top_k, stop_sequences et pénalités sont refusés sans
suppression silencieuse. Certains modèles refusent temperature/top_p même
si le protocole les accepte : une déclaration explicite de capacité native
par modèle est nécessaire, sinon pas d'invocation.

Drapeaux imposés :

- `store: false` afin de ne pas demander le stockage de la réponse;
- `stream: false` et `background: false` afin de rester synchrone;
- `tools: []`, `tool_choice: none`, `parallel_tool_calls: false`;
- `truncation: disabled`, `text.format.type: text`.

**Attention** : `store:false` n'est pas une garantie générale de zéro
rétention ni de zéro journalisation par le fournisseur. Les règles de
traitement des données du fournisseur restent applicables.

## 3. Mapping réponse fail-closed

Un seul item `output` de type `message`, rôle `assistant`, statut
`completed`, et un seul bloc `output_text` accepté. Toutes les
sorties tool, reasoning, refusal, image, annotations non vides et logprobs
non vides sont refusées, plutôt qu'effacées. Cela limite volontairement
ce MVP aux réponses réellement text-only; plusieurs modèles de raisonnement
produisent des items `reasoning` et ne satisferont pas ce contrat.

Un `status: completed` signifie que la requête est terminée, pas
nécessairement que le modèle a émis un `finish_reason=stop`: la
`FinishReasonCode` reste `UNKNOWN`. Les compteurs de tokens sont préservés
tels qu'observés, y compris caches et reasoning tokens, sinon `None`.
Aucune valeur totale n'est inventée.

## 4. Sécurité

- Endpoint officiel exact, HTTPS avec vérification TLS, aucune URL arbitraire.
- `trust_env=False`, `follow_redirects=False`, aucun proxy issu de
  l'environnement, une seule tentative sans retry automatique.
- Credentials conservés sous `CredentialRef` et résolus en infrastructure
  au dernier moment. Erreurs natives et bodies HTTP jamais renvoyés en clair.
- Taille de requête maximale 1 MiB et réponse 2 MiB, timeout par phase fini.
- `allow_live=False` par défaut. Aucune requête réseau n'est déclenchée
  à l'import, à la composition du catalogue ou sans opt-in d'exécution.
- `_test_transport` réservé exclusivement aux tests hors réseau : une
  injection de transport arbitraire ne bénéficie PAS des garanties TLS/
  destination démontrées pour la configuration standard.
- Limitation de deadline : le timeout sync HTTPX est par phase; il ne
  garantit pas un hard wall-clock timeout face à une réponse trickle.
  L'async emploie `asyncio.timeout`. Il faut revoir cette limite avant
  GO de production.
- L'extraction d'une chaîne secrète en Python ne garantit pas son effacement
  physique de mémoire. Les secrets ne doivent jamais être ajoutés aux logs.

## 5. Qualifier hors réseau

```bash
python -m pip install -e '.[dev,openai]'
python examples/33_openai_responses_mock.py
python -m pytest -q tests/acceptance/test_p7_l74_openai_responses.py
```

`MockTransport` ne prouve pas une vraie invocation cloud. Aucune vraie clé,
aucun appel facturé ni donnée personnelle n'ont été utilisés dans la CI.

## 6. Gate P7-G4 et GO cloud

Le précheck CI n'est pas un GO de fusion. Pour clore G4 : qualifier G1/G2/G3
dans l'ordre, régler les réserves de sécurité, obtenir une revue indépendante
sur les transports, vérifier le SHA exact de la PR et de main, puis conduire
un smoke cloud séparé, *approuvé*, avec prix du modèle vérifié, plafond de
tokens, nombre d'appels, deadline et budget maximal contrôlé en pratique.

Un budget estimé ou une simple variable d'environnement n'est PAS un
contrôle de coûts exécutoire. Aucune invocation live OpenAI n'est
déclenchée ou proposée comme déjà effectuée par ce document.

Pas de release GitHub, tag, PyPI ni secrets CI.
