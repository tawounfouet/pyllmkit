# PyLLMKit - P7 L7.2 - Secure Connection & Adapter Registry

- Date: 2026-11-06
- Statut: PR de développement L7.2 (P7-G2 non qualifié)
- Baseline: L7.1 PR #70 head `37d5d414`, non fusionnée au moment de l'ouverture
- Dépendance: PR #70 puis qualification P7-G1 et P7-G2 sur les SHA exacts
- Aucune connexion réseau, aucun SDK fournisseur, aucun secret en source.

## Contrat du registre

Le registre `AdapterRegistry` est indépendant du catalogue descriptif P6.
Il enregistre de manière explicite la clé exacte `AdapterKey(provider_id, runtime)`,
la connexion `ProviderConnectionConfig` et une fabrique synchrone/asynchrone.
Enregistrer une déclaration descriptive de fournisseur ne crée aucun adapter.

Les fabriques ne sont appelées que lors de l'invocation. `RegisteredInferencePort`
et `RegisteredAsyncInferencePort` sélectionnent le port seulement à partir du
`Deployment` déjà résolu par L7.1. Une absence ou une ambiguïté de binding
produit une erreur normalisée, jamais un repli implicite vers un autre fournisseur.

## Configuration sécurisée

Trois profils pilotes seulement :

- OpenAI: endpoint exact `https://api.openai.com/v1/responses`, clé opaque exigée.
- Anthropic: endpoint exact `https://api.anthropic.com/v1/messages`, clé opaque exigée.
- Ollama: `http://127.0.0.1:<port>/api/chat` ou `http://[::1]:<port>/api/chat`,
  uniquement par `ollama_local()` ou `allow_local=True` explicite.
  `localhost`, adresses LAN, metadata cloud et hosts distants sont refusés.

La vérification de TLS est imposée pour les profils cloud; les redirects
sont interdits dans tous les profils; deadlines et timeouts sont finis.
En local Ollama HTTP n'emploie pas TLS: `verify_tls=True` signifie qu'il
n'existe pas d'option pour le désactiver lors d'une future connexion TLS,
pas qu'Ollama utilise HTTPS.

`CredentialRef` n'est pas une clé. Le `CredentialResolverPort` est un contrat
d'infrastructure, avec `EnvCredentialResolver` explicite et facultatif pour
le développement; la valeur n'est chargée qu'à `resolve()`.
`SecretValue.reveal()` est une sortie explicite réservée aux transports
de confiance; Python ne garantit ni zéro copie ni effacement mémoire.
Ne jamais écrire `reveal()` dans un log, `repr` ou artefact de CI.

## Frontières et garanties non encore démontrées

L7.2 est un **preflight statique**. Il ne prouve ni DNS pinning, ni contrôle
de la destination TCP effectivement connectée, ni vérification d'un certificat
TLS, ni absence de proxy, ni blocage des redirects par un SDK. Aucun socket
n'est ouvert dans ce lot. L7.3 devra contrôler les IP à la connexion,
TLS, proxies et redirects selon ADR-052, avec des tests de transport.
Les variables `HTTP_PROXY`, `HTTPS_PROXY` et les transports locaux
seront traités explicitement au niveau réseau. Sans cela: NO-GO live.

Les erreurs d'initialisation de fabrique et HTTP sont converties en codes sûrs
sans payload brut; cela ne transforme pas les factories tierces en code fiable.
Des plugins injectés doivent être relus, isolés et autorisés par composition.

## Exemple hors réseau

Voir `examples/30_secure_registry_fake.py` : enregistrement explicite
d'un profil Ollama local, routing via un fake et réponse corrélée RunId,
**sans aucun appel au démon Ollama**.

## Qualification

P7-AC-009..016 et tests négatifs: registre distinct, doublons, synchronie,
références de secrets, validation URL/cloud/loopback, timeouts/redirects,
conversion d'erreurs et absence de fuite `repr`. Tous les tests sont hermétiques.
Le gate P7-G2 et la revue indépendante de sécurité restent à acquérir.
