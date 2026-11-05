# PyLLMKit - Registre de decisions architecturales P4-G0

> Date : 2026-11-05. Statut : les huit ADR sont **ACCEPTED par le proprietaire** le 2026-11-05; integration et CI main a confirmer. Ce registre ne constitue ni une review GitHub APPROVED ni une preuve CI post-merge.

| ADR | Decision adoptee | Lots | Etat |
|---|---|---|---|
| [ADR-022](../adr/ADR-022-tool-definition-and-execution-boundary.md) | Tool descriptif, aucune execution | L4.1/2 | ACCEPTED |
| [ADR-023](../adr/ADR-023-tool-call-identity-and-correlation.md) | ToolCallId opaque explicite, 0..1 resultat final | L4.2 | ACCEPTED |
| [ADR-024](../adr/ADR-024-json-schema-profile-and-validation.md) | P4-JSON-1, profil ferme et borné, sans $ref | L4.1/3 | ACCEPTED |
| [ADR-025](../adr/ADR-025-immutable-json-raw-parsed-and-validation.md) | Gel profond, raw/parsed/ABSENT distincts, VALID prouve | L4.1/2/3/4 | ACCEPTED |
| [ADR-026](../adr/ADR-026-tool-choice-and-capability-semantics.md) | AUTO/NONE/REQUIRED/SPECIFIC et support explicite | L4.1/4 | ACCEPTED |
| [ADR-027](../adr/ADR-027-response-format-and-structured-output-contract.md) | Text/JSON/Schema et VALID/INVALID/UNKNOWN | L4.3 | ACCEPTED |
| [ADR-028](../adr/ADR-028-p4-composition-with-m3.md) | Option B : wrapper P4, M3 immutable et inchange | L4.4 | ACCEPTED |
| [ADR-029](../adr/ADR-029-tooling-json-v1-and-compatibility.md) | Codec Tooling JSON v1 autonome, pas de v2 par defaut | L4.4 | ACCEPTED |

## Portee de la validation

- Le proprietaire a explicitement demande la declaration du gate P4-G0 et le lancement de L4.1; l'adoption des huit decisions est archivee dans [P4_G0_OWNER_ARCHITECTURE_APPROVAL.md](P4_G0_OWNER_ARCHITECTURE_APPROVAL.md).
- La qualification finale du gate exige l'integration de la PR et une CI exacte sur le nouveau SHA de main.
- Le gate est distinct des exigences d'implementation L4.1..L4.5 et de la publication.
- Aucune ADR precedente 001..021 n'est modifiee par cette proposition.

## Sujets exclus de l'autorisation

Aucun code P4, aucun SDK provider, aucun executable tools, aucune autorisation de bump, tag, release ou PyPI. Les issues #22, #35 et #36 restent ouvertes et suivies separement.
