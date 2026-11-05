# PyLLMKit P5 - Traçabilité des 48 cas d'acceptation

> Date de référence : 2026-11-05.
> P5-G0..P5-G5 GO techniques avec réserves sur SHAs main vérifiés. P5-G6 et M5 sont distincts, en qualification à la création de ce registre.
> Ne pas interpréter la matrice comme une autorisation de publication 0.1.0b1.

| AC | Scénario | ADR | Test source | Lot/Gate |
|---|---|---|---|---|
| P5-AC-001 | Stream comportemental et provider-free | ADR-030 | tests/acceptance/test_p5_l51_events.py | L5.1 / G1 |
| P5-AC-002 | Neuf événements typés et corrélés | ADR-030 | tests/acceptance/test_p5_l51_events.py | L5.1 / G1 |
| P5-AC-003 | Deltas texte littéraux et repr sûrs | ADR-030 | tests/acceptance/test_p5_l51_events.py | L5.1 / G1 |
| P5-AC-004 | Immutabilité des événements | ADR-030 | tests/acceptance/test_p5_l51_events.py | L5.1 / G1 |
| P5-AC-005 | ToolCallDelta canonique | ADR-033 | tests/acceptance/test_p5_l51_events.py | L5.1 / G1 |
| P5-AC-006 | Trois terminaisons distinctes | ADR-032 | tests/acceptance/test_p5_l51_events.py | L5.1 / G1 |
| P5-AC-007 | Valeurs invalides rejetées | ADR-031 | tests/acceptance/test_p5_l51_events.py | L5.1 / G1 |
| P5-AC-008 | Frontière sans SDK ni I/O | ADR-030 | tests/acceptance/test_p5_l51_events.py | L5.1 / G1 |
| P5-AC-009 | Début unique avant contenu | ADR-032 | tests/acceptance/test_p5_l52_ordering_lifecycle.py | L5.2 / G2 |
| P5-AC-010 | Reconstruction texte déterministe | ADR-034 | tests/acceptance/test_p5_l52_ordering_lifecycle.py | L5.2 / G2 |
| P5-AC-011 | Doublon de séquence rejeté | ADR-031 | tests/acceptance/test_p5_l52_ordering_lifecycle.py | L5.2 / G2 |
| P5-AC-012 | Ordre et trous rejetés | ADR-031 | tests/acceptance/test_p5_l52_ordering_lifecycle.py | L5.2 / G2 |
| P5-AC-013 | Correlation run_id stricte | ADR-031 | tests/acceptance/test_p5_l52_ordering_lifecycle.py | L5.2 / G2 |
| P5-AC-014 | Terminaison exclusive | ADR-032 | tests/acceptance/test_p5_l52_ordering_lifecycle.py | L5.2 / G2 |
| P5-AC-015 | EOF INCOMPLETE, jamais succès | ADR-032 | tests/acceptance/test_p5_l52_ordering_lifecycle.py | L5.2 / G2 |
| P5-AC-016 | Deltas tool distincts du texte | ADR-034 | tests/acceptance/test_p5_l52_ordering_lifecycle.py | L5.2 / G2 |
| P5-AC-017 | ToolCallDelta orphelin rejeté | ADR-033 | tests/acceptance/test_p5_l53_tool_call_streaming.py | L5.3 / G3 |
| P5-AC-018 | Deux appels entrelacés reconstruits | ADR-033 | tests/acceptance/test_p5_l53_tool_call_streaming.py | L5.3 / G3 |
| P5-AC-019 | IDs et noms conservés | ADR-033 | tests/acceptance/test_p5_l53_tool_call_streaming.py | L5.3 / G3 |
| P5-AC-020 | Double start/end rejeté | ADR-033 | tests/acceptance/test_p5_l53_tool_call_streaming.py | L5.3 / G3 |
| P5-AC-021 | Fragment après close rejeté | ADR-033 | tests/acceptance/test_p5_l53_tool_call_streaming.py | L5.3 / G3 |
| P5-AC-022 | Raw non parsé, jamais VALID implicite | ADR-034 | tests/acceptance/test_p5_l53_tool_call_streaming.py | L5.3 / G3 |
| P5-AC-023 | Aucun ToolResult fabriqué | ADR-034 | tests/acceptance/test_p5_l53_tool_call_streaming.py | L5.3 / G3 |
| P5-AC-024 | Budget raw par appel | ADR-038 | tests/acceptance/test_p5_l53_tool_call_streaming.py | L5.3 / G3 |
| P5-AC-025 | Itérateur synchrone et protocole | ADR-035 | tests/acceptance/test_p5_l54_sync_async.py | L5.4 / G4 |
| P5-AC-026 | Parité des itérateurs async | ADR-035 | tests/acceptance/test_p5_l54_sync_async.py | L5.4 / G4 |
| P5-AC-027 | Cancellation explicite partielle | ADR-032 | tests/acceptance/test_p5_l54_sync_async.py | L5.4 / G4 |
| P5-AC-028 | Arrêt anticipé sans succès fictif | ADR-035 | tests/acceptance/test_p5_l54_sync_async.py | L5.4 / G4 |
| P5-AC-029 | Usage snapshot incomplet | ADR-037 | tests/acceptance/test_p5_l54_sync_async.py | L5.4 / G4 |
| P5-AC-030 | Fermeture explicite sync | ADR-035 | tests/acceptance/test_p5_l54_sync_async.py | L5.4 / G4 |
| P5-AC-031 | Fermeture explicite async | ADR-035 | tests/acceptance/test_p5_l54_sync_async.py | L5.4 / G4 |
| P5-AC-032 | Ports protocoles abstraits | ADR-035 | tests/acceptance/test_p5_l54_sync_async.py | L5.4 / G4 |
| P5-AC-033 | Round-trip des 9 types d'événements | ADR-036 | tests/acceptance/test_p5_l55_streaming_json_v1.py | L5.5 / G5 |
| P5-AC-034 | Round-trip trace ordonnée | ADR-036 | tests/acceptance/test_p5_l55_streaming_json_v1.py | L5.5 / G5 |
| P5-AC-035 | Versions/champs/kinds invalides rejetés | ADR-036 | tests/acceptance/test_p5_l55_streaming_json_v1.py | L5.5 / G5 |
| P5-AC-036 | Payload et Usage stricts | ADR-036 | tests/acceptance/test_p5_l55_streaming_json_v1.py | L5.5 / G5 |
| P5-AC-037 | Fin falsifiée rejetée | ADR-036 | tests/acceptance/test_p5_l55_streaming_json_v1.py | L5.5 / G5 |
| P5-AC-038 | Failed/Cancelled/Incomplete distincts | ADR-037 | tests/acceptance/test_p5_l55_streaming_json_v1.py | L5.5 / G5 |
| P5-AC-039 | Run/ordre falsifié rejeté | ADR-036 | tests/acceptance/test_p5_l55_streaming_json_v1.py | L5.5 / G5 |
| P5-AC-040 | Anciens codecs inchangés | ADR-036 | tests/acceptance/test_p5_l55_streaming_json_v1.py | L5.5 / G5 |
| P5-AC-041 | Parité de bout en bout sync/async | ADR-035 | tests/acceptance/test_p5_l56_integration.py | L5.6 / G6 |
| P5-AC-042 | ToolCall raw via trace JSON | ADR-033 | tests/acceptance/test_p5_l56_integration.py | L5.6 / G6 |
| P5-AC-043 | Cancellation/post-terminal et preuve JSON | ADR-032 | tests/acceptance/test_p5_l56_integration.py | L5.6 / G6 |
| P5-AC-044 | Régression codecs M1-M4 | ADR-036 | tests/acceptance/test_p5_l56_integration.py | L5.6 / G6 |
| P5-AC-045 | Docs et isolation architecture | ADR-030 | tests/acceptance/test_p5_l56_integration.py | L5.6 / G6 |
| P5-AC-046 | Limite trace avant décodage | ADR-038 | tests/acceptance/test_p5_l56_integration.py | L5.6 / G6 |
| P5-AC-047 | Charge synthétique 10k événements | ADR-038 | tests/acceptance/test_p5_l56_integration.py | L5.6 / G6 |
| P5-AC-048 | API, packaging, version inchangée | ADR-038 | tests/acceptance/test_p5_l56_integration.py | L5.6 / G6 |


