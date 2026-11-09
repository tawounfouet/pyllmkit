"""M2-G4.1: strictly offline, synthetic invoice reconciliation and CLI contracts."""

from __future__ import annotations

import json
from dataclasses import replace
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from pyllmkit.adapters.cli.finops_invoice import (
    parse_synthetic_invoice_statement,
    parse_synthetic_invoice_statement_json,
)
from pyllmkit.adapters.cli.finops_quote import parse_quote_request, quote_media_scenario
from pyllmkit.adapters.cli.main import app
from pyllmkit.adapters.cli.media_catalog_v2 import load_media_catalog
from pyllmkit.adapters.cli.pricing_catalog_v2 import parse_price_catalog
from pyllmkit.domain.finops import FinOpsError
from pyllmkit.domain.finops.invoice_reconciliation import (
    InvoiceLineKind,
    SyntheticInvoiceLine,
    SyntheticInvoiceStatement,
    reconcile_synthetic_statement,
    reconciliation_to_dict,
)


def _scenario() -> dict[str, Any]:
    return {
        "schema_version": 1, "model_id": "gpt-image-2", "api_provider": "openai",
        "task": "text_to_image", "at": "2026-11-08T15:59:00+01:00",
        "parameters": {"quality": "high"}, "components": [
            {"meter": "image", "maximum": "2", "dimensions": {"quality": "high"}},
            {"meter": "input_token", "maximum": "1000", "dimensions": {}},
        ],
    }


def _prices() -> dict[str, Any]:
    return {
        "schema_version": 2, "revision": "synthetic-g4", "updated_at": "2026-11-08",
        "prices": [{
            "price_id": "fake-g4", "revision": "r1", "model_id": "gpt-image-2",
            "api_provider": "openai", "billing_provider": "openai",
            "deployment_channel": "direct", "currency": "USD",
            "valid_from": "2026-11-01T00:00:00+00:00", "valid_to": None,
            "source_url": "https://example.org/synthetic-only",
            "verified_at": "2026-11-08",
            "rates": [
                {"meter": "image", "amount": "0.025", "per": "1", "dimensions": {"quality": "high"}},
                {"meter": "input_token", "amount": "1", "per": "1000000", "dimensions": {}},
            ],
        }],
    }


def _quote(*, empty_tariff: bool = False):
    prices = _prices()
    if empty_tariff:
        prices["prices"] = []
    return quote_media_scenario(
        parse_quote_request(_scenario()),
        prices=parse_price_catalog(prices),
        media=load_media_catalog(),
    )


def _statement() -> dict[str, Any]:
    return {
        "schema_version": 1, "source_kind": "synthetic_fixture",
        "statement_id": "sample-001",
        "model_id": "gpt-image-2", "api_provider": "openai",
        "billing_provider": "openai", "deployment_channel": "direct",
        "currency": "USD", "lines": [
            {"line_id": "usage-01", "provider_request_id": "fake-call-001", "kind": "usage", "amount": "0.051"},
            {"line_id": "tax-01", "provider_request_id": "fake-call-001", "kind": "tax", "amount": "0.010"},
            {"line_id": "credit-01", "provider_request_id": "fake-call-001", "kind": "credit", "amount": "0.005"},
            {"line_id": "other-01", "provider_request_id": "other-call", "kind": "usage", "amount": "3"},
        ],
    }


def _reconcile(statement: dict[str, Any] | None = None, *, tolerance: Decimal = Decimal("0")):
    return reconcile_synthetic_statement(
        _quote(), parse_synthetic_invoice_statement(statement or _statement()),
        expected_provider_request_id="fake-call-001", tolerance=tolerance,
    )


