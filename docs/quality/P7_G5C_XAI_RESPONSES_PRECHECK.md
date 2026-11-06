# P7-G5c - xAI Grok Responses API (avant streaming)

- Statut: implementation et tests offline, GO technique de PR uniquement
- Parent: #75 Google Gemini
- API: https://docs.x.ai/developers/rest-api-reference/inference/responses
- Choix: Responses API recommandé par xAI, pas Chat Completions legacy
- Configuration: `ProviderConnectionConfig.xai(CredentialRef(...))`,
  `ProviderId("xai")` et `runtime="cloud"`
- Extra `pyllmkit[xai]` : HTTPX seulement

`store:false`, `tools:[]`, `tool_choice:none`, `stream:false`,
`truncation:disabled`, `background:false` par défaut dans le payload.
Ce drapeau n'est pas une garantie de zéro rétention de données chez xAI.

Texte strict: un seul item message assistant d'un seul bloc output_text;
tout élément `reasoning`, `encrypted_content`, `tool_calls`, refusal
ou plusieurs sorties est REFUSÉ. xAI Responses produit régulièrement
des éléments chiffrés de raisonnement avec les modèles Grok récents :
**ces modèles échoueront volontairement avec ce MVP**, tant qu'un
ValueObject dédié ne peut pas préserver cet état sans perte. Ne pas
prétendre offrir tous les modèles Grok. Les conversations multi-tours de
raisonnement ne peuvent pas être reprises fidèlement avec ce profil.

Status=completed reste `FinishReasonCode.UNKNOWN`. Usage natif :
`prompt_tokens`, `completion_tokens`, `total_tokens`, cache et
raisonnement observés, sans recomputation.

Transport TLS vérifié, proxy env et redirects interdits, une seule
tentative, requête <=1 MiB et réponse <=2 MiB. Timeout synchrone par
phase, pas de deadline murale garantie sur réponse trickle; async sous
`asyncio.timeout`. `allow_live=False` par défaut et résolution
credential différée. Les tests utilisent MockTransport et fausse clé.

Aucune vraie invocation xAI, aucun coût, aucune release. G1-G5b et
revues humaines restent bloquants avant toute fusion sur main.
