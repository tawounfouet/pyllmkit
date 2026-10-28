# Phase 1 - Acceptance & test traceability

Source: `01_PYLLMKIT_PHASE_1_IMPLEMENTATION_PLAN.md` §§7.3/9; `ROADMAP.md` §6.

## Selected M1 ACs

| AC | Proof |
|---|---|
| AC-001 | `tests/acceptance/test_phase_1_contracts.py::test_ac_001_model_instantiation_requires_no_provider_sdk` |
| AC-002 | `test_ac_002_family_can_have_multiple_versions_and_variants` |
| AC-004 | `test_ac_004_directional_modalities_and_unknown` |
| AC-005 | `test_ac_005_support_and_unknown_are_distinct` |
| AC-018(P1) | `test_ac_018_network_and_keys_are_unavailable_in_domain_tests`, autouse fixture & architecture guards |

AC-003 and AC-006–017 are **OUT OF SCOPE** and not qualified by M1.

## Source plan §7.3 test mapping

| Identifier | Evidence |
|---|---|
| TEST-M01 | `test_blank_or_invalid_model_id_is_rejected` |
| TEST-M02 | `test_ids_are_distinct_value_objects` |
| TEST-M03 | `test_model_identity_equality_and_snapshot_change` |
| TEST-M04 | `test_identity_is_value_based_and_immutable` |
| TEST-M05 | `test_family_variant_revision_are_independent` and AC-002 |
| TEST-M06 | `test_versions_do_not_require_semver` |
| TEST-M07 | `test_missing_architecture_and_limits_remain_unknown` |
| TEST-M08 | `test_no_deployment_or_endpoint_required` |
| TEST-M09 | `test_model_and_artifact_are_distinct` |
| TEST-M10 | `test_invalid_context_window_rejected` |
| TEST-C01 | `test_unknown_is_not_native_or_unsupported` |
| TEST-C02 | `test_all_declared_support_levels` |
| TEST-C03 | `test_partial_must_explain_limit` |
| TEST-C04 | `test_capability_id_extensible_and_immutable` |
| TEST-C05 | `test_union_intersection_difference_work_for_consistent_catalog` and conflicting-declaration test |
| TEST-MOD01 | `test_input_and_output_do_not_mix` |
| **TEST-MOD02** | **`tests/acceptance/test_m1_semantic_boundaries.py::test_mod02_image_modality_is_not_vision_capability`** (new review regression) |
| TEST-S01 | `test_model_round_trip_preserves_all_known_fields`, `test_composed_model_roundtrip_json` |
| TEST-A01 | `test_domain_packages_import_without_provider_sdk` |
| TEST-A02 | `test_domain_has_no_known_forbidden_imports`, `test_forbidden_imports_are_detected` |
| TEST-A03 | `test_ac_018_network_and_keys_are_unavailable_in_domain_tests`; socket guard |
| TEST-P01 | GitHub CI independent wheel and sdist installs + import smoke |

Additional invariant evidence: `test_model_016_017_alias_is_scoped_by_provider` proves distinct provider aliases may share an external string.

**No test mapping alone implies formal M1 approval.** Exact review-head CI and final integrated `main` CI are separate mandatory gates.
