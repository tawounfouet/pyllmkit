# PyLLMKit - Tooling JSON v1

> Date: 2026-11-05. Statut: proposition implementee sur branche L4.4, non encore qualifiee P4-G4.
> Sources: ADR-028 (composition separee), ADR-029 (codec independant), P4-JSON-1 (ADR-024).

## Contrat de la frontiere

Tooling JSON v1 represente des **objets JSON compatibles** de forme `dict[str, object]`. Ce codec ne parse jamais de texte JSON, n'effectue pas de requetes, ne charge aucun provider et n'execute jamais d'outil.

Tout objet enveloppe exige `schema_version: 1` comme entier exact, `object_type` identifiant le variant et la liste exacte des autres champs. Une cle manquante ou inconnue est rejetee. Les sous-objets sont eux aussi fermes.

## Variants autonomes

| object_type | Champs supplementaires requis |
|---|---|
| `tool_definition` | `name`, `description` (nullable), `schema` (objet P4-JSON-1) |
| `tool_choice` | `kind`, `name` (nullable) |
| `tool_call` | `call_id`, `tool_name`, `arguments` |
| `tool_result` | `call_id`, `is_error` (booleen exact), `value` (JSON) |
| `response_format` | `kind`, `strict` (nullable), `schema` (nullable) |
| `structured_output` | `response_format`, `raw`, `parsed_present`, `parsed`, `validation_status`, `validation_code` |
| `tool_call_output` | `calls` (liste non vide de tool_call) |
| `tooling_inference_intent` | `request` (Inference JSON v1), `tools`, `tool_choice` (nullable), `response_format` (nullable) |
| `tooling_inference_observation` | `run_id` (nullable), `call_output` (nullable), `structured_output` (nullable), `results` |

Le champ `arguments` comporte exactement `raw`, `parsed_present` et `parsed`. Quand `parsed_present=false`, `parsed` doit etre `null`; quand `parsed_present=true`, `parsed` peut etre `null` (JSON null valide). Cette distinction survit aux round-trips.

## Preuves et refus

`validation_status=VALID` n'est jamais pris pour acquis sur lecture. Le decodeur relance `validate_structured_output` et exige le meme resultat; tout statut ou code falsifie est rejete. Pour un objet construit non valide (UNKNOWN/not_validated), cette absence de preuve est preservee. Les messages d'erreur ne recopient pas les donnees d'origine.

Les conversions `ToolCallOutput -> TextOutput`, les downgrades vers Inference JSON v1 avec perte, les champs P4 injectes dans Inference JSON v1 et la creation d'un ToolResult automatique sont interdits.

Les noms d'objets et donnees M3 conservent leurs codecs d'origine. **Inference JSON v2 n'est pas livre** et necessiterait une ADR et des migrations separees.

## Limites et securite

- P4-JSON-1 est un sous-ensemble documente, pas Draft 2020-12 integral.
- Le decodeur traite une structure Python deja parse; politique des cles JSON textuelles dupliquees et texte JSON d'un provider : frontiere applicative distincte.
- Les tableaux conservent l'ordre; les objets JSON sont copies defensivement. Les identifiants et les statuts d'erreur sont preserves.
- Aucune execution, aucun reseau ni credential.