## Chaîne de preuves historiques

| Gate | PR | SHA qualifiant de main | Run GitHub Actions | Verdict |
|---|---|---|---|---|
| P5-G0 | #51 | 47538ce | #42100071595 | GO avec réserves |
| P5-G1 | #52 | 5157425 | #42100651109 | GO avec réserves |
| P5-G2 | #53 | 9039a1b | #42101437194 | GO avec réserves |
| P5-G3 | #54 | 53a965c | #42102029484 | GO avec réserves |
| P5-G4 | #55 | 6388711 | #42102577288 | GO avec réserves |
| P5-G5 | #56 | 6070ca4 | #42103272574 | GO avec réserves |
| P5-G6 | #57 (prévue) | TBD après intégration | TBD | NON QUALIFIÉ |
| M5 | revue finale distincte | TBD | TBD | NON QUALIFIÉ |

La suite CI globale comporte des tests hérités M1-M4. Les nombres de tests et la couverture calculée ne peuvent être déduits de ce document et doivent être reportés depuis les logs CI du SHA exact. Tests d'acceptation ne signifient pas test externe provider. Chaque case est tracée par son identifiant dans les tests du lot. Les limites charge sont contrôlées hors réseau; aucun SLA réel de transport n'est impliqué.

## Réserves transverses

Issue #22 : protection main non effective lors de M4, à revalider. Issue #35 : release NO-GO. Issue #36 : future frontière provider. Pas de validation de pairs indépendante revendiquée. Le paquet reste en 0.1.0a2; la cible 0.1.0b1 est indicative.
