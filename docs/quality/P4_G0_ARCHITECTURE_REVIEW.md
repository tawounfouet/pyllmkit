# P4-G0 - Revue contradictoire de l'architecture

> Date de revue : 2026-11-05. Etat : TECHNICAL DESIGN REVIEW COMPLETED; owner sign-off et gate post-merge encore ouverts.
> Repository : tawounfouet/pyllmkit. PR de conception : #38.

## Baseline et preuves consultees

- main : 3d5ffc811c33ae6dabf392b2c7d24f7ec2a27dc6 ; plan P4 de la branche de PR #38.
- Baseline M3 : M3_GATE_REVIEW, GO technique avec reserves; CI main #42070067345, 802 tests et couverture globale 95 % sur Python 3.11 rapportes par la qualification.
- Controle direct du code : request.py ne contient que target/messages/generation_config; response.py n'accepte que TextOutput; output.py definit InferenceOutput comme alias TextOutput; serialization.py impose Inference JSON v1 avec champs exacts; compatibility.py valide uniquement les parametres de generation.
- GitHub : les ADR-001..021 existent sur main, aucune collision pour ADR-022..029; PR #38 ouverte en draft avec CI initiale success; aucune review GitHub soumise.
- Gouvernance : /branches/main indique protected=false; endpoint /branches/main/protection refuse 403 avec les droits du connecteur; /rulesets retourne []; issues #22/#35/#36 ouvertes.

## Matrice de revue des decisions

| Risque critique | Choix propose | Element falsifiable / gate |
|---|---|---|
| Execution arbitraire | ADR-022 aucun executable dans Tool | Tests architecture L4.1, AC-033 |
| Appels confondus | ADR-023 IDs explicites, correlation stricte | AC-009..016 |
| Conformite JSON sur-vendue | ADR-024 profil P4-JSON-1 ferme, reject unknown | AC-002/019/021/038 |
| Mutation cachee | ADR-025 gel profond, raw != parsed != preuve | AC-012/013/024/039 |
| Capability inventee | ADR-026 support UNKNOWN distinct de NATIVE | AC-023/026/027 |
| Sortie invalide promue valide | ADR-027 validation explicite | AC-017..024 |
| M3 API deterioree | ADR-028 composition B sans mutation des classes M3 | AC-025..029/032 |
| Codec v1 altere | ADR-029 namespace Tooling v1 autonome | AC-029..032 |

## Arbitrages explicitement recommandes

**F-01 - Schema :** un profil limite est preferable a une conformite Draft 2020-12 non prouvee. Les mots-cles inconnus et references distantes sont refuses. Les limites de taille/profondeur sont locales au domaine, documentees et testables.

**F-02 - Immutabilite :** les Value Objects utilisent une copie profonde et une representation JSON reellement immutable. frozen dataclass seule ne suffit pas.

**F-03 - Compatibilite M3 :** choisir Option B. Il n'existe aucun besoin P4-M4 prouve imposant de modifier InferenceRequest / InferenceResponse ni de produire Inference JSON v2. Le risque de rupture v1 est superieur a la commodite d'ajouter des champs aujourd'hui.

**F-04 - Tool boundary :** le resultat d'un outil n'est pas le resultat d'execution d'une inference, et la demande d'appel n'est pas l'execution. M4 reste offline.

**F-05 - Evidence :** une CI de la PR ne vaut pas CI du SHA integre sur main. La revue GitHub est absente et la protection de main n'est pas enforcee.

## Conditions avant verdict P4-G0 GO

1. Le proprietaire accepte explicitement le profil P4-JSON-1, le gel profond et la composition B avec un codec autonome.
2. Les huit ADR et le registre sont integres sans collision sur main via une PR; aucune fusion sans decision du proprietaire.
3. La CI de PR est verte apres ajout des ADR, puis la CI push sur le nouveau SHA main est verte (Python 3.11, 3.12, 3.13, Ruff, mypy, tests, exemples, packaging).
4. Un PV gate final documente SHA, PR, review, CI et reserves; la protection de main reste un risque gouvernance explicite.
5. L4.1 ne commence pas sous statut G0-GO avant ces preuves.

## Avis de revue

Les huit arbitrages sont **coherents et recommandables pour adoption**. L'absence de signature sur leurs versions finales et de preuve sur main interdit a cette etape de qualifier G0 comme GO effectivement realise. Aucune release n'est autorisee.
