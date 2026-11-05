# ADR-027 - ResponseFormat and StructuredOutput contract

- Date : 2026-11-05
- Statut : ACCEPTED (owner, 2026-11-05; P4-G0 qualifié main@b66e94e3, CI #42079191595 SUCCESS)
- Phase : L4.3
- Sources : ADR-024/025/026, TOOL-011 a TOOL-021, P4-AC-017 a 024.

> Approbation du proprietaire : [P4_G0_OWNER_ARCHITECTURE_APPROVAL.md](../quality/P4_G0_OWNER_ARCHITECTURE_APPROVAL.md). Aucune revue tierce revendiquee.

## Decision adoptee

1. ResponseFormat est une union typée de TextResponseFormat, JsonResponseFormat et SchemaResponseFormat. L'absence de format signifie non specifie, pas JSON par defaut.
2. TextResponseFormat autorise du texte libre sans reclamer STRUCTURED_OUTPUT. JsonResponseFormat demande une valeur JSON sans pretendre a une validation de schema. SchemaResponseFormat comporte un schema du profil P4-JSON-1.
3. strict: bool | None est represente exactement. None signifie instruction non renseignee, False signifie explicitement non strict, True est une contrainte demandee; ce champ ne constitue jamais une preuve de support natif.
4. StructuredOutput garde raw (optionnel), parsed (ABSENT ou valeur JSON immutable), format demande et resultat de validation. La provenance d'une valeur peut etre fournie explicitement, jamais devinee.
5. Le rapport de validation comporte statut UNKNOWN, VALID ou INVALID; diagnostics stables, bornes et expurges. Une valeur INVALID/UNKNOWN ne peut pas etre serialisee comme VALID ou utilisee comme preuve de conformite.
6. Un schema valide ne prouve pas une instance valide. Une chaine JSON syntaxiquement valide ne prouve pas la conformite au SchemaResponseFormat. La validation d'instance ne s'annonce VALID qu'apres evaluation reelle selon ADR-024.
7. Les informations de capabilities NATIVE/EMULATED/PARTIAL/UNSUPPORTED/UNKNOWN restent distinctes de la preuve de validite de la sortie. Pas de repair automatique, retry ni appel provider en M4.
8. Les sorties structurees et les demandes d'outils ne changent pas InferenceResponse.output de M3, limite a TextOutput.

## Alternatives ecartees

- json_mode: bool : insuffisant pour exprimer la forme attendue.
- returned_dict implique VALID : confusion parsing/validation.
- Force schema strict universel : support provider heterogene.

## Preuves

P4-AC-017..024 : texte, JSON, schema invalide, strict=None vs False, validation positive et negative, UNKNOWN, absence de fuite du raw. Exemples hors ligne obligatoires.
