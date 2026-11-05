# ADR-020 - Schema JSON Inference v1 independant

- Statut : **PROPOSED** (P3-BOOT, 2026-11-05).
- Sources : plan Phase 3 section 8, ADR-004/012, SER-001..006, PIR2-03/04/06.

## Contexte

Model v1 et Interaction v1 sont deja des contrats distincts. Les primitives Inference necessitent une persistance et inspection deterministes, sans se transformer en wire format d'un fournisseur.

## Decision proposee

1. Introduire **INFERENCE_SCHEMA_VERSION = 1** dans le namespace Inference; ne pas modifier le schema Model v1 ni Interaction v1.
2. Les enveloppes P0 publiees sont **inference_request**, **inference_response** et un **inference_run** snapshot. Chacune contient schema_version entier exact 1, object_type exact et champs obligatoires explicites.
3. JSON request : target discriminant kind + value, messages comme sous-objets **Interaction JSON v1 entiers**, generation_config optionnelle mais champ present avec null ou objet canonique.
4. JSON response : run_id, TextOutput discrimine, finish_reason nullable (code + native_reason), usage nullable. Output vide conserve.
5. JSON run snapshot : run_id, request, attempt, state, timestamps aware en ISO 8601 explicites ou null, response/failure exclusifs selon etat. Revalider les invariants lors du decodage.
6. Les champs optionnels autorises dans un objet ont une politique **presente et null** canonique pour v1; les champs absents non prevus et les cles surnumeraires sont refuses. Ne pas rendre l'absence de champ equivalente a une valeur fabriquee.
7. Utiliser des fonctions explicites request_to_dict/from_dict, response_to_dict/from_dict, run_to_dict/from_dict. Text-to-JSON est une frontiere separee; json.dumps(..., allow_nan=False) est compatible.
8. Refuser object_type, schema_version, variantes et champs inconnus, mauvaise cardinalite, bool pour int, NaN/Inf et types invalides, sans echo des prompts ou URL sensibles dans les erreurs.
9. Maintenir ordre/duplications des messages et ContentParts; conserver le contenu exact des MediaSourceRef dans le mapping, mais ne jamais faire de fetch.
10. La politique de **cles JSON dupliquees** appartient au parseur de texte; json.loads standard ne garantit pas leur detection. Documenter ce risque, ne pas revendiquer une garantie inexistante.
11. Tout nouveau ContentPart ou Output incompatible impose ADR et versionnement/migration; aucune conversion provider implicite.

## Exemple non normatif, soumis a G0

~~~json
{
  "schema_version": 1,
  "object_type": "inference_request",
  "target": {"kind": "model", "value": "example/model"},
  "messages": [
    {"schema_version": 1, "object_type": "message",
     "role": "user", "content": {"parts": [{"kind": "text", "text": "Bonjour"}]}}
  ],
  "generation_config": null
}
~~~

## Alternatives

- Reutiliser le namespace Interaction pour Inference : rejete.
- Dupliquer une version compacte du Message : rejete en v1, risque de divergence.
- Decoder laxiste ou drop d'extension : rejete.

## Verification

- Round-trip Request/Response/Run snapshot, null, Unicode, ordre, ids et horodatages.
- Tests de refus unknown/missing/invalid, de redaction, et de non-regression M1/M2.
- Tests P3-AC-021..028. Format final a confirmer par fixtures avant G0.