def test_synthetic_match_uses_usage_not_tax_adjusted_net() -> None:
    result = reconciliation_to_dict(_reconcile())
    assert result["status"] == "matched_synthetic"
    assert result["reason"] == "declared_usage_agrees_only"
    assert result["quote_amount"] == {"value": "0.051", "currency": "USD"}
    assert result["usage_amount"] == {"value": "0.051", "currency": "USD"}
    assert result["tax_amount"] == {"value": "0.010", "currency": "USD"}
    assert result["credit_amount"] == {"value": "0.005", "currency": "USD"}
    assert result["net_amount"] == "0.056"
    assert result["usage_variance"] == "0.000"
    assert result["matched_line_ids"] == ["usage-01", "tax-01", "credit-01"]
    assert result["provider_request_correlation"] == "caller_declared_not_verified"
    assert result["provider_invoice_verified"] is False
    assert result["budget_ledger_mutated"] is False
    assert result["live_authorized"] is False


def test_variance_has_exact_decimal_sign_and_optional_tolerance() -> None:
    data = _statement()
    data["lines"][0]["amount"] = "0.055"
    result = _reconcile(data)
    assert result.status == "variance_synthetic"
    assert result.usage_variance == Decimal("0.004")
    assert _reconcile(data, tolerance=Decimal("0.004")).status == "matched_synthetic"


def test_negative_usage_variance_is_preserved() -> None:
    data = _statement()
    data["lines"][0]["amount"] = "0.040"
    result = _reconcile(data)
    assert result.usage_variance == Decimal("-0.011")
    assert result.status == "variance_synthetic"


def test_unmatched_request_reports_null_not_zero() -> None:
    result = reconcile_synthetic_statement(
        _quote(), parse_synthetic_invoice_statement(_statement()),
        expected_provider_request_id="missing-call",
    )
    payload = reconciliation_to_dict(result)
    assert payload["status"] == "unmatched"
    assert payload["usage_amount"] is None
    assert payload["net_amount"] is None
    assert payload["usage_variance"] is None
    assert payload["matched_line_ids"] == []


def test_tax_only_has_no_usage_subtotal_and_no_false_zero() -> None:
    data = _statement()
    data["lines"] = [data["lines"][1], data["lines"][2]]
    report = reconciliation_to_dict(_reconcile(data))
    assert report["status"] == "indeterminate"
    assert report["reason"] == "usage_lines_missing"
    assert report["usage_amount"] is None
    assert report["tax_amount"] == {"value": "0.010", "currency": "USD"}
    assert report["net_amount"] is None


def test_zero_usage_is_a_valid_declared_amount_not_missing() -> None:
    data = _statement()
    data["lines"] = [{
        "line_id": "zero-usage", "provider_request_id": "fake-call-001",
        "kind": "usage", "amount": "0",
    }]
    result = _reconcile(data)
    assert result.status == "variance_synthetic"
    assert result.usage_amount is not None and result.usage_amount.amount == 0
    assert result.usage_variance == Decimal("-0.051")


def test_credits_can_exceed_usage_without_treating_net_as_money() -> None:
    data = _statement()
    data["lines"][2]["amount"] = "10"
    assert _reconcile(data).net_amount == Decimal("-9.939")


@pytest.mark.parametrize("field", [
    "model_id", "api_provider", "billing_provider", "deployment_channel", "currency",
])
def test_billing_route_mismatch_refuses_reconciliation(field: str) -> None:
    data = _statement()
    data[field] = "EUR" if field == "currency" else "different"
    result = _reconcile(data)
    assert result.status == "indeterminate"
    assert result.reason == "billing_route_mismatch"
    assert result.usage_amount is None


def test_quote_missing_tariff_cannot_be_reconciled() -> None:
    result = reconcile_synthetic_statement(
        _quote(empty_tariff=True),
        parse_synthetic_invoice_statement(_statement()),
        expected_provider_request_id="fake-call-001",
    )
    assert result.status == "indeterminate"
    assert result.reason == "quote_not_priced"


def test_multiple_usage_lines_for_same_request_aggregate_exactly() -> None:
    data = _statement()
    data["lines"][0]["amount"] = "0.050"
    data["lines"].append({
        "line_id": "usage-02", "provider_request_id": "fake-call-001",
        "kind": "usage", "amount": "0.001",
    })
    result = _reconcile(data)
    assert result.status == "matched_synthetic"
    assert result.usage_amount is not None and result.usage_amount.amount == Decimal("0.051")


