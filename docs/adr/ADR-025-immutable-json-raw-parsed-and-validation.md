# ADR-025 - Immutable JSON, raw/parsed and validation evidence

- Date : 2026-11-05
- Statut : ACCEPTED (owner, 2026-11-05; P4-G0 CI main a verifier)
- Phase : L4.1 a L4.4
- Sources : ADR-024, TOOL-008, TOOL-014, P4-AC-012/013/020/024/030/039.

## Probleme

Une dataclass frozen contenant un dict mutable ne constitue pas un Value Object immuable. En outre, des arguments ou sorties parsables ne sont pas necessairement conformes au schema. Le raw peut contenir des secrets.

## Decision recommandee

1. Utiliser une representation JSON immutable recursive, avec tags explicites pour object et array et stockage defensif des valeurs scalaires. L'ordre des tableaux est preserve. Les cles d'objet sont normalisees en ordre lexicographique pour produire un mapping stable, sans pretendre que l'ordre source porte une semantique JSON.
2. Le JSON est exactement null, bool, int, float fini, str, array ou object a cles string. bool n'est pas converti en int; NaN, Infinity, types arbitraires, dates, bytes et cycles Python sont refuses. La profondeur et la taille suivent les limites approuvees en ADR-024.
3. La construction depuis un dict/list copie tout le graphe et le gele profondement; une API de restitution cree une nouvelle structure mutable par appel, sans exposer une reference interne.
4. ToolArguments distingue raw: str | None, parsed: valeur JSON | ABSENT, et validation_status. ABSENT est distinct de JSON null. Raw non nul ne declenche pas de parsing implicite.
5. Les etats de validation sont UNKNOWN (aucune preuve), VALID (validation executee et reussie) et INVALID (validation executee et echouee). Le caller ne peut pas marquer arbitrairement VALID au constructeur public sans rapport provenant d'un validateur approuve.
6. Validation de schema, parsing de texte JSON, validation d'instance et evaluation de support provider sont quatre operations independantes. Tout diagnostic contient code et chemin bornes, pas la charge brute.
7. ToolResult.value et StructuredOutput.parsed suivent la meme politique immutable; repr, erreurs, tests et logs du core n'affichent ni raw, ni schema complet, ni arguments ou resultats sensibles.
8. Les codecs reconstruisent exactement raw/parsed/absent et les statuts, et refusent une representation impossible au lieu de la tronquer.

## Alternatives ecartees

- dataclass(frozen=True) + dict interne : mutabilite indirecte.
- Conversion raw -> parsed automatique : fausse garantie et confusion d'origines.
- Status VALID librement assignable : validation non demontree.

## Verification

Tests de mutation indirecte, round-trip, JSON null contre absent, schema invalid, finite number, objets cycliques, redacteur de repr et diagnostic securise. Aucun besoin d'installer un SDK provider pour valider.
