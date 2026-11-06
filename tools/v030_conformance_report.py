"""Execute the offline 0.3.0 conformance suite and archive safe evidence.

This is a development/CI evidence generator, not a live compatibility probe.
Only controlled identifiers are serialized from JUnit; no failure bodies,
prompt contents, HTTP traces, stack traces or credentials are retained.
"""

from __future__ import annotations

import argparse
import json
import platform
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

_PROVIDERS = ("openai", "anthropic", "google", "xai", "mistral", "ollama")
_REQUIRED: dict[str, int] = {
    "test_six_native_encoders_preserve_text_and_explicit_token_limit": 6,
    "test_generation_snapshot_missing_fails_before_adapter": 6,
    "test_developer_role_is_not_silently_coerced": 6,
    "test_status_failure_has_one_safe_code_and_one_transport_attempt": 108,
    "test_explicit_live_opt_in_gate_prevents_even_mock_transport_contact": 12,
    "test_native_response_projection_is_consistent_and_lossless": 24,
    "test_native_stream_conformance": 60,
    "test_pre_cancelled_native_session_never_contacts_transport": 12,
}
_ALLOWED = ("PASS", "FAIL", "NOT_APPLICABLE", "UNSUPPORTED", "BLOCKED")
_FAILURE_TYPE = re.compile(r"[A-Za-z0-9_.]{1,100}\Z")
_SHA = re.compile(r"[0-9a-fA-F]{40}\Z")


def _provider(test_name: str) -> str | None:
    if "[" not in test_name or not test_name.endswith("]"):
        return None
    parameter = test_name.rsplit("[", 1)[-1][:-1]
    last = parameter.rsplit("-", 1)[-1]
    return last if last in _PROVIDERS else None


def _mode(test_name: str) -> str:
    if "[" not in test_name:
        return "unspecified"
    params = test_name.rsplit("[", 1)[-1][:-1].split("-")
    if "async" in params:
        return "async"
    if "sync" in params:
        return "sync"
    return "codec"


def _operation(method: str, mode: str) -> str:
    if method.startswith("test_native_stream_conformance"):
        return "astream_prepared" if mode == "async" else "stream_prepared"
    if method.startswith("test_pre_cancelled_native_session"):
        return "open_astream" if mode == "async" else "open_stream"
    if ("adapter" in method or "response_projection" in method or "status_failure" in method
            or method.startswith("test_explicit_live_opt_in_gate")):
        return "ainvoke" if mode == "async" else "invoke"
    return "encode_or_prepare"


def _status(testcase: ET.Element) -> tuple[str, str | None]:
    failure = testcase.find("failure")
    error = testcase.find("error")
    skipped = testcase.find("skipped")
    if failure is not None or error is not None:
        node = failure if failure is not None else error
        assert node is not None
        native_type = node.attrib.get("type", "")
        safe_type = native_type if _FAILURE_TYPE.fullmatch(native_type) else "test_failure"
        return "FAIL", safe_type
    if skipped is not None:
        return "BLOCKED", "unexpected_skip"
    return "PASS", None


def _records(xml_file: Path) -> list[dict[str, object]]:
    root = ET.parse(xml_file).getroot()
    records: list[dict[str, object]] = []
    for case in root.findall(".//testcase"):
        name = case.get("name", "")
        method = name.split("[", 1)[0]
        provider = _provider(name)
        mode = _mode(name)
        status, reason = _status(case)
        records.append({
            "case_id": name,
            "scenario_id": method,
            "provider": provider,
            "mode": mode,
            "operation": _operation(method, mode),
            "fixture_id": (
                "v030-s2-stream-v1"
                if method in {
                    "test_native_stream_conformance",
                    "test_pre_cancelled_native_session_never_contacts_transport",
                }
                else "v030-s2-http-synthetic-v1"
            ),
            "status": status,
            "failure_type": reason,
        })
    return records


