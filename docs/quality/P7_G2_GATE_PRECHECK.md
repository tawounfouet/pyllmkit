# PyLLMKit - P7-G2 Secure Connection & Adapter Registry - Precheck

- Date: 2026-11-06
- Statut: GO TECHNIQUE DE PR, AVEC RÉSERVES - PAS UN GO DE FUSION
- Phase: P7 / lot L7.2, gate G2
- Dépendance: PR #70 (L7.1) en attente de revue humaine indépendante et fusion
- PR de ce lot: https://github.com/tawounfouet/pyllmkit/pull/71
- Dernier code qualifié avant ce précheck: `895bcd5f0c918925d58e08eadc3156babd4f755a`
- CI code push: https://github.com/tawounfouet/pyllmkit/actions/runs/42190550820 - SUCCESS
- CI code PR: https://github.com/tawounfouet/pyllmkit/actions/runs/42190557150 - SUCCESS
- Nouveau HEAD après précheck: nouveau SHA à vérifier sur CI, sans présumer du résultat.

## Contrôles observés sur le code

| Contrôle | Preuve |
|---|---|
| Python 3.11/3.12/3.13 | CI push et PR: success sur la matrice |
| Ruff | success |
| mypy strict | success, 100 fichiers source |
| Tests généraux | 1 298 passed sur Python 3.11 |
| Couverture avec branches du domaine historique | 96.61 %, seuil 95 % |
| Tests L7.1 séparés | 34 passed, 98.44 % de couverture du noyau et fake |
| Tests L7.2 spécifiques | 75 passed, 100.00 % de couverture des 5 modules mesurés, avec branches |
| Exemple 30 | exécution hermétique vérifiée dans CI |
| Sdist et wheel | build et smoke tests en CI réussis |
| Provider SDK / réseau réel | aucun; profil statique seulement |

## Vérifications P7-AC

- P7-AC-009: registre exécutable séparé du catalogue descriptif.
- P7-AC-010: exactitude, doublons et choix du binding, absence de fallback.
- P7-AC-011: factories différées, contrats sync/async indépendants.
- P7-AC-012: références opaques, redaction, source env explicitement autorisée.
- P7-AC-013: cloud official endpoints seuls; TLS requis et redirects interdits.
- P7-AC-014: Ollama loopback par IP et opt-in; rejets SSRF syntaxiques.
- P7-AC-015: validation des deadlines/options; rejet des hôtes et types non conformes.
- P7-AC-016: erreurs de transport HTTP normalisées sans payload natif.

Cette qualification couvre les contrats offline et ne prétend pas démontrer
la sûreté de connexions réelles, de résolution DNS, de proxies ou de TLS.

## Réserves et frontières

1. PR #70 doit être revue et qualifiée; ne pas fusionner la PR #71 avant G1.
2. Aucune revue de code/sécurité humaine indépendante ne figure dans les preuves.
3. `main` était non protégée lors du contrôle P7-G0 (#22). À vérifier avant merge.
4. Aucun adapter transport Ollama/OpenAI/Anthropic n'est implémenté en L7.2.
5. DNS pinning, validation IP réellement connectée, TLS runtime, proxy, redirects
   et secret handling d'un vrai transport devront être vérifiés en L7.3 avant GO live.
6. #35 release NO-GO et #36 frontière provider demeurent réservées.
7. Les versions 0.2.0a1..0.2.0a3 sont des cibles, pas des releases.

## Décision

**GO technique pour soumettre la PR #71 en revue et préparer L7.3 en sandbox.**
**NO-GO de fusion de #71 sur main, GO live, tag ou PyPI** avant revue indépendante,
qualification de la chaîne de dépendance et preuves de transports contrôlés.

Le verdict final G2 devra être réévalué après décision de fusion et CI push
sur le SHA exact de main. Aucun contrôle ne peut être inféré de ce précheck.
