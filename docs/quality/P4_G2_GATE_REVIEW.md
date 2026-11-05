# PyLLMKit - P4-G2 Tool Call Ready - Revue de gate

> Date : 2026-11-05
> Decision : **GO TECHNIQUE AVEC RESERVES**, autorisation d'ouvrir L4.3.
> SHA exact qualifiant de main : [a7991d9fc6648b280744e7ca461d79c7c2544b60](https://github.com/tawounfouet/pyllmkit/commit/a7991d9fc6648b280744e7ca461d79c7c2544b60).
> CI push/main : [GitHub Actions #42084636736](https://github.com/tawounfouet/pyllmkit/actions/runs/42084636736), **completed/success**.
> Autorite : proprietaire du projet, instruction explicite de valider et fusionner la PR #42.
> No release / tag / publication : **NOT AUTHORIZED**.

## 1. Portee de la decision

P4-G2 confirme la disponibilite technique des primitives de domaine pour representer, valider et correler localement des demandes d'appels d'outils et leurs resultats. Ce gate **ne** valide **pas** l'execution des outils, ni un provider SDK, ni un agent, ni les sorties structurees (L4.3), ni le streaming (P5).

## 2. Preuves exactes

| Controle | Etat / preuve |
|---|---|
| Baseline P4-G1 | GO avec reserves, [P4_G1_GATE_REVIEW.md](P4_G1_GATE_REVIEW.md) |
| PR du lot | [#42](https://github.com/tawounfouet/pyllmkit/pull/42), merge squash autorise par le proprietaire |
| Head PR | b6c4e8366c1a4b834ba473a570f9ef55138e14bb |
| CI PR qualifiante | [#42083476399](https://github.com/tawounfouet/pyllmkit/actions/runs/42083476399) completed/success |
| SHA main apres merge | a7991d9fc6648b280744e7ca461d79c7c2544b60 |
| CI push/main | [#42084636736](https://github.com/tawounfouet/pyllmkit/actions/runs/42084636736), completed/success |
| Python 3.11 | SUCCESS, job 127446332232 |
| Python 3.12 | SUCCESS, job 127446331934 |
| Python 3.13 | SUCCESS, job 127446332314 |
| Tests Python 3.11 | **884 passed**, zero echec |
| Couverture globale branches incluses | **95 %** (1788 statements, 65 misses, 688 branches, 58 partial) |
| Ruff | All checks passed |
| mypy strict | Success: no issues found in 49 source files |
| Wheel / sdist / exemples | Workflow CI complet SUCCESS, exemple 14 inclus en source et environnements isoles |
| Cas d'acceptation | P4-AC-009..016 dans tests/acceptance/test_p4_l42_tool_calls.py |
| Non-regression M1-M3/L4.1 | Tests cumulatifs et CI main verts |
| Revue GitHub tierce | **ABSENTE**; l'approbation du proprietaire est distincte |
| Protection main | **NON EFFECTIVE**, protected=false a la verification du 2026-11-05 |
| Release | **NON AUTORISEE**, issue #35 ouverte |

Le chiffre de 884 tests correspond a la suite **cumulative** et non a 884 tests specifiques L4.2.

## 3. Objets et semantique qualifies

- `ToolCallId` : identifiant fourni par le caller, explicite, opaque, valide et stable dans le contexte local.
- `ToolArguments` : chaine raw optionnelle, parsed optionnel et distinct de JSON null, stockage JSON immutable.
- `ToolCall` : Entity immutable, egalite definie par son identite et non ses parametres; aucune execution.
- `ToolResult` : valeur JSON immutable et statut d'echec explicite `is_error`; aucune generation automatique.
- `validate_tool_call` : validation declarative des arguments parses selon P4-JSON-1, rapport VALID/INVALID/UNKNOWN, sans inference de conformite a partir de raw.
- `attach_tool_result` : operation pure; rejette appels ou resultats dupliques, resultat orphelin, ID inconnu.
- `examples/14_define_tool_call_and_result.py` : demonstration offline.

## 4. NO-GO revus sur le perimetre du gate

1. Identite ambigue ou auto-generee : non constatee dans le perimetre qualifie.
2. Resultat orphelin / final duplique accepte : refus par validations et tests.
3. Raw confondu avec parsed / UNKNOWN promu VALID : tests negatifs disponibles.
4. Validation par execution de code : aucun executant dans le domaine.
5. Dependances provider / secrets / reseau : absence controlee par fitness tests et installation offline.
6. Regressions M1/M2/M3 : suite complete CI verte.

Ces conclusions ne representent pas un audit de securite d'un futur executant ni une attestation de production.

## 5. Reserves et recommandations

- [#22](https://github.com/tawounfouet/pyllmkit/issues/22) : protection effective de main a corriger. Les procedures de CI pratiques ne compensent pas une politique GitHub enforced.
- [#35](https://github.com/tawounfouet/pyllmkit/issues/35) : decision de release a traiter separement.
- [#36](https://github.com/tawounfouet/pyllmkit/issues/36) : futurs adapters provider et frontiere I/O non encore qualifies.
- Aucun APPROVED review humain independant sur la PR #42. Autorite owner explicite, revue technique assistee.

## 6. Verdict et suite

**P4-G2 = GO TECHNIQUE AVEC RESERVES** sur le SHA qualifiant indique.

Ouverture autorisee de **L4.3 - Structured Output** sur une nouvelle branche. Portee cible : `TextResponseFormat`, `JsonResponseFormat`, `SchemaResponseFormat`, `StructuredOutput` et validation pure selon ADR-024/025/026/027. La prochaine gate sera P4-G3, a qualifier sur son propre SHA main.

## 7. Archivage

Ce PV est cree dans une PR documentaire apres la qualification du SHA main. Sa propre CI et sa fusion sont un travail d'archivage distinct, sans pretendre que le PV etait present sur le commit de qualification.
