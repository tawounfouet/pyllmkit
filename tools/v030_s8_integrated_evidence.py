"""S8 independent audit of v0.3.0 offline six-provider conformance evidence.

This tool validates an existing sanitized S2-S7 JSON report, never executes
provider traffic and never grants live, production or publication approval.
It deliberately freezes the S8 accepted oracle minima independently of the
reporter's internal manifest, so an accidental deletion cannot self-certify.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import re
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

_PROVIDERS = ("openai", "anthropic", "google", "xai", "mistral", "ollama")
_CLOUD = _PROVIDERS[:-1]
_HEX_SHA = re.compile(r"[0-9a-f]{40}\Z")

# Frozen integrated S8 profile. Update only with a reviewed gate decision.
_MINIMUMS: dict[str, int] = {
    "test_six_native_encoders_preserve_text_and_explicit_token_limit": 6,
    "test_generation_snapshot_missing_fails_before_adapter": 6,
    "test_developer_role_is_not_silently_coerced": 6,
    "test_status_failure_has_one_safe_code_and_one_transport_attempt": 108,
    "test_explicit_live_opt_in_gate_prevents_even_mock_transport_contact": 12,
    "test_native_response_projection_is_consistent_and_lossless": 24,
    "test_native_stream_conformance": 84,
    "test_pre_cancelled_native_session_never_contacts_transport": 12,
    "test_ollama_json_content_type_is_explicitly_supported": 2,
    "test_native_transport_error_is_sanitized_and_nonretryable": 48,
    "test_native_response_failure_is_strict_and_nonleaking": 72,
    "test_explicit_native_parameter_is_mapped_or_rejected": 48,
    "test_adapter_rejects_non_native_assessment_even_when_prepared": 72,
    "test_adapter_rejects_missing_assessment_without_silent_acceptance": 18,
    "test_application_refuses_non_native_support_before_adapter": 24,
    "test_supported_multiturn_text_history_is_lossless": 6,
    "test_history_role_restrictions_are_explicit_not_coerced": 30,
    "test_native_response_usage_and_finish_semantics": 60,
    "test_cancel_after_first_delta_closes_native_mock_transport": 12,
    "test_single_use_stream_session_rejects_replay_without_second_call": 12,
    "test_external_async_task_cancel_propagates_and_closes_native_mock_socket": 6,
    "test_cancel_after_completed_stream_has_no_second_terminal": 12,
    "test_cloud_rejects_any_unapproved_endpoint_before_secret_and_transport": 40,
    "test_cloud_valid_endpoint_still_works_with_synthetic_credential": 10,
    "test_openai_config_mutated_after_construction_is_rejected_at_call": 2,
    "test_ollama_mutated_destination_is_rejected_as_noncanonical": 8,
    "test_expired_invocation_deadline_prevents_native_egress": 12,
}
_EXPECTED_STATUSES = ("PASS", "FAIL", "NOT_APPLICABLE", "UNSUPPORTED", "BLOCKED")
_FIELDS = frozenset({
    "case_id", "scenario_id", "provider", "mode", "operation",
    "fixture_id", "status", "failure_type",
})
_FORBIDDEN_EVIDENCE_SPANS = (
    "://", "Bearer ", "Authorization:", "PYLLMKIT-V030-SYNTHETIC-SECRET",
    "SYNTHETIC-NATIVE-ERROR-CONFIDENTIAL", "API-KEY-FAKE",
)


def _providers_for(scenario: str) -> tuple[str, ...]:
    if scenario in {
        "test_ollama_json_content_type_is_explicitly_supported",
        "test_ollama_mutated_destination_is_rejected_as_noncanonical",
    }:
        return ("ollama",)
    if scenario == "test_openai_config_mutated_after_construction_is_rejected_at_call":
        return ("openai",)
    if scenario.startswith("test_cloud_"):
        return _CLOUD
    return _PROVIDERS


def assess_evidence(
    report: Any, *, expected_head: str,
    expected_tested: str, expected_python: str,
) -> list[str]:
    """Return deterministic, code-only violations without copying test data."""
    if not isinstance(report, dict):
        return ["report_not_object"]
    errors: list[str] = []
    checks = {
        "schema_version": "v030-conformance-evidence-v1",
        "milestone": "0.3.0",
        "tested_sha": expected_tested,
        "head_sha": expected_head,
        "python": expected_python,
        "source_kind": "synthetic_offline_mock_transport",
        "network_allowed": False,
        "status_vocabulary": list(_EXPECTED_STATUSES),
        "provider_axis": list(_PROVIDERS),
        "verdict": "PASS",
        "errors": [],
    }
    for key, expected in checks.items():
        if report.get(key) != expected:
            errors.append(f"metadata_mismatch:{key}")
    records = report.get("records")
    if not isinstance(records, list):
        return errors + ["records_not_array"]
    if len(records) < sum(_MINIMUMS.values()):
        errors.append("insufficient_total_cases")
    observed: Counter[str] = Counter()
    per_provider: Counter[tuple[str, str]] = Counter()
    per_mode: Counter[tuple[str, str, str]] = Counter()
    unique: set[str] = set()
    for entry in records:
        if not isinstance(entry, dict) or set(entry) != _FIELDS:
            errors.append("invalid_record_shape")
            continue
        case_id = entry["case_id"]
        scenario = entry["scenario_id"]
        provider = entry["provider"]
        mode = entry["mode"]
        operation = entry["operation"]
        fixture = entry["fixture_id"]
        if (
            not isinstance(case_id, str)
            or not isinstance(scenario, str)
            or not isinstance(provider, str)
            or not isinstance(mode, str)
            or not isinstance(operation, str)
            or not isinstance(fixture, str)
            or len(case_id) > 512
            or len(scenario) > 150
        ):
            errors.append("invalid_record_identifiers")
            continue
        if (
            not case_id.startswith(scenario + "[")
            or not case_id.endswith("]")
            or scenario not in _MINIMUMS
            or provider not in _PROVIDERS
            or mode not in ("sync", "async", "codec")
            or not re.fullmatch(r"[a-z_]{3,50}", operation)
            or not fixture.startswith("v030-")
        ):
            errors.append("unrecognized_record_identity")
            continue
        if any(span in case_id for span in _FORBIDDEN_EVIDENCE_SPANS):
            errors.append("unsafe_case_identifier")
        if entry["status"] != "PASS" or entry["failure_type"] is not None:
            errors.append("nonpassing_case")
        if case_id in unique:
            errors.append("duplicated_case_identifier")
        unique.add(case_id)
        if provider not in _providers_for(scenario):
            errors.append("scenario_provider_outside_scope")
        observed[scenario] += 1
        per_provider[(scenario, provider)] += 1
        per_mode[(scenario, provider, mode)] += 1
    for scenario, minimum in _MINIMUMS.items():
        if observed[scenario] < minimum:
            errors.append(f"missing_scenario:{scenario}")
        allowed = _providers_for(scenario)
        per_member_min = minimum // len(allowed)
        for provider in allowed:
            if per_provider[(scenario, provider)] < per_member_min:
                errors.append(f"missing_provider:{scenario}:{provider}")
    # The two native stream/error matrices explicitly promise both modes.
    for scenario in (
        "test_native_stream_conformance",
        "test_native_response_failure_is_strict_and_nonleaking",
        "test_cancel_after_first_delta_closes_native_mock_transport",
        "test_expired_invocation_deadline_prevents_native_egress",
    ):
        for provider in _PROVIDERS:
            for mode in ("sync", "async"):
                if per_mode[(scenario, provider, mode)] < 1:
                    errors.append(f"missing_mode:{scenario}:{provider}:{mode}")
    counts = report.get("counts")
    if not isinstance(counts, dict) or counts != {"PASS": len(records)}:
        errors.append("status_counts_inconsistent")
    return sorted(set(errors))


def _render_md(result: dict[str, Any]) -> str:
    violations = result["violations"]
    rows = [
        "# PyLLMKit 0.3.0 - S8 Offline Evidence Integrity",
        "",
        f"- Tested SHA: `{result['tested_sha']}`",
        f"- PR head SHA: `{result['head_sha']}`",
        f"- Python: `{result['python']}`",
        f"- Source conformance SHA256: `{result['source_sha256']}`",
        f"- Offline verdict: **{result['offline_verdict']}**",
        f"- Conformance cases: **{result['case_count']}**",
        f"- Required scenario families: **{result['required_families']}**",
        "",
        "## Authority boundaries",
        "",
        "- Synthetic MockTransport evidence only; no real DNS, peer-IP or TLS attestation.",
        "- This script does not inspect GitHub reviews, branch protections or live budgets.",
        "- S8 governance approval: **PENDING**.",
        "- Authorized live canary: **NO**; production: **NO**; package publication: **NO**.",
        "- No secret, prompt, response body or raw JUnit report is included.",
        "",
    ]
    if violations:
        rows += ["## Integrity violations", ""]
        rows += [f"- `{value}`" for value in violations]
        rows.append("")
    return "\n".join(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence-json", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--head-sha", required=True)
    parser.add_argument("--tested-sha", required=True)
    args = parser.parse_args()
    if not all(
        _HEX_SHA.fullmatch(value)
        for value in (args.head_sha, args.tested_sha)
    ):
        parser.error("expected exact lowercase 40-hex Git SHA")
    try:
        raw = args.evidence_json.read_bytes()
        if len(raw) > 4_000_000:
            raise ValueError("evidence_size_limit")
        report = json.loads(raw)
    except (OSError, UnicodeError, ValueError, TypeError):
        raw = b""
        report = None
    violations = assess_evidence(
        report,
        expected_head=args.head_sha,
        expected_tested=args.tested_sha,
        expected_python=platform.python_version(),
    )
    output = args.output_dir
    output.mkdir(parents=True, exist_ok=True)
    result = {
        "schema_version": "v030-s8-offline-gate-v1",
        "tested_sha": args.tested_sha,
        "head_sha": args.head_sha,
        "python": platform.python_version(),
        "generated_at": datetime.now(UTC).isoformat(),
        "source_sha256": hashlib.sha256(raw).hexdigest(),
        "case_count": len(report.get("records", [])) if isinstance(report, dict)
            and isinstance(report.get("records"), list) else 0,
        "required_families": len(_MINIMUMS),
        "offline_verdict": "PASS" if not violations else "FAIL",
        "violations": violations,
        "governance_gate": "PENDING_INDEPENDENT_REVIEW",
        "live_canary_authorized": False,
        "production_authorized": False,
        "release_authorized": False,
    }
    (output / "s8-offline-gate.json").write_text(
        json.dumps(result, indent=2) + "\n", encoding="utf-8",
    )
    (output / "s8-offline-gate.md").write_text(_render_md(result), encoding="utf-8")
    print(f"s8 evidence verdict={result['offline_verdict']} cases={result['case_count']}")
    if violations:
        print("s8 violations: " + ",".join(violations))
    return 1 if violations else 0


if __name__ == "__main__":
    raise SystemExit(main())
