# P7-G5b - Google Gemini generateContent

- Date: 2026-11-06
- Statut: prototype adapter + tests hermétiques, GO de revue uniquement
- Parent: PR #74 Anthropic G5
- Contrat: https://ai.google.dev/api/generate-content
- Endpoint fixé: `https://generativelanguage.googleapis.com/v1beta/models/{alias}:generateContent`
- Auth: header `x-goog-api-key`, résolu par `CredentialResolverPort`
- Extra: `pyllmkit[google]` (HTTPX optionnel, non SDK Google)

## Invariants

Le catalogue P6 décrit; `AdapterRegistry` autorise explicitement un binding
exact `ProviderId("google")`, `runtime="cloud"`, modèle natif et port.

L'alias est un segment chemin strictement validé : pas de slash, query,
fragment ou encodage arbitraire. HTTPS exact, trust_env=False,
follow_redirects=False, verify=True; une seule tentative, taille 1 MiB/2 MiB.

SYSTEM n'est pas assimilé à USER : il devient `systemInstruction` en
première position uniquement. ASSISTANT devient `role=model`. Le
dialogue texte initial impose l'alternance USER/MODEL et une dernière entrée
USER. Les structures non représentables sont refusées.

`generationConfig` inclut un seul candidat, `responseMimeType=text/plain`,
et uniquement les paramètres déclarés NATIVE via snapshot. La requête
impose `store:false`; ce paramètre ne garantit pas zéro rétention dans
l'infrastructure fournisseur.

Réponse: un seul candidat texte, STOP/LENGTH/UNKNOWN explicite, contenus
bloqués ou enrichis (tools, reasoning, citations, grounding) refusés.
`modelVersion` est une version fournisseur résolue, pas forcément
identique à l'alias envoyé; elle n'est pas utilisée comme preuve d'identité.
Usage: valeurs Google observées seulement; aucun compteur calculé.

Les tests utilisent HTTPX MockTransport. `allow_live=False` par défaut.
Aucune clé réelle, aucune connexion Google, aucun coût, aucune release.
Les gates #70-#74, la protection de main et les revues de sécurité sont
pré-requis à un GO live. Streaming non implémenté.

## Addendum technique

CI initiale sur `25dbea6cfc8d4e1baa28a8686462f4a818d3c756` : 1 534 tests généraux réussis, 71 tests Gemini réussis, couverture 95,44 % du mapping + transport cloud. Le seuil de la CI est relevé à 95 %. Un contrôle secondaire du chemin demandé par le transport est ajouté pour refuser les URL arbitraires, en plus de la validation de la configuration et de l'alias. Le HEAD final doit être requalifié par GitHub Actions.
