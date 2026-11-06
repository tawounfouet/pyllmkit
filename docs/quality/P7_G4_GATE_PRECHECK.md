# PyLLMKit - P7-G4 - OpenAI Responses Adapter - Préqualification

- Date: 2026-11-06
- Statut: PRECHECK TECHNIQUE DE PR, P7-G4 NON CLOTURE
- PR: https://github.com/tawounfouet/pyllmkit/pull/73
- Branche: `p7/l74-openai-responses-adapter`
- HEAD avant ce précheck: `8d0a876b8c2ba0863f8d736b355d416570bbe8ef`
- CI finale: à vérifier sur SHA exact du commit final
- Dépendances non fusionnées: #70, #71, #72

## Résultats contrôlés sur le HEAD précédent

- Python 3.12, CI push #42193964395, jobs de validation : succès.
- Tests généraux: 1 396 passed; couverture domaine historique 96,61 % (branches).
- L7.1: 34 passed, couverture 98,44 %.
- L7.2: 75 passed, couverture 100,00 %.
- L7.3: 44 passed, couverture 98,90 %.
- L7.4: 54 passed, couverture 99,69 % avec branches, seuil précédent 85 %.
- Ruff et mypy strict (104 fichiers source) réussis sur Python 3.12.
- Packaging wheel/sdist et exemples hors réseau validés par la CI.
- Les tests L7.1..L7.4 sont sous-ensembles exécutés à nouveau et ne
  doivent pas être additionnés aux 1 396 tests généraux comme cas distincts.

Le présent commit relève le seuil L7.4 à 95 %, documente le contrat API
et ajoute un smoke d'import de la wheel sans HTTPX, à vérifier en CI final.

## Matrice d'acceptation proposée

| AC | Contract offline | Limite |
|---|---|---|
| 025 | Activation explicite et aucune requête par défaut | pas de live |
| 026 | API Responses, store=false, tools interdits, usage/RunId | mock |
| 027 | ordre et rôles préservés, aucun effacement | mock |
| 028 | paramètres compatibles et rejets | profil texte limité |
| 029 | statuts, outputs non textuels, usages partiels, UNKNOWN | mocks |
| 030 | HTTP 3xx/4xx/5xx, secrets et bodies non exposés | mock |
| 031 | parité sync/async et headers contrôlés | mock |
| 032 | deadline et tailles bornées, erreurs sûres | pas de budget live |

## Risques / réserves

- Aucune première invocation OpenAI réelle; pas de facturation engagée.
- Le profil rejette les items reasoning/refusal/tool, conformément à ADR-054.
- Le transport utilise HTTPX et non le SDK officiel `openai` : revue de
  conformité API continue et tests de dérive contractuelle indispensables.
- Deadline sync non strictement murale face à une réponse trickle.
- Le budget cloud n'est pas encore gouverné par un mécanisme applicatif
  exécutoire. NO-GO live jusqu'à définition et validation du budget.
- Aucune revue humaine indépendante enregistrée sur #70..#73 au démarrage.
- `main` non protégée (#22); release (#35) et boundary (#36) ouvertes.
- Version `0.1.0a2` inchangée; `0.2.0a2` cible seulement.

## Verdict

GO POUR REVUE DE PR SI CI DU HEAD FINAL REUSSIE. NO-GO POUR FUSION
AUTOMATIQUE, CLOUD LIVE PAYANT, TAG, PUBLICATION OU PRODUCTION.

Après validation des dépendances, rebaser/retarget puis qualifier la CI
sur les SHA exacts, obtenir revue indépendante, et archiver un PV final.
