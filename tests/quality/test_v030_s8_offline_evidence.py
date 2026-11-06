"""S8 evidence gate: independent mutation and provenance qualification."""

from copy import deepcopy

import pytest

from tools.v030_s8_integrated_evidence import (
    _MINIMUMS,
    _PROVIDERS,
    _providers_for,
    assess_evidence,
)

_HEAD = "a" * 40
_TESTED = "b" * 40
_PYTHON = "3.12.9"


def _valid_report() -> dict[str, object]:
    records: list[dict[str, object]] = []
    for scenario, minimum in _MINIMUMS.items():
        allowed = _providers_for(scenario)
        for index in range(minimum):
            provider = allowed[index % len(allowed)]
            mode = "async" if (index // len(allowed)) % 2 else "sync"
            records.append({
                "case_id": f"{scenario}[{index:03d}-{mode}-{provider}]",
                "scenario_id": scenario,
                "provider": provider,
                "mode": mode,
                "operation": "ainvoke" if mode == "async" else "invoke",
                "fixture_id": "v030-synthetic-test-fixture-v1",
                "status": "PASS",
                "failure_type": None,
            })
    return {
        "schema_version": "v030-conformance-evidence-v1",
        "milestone": "0.3.0",
        "head_sha": _HEAD,
        "tested_sha": _TESTED,
        "python": _PYTHON,
        "source_kind": "synthetic_offline_mock_transport",
        "network_allowed": False,
        "provider_axis": list(_PROVIDERS),
        "status_vocabulary": [
            "PASS", "FAIL", "NOT_APPLICABLE", "UNSUPPORTED", "BLOCKED",
        ],
        "verdict": "PASS",
        "errors": [],
        "counts": {"PASS": len(records)},
        "records": records,
    }


def _check(payload: object) -> list[str]:
    return assess_evidence(
        payload, expected_head=_HEAD,
        expected_tested=_TESTED, expected_python=_PYTHON,
    )


def test_complete_synthetic_baseline_is_accepted() -> None:
    report = _valid_report()
    assert len(report["records"]) == 752  # type: ignore[arg-type]
    assert _check(report) == []


@pytest.mark.parametrize(
    ("field", "changed", "reason"),
    [
        ("head_sha", "c" * 40, "metadata_mismatch:head_sha"),
        ("tested_sha", "d" * 40, "metadata_mismatch:tested_sha"),
        ("python", "3.14.0", "metadata_mismatch:python"),
        ("network_allowed", True, "metadata_mismatch:network_allowed"),
        ("source_kind", "live", "metadata_mismatch:source_kind"),
        ("verdict", "FAIL", "metadata_mismatch:verdict"),
    ],
)
def test_false_provenance_cannot_self_certify(
    field: str, changed: object, reason: str,
) -> None:
    evidence = _valid_report()
    evidence[field] = changed
    assert reason in _check(evidence)


def test_missing_scenario_detected_even_if_report_claims_pass() -> None:
    report = _valid_report()
    records = report["records"]
    assert isinstance(records, list)
    records.pop()
    report["counts"] = {"PASS": len(records)}
    assert "insufficient_total_cases" in _check(report)


def test_provider_axis_in_a_single_scenario_is_mandatory() -> None:
    report = _valid_report()
    records = report["records"]
    assert isinstance(records, list)
    scenario = "test_cloud_valid_endpoint_still_works_with_synthetic_credential"
    for item in records:
        assert isinstance(item, dict)
        if item["scenario_id"] == scenario and item["provider"] == "google":
            item["provider"] = "openai"
    errors = _check(report)
    assert f"missing_provider:{scenario}:google" in errors


def test_error_and_skip_are_never_laundered_into_pass() -> None:
    report = _valid_report()
    records = report["records"]
    assert isinstance(records, list)
    entry = records[0]
    assert isinstance(entry, dict)
    entry["status"] = "BLOCKED"
    assert "nonpassing_case" in _check(report)


def test_duplicate_case_id_is_visible_even_if_all_marked_pass() -> None:
    report = _valid_report()
    records = report["records"]
    assert isinstance(records, list)
    entry = records[1]
    assert isinstance(entry, dict)
    first = records[0]
    assert isinstance(first, dict)
    entry["case_id"] = first["case_id"]
    assert "duplicated_case_identifier" in _check(report)


def test_raw_endpoint_must_not_enter_safe_evidence_identifier() -> None:
    report = _valid_report()
    records = report["records"]
    assert isinstance(records, list)
    entry = records[0]
    assert isinstance(entry, dict)
    entry["case_id"] = f"{entry['scenario_id']}[https://evil.example-openai]"
    assert "unsafe_case_identifier" in _check(report)


def test_missing_async_mode_fails_closed_even_with_pass_counts() -> None:
    report = _valid_report()
    records = report["records"]
    assert isinstance(records, list)
    for entry in records:
        assert isinstance(entry, dict)
        if entry["scenario_id"] == "test_native_stream_conformance" and entry["provider"] == "ollama":
            entry["mode"] = "sync"
    assert "missing_mode:test_native_stream_conformance:ollama:async" in _check(report)


def test_malformed_report_is_not_accepted() -> None:
    assert _check(None) == ["report_not_object"]
    assert "records_not_array" in _check({"records": "not-array"})


def test_error_outputs_are_code_only_and_never_repeat_payloads() -> None:
    data = deepcopy(_valid_report())
    records = data["records"]
    assert isinstance(records, list)
    assert isinstance(records[0], dict)
    records[0]["body"] = "SYNTHETIC-SECRET-PLACEHOLDER"
    assert "invalid_record_shape" in _check(data)
    assert not any("PLACEHOLDER" in item for item in _check(data))
