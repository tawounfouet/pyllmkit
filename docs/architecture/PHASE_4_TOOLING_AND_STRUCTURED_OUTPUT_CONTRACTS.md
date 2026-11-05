# PyLLMKit - Architecture des contrats Tooling & Structured Output (P4)

> État : contrat de documentation L4.5 en cours de qualification P4-G5.
> Décisions acceptées : ADR-022 à ADR-029. Code P4-G0 à P4-G4 intégré. Preuves par gate dans `docs/quality/`.
> Aucun provider LLM, moteur d'exécution d'outils ou transport HTTP n'est fourni par M4.

## 1. Intention et limites du domaine

PyLLMKit permet de **décrire** un outil, une demande de tool call, un résultat observé et une sortie structurée, puis de les valider et les sérialiser **hors réseau**. Il ne lance aucun appel au modèle ni aucun handler d'outil. Une déclaration de capability n'est pas une exécution.

| Sous-domaine | Primitives | Responsabilité |
|---|---|---|
| Model (M1) | Model, CapabilitySupport, SupportLevel | Vocabulaire des modèles et capacités déclarées |
| Interaction (M2) | Message, Content, ContentPart | Entrées de conversation, sans content ToolCall v2 |
| Inference (M3) | InferenceRequest, InferenceResponse, InferenceRun | Contrats v1 inchangés : Request et TextOutput |
| Tooling (P4 L4.1-2) | ToolSchema, Tool, ToolChoice, ToolCallId, ToolArguments, ToolCall, ToolResult | Déclaration, identité et corrélation; aucune exécution |
| Structured Output (P4 L4.3) | Text/Json/SchemaResponseFormat, StructuredOutput | Format demandé, raw/parsed et preuve de validation |
| Tooling Inference (P4 L4.4) | ToolingInferenceIntent, ToolCallOutput, ToolingInferenceObservation | Composition hors du modèle M3; aucune réponse M3 fictive |
| Serialization (P4 L4.4) | Tooling JSON v1 | Codec de dictionnaires JSON, sans parser texte ni I/O |

## 2. Flux de données

```text
InferenceRequest M3 (inchangée)
    + ToolSchema / Tool[] / ToolChoice / ResponseFormat
    -> ToolingInferenceIntent                  (intent, sans invocation)
    -> ToolCallOutput / ToolCall[]             (observations, sans exécution)
    -> ToolResult[]                            (résultats fournis par le caller)
    -> ToolingInferenceObservation
    -> Tooling JSON v1 dict -> dict round-trip (sans perte)
```

Un consommateur peut écrire séparément un exécuteur ou un adapter, mais M4 n'en expose aucun. Pythos, PyAgentsKit ou un autre moteur externe doit gérer lui-même les permissions, les secrets et la sécurité de l'exécution réelle.

## 3. Invariants qualifiés

1. **TOOL-003 / ADR-022 :** un `Tool` est une description non exécutable. `ToolCall` est une Entity identifiée, pas un handler.
2. **TOOL-004..010 / ADR-023 :** identifiant explicite `ToolCallId`, sensibles à la casse, un résultat final au plus par appel dans un contexte local. Rejeter les orphelins et doublons.
3. **ADR-024 :** profil de schéma limité `P4-JSON-1`, fermé aux mots-clés inconnus. Pas de promesse de conformité complète Draft 2020-12 ni de `$ref` distant.
4. **ADR-025 :** immutabilité profonde, copie défensive, distinction `raw`, `parsed`, `parsed_present` et JSON `null`. Aucune donnée sensible dans `repr` ou les diagnostics de validation.
5. **ADR-026 :** choix AUTO/NONE/REQUIRED/SPECIFIC_TOOL, capacités explicites; UNKNOWN/EMULATED/PARTIAL non assimilés à NATIVE.
6. **ADR-027 :** formats Text, JSON et Schema; `strict=None` distinct de `False`; VALID uniquement après validation effective.
7. **ADR-028 :** wrappers P4 séparés, aucune mutation des objets M3 ni conversion ToolCallOutput en TextOutput.
8. **ADR-029 :** Tooling JSON v1 autonome, `schema_version` et `object_type` stricts, champs exacts, refus des valeurs non représentables; Inference JSON v2 non introduit.

## 4. Contrats publics et frontières

Les chemins d'import canoniques de P4 sont `pyllmkit.domain.tooling`, `pyllmkit.domain.structured_output` et `pyllmkit.domain.tooling_inference`. Les codecs P4 sont dans `tooling.serialization` et `tooling_inference.serialization`.

La racine `pyllmkit.domain` conserve ses réexports M1-M3 pour compatibilité. L4.5 n'ajoute pas une façade d'exécution ni un God Client à la racine.

`Tooling JSON v1` est détaillé dans [TOOLING_JSON_SCHEMA_V1.md](TOOLING_JSON_SCHEMA_V1.md). Les objets sérialisés sont des `dict`, pas des requêtes HTTP, du JSON textuel ou des fichiers.

## 5. Qualité et sécurité

- Appels hors ligne uniquement, sans credentials requis.
- DomainValidationError à messages contrôlés, pas de `repr` des charges sensibles.
- Régressions M1/M2/M3 et codecs JSON v1 couverts par la CI cumulative.
- Matrice Python 3.11/3.12/3.13, Ruff, mypy strict, pytest couverture de branches.
- Exemples 13 à 17, source et installations isolées wheel/sdist.
- Tests P4-AC-001..040 et matrice de preuve [PHASE_4_TRACEABILITY.md](../quality/PHASE_4_TRACEABILITY.md).

## 6. Non-objectifs de M4 et évolutions

Aucun LLM provider, aucun transport, aucun exécuteur d'outil, streaming de fragments ToolCall, agent autonome, retry/repair, ni Inference JSON v2. Le traitement du JSON textuel, des clés dupliquées, des contenus hostiles d'un provider et des contrôles d'accès relève d'une future frontière applicative documentée, non d'une garantie de ce domaine.

L'achèvement de P4-G5 et la revue M4 sont deux gates distincts. La publication PyPI exige une approbation supplémentaire.
