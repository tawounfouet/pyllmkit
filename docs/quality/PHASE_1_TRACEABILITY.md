# Phase 1 - Acceptance & test traceability

Source: `01_PYLLMKIT_PHASE_1_IMPLEMENTATION_PLAN.md` §7.3 and §9.
Only **AC-001, AC-002, AC-004, AC-005, AC-018(P1)** are targeted by M1.

| Source criterion | Claimed coverage | Executable evidence |
|---|---|---|
| AC-001 | Instantiate Model without SDK | `tests/acceptance/test_phase_1_contracts.py::test_ac_001_model_instantiation_requires_no_provider_sdk`; import smoke tests |
| AC-002 | One family, different versions and variants | `test_ac_002_family_can_have_multiple_versions_and_variants`, `tests/unit/domain/models/test_model_domain.py` |
| AC-004 | Explicit modalities by input/output | `test_ac_004_directional_modalities_and_unknown`, modality unit tests |
| AC-005 | Declared Capability/SupportLevel | `test_ac_005_support_and_unknown_are_distinct`, capability unit tests |
| AC-018(P1) | Domain tests offline and without credentials | `test_ac_018_network_and_keys_are_unavailable_in_domain_tests`, `tests/conftest.py`, architecture tests |
| AC-003 | **OUT OF SCOPE** | Deployments are not implemented in Phase 1 |
| AC-006 through AC-017 | **OUT OF SCOPE** | Future roadmap, with no implied MVP qualification |

## Detailed §7.3 Phase 1 test cases

| Test ID | Evidence (examples) |
|---|---|
| TEST-M01 | `test_blank_or_invalid_model_id_is_rejected` |
| TEST-M02 | `test_ids_are_distinct_value_objects` |
| TEST-M03 | `test_model_identity_equality_and_snapshot_change` |
| TEST-M04 | `test_identity_is_value_based_and_immutable` |
| TEST-M05 | `test_family_variant_revision_are_independent`; AC-002 |
| TEST-M06 | `test_versions_do_not_require_semver` |
| TEST-M07 | `test_missing_architecture_and_limits_remain_unknown` |
| TEST-M08 | `test_no_deployment_or_endpoint_required` |
| TEST-M09 | `test_model_and_artifact_are_distinct` |
| TEST-M10 | `test_invalid_context_window_rejected` |
| TEST-C01 | `test_unknown_is_not_native_or_unsupported`; AC-005 |
| TEST-C02 | `test_all_declared_support_levels` |
| TEST-C03 | `test_partial_must_explain_limit` |
| TEST-C04 | `test_capability_id_extensible_and_immutable` |
| TEST-C05 | `test_union_intersection_difference_work_for_consistent_catalog`; conflicting-entries test |
| TEST-MOD01 | `test_input_and_output_do_not_mix` |
| TEST-MOD02 | `test_ac_004_directional_modalities_and_unknown`; `test_ac_005_support_and_unknown_are_distinct` |
| TEST-S01 | `test_model_round_trip_preserves_all_known_fields`, `test_composed_model_roundtrip_json` |
| TEST-A01 | `test_domain_packages_import_without_provider_sdk` |
| TEST-A02 | `test_domain_has_no_known_forbidden_imports`, `test_forbidden_imports_are_detected` |
| TEST-A03 | `test_ac_018_network_and_keys_are_unavailable_in_domain_tests`; socket-blocked fixture |
| TEST-P01 | CI wheel/sdist isolated venv install and domain smoke import |

No checkbox is automatically approved by the presence of a test alone: require a successful CI run at the reviewed SHA and acceptance of the test's adequacy.

## Open items

- Release readiness and M1 approval are separate from a successful CI run.
- Architecture ADRs remain proposals until reviewed.
- Coverage of security, dynamic imports, or arbitrary SDK usage is bounded by the fitness tests; not a comprehensive security audit.
