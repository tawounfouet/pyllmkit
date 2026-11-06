# PyLLMKit - P7-G5 Anthropic Messages Adapter - Précheck

- Date : 2026-11-06
- Statut : GO TECHNIQUE DE PR, NO-GO LIVE ET NO-GO FUSION
- PR : https://github.com/tawounfouet/pyllmkit/pull/74
- Base stackée : `p7/l74-openai-responses-adapter` (PR #73)
- Pré-requis non fusionnés : PR #70, #71, #72, #73
- HEAD code vérifié avant ce précheck : `5375903ba668c450d986adf07eda1c9e456566a1`
- CI push code : https://github.com/tawounfouet/pyllmkit/actions/runs/42195723306
- CI PR code : https://github.com/tawounfouet/pyllmkit/actions/runs/42195730208
- CI du HEAD final documentaire : en attente de vérification SHA

## 1. Contrôles techniques observés

| Critère | Résultat initial constaté |
|---|---|
| Ruff | PASS |
| mypy strict | PASS, 106 fichiers source |
| Python 3.11, 3.12, 3.13 | CI push 3/3 jobs success |
| Tests généraux | 1 463 passed |
| Couverture domaine historique | 96,61 % avec branches, seuil 95 % |
| L7.1 | 34 tests, 98,44 % |
| L7.2 | 75 tests, 100,00 % |
| L7.3 | 44 tests, 98,90 % |
| L7.4 | 54 tests, 99,69 % |
| L7.5 | 67 tests, 99,45 % avec branches |
| Transport réseau réel | NON EXECUTE |
| Test cloud facturé | NON EXECUTE |
| Qualité distribution | wheel/sdist et exemples offline testés en CI |

Les tests ciblés des lots précédents sont rejoués et inclus dans
l'ensemble général. Ne jamais les sommer comme s'il s'agissait de
tests distincts.

Le présent commit renforce le seuil CI dédié L7.5 à 95 %, conserve les
tests hermétiques et confirme l'import de la wheel sans HTTPX.
Les résultats devront être confirmés sur son SHA final exact.

## 2. P7-AC-033 à P7-AC-040

| AC | Test métier / infrastructure | Limite |
|---|---|---|
| 033 | `allow_live=False`, zéro requête | mock |
| 034 | `POST /v1/messages`, headers, max_tokens, correlation | mock |
| 035 | mapping SYSTEM et alternance, refus DEVELOPER/TOOL | domaine strict |
| 036 | paramétrage explicite et support NATIVE | snapshot fourni |
| 037 | stop_reason, refus tools et reasoning | fixtures |
| 038 | Usage partiel, cache read, cache create refusé | pas de coûts |
| 039 | codes HTTP, secrets masqués, absence de fuite | MockTransport |
| 040 | parité async, timeout, taille et erreurs | MockTransport |

## 3. Réserves et critères NO-GO

- Les PR #70..#73 restent ouvertes et sans revues indépendantes
  constatées au dernier contrôle. G1-G4 non clôturés sur main.
- Protection `main` non active (#22). Release non autorisée (#35),
  frontière provider toujours sous réserve (#36).
- Le transport est une implémentation HTTPX filaire, pas le SDK Anthropic
  officiel. Le versionnement de l'API est épinglé à `2026-10-21`, avec
  obligation de surveiller la dérive contractuelle.
- Deadline synchrone face à une réponse trickle sans garantie stricte.
- Les règles de rétention de données et les politiques de sécurité du
  fournisseur restent applicables.
- Aucune autorisation de coût, budget exécutoire ni smoke live réel.
- Version courante `0.1.0a2`. Pas de tag/release PyPI.

## 4. Décision proposée

GO uniquement pour revue technique de PR #74 si la CI du HEAD final est
réussie. NO-GO merge automatique, live payant et production.

La clôture P7-G5 nécessitera revue humaine indépendante, qualification
de la chaîne G1-G4, preuve live autorisée (budget et secrets hors logs),
CI PR et CI post-merge sur SHA exact, et procès-verbal final.
