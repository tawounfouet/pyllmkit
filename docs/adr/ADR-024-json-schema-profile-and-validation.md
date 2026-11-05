# ADR-024 - JSON Schema profile and validation limits

- Date : 2026-11-05
- Statut : RECOMMENDED FOR P4-G0 ADOPTION
- Phase : L4.1, L4.3 et L4.4
- Sources : TOOL-002/012/014, ADR-022, P4-AC-002/019/021/022/038.

## Problematique

Le corpus exige des schemas valides mais ne choisit ni dialecte ni moteur de validation. Il est incorrect de revendiquer la conformite complete a JSON Schema Draft 2020-12 sans implementation et tests correspondants.

## Decision recommandee : profil P4-JSON-1

1. Adopter un **sous-ensemble explicite et ferme** de JSON Schema, base sur la semantique des mots-cles standard, nomme P4-JSON-1. Ne jamais annoncer la prise en charge integrale de Draft 2020-12.
2. Le profil accepte les types JSON object, array, string, integer, number, boolean, null; type peut etre un nom ou une liste non vide de noms uniques. Les bool ne sont pas des integer/number. L'absence de type ne garantit pas d'autres assertions que celles presentes.
3. Mots-cles autorises : type, properties, required, additionalProperties, items, enum, const, minItems, maxItems, minLength, maxLength, minimum, maximum, description, title. La semantique de chacun suit JSON Schema pour son domaine applicable. Properties est un objet a cles string; required est une liste de strings uniques; items est un unique schema; additionalProperties est un booleen.
4. Tous les autres mots-cles sont rejetes au niveau declaration, notamment $ref, $defs, $id, $schema, remote reference, oneOf, anyOf, allOf, not, pattern, format, unevaluatedProperties et le mode regex. Aucun reseau ni resolution de references.
5. La version initiale impose une profondeur maximale de 32, une taille maximale de 1 MiB par schema JSON canonique et un maximum de 10 000 noeuds; une erreur explicite est produite si la limite est depassee. Ces valeurs sont des limites de protection **locales a PyLLMKit**, pas des capacites universelles de provider.
6. Les schemas recus comme dict/list Python sont copies et verifies avant gel profond; cycles Python, clés non string, NaN/Infinity et valeurs non JSON sont refuses.
7. La validation structurelle d'un schema et la validation d'une instance sont deux operations distinctes et testees. Un statut VALID ne peut resulter que d'une validation reussie effectivement executee.
8. Le validateur minimal est pur et sans dependance runtime obligatoire a un SDK externe. Une extension JSON Schema complete pourrait etre proposee par ADR ulterieure et dependency optionnelle explicitement approuvee.

## Alternatives considerees

- Draft 2020-12 complet dans le core : surface, dependencies et garanties excessives pour M4.
- Simples assertions ad hoc sans version de profil : interoperabilite et documentation trompeuses.
- $ref distant : I/O implicite, indisponibilite et risques SSRF.

## Criteres d'acceptation

Tests sur nested objects/arrays, type union incluant null, required, additionalProperties, enum/const, bornes et type numerique; rejets d'une cle inconnue, de $ref, d'une structure cyclique, des limites de profondeur/taille, et de non-conformite instance. Documentation exhaustive du profil et distinction stricte entre validation du schema et validation du contenu.

## Point de vigilance

La validation de schema n'atteste ni que le provider comprend ce schema ni que sa reponse sera conforme. La compatibilite effective releve d'une declaration explicite de capability.
