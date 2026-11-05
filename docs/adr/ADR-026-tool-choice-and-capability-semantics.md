# ADR-026 - Tool choice and capability semantics

- Date : 2026-11-05
- Statut : ACCEPTED (owner, 2026-11-05; P4-G0 qualifié main@b66e94e3, CI #42079191595 SUCCESS)
- Phase : L4.1 et L4.4
- Sources : capability model M1, ADR-021, TOOL-005/010/013, INF-009/010.

> Approbation du proprietaire : [P4_G0_OWNER_ARCHITECTURE_APPROVAL.md](../quality/P4_G0_OWNER_ARCHITECTURE_APPROVAL.md). Aucune revue tierce revendiquee.

## Decision adoptee

1. ToolChoice est une union discriminable de quatre politiques : AUTO, NONE, REQUIRED et SPECIFIC_TOOL(name). name est obligatoire et non vide uniquement pour SPECIFIC_TOOL. Le modele est immutable et serialisable.
2. Le domaine verifie la coherence interne de la politique et du ToolSet fourni : REQUIRED exige au moins un outil; SPECIFIC_TOOL doit nommer un outil existant; les doublons de noms sont interdits. NONE peut coexister avec une declaration de tools mais n'autorise aucun appel implicite.
3. AUTO signifie autoriser une selection dans un contexte capable de l'assumer; il ne promet pas que le provider choisira, ni qu'un tool sera execute. REQUIRED et SPECIFIC_TOOL sont des intentions, pas des garanties de reponse.
4. La presence d'un ToolSet non vide cree une exigence de TOOL_CALLING. SchemaResponseFormat cree une exigence de STRUCTURED_OUTPUT. Ces capabilities sont distinctes du GenerationSupportSnapshot M3, qui ne couvre que les parametres de generation.
5. Un rapport de support doit distinguer explicitement NATIVE, EMULATED, PARTIAL, UNSUPPORTED et UNKNOWN (ou absence de declaration). Le niveau UNKNOWN n'est jamais promu en NATIVE et une emulation n'est pas native.
6. UNSUPPORTED connu conduit au rejet. PARTIAL et EMULATED sont transmis au caller avec leurs contraintes sans substitution silencieuse. UNKNOWN reste indetermine, sans declaration de succes provider.
7. Les contraintes de nombre d'outils et de parallelisme ne sont jamais inventees; elles dependent du contexte et des declaratifs recus.
8. Aucune invocation ou resolution de provider n'est incluse dans cette politique.

## Alternatives ecartees

- bool force_tool_call : ecrase NONE/AUTO/REQUIRED/SPECIFIC.
- Reutiliser GenerationSupportSnapshot pour les tools : faux perimetre.
- Emulation par defaut sur un UNKNOWN : fausse conformite.

## Verification

P4-AC-005..008, 023, 025..027. Tests du nom inexistant, de REQUIRED sans tool, de NONE, du support connu UNSUPPORTED, du niveau UNKNOWN et des contraintes partielles. Les diagnostics n'exposent pas de valeurs sensibles.
