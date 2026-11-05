# ADR-028 - Composition of P4 with qualified M3 contracts

- Date : 2026-11-05
- Statut : ACCEPTED (owner, 2026-11-05; P4-G0 qualifié main@b66e94e3, CI #42079191595 SUCCESS)
- Phase : L4.4
- Sources : ADR-014/017/020/021, Inference M3 qualifiee, plan P4 section 4.1.

## Constat technique verifie sur main

- InferenceRequest(target, messages, generation_config) ne connait pas tools, tool_choice ou response_format.
- InferenceResponse.output accepte seulement TextOutput; InferenceOutput est un alias de TextOutput, pas une union runtime.
- Inference JSON v1 exige exactement ses champs, sans extensions P4.
- GenerationSupportSnapshot couvre uniquement la generation; aucun snapshot P4 n'est implicite.

> Approbation du proprietaire : [P4_G0_OWNER_ARCHITECTURE_APPROVAL.md](../quality/P4_G0_OWNER_ARCHITECTURE_APPROVAL.md). Aucune revue tierce revendiquee.

## Decision adoptee : OPTION B

1. Preserver exactement les constructeurs, types, egalite, immutabilite, codecs et invariants M3. **Aucune modification de InferenceRequest, InferenceResponse, InferenceRun ni Interaction JSON v1 en P4.**
2. Introduire une composition explicite, initialement nommee ToolingInferenceIntent, contenant une InferenceRequest M3 intacte, un tuple ordonne de Tool, ToolChoice optionnel et ResponseFormat optionnel. Toute politique de choix est validee contre ses outils.
3. Introduire, seulement si utile pour les cas d'acceptation, une ToolingInferenceObservation contenant des ToolCall et une StructuredOutput optionnelle, independamment de InferenceResponse M3. Tout InferenceRunId associe est fourni explicitement par le caller. Ne jamais fabriquer une InferenceResponse avec TextOutput fictif.
4. Un ToolCallOutput peut etre represente comme un Value Object P4 autonome, jamais comme un nouveau variant du codec Inference v1. FinishReasonCode.TOOL_CALL n'implique pas qu'un ToolResult a ete execute.
5. Les rapports de compatibilite P4 consomment des declarations TOOL_CALLING / STRUCTURED_OUTPUT explicites. Une cible de M3 ne devient pas automatiquement compatible avec P4.
6. Un Run M3 ne doit pas passer a COMPLETED uniquement pour rendre une sortie outil non representable en TextOutput. La gestion runtime de sorties alternatives sera arbitree dans une future ADR v2.
7. Les API P4 sont provider-agnostic et ne necessitent aucun endpoint, credentiel ni executor.

## Alternative A repoussee

Ajouter tools, tool_choice, response_format a InferenceRequest et des variants a InferenceResponse necessiterait un nouveau contrat API et un Inference JSON v2 avec migrations. Cette option sera reevaluee seulement si des cas d'usage observes la justifient.

## Criteres de qualification

Zero changement de schemas Model/Interaction/Inference v1; aucune suppression de champs; tests sur composition vide, simple et multiple, IDs, support inconnu, output ToolCall distinct du TextOutput, non regression M1/M2/M3. P4-AC-025..029/032.
