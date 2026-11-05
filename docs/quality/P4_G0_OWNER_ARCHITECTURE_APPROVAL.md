# P4-G0 - Approbation du proprietaire des decisions architecturales

> **Date :** 2026-11-05
> **Autorite :** proprietaire de PyLLMKit, autorisation explicite dans la conversation du projet : "Pythos Vas-y declare P4-G0 Architecture Ready et demarre L4.1 - Tool Domain sur une nouvelle branche d'implementation."
> **Portee :** adoption des huit ADR-022 a ADR-029 selon leur texte dans la PR #38, autorisation d'integration du dossier P4-G0 et de lancement L4.1 **sous reserve des preuves CI sur le SHA final de main**.
> **Limitations :** approbation du proprietaire en conversation; ne constitue pas une revue GitHub independante ni une preuve de branch protection.

## Decisions adoptees

| Decision | Statut adopte | Limite |
|---|---|---|
| ADR-022 | ACCEPTED | Tool est descriptif et n'execute pas |
| ADR-023 | ACCEPTED | ID d'appel explicite, correlation et 0..1 resultat final |
| ADR-024 | ACCEPTED | Profil ferme P4-JSON-1; pas de conformite Draft complet revendiquee |
| ADR-025 | ACCEPTED | Immutabilite profonde, raw/parsed/ABSENT et preuve de validation |
| ADR-026 | ACCEPTED | Choix d'outil type et capability UNKNOWN conservee |
| ADR-027 | ACCEPTED | Text/JSON/Schema et VALID/INVALID/UNKNOWN |
| ADR-028 | ACCEPTED | Option B : wrappers P4 separes, M3 inchange |
| ADR-029 | ACCEPTED | Tooling JSON v1 propre, aucune extension implicite Inference v1 |

## Gouvernance et criteres de GO

- M3 reste le socle technique (main initial 3d5ffc811c33ae6dabf392b2c7d24f7ec2a27dc6).
- PR #38 : CI PR 42078218379 et CI push branche 42078209409 SUCCESS avant cette approbation. Toute mise a jour exige un recontrole du nouveau SHA.
- Le GO technique P4-G0 est prononce uniquement apres integration des ADR et du plan sur main ET verification de la CI push exacte du nouveau main SHA.
- Sans preuve post-merge, le statut est APPROVED DESIGN / PENDING GATE EVIDENCE, pas GO atteste.
- Le proprietaire autorise l'ouverture de la branche L4.1 apres le GO technique P4-G0; le merge de la PR L4.1 requiert sa propre qualification.
- Issues #22 (protection de main), #35 (release) et #36 (frontiere provider) restent ouvertes. La publication reste NO-GO. Aucune revue tierce n'est inventee.
- Aucun code P4 n'est livre par cette decision seule.

## Historique

- 2026-11-05 : propositions ADR-022..029 redigees sur la PR #38.
- 2026-11-05 : owner demande de declarer P4-G0 et de commencer L4.1.
- Integration et CI main : a consigner dans le PV final avec SHA precis.
