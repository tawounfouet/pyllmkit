# ADR-023 - ToolCall identity and correlation

- Date : 2026-11-05
- Statut : ACCEPTED (owner, 2026-11-05; P4-G0 qualifié main@b66e94e3, CI #42079191595 SUCCESS)
- Phase : L4.2
- Sources : ADR-022, TOOL-004 a TOOL-010, domaine 05/06, P4-AC-009 a 016.

> Approbation du proprietaire : [P4_G0_OWNER_ARCHITECTURE_APPROVAL.md](../quality/P4_G0_OWNER_ARCHITECTURE_APPROVAL.md). Aucune revue tierce revendiquee.

## Contexte

Plusieurs appels peuvent utiliser le meme outil avec les memes arguments. Leur egalite de contenu ne suffit pas pour determiner a quel appel rattacher un resultat.

## Decision adoptee

1. ToolCallId est un Identifier/Value Object opaque, sensible a la casse, de type str exact, non vide apres une verification de blanc, avec une longueur maximale documentee de 256 caracteres. Aucun UUID automatique et aucune normalisation destructive.
2. ToolCall est une Entity immutable par snapshot. Son egalite et son hachage reposent sur ToolCallId; sa comparaison par contenu est une operation differente. Deux appels a arguments identiques mais a IDs distincts sont deux appels.
3. La portee d'unicite est un contexte local explicite de correlation, pas le monde entier. Les identifiants issus d'un provider sont conserves comme valeurs lorsqu'ils respectent le contrat, sans presumer de leur unicite globale.
4. ToolCall contient tool_name et ToolArguments. Son nom doit referencer une declaration disponible dans le contexte de validation fourni. Aucune recherche implicite dans un registry distant.
5. ToolResult porte obligatoirement un ToolCallId identique a celui d'un appel connu du contexte. La correspondance sur le seul tool_name est interdite.
6. M4 accepte au plus un resultat final par ToolCall dans un meme contexte. L'attachement d'un second resultat final est rejete, y compris s'il reproduit la meme valeur. Les deltas de streaming sont reserves a P5.
7. Un resultat est soit un succes, soit un echec explicite via is_error de type bool exact. Aucune inversion implicite du statut, aucune exception native recopiee en clair.
8. Aucune correlation a InferenceRunId n'est inventee. Un lien a un Run, s'il existe, doit etre fourni explicitement par le caller dans une composition distincte.

## Alternatives ecartees

- Identifiant derive de tool_name + arguments : collisions entre appels legitimes.
- Auto-generation lors de la construction : provenance masquee.
- Association 0..n de resultats finaux : ambiguites pour M4.

## Preuves et criteres

P4-AC-009..016 : collision, ID vide, outil inconnu, arguments bruts distincts, resultat orphelin, resultat final duplique et is_error. Les tests doivent prouver l'absence d'execution et de fuite sensible dans repr / erreurs.

## Migration

Pas de conversion de ToolCall en TextOutput M3. Un ToolResult doit rester distinct d'une reponse d'inference.
