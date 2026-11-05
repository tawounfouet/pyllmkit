# ADR-029 - Tooling JSON v1, versioning and no silent loss

- Date : 2026-11-05
- Statut : RECOMMENDED FOR P4-G0 ADOPTION
- Phase : L4.4 et L4.5
- Sources : ADR-004/012/020/025/028, Model/Interaction/Inference JSON v1.

## Decision recommandee

1. Creer **Tooling JSON v1** sous namespace distinct, avec schema_version entier exact 1 et object_type discriminant strict. Ne jamais ajouter de cles P4 aux enveloppes Inference JSON v1.
2. Les enveloppes necessaires a M4 sont tool_definition, tool_choice, tool_call, tool_result, response_format, structured_output et, si les wrappers ADR-028 sont retenus, tooling_inference_intent et tooling_inference_observation.
3. Chaque kind dispose d'une liste ferme de champs requis, y compris les champs nullable explicitement presents. Une cle inconnue, omise, mal typee, ou un object_type/schema_version inconnu est refuse. L'ordre des ToolCalls et des tools est preserve.
4. Les IDs, le raw, la valeur parsed ou ABSENT, les statuts UNKNOWN/VALID/INVALID et is_error doivent traverser les round-trips sans perte. JSON null n'est pas ABSENT; absence de champ n'est pas null.
5. Le codec convertit des objets de domaine en valeurs JSON compatibles et inversement. Il ne lit pas de fichier, ne parse pas de flux HTTP et n'appelle pas de provider. Le texte JSON et le refus des cles dupliquees dans un texte appartiennent a la frontiere de parsing; un exemple de parseur strict et des tests de boundary seront fournis.
6. Toute tentative de serialiser une valeur P4 non representable via Inference JSON v1 doit echouer explicitement. Le downgrade avec perte de sens, les conversions ToolCallOutput -> TextOutput et la creation de ToolResult sont interdits.
7. Les garanties immutables et le profil P4-JSON-1 des ADR-024/025 s'appliquent aux charges. Aucun raw, schema sensible ni secret n'apparait dans les messages d'erreur ou repr.
8. **Inference JSON v2 n'est pas cree a G0 ni promis comme livrable obligatoire de M4.** Il faudra une ADR separee, des fixtures de migration, un codec distinct et une justification d'integration avant toute creation.

## Alternatives ecartees

- Extension opportuniste de v1 : rupture du contrat strict accepte.
- Unknown keys ignorees : perte silencieuse.
- Codec unique provider-like : couplage au format d'une API particuliere.

## Validation

P4-AC-029..032, 038/039. Fixtures JSON canoniques, round-trip multi-objets, tests de rejet de versions et kinds inconnus, de pertes d'IDs, de valeurs non finies, de champs inconnus et de regression Model/Interaction/Inference v1. Wheel/sdist sans provider.
