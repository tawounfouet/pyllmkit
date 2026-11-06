"""Unit tests for the conformance evidence gate, including safe failures."""

import xml.etree.ElementTree as ET

import pytest

from tools.v030_conformance_report import (
    _mode,
    _operation,
    _provider,
    _status,
)


@pytest.mark.parametrize(
    ("case", "provider", "mode"),
    [
        ("test_native_stream_conformance[complete-sync-openai]", "openai", "sync"),
        ("test_native_stream_conformance[malformed-async-xai]", "xai", "async"),
        ("test_native_response_projection_is_consistent_and_lossless"
         "[usage_present-async-mistral]", "mistral", "async"),
        ("test_ollama_json_content_type_is_explicitly_supported[sync]", "ollama", "sync"),
        ("test_ollama_json_content_type_is_explicitly_supported[async]", "ollama", "async"),
        ("test_generation_snapshot_missing_fails_before_adapter[google]", "google", "codec"),
    ],
)
def test_case_axes_are_explicit(case: str, provider: str, mode: str) -> None:
    assert _provider(case) == provider
    assert _mode(case) == mode


@pytest.mark.parametrize(
    ("case", "operation"),
    [
        ("test_native_stream_conformance[complete-sync-openai]", "stream_prepared"),
        ("test_native_stream_conformance[complete-async-openai]", "astream_prepared"),
        ("test_ollama_json_content_type_is_explicitly_supported[sync]", "stream_prepared"),
        ("test_ollama_json_content_type_is_explicitly_supported[async]", "astream_prepared"),
        ("test_pre_cancelled_native_session_never_contacts_transport[sync-google]",
         "open_stream"),
        ("test_status_failure_has_one_safe_code_and_one_transport_attempt"
         "[400-invalid_request-async-xai]", "ainvoke"),
    ],
)
def test_case_operation_is_not_silently_misclassified(case: str, operation: str) -> None:
    assert _operation(case.split("[", 1)[0], _mode(case)) == operation


def test_junit_failures_never_expose_native_failure_message() -> None:
    case = ET.fromstring(
        '<testcase name="demo">'
        '<failure type="AssertionError" message="API-KEY-FAKE">API-KEY-FAKE</failure>'
        '</testcase>'
    )
    assert _status(case) == ("FAIL", "AssertionError")


def test_junit_untrusted_failure_type_is_replaced() -> None:
    case = ET.fromstring(
        '<testcase name="demo"><error type="secret: value" /></testcase>'
    )
    assert _status(case) == ("FAIL", "test_failure")


def test_junit_skips_are_visible_as_blocked() -> None:
    case = ET.fromstring(
        '<testcase name="demo"><skipped message="not available" /></testcase>'
    )
    assert _status(case) == ("BLOCKED", "unexpected_skip")
