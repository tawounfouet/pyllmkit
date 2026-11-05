# PyLLMKit - Registre de decisions architecturales P4-G0

> Date : 2026-11-05. Statut : propositions **resolues techniquement** dans la PR #38, non encore adoptees sur main. Ce registre ne constitue ni une review GitHub APPROVED ni une preuve CI post-merge.

| ADR | Decision recommandee | Lots | Etat |
|---|---|---|---|
| [ADR-022](../adr/ADR-022-tool-definition-and-execution-boundary.md) | Tool descriptif, aucune execution | L4.1/2 | RECOMMENDED |
| [ADR-023](../adr/ADR-023-tool-call-identity-and-correlation.md) | ToolCallId opaque explicite, 0..1 resultat final | L4.2 | RECOMMENDED |
| [ADR-024](../adr/ADR-024-json-schema-profile-and-validation.md) | P4-JSON-1, profil ferme et borné, sans $ref | L4.1/3 | RECOMMENDED |
| [ADR-025](../adr/ADR-025-immutable-json-raw-parsed-and-validation.md) | Gel profond, raw/parsed/ABSENT distincts, VALID prouve | L4.1/2/3/4 | RECOMMENDED |
| [ADR-026](../adr/ADR-026-tool-choice-and-capability-semantics.md) | AUTO/NONE/REQUIRED/SPECIFIC et support explicite | L4.1/4 | RECOMMENDED |
| [ADR-027](../adr/ADR-027-response-format-and-structured-output-contract.md) | Text/JSON/Schema et VALID/INVALID/UNKNOWN | L4.3 | RECOMMENDED |
| [ADR-028](../adr/ADR-028-p4-composition-with-m3.md) | Option B : wrapper P4, M3 immutable et inchange | L4.4 | RECOMMENDED |
| [ADR-029](../adr/ADR-029-tooling-json-v1-and-compatibility.md) | Codec Tooling JSON v1 autonome, pas de v2 par defaut | L4.4 | RECOMMENDED |

## Portee de la validation

- La demande du proprietaire du 5 novembre 2026 autorise l'instruction de P4-G0 et l'elaboration des huit decisions.
- Elle n'est **pas** revendiquee comme une approbation explicite du texte individuel de chaque ADR non encore soumis au proprietaire.
- L'adoption formelle exige la revue des huit decisions, l'approbation documentee du proprietaire, l'integration de la PR et la verification de sa CI exacte sur main.
- Le gate est distinct des exigences d'implementation L4.1..L4.5 et de la publication.
- Aucune ADR precedente 001..021 n'est modifiee par cette proposition.

## Sujets exclus de l'autorisation

Aucun code P4, aucun SDK provider, aucun executable tools, aucune autorisation de bump, tag, release ou PyPI. Les issues #22, #35 et #36 restent ouvertes et suivies separement.
