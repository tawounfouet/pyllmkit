# PyLLMKit - P3 L3.2 Implementation Summary

> Date: 2026-11-05
> Lot: L3.2 - Inference Response Domain
> Statut: IMPLEMENTED ON FEATURE BRANCH - G2 NOT YET QUALIFIED
> Release: 0.1.0a3 future candidate, non publiee (metadata 0.1.0a2)
> Architecture: ADR-014, ADR-017, ADR-018 ACCEPTED at G0
> Baseline: main 11b838f7002557a8232665f2af21f64bb2958938 (G1 GO)
> Gate: P3-G2 to be decided only after PR merge and CI on exact main SHA

## Livrables de code

| Fichier | Primitive | Responsabilite |
|---|---|---|
| inference/identifiers.py | InferenceRunId | Identite forte explicite et immuable, partageable avec le futur aggregate Run |
| inference/output.py | TextOutput; InferenceOutput alias | Sortie texte y compris vide, type discriminant text; famille conceptuelle non instanciable |
| inference/finish.py | FinishReasonCode, FinishReason | Sept codes fermes; native_reason optionnel preserve; absent None != UNKNOWN |
| inference/usage.py | Usage | Cinq compteurs exacts non negatifs ou None; aucun total calcule |
| inference/response.py | InferenceResponse | Value Object immutable, correlation RunId et sortie requise |
| inference/__init__.py et domain/__init__.py | Reexports publics | Compatibilite ascendante M1/M2/L3.1 |
| examples/09_define_inference_response.py | Exemple hors ligne | Aucun fournisseur contacte |

## Tracabilite P3-AC-008..013

| AC | Test | Resultat attendu |
|---|---|---|
| 008 | Response + TextOutput | Valeurs normalisees, pas de SDK |
| 009 | FinishReason UNKNOWN | Valeur native preservee, pas de STOP invente |
| 010 | Usage absent | None et non des zeros |
| 011 | Usage partiel | total_tokens non invente |
| 012 | Compteur negatif, bool et float | Rejet DomainValidationError |
| 013 | Usage != Pricing != Cost | Aucun champ ou calcul de tarification |

L'ensemble des tests P3 est independant des credentials, appels reseau et des formats wire providers. Une response n'est pas un Run et ne suppose pas son etat COMPLETED; L3.3 implementera les transitions et la verification run_id lors de complete. Le codec JSON Inference v1 est reserve a L3.4.

## Cas particuliers

1. `TextOutput("")` est valide; `TextOutput(None)` echoue.
2. `FinishReason(FinishReasonCode.UNKNOWN, "native")` est distinct de `finish_reason=None`; aucune normalisation implicite.
3. `FinishReasonCode.TOOL_CALL` decrit uniquement une raison d'arret, sans tools executables.
4. `Usage(input_tokens=10, output_tokens=4, total_tokens=99)` conserve 99, observe, sans corriger la source.
5. `Usage()` est un VO structurellement valide sans observation; pour une source qui ne rapporte aucun usage, preferer `InferenceResponse(..., usage=None)`.
6. `InferenceRunId` est fourni par l'appelant, et aucun UUID/clock/retry ou provider metadata n'est genere.
7. La repr textuelle de TextOutput/InferenceResponse omet le texte genere et celle de FinishReason omet la valeur native; ce n'est pas une promesse de redaction en aval.

## Qualite et gates

- Couverture attendue : tests unitaires, erreurs de type, immutabilite, hash/value equality, Unicode/vide, source native, partial Usage et acceptance 008..013.
- Architecture : test L3.1/L3.2 des imports et interdictions SDK.
- CI : Ruff, mypy, pytest avec couverture branche, exemples offline, packaging wheel/sdist et smoke L3.2.
- **Aucun resultat CI final ni GO G2 n'est declare par cette note.** Les preuves exactes de commit devront etre ajoutees au PV G2 apres integration controlee.
- Risques preexistants : issue #20 (dette M2), issue #22 (main non protegee). Aucune release autorisee.

**Prochaine action : CI sur PR, merge controle si qualifie, CI main exact puis PV G2.**