def _verify(records: list[dict[str, object]], process_status: int) -> list[str]:
    errors: list[str] = []
    observed = Counter(str(item["scenario_id"]) for item in records)
    for name, minimum in _REQUIRED.items():
        if observed[name] < minimum:
            errors.append(f"missing_required_cases:{name}:{observed[name]}:{minimum}")
    if process_status != 0:
        errors.append(f"pytest_nonzero_exit:{process_status}")
    if any(item["status"] != "PASS" for item in records):
        errors.append("nonpass_scenarios_present")
    ids = [str(item["case_id"]) for item in records]
    if len(set(ids)) != len(ids):
        errors.append("duplicate_test_case_identifier")
    for scenario in _REQUIRED:
        providers = {
            item["provider"] for item in records
            if item["scenario_id"] == scenario
        }
        if providers != set(_PROVIDERS):
            errors.append(f"incomplete_provider_axis:{scenario}")
    if not records:
        errors.append("empty_conformance_report")
    return errors


def _markdown(data: dict[str, object]) -> str:
    rows = data["records"]
    assert isinstance(rows, list)
    counts = Counter(str(entry["provider"]) for entry in rows)
    passing = Counter(
        str(entry["provider"]) for entry in rows if entry["status"] == "PASS"
    )
    result = [
        "# PyLLMKit 0.3.0 - Offline Conformance Evidence",
        "",
        f"- Tested SHA: `{data['tested_sha']}`",
        f"- PR head SHA: `{data['head_sha']}`",
        f"- Python: `{data['python']}`",
        f"- Timestamp: `{data['generated_at']}`",
        f"- Verdict: **{data['verdict']}**",
        f"- Cases: **{len(rows)}**",
        "",
        "| Provider | PASS | Total |",
        "|---|---:|---:|",
    ]
    for provider in _PROVIDERS:
        result.append(f"| {provider} | {passing[provider]} | {counts[provider]} |")
    result += [
        "",
        "## Scenario coverage",
        "",
        "| Scenario | Observed | Minimum |",
        "|---|---:|---:|",
    ]
    observed = Counter(str(item["scenario_id"]) for item in rows)
    for scenario, minimum in _REQUIRED.items():
        result.append(f"| `{scenario}` | {observed[scenario]} | {minimum} |")
    result += [
        "",
        "## Boundaries and provenance",
        "",
        "- All wire fixtures and secrets are synthetic; no real network access.",
        "- Stream fixtures follow the P7 L7.6 synthetic fixture shapes.",
        "- PASS means local offline test success, **not** live provider certification.",
        "- This evidence does not approve production, live canaries or release.",
        "- No test failure messages or native HTTP bodies are included.",
        "",
    ]
    errors = data["errors"]
    assert isinstance(errors, list)
    if errors:
        result += ["## Gate violations", ""]
        result.extend(f"- `{str(value)}`" for value in errors)
        result.append("")
    return "\n".join(result)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--head-sha", required=True)
    parser.add_argument("--tested-sha", required=True)
    args = parser.parse_args()
    for key in ("head_sha", "tested_sha"):
        if _SHA.fullmatch(getattr(args, key)) is None:
            parser.error(f"{key} must be an exact 40-hex commit SHA")

    output: Path = args.output_dir
    output.mkdir(parents=True, exist_ok=True)
    junit = output / "junit.xml"
    completed = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "tests/conformance",
         f"--junitxml={junit}"],
        check=False, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True,
    )
    try:
        records = _records(junit)
    except (ET.ParseError, FileNotFoundError, ValueError):
        records = []
    # JUnit may contain exception tracebacks or fixture values. Never archive it.
    junit.unlink(missing_ok=True)
    errors = _verify(records, completed.returncode)
    data: dict[str, object] = {
        "schema_version": "v030-conformance-evidence-v1",
        "milestone": "0.3.0",
        "tested_sha": args.tested_sha.lower(),
        "head_sha": args.head_sha.lower(),
        "python": platform.python_version(),
        "generated_at": datetime.now(UTC).isoformat(),
        "provider_axis": list(_PROVIDERS),
        "status_vocabulary": list(_ALLOWED),
        "source_kind": "synthetic_offline_mock_transport",
        "network_allowed": False,
        "counts": dict(Counter(str(item["status"]) for item in records)),
        "verdict": "PASS" if not errors else "FAIL",
        "errors": errors,
        "records": records,
    }
    (output / "conformance.json").write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8",
    )
    (output / "conformance.md").write_text(_markdown(data), encoding="utf-8")
    print(f"conformance verdict={data['verdict']} cases={len(records)}")
    if errors:
        print("conformance errors: " + ",".join(errors))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
