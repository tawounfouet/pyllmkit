# PyLLMKit - Phase 4 : traçabilité des 40 cas d'acceptation

> Date : 2026-11-05.
> **Statut : P4-G0..G4 GO techniques avec réserves, L4.5 et P4-G5 NON QUALIFIÉS.**
> Les P4-AC-001..040 sont les cas du plan `docs/04_PYLLMKIT_PHASE_4_IMPLEMENTATION_PLAN.md`. Les ADR-022..029 sont ACCEPTED.
> Ce registre est une traçabilité, pas une revendication de passage anticipé du gate G5.

## Matrice exhaustive P4-AC-001..040

| AC | Scénario | Source | ADR | Test | Gate / PR | Qualification |
|---|---|---|---|---|---|---|
| 001 | Tool immuable descriptif | TOOL-001/003 | 022 | `tests/acceptance/test_p4_l41_tools.py` | G1 / #40 | PASS G1 |
| 002 | Profil de schema valide; reject $ref | TOOL-002 | 024 | `tests/acceptance/test_p4_l41_tools.py` | G1 / #40 | PASS G1 |
| 003 | Nom/description d'outil valides | TOOL-001 | 022 | `tests/acceptance/test_p4_l41_tools.py` | G1 / #40 | PASS G1 |
| 004 | Gel defensif du schema | NFR-006 | 025 | `tests/acceptance/test_p4_l41_tools.py` | G1 / #40 | PASS G1 |
| 005 | Unicite ToolSet | ValidateToolSet | 026 | `tests/acceptance/test_p4_l41_tools.py` | G1 / #40 | PASS G1 |
| 006 | Policies AUTO/NONE/REQUIRED/SPECIFIC | UC-011 | 026 | `tests/acceptance/test_p4_l41_tools.py` | G1 / #40 | PASS G1 |
| 007 | SpecificTool inexistant rejete | TOOL-005 | 026 | `tests/acceptance/test_p4_l41_tools.py` | G1 / #40 | PASS G1 |
| 008 | REQUIRED sans tools rejete | TOOL-005 | 026 | `tests/acceptance/test_p4_l41_tools.py` | G1 / #40 | PASS G1 |
| 009 | Identite par call ID | TOOL-004 | 023 | `tests/acceptance/test_p4_l42_tool_calls.py` | G2 / #42 | PASS G2 |
| 010 | Call ID invalide rejete | TOOL-004 | 023 | `tests/acceptance/test_p4_l42_tool_calls.py` | G2 / #42 | PASS G2 |
| 011 | Reference d'outil inconnu rejetee | TOOL-005 | 023 | `tests/acceptance/test_p4_l42_tool_calls.py` | G2 / #42 | PASS G2 |
| 012 | raw distinct de parsed/absent | TOOL-008 | 025 | `tests/acceptance/test_p4_l42_tool_calls.py` | G2 / #42 | PASS G2 |
| 013 | Validation schema arguments | TOOL-014 | 024/025 | `tests/acceptance/test_p4_l42_tool_calls.py` | G2 / #42 | PASS G2 |
| 014 | Resultat orphelin rejete | TOOL-006 | 023 | `tests/acceptance/test_p4_l42_tool_calls.py` | G2 / #42 | PASS G2 |
| 015 | Resultat final duplique rejete | TOOL-006 | 023 | `tests/acceptance/test_p4_l42_tool_calls.py` | G2 / #42 | PASS G2 |
| 016 | is_error conserve et redaction | TOOL-009 | 023/025 | `tests/acceptance/test_p4_l42_tool_calls.py` | G2 / #42 | PASS G2 |
| 017 | TextResponseFormat | TOOL-011 | 027 | `tests/acceptance/test_p4_l43_structured_output.py` | G3 / #44 | PASS G3 |
| 018 | JsonResponseFormat | TOOL-016 | 027 | `tests/acceptance/test_p4_l43_structured_output.py` | G3 / #44 | PASS G3 |
| 019 | Schema invalide rejete | TOOL-012 | 024/027 | `tests/acceptance/test_p4_l43_structured_output.py` | G3 / #44 | PASS G3 |
| 020 | strict None vs False | TOOL-017 | 027 | `tests/acceptance/test_p4_l43_structured_output.py` | G3 / #44 | PASS G3 |
| 021 | Schema valide produit VALID prouve | TOOL-014 | 027 | `tests/acceptance/test_p4_l43_structured_output.py` | G3 / #44 | PASS G3 |
| 022 | Sortie invalide/UNKNOWN non promue | TOOL-020 | 027 | `tests/acceptance/test_p4_l43_structured_output.py` | G3 / #44 | PASS G3 |
| 023 | Capability UNKNOWN vs NATIVE | TOOL-013 | 026/027 | `tests/acceptance/test_p4_l43_structured_output.py` | G3 / #44 | PASS G3 |
| 024 | raw secret pas en repr | TOOL-021 | 025/027 | `tests/acceptance/test_p4_l43_structured_output.py` | G3 / #44 | PASS G3 |
| 025 | Composition M3 et Tools/Choice | ADR-028 | 028 | `tests/acceptance/test_p4_l44_contracts_and_codecs.py` | G4 / #46 | PASS G4 |
| 026 | Tool support UNSUPPORTED refuse | INF-009 | 026/028 | `tests/acceptance/test_p4_l44_contracts_and_codecs.py` | G4 / #46 | PASS G4 |
| 027 | SchemaSupport UNKNOWN explicite | INF-010 | 026/028 | `tests/acceptance/test_p4_l44_contracts_and_codecs.py` | G4 / #46 | PASS G4 |
| 028 | ToolCallOutput sans ToolResult artificiel | INV-010 | 028 | `tests/acceptance/test_p4_l44_contracts_and_codecs.py` | G4 / #46 | PASS G4 |
| 029 | Inference JSON v1 refuse P4 | ADR-020/028/029 | 028/029 | `tests/acceptance/test_p4_l44_contracts_and_codecs.py` | G4 / #46 | PASS G4 |
| 030 | Round-trip Tooling JSON v1 | NFR-008 | 029 | `tests/acceptance/test_p4_l44_contracts_and_codecs.py` | G4 / #46 | PASS G4 |
| 031 | Version et kind inconnus rejetes | NFR-010 | 029 | `tests/acceptance/test_p4_l44_contracts_and_codecs.py` | G4 / #46 | PASS G4 |
| 032 | Regressions Model/Interaction/Inference v1 | M1/M2/M3 | 028/029 | `tests/acceptance/test_p4_l44_contracts_and_codecs.py` | G4 / #46 | PASS G4 |
| 033 | Aucun SDK/provider/executor en domaine | TOOL-003 | 022/028 | `tests/acceptance/test_p4_l45_integration.py` | G5 / #48 | PENDING G5 |
| 034 | Domain offline sans credentials | NFR-003/005 | 022 | `tests/acceptance/test_p4_l45_integration.py` | G5 / #48 | PENDING G5 |
| 035 | Walkthrough tool->call->result offline | UC-011/012 | 023/028 | `tests/acceptance/test_p4_l45_integration.py` | G5 / #48 | PENDING G5 |
| 036 | Snippet README copiable | NFR-docs | 027/028 | `tests/acceptance/test_p4_l45_integration.py` | G5 / #48 | PENDING G5 |
| 037 | Wheel/sdist et py.typed | NFR-001/004 | 029 | `tests/acceptance/test_p4_l45_integration.py + CI` | G5 / #48 | PENDING G5 |
| 038 | Schema hostile/ref distante rejete | ADR-024 | 024/029 | `tests/acceptance/test_p4_l44_contracts_and_codecs.py + tests/acceptance/test_p4_l45_integration.py` | G4/G5 / #46/#48 | PASS G4; extension G5 PENDING |
| 039 | Aucun secret dans erreur/repr | NFR-security | 025/029 | `tests/acceptance/test_p4_l44_contracts_and_codecs.py + tests/acceptance/test_p4_l45_integration.py` | G4/G5 / #46/#48 | PASS G4; extension G5 PENDING |
| 040 | Revue quarante AC/gates | Convention PyKit | 022-029 | `tests/acceptance/test_p4_l45_integration.py` | G5 / #48 | PENDING G5 |

