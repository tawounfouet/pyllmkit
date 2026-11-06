# PyLLMKit - P7-G3 Ollama Adapter - Precheck

- Date: 2026-11-06
- Statut: GO TECHNIQUE POUR REVUE DE PR; NO-GO LIVE ET NO-GO FUSION
- PR: https://github.com/tawounfouet/pyllmkit/pull/72
- HEAD de code vérifié avant ce document: `fa2b5f07e057e927e779567dac773af40907733f`
- CI push: https://github.com/tawounfouet/pyllmkit/actions/runs/42192518529
- CI pull request: https://github.com/tawounfouet/pyllmkit/actions/runs/42192523733
- CI du HEAD documentaire final: vérifier sur SHA exact après le présent changement
- Dépendances: #70 (P7-G1), #71 (P7-G2), non fusionnées

## Contrôles observés

| Axe | Résultat observé |
|---|---|
| Python 3.11, 3.12, 3.13 | Matrice de CI sur PR / push, statut à relire sur SHA final |
| Tests généraux | 1 342 passed en environnement Python 3.12 |
| Couverture du domaine historique | 96,61 % avec branches |
| L7.1 | 34 tests, 98,44 % |
| L7.2 | 75 tests, 100,00 % |
| L7.3 | 44 tests, 98,90 % avec branches (seuil à fixer à 95 %) |
| Ruff, mypy | CI Python 3.12: succès (102 modules source) |
| Wheel et sdist | Vérifications package inclues dans CI |
| HTTP réseau réel | AUCUN dans CI |
| Appel à un modèle Ollama réel | NON EXÉCUTÉ |

Les comptes des tests spécialisés peuvent réexécuter certains tests des
1 342 tests généraux. Ne pas sommer ces nombres comme tests distincts.

## Couverts par les tests simulés P7-AC-017..024

- Opt-in local explicite (par défaut aucun réseau).
- Encodage rôle et texte avec mapping non destructif.
- Refus des paramètres incompatibles et des blocks non textuels.
- Préservation du RunId, des usages partiels et des finish reasons inconnues.
- HTTP 3xx, 4xx, 5xx et erreurs réseau normalisées.
- Async réel avec HTTPX MockTransport, sans invoquer de modèle.
- Bornes de taille, refus des endpoints non conformes, deadlines expirées.
- Validation de la séparation des SDK HTTP optionnels et du coeur Python.

## Risques et NON-proven

- `MockTransport` prouve des contrats locaux, pas une invocation réelle.
- La première réponse d'un vrai démon Ollama est encore à démontrer sur
  poste autorisé. Le script `examples/32_ollama_live_opt_in.py` nécessite
  un opt-in triple plus un alias de modèle explicite; pas d'exécution dans CI.
- Revue indépendante de code et sécurité transport non constatée.
- La deadline murale stricte en streaming de réponse synchrone n'est pas
  encore garantie par le timeout par phase HTTPX (risque de trickle).
- Le serveur Ollama local et sa propre configuration sont hors du périmètre
  de garantie du client; il ne doit pas écouter sur une interface LAN.
- Les factories `_test_transport` sont réservées à la simulation et
  n'attestent aucune sécurité si un transport arbitraire est injecté.
- #22 `main` non protégée, #35 release, #36 boundary demeurent ouverts.
- Version déclarée reste 0.1.0a2, pas de tag, pas de release PyPI.

## Règle d'enchaînement

Réaliser revue et qualification finale G1 -> fusion #70 -> CI main SHA exact,
puis G2 -> retarget #71, fusion et CI main SHA exact. Rebaser/retarget #72
une fois les dépendances satisfaites; obtenir revue de sécurité, smoke live
local autorisé et son attestation assainie. G3 ne peut devenir GO final avant
ces étapes. Aucune fusion ni publication autorisée par ce précheck.
