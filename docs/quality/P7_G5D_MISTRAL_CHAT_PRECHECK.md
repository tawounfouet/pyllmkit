# P7-G5d - Mistral AI Chat Completions avant streaming

- Statut: implémentation hors réseau en PR empilée sur #76 xAI
- API native: https://docs.mistral.ai/api
- Endpoint fixe: https://api.mistral.ai/v1/chat/completions
- Profil: `ProviderId("mistral")`, `runtime="cloud"`, `ProviderConnectionConfig.mistral(...)`
- Extra `pyllmkit[mistral]`: HTTPX optionnel, pas de SDK fournisseur

Mapping strict en une requête `stream:false`, `n:1`, `tools:[]`,
`tool_choice:none`, `parallel_tool_calls:false`, `safe_prompt:false`
(pas d'injection de prompts); `response_format:{"type":"text"}`.
Rôles SYSTEM / USER / ASSISTANT, sans DEVELOPER et sans TOOL,
messages à un seul bloc texte, aucun merging silencieux.
Les paramètres sont mappés seulement avec capacité NATIVE attestée :
`max_output_tokens->max_tokens`, `seed->random_seed`,
`stop_sequences->stop`, temperature/top_p/top_k et pénalités.

Réponse `object=chat.completion`, un choix `index=0`, un message
assistant texte. Les tool_calls, reasoning_content, refusals,
contenus typés ou sorties multiples sont refusés. stop=STOP, length=LENGTH,
raison inconnue UNKNOWN. Usage partiel sans totaux inventés.

L'API Chat Completions de Mistral n'expose pas `store:false` dans le
contrat consulté. La bibliothèque n'invente donc pas de paramètre privacy
non documenté. Les politiques de rétention fournisseur doivent être
acceptées séparément avant un test live.

Sécurité: HTTPS exact, header Bearer, `trust_env=False`, redirects
interdits, TLS vérifié, timeout fini, une tentative, 1 MiB/2 MiB.
Pas de deadline murale stricte sync sur réponse infinie trickle.
`allow_live=False` par défaut; MockTransport ne constitue aucune
preuve de connectivité ni de facturation. Aucun test cloud réel ou
release. G1..G5c et revues indépendantes prérequis avant fusion.

Documentation: https://docs.mistral.ai/inference/conversations/chat-completion

## Préqualification CI et composition transversale

Sur le code pré-documentaire `a75b08c4b5de445299d4c9ecfcf7750096c43cab`, les jobs CI sur Python 3.13 ont validé 1 640 tests généraux, 56 tests Mistral et 98,05 % de couverture avec branches des deux nouveaux modules Mistral. Le présent commit fixe le seuil à 95 %, ajoute le test transversal de routage des six fournisseurs en sync/async, et l'exemple offline #38. Il faut confirmer la CI sur le SHA final du présent commit.
