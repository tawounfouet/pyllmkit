# PyLLMKit - Remédiation multimodale : sécurité, CI et limites

> Date : 2026-11-07
> Statut : compte rendu de remédiation **sur main, après le tag Git v0.3.0**.
> Portée : correctifs de code et preuves de tests synthétiques, sans certification provider-live.

## 1. Contexte et baseline

Le commit de déploiement multimodal initial `f28040d897a6e6e5b209580450c6a54cab011de6` ajoutait entrées images/audio/vidéo, sorties génératives, nouveaux adapters et commandes `generate`. Le workflow [#42337593442](https://github.com/tawounfouet/pyllmkit/actions/runs/42337593442) a échoué sur Python 3.11/3.12/3.13 : bien que 3 025 tests pytest passent, la couverture **Ollama + mapping** était **91,39 % contre 95 %**. Le gate ne réunissait pas les nouveaux tests multimodaux, révélant ensuite des lacunes similaires dans les gates OpenAI et Gemini.

## 2. Modifications intégrées dans PR #111

| Zone | Problème constaté | Remédiation et preuve attendue |
|---|---|---|
| Six adaptateurs | Tests multimodaux hors périmètre des anciens gates | Intégrer les scénarios multimodaux dans chaque gate, sans abaisser les seuils ; ajouter les négatifs Gemini |
| Auth API média | URL potentiellement falsifiée, redirects et proxy implicite | HTTPS et origines strictes, IP DNS publique épinglée à la connexion avec SNI/certificat d'origine, redirects/proxies refusés |
| Réception média distant | URL fournisseur non fiable, rebinding/SSRF, réponse sans limite | Autorisation limitée aux hôtes fournisseurs, DNS public, IP TLS épinglée, pas de redirection, réponse limitée à 100 MiB |
| Corps HTTP | Lecture non bornée, fuite possible via exceptions | Lecture `limit+1`, plafond réponse API 160 MiB, erreurs HTTP bornées à 8 KiB, exceptions assainies |
| Fichier de sortie CLI | Saver suivait une URL distante arbitraire | Saver refuse `kind=uri`; seuls fichiers et contenus locaux/déjà matérialisés sont admis |
| Entrées multimodales | CLI acceptait 100 Mo, transports bloquaient souvent dès 1 MiB | Budget **1 MiB texte**, **24 MiB requête média encodée**, **16 MiB par fichier média** ; rejet explicite hors budget |
| Confidentialité | Exceptions imprévues potentiellement affichées brutes | Messages génériques pour erreurs non gérées de `generate`; tests avec fausses clés |
| Artefacts | Base64 permissif, noms de fichiers libres, octets non bornés | Décodage strict, plafonds, préfixes de modèles assainis |

Tous les modes `mock` restent sans réseau. Les nouveaux tests simulent les connexions, certificats, DNS et réponses ; ils n'ouvrent pas de sockets vers des fournisseurs.

## 3. Qualification technique et stratégie

- Première CI complète verte de remédiation : [#42339003349](https://github.com/tawounfouet/pyllmkit/actions/runs/42339003349) (et CI PR [#42339006653](https://github.com/tawounfouet/pyllmkit/actions/runs/42339006653)), sur `fc302140c6f7ec1c069e5fba2d2e9713b14eba9f`.
- Seconde CI complète verte avec limite de requêtes : [#42339308625](https://github.com/tawounfouet/pyllmkit/actions/runs/42339308625), sur `6861e0fd89606c4b4e7eee58fee9bf2709f0bb94`. Sur chaque Python 3.11/3.12/3.13 : **3 047 pytest PASS**, **752 scénarios conformance PASS**, Ruff PASS, mypy strict PASS, wheel/sdist PASS.
- Les tests ajoutés à ce document et les changements de documentation doivent être requalifiés sur leur SHA PR final, puis sur `main` après fusion.
- Les seuils historiques de couverture ont été préservés : toute violation reste un échec de CI.

## 4. Compatibilité

L'acceptation de fichiers média locaux passe de 100 Mo théoriques à un maximum de 16 MiB cohérent avec le budget wire de 24 MiB. Les URL non approuvées, redirections et accès internes sont refusés plutôt que silencieusement redirigés. Des CDN légitimes inconnus nécessiteront un examen pour être explicitement admis. Les URLs media `kind=uri` ne sont plus téléchargeables directement par le saver CLI.

## 5. Risques résiduels et suivi

- **Provider-live non homologué** : compatibilité réelle des endpoints et CDN, quotas/budgets et temps de génération n'ont pas été certifiés par ces tests hermétiques.
- **P7-L7.8 non clos** : garde-fous egress des transports `httpx` historiques, limites de coût, rate limiting, canaris opt-in, monitoring et décisions de release restent à traiter dans [#81](https://github.com/tawounfouet/pyllmkit/issues/81). Le fait que les tests réseau simulés soient verts ne signifie pas que tous les risques de production ont disparu.
- **Distribution** : le tag `v0.3.0` reste sur `1e98d1a8184303c2a18caa14a819099a9be169cf`. Ce code multimodal `Unreleased` sur `main` ne correspond pas au contenu immuable du tag. Pas de GitHub Release ni PyPI demandé.
- **Tests de charge réels** : rafales de médias, saturation mémoire et disques, concurrence de téléchargements, interruption/cancel, CDN réels restent hors qualification actuelle.

## 6. Décision

**GO** pour intégrer les correctifs de ce chantier à `main` lorsque Ruff, mypy, pytest, gates de conformité, packaging, GitGuardian et CI post-merge exact-SHA sont tous verts. **NO-GO** pour prétendre à une certification live/production ou publier un artefact sans décision séparée du propriétaire.
