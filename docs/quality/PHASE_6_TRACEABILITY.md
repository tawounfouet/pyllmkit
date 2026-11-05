# Phase 6 - Registry & Discovery: traçabilité des 56 cas d'acceptation

- Date : 2026-11-05
- Statut : candidats sur branches de PR, aucun gate P6 ni M6 qualifié sur main.
- Source : libellés dérivés des tests exécutables et contrat ADR-039..048. Ce n'est pas une transcription garantie du plan détaillé externe.
- CI de référence : à renseigner sur le SHA exact du dernier lot.

## Matrice des cas effectivement identifiés

| Cas | Libellé du test représentatif | Fichier de test | Gate |
|---|---|---|---|
| P6-AC-001 | provider id is typed opaque ordered immutable | `tests/acceptance/test_p6_l61_domain.py` | P6-G1 / L6.1 |
| P6-AC-002 | provider is passive with unknown declarations | `tests/acceptance/test_p6_l61_domain.py` | P6-G1 / L6.1 |
| P6-AC-003 | deployment reuses existing id types | `tests/acceptance/test_p6_l61_domain.py` | P6-G1 / L6.1 |
| P6-AC-004 | multiple deployments reference one model | `tests/acceptance/test_p6_l61_domain.py` | P6-G1 / L6.1 |
| P6-AC-005 | local deployment without provider is valid | `tests/acceptance/test_p6_l61_domain.py` | P6-G1 / L6.1 |
| P6-AC-006 | explicit status transition and deprecated terminal | `tests/acceptance/test_p6_l61_domain.py` | P6-G1 / L6.1 |
| P6-AC-007 | snapshot keeps typed metadata and immutable state | `tests/acceptance/test_p6_l61_domain.py` | P6-G1 / L6.1 |
| P6-AC-008 | provider alias stays string and id contract unchanged | `tests/acceptance/test_p6_l61_domain.py` | P6-G1 / L6.1 |
| P6-AC-009 | model registry implements port with exact lookup | `tests/acceptance/test_p6_l62_registries.py` | P6-G2 / L6.2 |
| P6-AC-010 | deployment registry enforces existing typed references | `tests/acceptance/test_p6_l62_registries.py` | P6-G2 / L6.2 |
| P6-AC-011 | provider catalog is metadata only and separate port | `tests/acceptance/test_p6_l62_registries.py` | P6-G2 / L6.2 |
| P6-AC-012 | idempotent register preserves original snapshot object | `tests/acceptance/test_p6_l62_registries.py` | P6-G2 / L6.2 |
| P6-AC-013 | model collision checks all metadata not identity only | `tests/acceptance/test_p6_l62_registries.py` | P6-G2 / L6.2 |
| P6-AC-014 | referenced model and provider cannot be removed | `tests/acceptance/test_p6_l62_registries.py` | P6-G2 / L6.2 |
| P6-AC-015 | all three registries return sorted tuple not insertion order | `tests/acceptance/test_p6_l62_registries.py` | P6-G2 / L6.2 |
| P6-AC-016 | snapshot and find results are immutable and no dict is exposed | `tests/acceptance/test_p6_l62_registries.py` | P6-G2 / L6.2 |
| P6-AC-017 | model family search keeps distinct variants and ids | `tests/acceptance/test_p6_l63_queries.py` | P6-G3 / L6.3 |
| P6-AC-018 | native mode vs explicit usable keeps unknown out | `tests/acceptance/test_p6_l63_queries.py` | P6-G3 / L6.3 |
| P6-AC-019 | input and output modalities must match independently | `tests/acceptance/test_p6_l63_queries.py` | P6-G3 / L6.3 |
| P6-AC-020 | provider filter matches verified alias without rewriting model id | `tests/acceptance/test_p6_l63_queries.py` | P6-G3 / L6.3 |
| P6-AC-021 | context limit requires known declared value | `tests/acceptance/test_p6_l63_queries.py` | P6-G3 / L6.3 |
| P6-AC-022 | deployment filters status region runtime model provider | `tests/acceptance/test_p6_l63_queries.py` | P6-G3 / L6.3 |
| P6-AC-023 | conjunctive search is stable readonly and no mutation | `tests/acceptance/test_p6_l63_queries.py` | P6-G3 / L6.3 |
| P6-AC-024 | unknown deployment capability is not a confirmed match | `tests/acceptance/test_p6_l63_queries.py` | P6-G3 / L6.3 |
| P6-AC-025 | all native sources are confirmed and deterministic | `tests/acceptance/test_p6_l64_effective_capabilities.py` | P6-G4 / L6.4 |
| P6-AC-026 | unknown deployment remains unknown not native | `tests/acceptance/test_p6_l64_effective_capabilities.py` | P6-G4 / L6.4 |
| P6-AC-027 | explicit unsupported vetoes unknown | `tests/acceptance/test_p6_l64_effective_capabilities.py` | P6-G4 / L6.4 |
| P6-AC-028 | mixed support preserves emulation | `tests/acceptance/test_p6_l64_effective_capabilities.py` | P6-G4 / L6.4 |
| P6-AC-029 | local provider is not applicable only when proven absent | `tests/acceptance/test_p6_l64_effective_capabilities.py` | P6-G4 / L6.4 |
| P6-AC-030 | requested capabilities are canonical and reject duplicate ids | `tests/acceptance/test_p6_l64_effective_capabilities.py` | P6-G4 / L6.4 |
| P6-AC-031 | limits minimum known bound keeps unknown provisional | `tests/acceptance/test_p6_l64_effective_capabilities.py` | P6-G4 / L6.4 |
| P6-AC-032 | restrictive numeric boolean and tuple constraints | `tests/acceptance/test_p6_l64_effective_capabilities.py` | P6-G4 / L6.4 |
| P6-AC-033 | one eligible model deployment is selected with evidence | `tests/acceptance/test_p6_l65_deployment_resolution.py` | P6-G5 / L6.5 |
| P6-AC-034 | no candidate produces typed no compatible report | `tests/acceptance/test_p6_l65_deployment_resolution.py` | P6-G5 / L6.5 |
| P6-AC-035 | multiple eligible deployments are ambiguous never first | `tests/acceptance/test_p6_l65_deployment_resolution.py` | P6-G5 / L6.5 |
| P6-AC-036 | provider region runtime filters are hard constraints | `tests/acceptance/test_p6_l65_deployment_resolution.py` | P6-G5 / L6.5 |
| P6-AC-037 | unknown capability fails strict selection | `tests/acceptance/test_p6_l65_deployment_resolution.py` | P6-G5 / L6.5 |
| P6-AC-038 | declared status is required by default not live health | `tests/acceptance/test_p6_l65_deployment_resolution.py` | P6-G5 / L6.5 |
| P6-AC-039 | exact target is not redirected or silently fallback | `tests/acceptance/test_p6_l65_deployment_resolution.py` | P6-G5 / L6.5 |
| P6-AC-040 | pure reproducible order independent of registry insertion | `tests/acceptance/test_p6_l65_deployment_resolution.py` | P6-G5 / L6.5 |
| P6-AC-041 | static source is typed pure and never registers automatically | `tests/acceptance/test_p6_l66_offline_discovery_merge.py` | P6-G6 / L6.6 |
| P6-AC-042 | time is utc injected and future skew explicit | `tests/acceptance/test_p6_l66_offline_discovery_merge.py` | P6-G6 / L6.6 |
| P6-AC-043 | import three kinds with origin and one revision | `tests/acceptance/test_p6_l66_offline_discovery_merge.py` | P6-G6 / L6.6 |
| P6-AC-044 | preview is read only and sorted regardless of batch order | `tests/acceptance/test_p6_l66_offline_discovery_merge.py` | P6-G6 / L6.6 |
| P6-AC-045 | model collision rejects full batch not identity only | `tests/acceptance/test_p6_l66_offline_discovery_merge.py` | P6-G6 / L6.6 |
| P6-AC-046 | missing model provider references reject whole batch | `tests/acceptance/test_p6_l66_offline_discovery_merge.py` | P6-G6 / L6.6 |
| P6-AC-047 | idempotent replay is no op and preserves original provenance | `tests/acceptance/test_p6_l66_offline_discovery_merge.py` | P6-G6 / L6.6 |
| P6-AC-048 | commutative import of disjoint batches yields same catalog | `tests/acceptance/test_p6_l66_offline_discovery_merge.py` | P6-G6 / L6.6 |
| P6-AC-049 | offline end to end import search resolve with three port integration | `tests/acceptance/test_p6_l67_integration_quality.py` | P6-G7 / L6.7 |
| P6-AC-050 | explicit public api does not require provider sdk | `tests/acceptance/test_p6_l67_integration_quality.py` | P6-G7 / L6.7 |
| P6-AC-051 | domain registry import fitness no adapters application or network | `tests/acceptance/test_p6_l67_integration_quality.py` | P6-G7 / L6.7 |
| P6-AC-052 | rejected merge preserves privacy and original metadata | `tests/acceptance/test_p6_l67_integration_quality.py` | P6-G7 / L6.7 |
| P6-AC-053 | legacy model json v1 remains independent of p6 registry | `tests/acceptance/test_p6_l67_integration_quality.py` | P6-G7 / L6.7 |
| P6-AC-054 | snapshot replay noop without side effects | `tests/acceptance/test_p6_l67_integration_quality.py` | P6-G7 / L6.7 |
| P6-AC-055 | package version and python distribution constraints remain stable | `tests/acceptance/test_p6_l67_integration_quality.py` | P6-G7 / L6.7 |
| P6-AC-056 | 56 unique acceptance labels and six example files present | `tests/acceptance/test_p6_l67_integration_quality.py` | P6-G7 / L6.7 |

## Limites et preuves nécessaires

- Ce registre d'acceptation prouve la présence des 56 identifiants uniques dans les tests. La réussite des tests dépend des workflows CI vérifiés, et ne vaut pas validation d'un fournisseur externe.
- La suite hérite des tests M1-M5 et des codecs existants. Les exemples 23..28 doivent s'exécuter depuis checkout, wheel et sdist sur Python 3.11, 3.12 et 3.13.
- Chaque gate nécessite une approbation documentaire et une CI push/main après fusion sur le SHA exact. Une CI de PR ne remplace pas cette preuve.
- Revue finale M6 séparée de P6-G7. Release 0.1.0b2 non autorisée; version source 0.1.0a2.
- Sujets #22 (main), #35 (release), #36 (frontière providers) restent sous réserve.