def test_duplicate_line_ids_rejected_even_on_other_requests() -> None:
    data = _statement()
    data["lines"][3]["line_id"] = "usage-01"
    with pytest.raises(FinOpsError, match="duplicate_invoice_line_id"):
        parse_synthetic_invoice_statement(data)


@pytest.mark.parametrize("invalid", [
    "0.01e3", "-0.01", "NaN", "Infinity", " 0.1", ".1", "1.", "0.01USD",
])
def test_strict_invoice_money_rejects_ambiguous_numbers(invalid: str) -> None:
    data = _statement()
    data["lines"][0]["amount"] = invalid
    with pytest.raises(FinOpsError, match="invalid_invoice_amount"):
        parse_synthetic_invoice_statement(data)


def test_json_floats_and_unknown_fields_are_rejected() -> None:
    data = _statement()
    data["lines"][0]["amount"] = 0.051
    with pytest.raises(FinOpsError, match="invalid_invoice_amount"):
        parse_synthetic_invoice_statement(data)
    data = _statement()
    data["extra"] = "untrusted"
    with pytest.raises(FinOpsError, match="invalid_invoice_statement_fields"):
        parse_synthetic_invoice_statement(data)
    data = _statement()
    data["lines"][0]["extra"] = "untrusted"
    with pytest.raises(FinOpsError, match="invalid_invoice_line_fields"):
        parse_synthetic_invoice_statement(data)


@pytest.mark.parametrize("bad_kind", ["charge", "refund", "", 42, None])
def test_only_explicit_usage_tax_credit_kinds_are_accepted(bad_kind: object) -> None:
    data = _statement()
    data["lines"][0]["kind"] = bad_kind
    with pytest.raises(FinOpsError, match="invalid_invoice_line_kind"):
        parse_synthetic_invoice_statement(data)


def test_unverified_source_rejected_and_never_authenticates_input() -> None:
    data = _statement()
    data["source_kind"] = "provider_verified"
    with pytest.raises(FinOpsError, match="invoice_source_not_verified"):
        parse_synthetic_invoice_statement(data)


@pytest.mark.parametrize("bad", [
    Decimal("-0.01"), Decimal("NaN"), Decimal("Infinity"),
])
def test_invalid_tolerance_refused(bad: Decimal) -> None:
    with pytest.raises(FinOpsError, match="invalid_reconciliation_tolerance"):
        _reconcile(tolerance=bad)


def test_invalid_request_id_and_invalid_reconciliation_types_refused() -> None:
    with pytest.raises(FinOpsError, match="invalid_expected_provider_request_id"):
        reconcile_synthetic_statement(
            _quote(), parse_synthetic_invoice_statement(_statement()),
            expected_provider_request_id="x y",
        )
    with pytest.raises(FinOpsError, match="invalid_reconciliation_input"):
        reconcile_synthetic_statement(
            None, parse_synthetic_invoice_statement(_statement()),  # type: ignore[arg-type]
            expected_provider_request_id="fake-call-001",
        )


def test_malformed_json_duplicate_keys_constants_and_limits() -> None:
    data = json.dumps(_statement())
    with pytest.raises(FinOpsError, match="duplicate_invoice_json_key"):
        parse_synthetic_invoice_statement_json(data.replace(
            '"statement_id": "sample-001"', '"statement_id": "sample-001", "statement_id": "fake"',
        ))
    with pytest.raises(FinOpsError, match="invalid_invoice_json_constant"):
        parse_synthetic_invoice_statement_json(data.replace(
            '"amount": "0.051"', '"amount": NaN',
        ))
    with pytest.raises(FinOpsError, match="invoice_statement_too_large"):
        parse_synthetic_invoice_statement_json(" " * 1_000_001)
    with pytest.raises(FinOpsError, match="invalid_invoice_json"):
        parse_synthetic_invoice_statement_json("{")
    with pytest.raises(FinOpsError, match="invalid_invoice_json_content"):
        parse_synthetic_invoice_statement_json(123)  # type: ignore[arg-type]