## Chaîne des gates sur les SHAs réellement intégrés dans main

| Gate | PR de code et/ou docs | SHA main qualifiant (code) | CI push/main | Statut |
|---|---|---|---|---|
| P4-G0 | #38, #39 | `b66e94e3bcfec9b84fc77fd5e2860612f55827eb` | [#42079191595](https://github.com/tawounfouet/pyllmkit/actions/runs/42079191595) | GO avec réserves |
| P4-G1 | #40, #41 | `764809cedf4f79866757e14ed92fc9427cc87d56` | [#42082114438](https://github.com/tawounfouet/pyllmkit/actions/runs/42082114438) | GO avec réserves |
| P4-G2 | #42, #43 | `a7991d9fc6648b280744e7ca461d79c7c2544b60` | [#42084636736](https://github.com/tawounfouet/pyllmkit/actions/runs/42084636736) | GO avec réserves |
| P4-G3 | #44, #45 | `f187fe5278980a84e578a1a3d65ed21d2a117e78` | [#42087094649](https://github.com/tawounfouet/pyllmkit/actions/runs/42087094649) | GO avec réserves |
| P4-G4 | #46, #47 | `ab0257a0a9a08f2320b580340ba84c92609bbfc0` | [#42089506022](https://github.com/tawounfouet/pyllmkit/actions/runs/42089506022) | GO avec réserves |
| **P4-G5** | **L4.5 PR à qualifier** | **PENDING SHA** | **PENDING CI** | **PENDING** |
| **M4** | **Revue finale distincte** | **PENDING** | **PENDING** | **NO-GO d'attestation** |

