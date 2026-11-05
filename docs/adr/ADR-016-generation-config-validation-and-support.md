# ADR-016 - GenerationConfig, absence, types numeriques et compatibilite
> **Decision owner P3-G0 (2026-11-05)** : `ACCEPTED`, sous autorite du proprietaire dans la conversation du projet. Cette autorisation concerne les contrats et leur integration, **pas** une GitHub review externe ni la publication d'un package. 
> **Arbitrage retenu :** Exact finite float for decimal parameters (including temperature=0.0 but not integer 0); strict integer excluding bool; optional fields None; no provider defaults.


- **Statut : ACCEPTED** - adoption explicite par le proprietaire pour P3-G0 le 2026-11-05. Contrat de conception adopte, implementation Python non commencee.
- Sources : Phase 3 sections 4 et 5.2, FR-016/017, INF-001..005, SER-004.

## Contexte

GenerationConfig exprime des intentions de generation, sans copier les options ou defaults d'un provider. Le constructeur ne dispose pas des capabilities effectives de la cible.

## Decision adoptee

1. Value Object frozen, slots, compare par valeur, et sans dependances provider. Les 8 champs optionnels valent **None** lorsqu'ils ne sont pas specifies.
2. **float exact et fini** pour temperature, top_p, presence_penalty, frequency_penalty (donc **temperature=0.0 valide, temperature=0 int invalide**, tout comme True, NaN et Infinity). Ce choix strict et pedagogique est **approuve explicitement en G0**; alternative possible : accepter int et float hors bool avec une representation canonique.
3. **int exact** hors bool pour top_k, max_output_tokens et seed. Aucun cast implicite de float, str ou bool en int.
4. Valeurs acceptees : temperature >= 0.0, 0.0 < top_p <= 1.0, top_k >= 1, max_output_tokens >= 1. seed est tout entier, y compris 0 et negatif, tant qu'aucune borne commune n'est justifiee. Les deux penalties doivent etre finis, sans imposer un intervalle fournisseur.
5. **stop_sequences** vaut None, ou un **tuple exact** de strings exactes non vides; () explicite est autorise et distinct de None. Ordre et repetitions preserves. Pas de coercition depuis list ou iterateur; le JSON utilise un tableau uniquement lorsqu'une valeur est presente.
6. La presence d'un parametre valide **structurellement** n'est pas une preuve de support effectif. Un resolver futur pourra fournir un report de compatibilite sur capacites/limites connues. En cas de support inconnu : UNKNOWN/non evalue, jamais NATIVE implicitement. En cas de refus explicite du parametre par une cible resolue : diagnostic explicite, aucune suppression silencieuse.
7. Aucun field provider_options, native_payload, tools ou response_format dans GenerationConfig P0. Ne pas introduire de dictionnaire mutable d'escape hatch dans le core.
8. Le JSON Inference v1 preserve explicitement None, 0.0, (), 0 et toute valeur presente. Les champs nullable sont tous presents dans l'objet config selon ADR-020; l'objet config peut lui-meme etre null dans une Request.

## Matrice de types / bornes

| Champ | Type P0 | Valide | Invalide | Absence |
|---|---|---|---|---|
| temperature | float fini | 0.0, 0.7 | 0 (int), True, -0.1, NaN, inf | None |
| top_p | float fini | 0.1, 1.0 | 0.0, 1 (int), 1.1, NaN | None |
| top_k | int exact | 1, 40 | 0, -1, True, 2.0 | None |
| max_output_tokens | int exact | 1, 256 | 0, -1, True, 2.0 | None |
| seed | int exact | -1, 0, 8 | True, 1.5, "1" | None |
| stop_sequences | tuple[str,...] exact | (), ("STOP",), ("X","X") | ["X"], ("",), (None,) | None |
| presence_penalty | float fini | -2.0, 0.0, 3.0 | 0 (int), NaN | None |
| frequency_penalty | float fini | -2.0, 0.0, 3.0 | 0 (int), inf | None |

Les exemples de penalties ne promettent pas un support provider ou une borne universelle.

## Alternatives et risques

- Accepter int pour les champs decimaux, hors bool : alternative ergonomique a arbitrer explicitement.
- Valeurs par defaut imposees d'apres un fournisseur : rejete.
- UNSET distinct de None : differe tant qu'aucune semantique explicite de null vs absent n'est necessaire.
- Borne universelle de penalties issue d'un seul SDK : rejetee.
- Validation effective dans le constructeur : rejetee.

## Evidence demandee

- P3-AC-004..007 et P3-AC-021, tests des bornes, bool, float non fini, vide/None, tuple, non-coercition et serialization.
- Tableau de support UNKNOWN / support connu sans network.
- Decision G0 specifique sur la **rigidite des types float** et les valeurs negatives de seed.

**Statut : ACCEPTED pour la conception P3.** Aucune implementation n'est revendiquee.