def test_too_many_invoice_lines_rejected() -> None:
    data = _statement()
    data["lines"] = [
        {
            "line_id": f"line-{i}", "provider_request_id": "fake-call-001",
            "kind": "usage", "amount": "0",
        }
        for i in range(2001)
    ]
    with pytest.raises(FinOpsError, match="invalid_invoice_lines"):
        parse_synthetic_invoice_statement(data)


def test_synthetic_statement_and_line_are_immutable_domain_objects() -> None:
    statement = parse_synthetic_invoice_statement(_statement())
    assert isinstance(statement, SyntheticInvoiceStatement)
    assert all(isinstance(line, SyntheticInvoiceLine) for line in statement.lines)
    assert statement.lines[0].kind is InvoiceLineKind.USAGE
    with pytest.raises(FinOpsError, match="invoice_currency_mismatch"):
        replace(statement, currency="EUR")


def test_cli_reports_synthetic_match_and_preserves_budget_db(tmp_path: Path) -> None:
    runner = CliRunner()
    scenario = tmp_path / "scenario.json"
    prices = tmp_path / "prices.json"
    invoice = tmp_path / "invoice.json"
    scenario.write_text(json.dumps(_scenario()), encoding="utf-8")
    prices.write_text(json.dumps(_prices()), encoding="utf-8")
    invoice.write_text(json.dumps(_statement()), encoding="utf-8")
    cmd = [
        "finops", "reconcile", "--request", str(scenario),
        "--pricing-catalog", str(prices), "--statement", str(invoice),
        "--provider-request-id", "fake-call-001",
    ]
    result = runner.invoke(app, cmd)
    assert result.exit_code == 0, result.output
    report = json.loads(result.output)
    assert report["status"] == "matched_synthetic"
    assert report["net_amount"] == "0.056"
    assert report["provider_invoice_verified"] is False
    assert report["budget_ledger_mutated"] is False
    assert not (tmp_path / "finops-sandbox.db").exists()
    assert json.loads(runner.invoke(app, cmd).output) == report


def test_cli_variance_and_unmatched_return_exit_3(tmp_path: Path) -> None:
    runner = CliRunner()
    scenario, prices, invoice = (tmp_path / x for x in ("scenario.json", "prices.json", "invoice.json"))
    scenario.write_text(json.dumps(_scenario()), encoding="utf-8")
    prices.write_text(json.dumps(_prices()), encoding="utf-8")
    data = _statement()
    data["lines"][0]["amount"] = "0.060"
    invoice.write_text(json.dumps(data), encoding="utf-8")
    args = ["finops", "reconcile", "--request", str(scenario), "--pricing-catalog", str(prices),
            "--statement", str(invoice)]
    variance = runner.invoke(app, [*args, "--provider-request-id", "fake-call-001"])
    assert variance.exit_code == 3, variance.output
    assert json.loads(variance.output)["status"] == "variance_synthetic"
    missing = runner.invoke(app, [*args, "--provider-request-id", "missing"])
    assert missing.exit_code == 3, missing.output
    assert json.loads(missing.output)["status"] == "unmatched"


def test_cli_missing_invoice_and_invalid_tolerance_fail_closed(tmp_path: Path) -> None:
    runner = CliRunner()
    missing = runner.invoke(app, [
        "finops", "reconcile", "--request", str(tmp_path / "missing.json"),
        "--statement", str(tmp_path / "absent.json"), "--provider-request-id", "p",
    ])
    assert missing.exit_code == 2
    assert json.loads(missing.output)["live_authorized"] is False
    scenario = tmp_path / "scenario.json"
    invoice = tmp_path / "invoice.json"
    scenario.write_text(json.dumps(_scenario()), encoding="utf-8")
    invoice.write_text(json.dumps(_statement()), encoding="utf-8")
    invalid = runner.invoke(app, [
        "finops", "reconcile", "--request", str(scenario),
        "--statement", str(invoice), "--provider-request-id", "p",
        "--tolerance", "NaN",
    ])
    assert invalid.exit_code == 3
    assert json.loads(invalid.output)["reason"] == "invalid_reconciliation_tolerance"