Un test de PR L4.5 ne compte pas comme PASS G5 tant qu'une CI de push sur le commit exact intégré à `main` n'a pas réussi. Les tests antérieurs AC-001..032 sont qualifiés par leurs gates respectifs; tous sont en outre repris dans les suites de régression suivantes.

## Préoccupations transversales

- AC-033 : guards d'architecture existants pour L4.1..4 et nouvelle surveillance transverse L4.5.
- AC-034 : tests et exemples hors ligne, credentials vides dans GitHub Actions.
- AC-035 : [exemple 17](../../examples/17_full_tooling_walkthrough.py), parcourant Tool -> ToolCall -> ToolResult -> StructuredOutput -> Tooling JSON v1 sans appeler de modèle.
- AC-036 : README sous forme de snippet Python exécuté via la CI.
- AC-037 : `pyproject.toml`, `LICENSE`, `py.typed`, imports canoniques, wheel/sdist isolés en CI.
- AC-038 : scénarios hostiles (`$ref`, profondeur, valeurs non finies), déjà observés sur G1/G4, intégrés à G5.
- AC-039 : protections de `repr` et DomainValidationError, charges brutes non recopiées.
- AC-040 : matrice 001..040 et PV G0..G5 sur SHA réel; **la preuve de G5 est à compléter après merge**.

## Dette et limites

Issues [#22](https://github.com/tawounfouet/pyllmkit/issues/22), [#35](https://github.com/tawounfouet/pyllmkit/issues/35), [#36](https://github.com/tawounfouet/pyllmkit/issues/36) ouvertes : protections `main`, release, future frontière provider. Aucune review tierce APPROVED n'a été supposée. La version déclarée reste `0.1.0a2`, sans publication.

Les tests de la suite cumulative dépassent le nombre de recettes P4; on ne doit pas les présenter comme des tests exclusivement P4.
