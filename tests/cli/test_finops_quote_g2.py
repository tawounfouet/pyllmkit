"""M2-G2: offline preflight quote contracts, SDK and CLI - synthetic prices only."""

from __future__ import annotations

import copy
import json
from dataclasses import replace
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from pyllmkit.adapters.cli.finops_quote import (
    load_quote_request,
    parse_quote_request,
    parse_quote_request_json,
    quote_media_scenario,
)
from pyllmkit.adapters.cli.main import app
from pyllmkit.adapters.cli.media_catalog_v2 import load_media_catalog
from pyllmkit.adapters.cli.pricing_catalog_v2 import (
    load_price_catalog,
    parse_price_catalog,
)
from pyllmkit.domain.finops import FinOpsError
from pyllmkit.domain.finops.quoting import (
    quote_scenario,
    quote_to_dict,
)

AT = datetime(2026, 11, 8, 12, tzinfo=UTC)


def _tariff(*, valid_to: str | None = None) -> dict[str, Any]:
    return {
        "price_id": "synthetic-image-v1",
        "revision": "r1",
        "model_id": "gpt-image-2",
        "api_provider": "openai",
        "billing_provider": "openai",
        "deployment_channel": "direct",
        "currency": "USD",
        "valid_from": "2026-11-01T00:00:00+00:00",
        "valid_to": valid_to,
        "verified_at": "2026-11-08",
        "source_url": "https://example.org/fictional-only",
        "rates": [
            {"meter": "image", "amount": "0.025", "per": "1", "dimensions": {"quality": "high"}},
            {"meter": "input_token", "amount": "1", "per": "1000000", "dimensions": {}},
            {"meter": "output_token", "amount": "4", "per": "1000000", "dimensions": {}},
        ],
    }


def _catalog(*, valid_to: str | None = None) -> dict[str, Any]:
    return {
        "schema_version": 2,
        "revision": "m2-g2-test.1",
        "updated_at": "2026-11-08",
        "prices": [_tariff(valid_to=valid_to)],
    }


def _request(
    components: list[dict[str, Any]] | None = None, *,
    task: str = "text_to_image",
    params: dict[str, str] | None = None,
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "model_id": "gpt-image-2",
        "api_provider": "openai",
        "task": task,
        "at": AT.isoformat(),
        "parameters": {"quality": "high"} if params is None else params,
        "components": components if components is not None else [
            {"meter": "image", "maximum": "2", "dimensions": {"quality": "high"}},
            {"meter": "input_token", "maximum": "1000", "dimensions": {}},
        ],
    }


def _quote(
    request: dict[str, Any] | None = None, *,
    catalog: dict[str, Any] | None = None,
):
    scenario = parse_quote_request(_request() if request is None else request)
    prices = parse_price_catalog(_catalog() if catalog is None else catalog)
    return quote_media_scenario(scenario, prices=prices, media=load_media_catalog())


def test_sdk_returns_exact_decimal_composite_priced_scenario() -> None:
    quote = _quote()
    assert quote.status == "priced_scenario"
    assert quote.reason == "declared_components_priced_only"
    assert quote.scenario_priced
    assert quote.amount is not None
    assert quote.amount.amount == Decimal("0.051")
    assert quote.amount.currency == "USD"
    assert quote.source_url == "https://example.org/fictional-only"
    assert quote.price_revision == "r1"
    assert quote.catalog_revision == "m2-g2-test.1"
    assert quote.coverage == "declared_components_only"
    assert not quote.live_authorized
    assert sum((line.subtotal for line in quote.lines), Decimal(0)) == quote.amount.amount
    payload = quote_to_dict(quote)
    assert payload["amount"] == {"value": "0.051", "currency": "USD"}
    assert payload["live_authorized"] is False
    assert payload["provider_quote_verified"] is False
    assert payload["atomic_budget_reserved"] is False


def test_packed_catalog_without_vendor_prices_yields_unknown_not_free() -> None:
    scenario = parse_quote_request(_request())
    quote = quote_media_scenario(
        scenario, prices=load_price_catalog(), media=load_media_catalog(),
    )
    assert quote.status == "unknown"
    assert quote.reason == "missing_tariff"
    assert quote.amount is None
    assert not quote.scenario_priced
    assert quote_to_dict(quote)["amount"] is None


def test_missing_declared_token_rate_prevents_partial_total() -> None:
    catalog = _catalog()
    catalog["prices"][0]["rates"] = catalog["prices"][0]["rates"][:1]
    quote = _quote(catalog=catalog)
    assert quote.status == "incomplete"
    assert quote.reason == "missing_meter_rate"
    assert quote.amount is None
    assert quote.missing_rates == ("input_token",)
    assert len(quote.lines) == 1
    assert quote_to_dict(quote)["amount"] is None


def test_unknown_maximum_is_never_assumed_to_be_zero() -> None:
    request = _request()
    request["components"][1]["maximum"] = None
    quote = _quote(request)
    assert quote.status == "incomplete"
    assert quote.reason == "missing_quantity_bound"
    assert quote.missing_bounds == ("input_token",)
    assert quote.amount is None


def test_known_explicit_zero_can_be_priced_without_claiming_free_model() -> None:
    req = _request(components=[
        {"meter": "image", "maximum": "0", "dimensions": {"quality": "high"}},
    ])
    quote = _quote(req)
    assert quote.amount is not None
    assert quote.amount.amount == Decimal(0)
    assert quote.coverage == "declared_components_only"
    assert not quote.live_authorized


def test_extra_vendor_meter_is_not_charged_silently_or_claimed_complete() -> None:
    req = _request(components=[
        {"meter": "image", "maximum": "1", "dimensions": {"quality": "high"}},
    ])
    quote = _quote(req)
    assert quote.scenario_priced
    assert len(quote.lines) == 1
    assert quote.coverage == "declared_components_only"
    assert not quote.live_authorized


def test_multidimensional_video_and_audio_rates_can_be_compounded_purely() -> None:
    req = _request(
        task="text_to_video",
        params={"resolution": "720p", "audio_mode": "enabled"},
        components=[
            {"meter": "video_second", "maximum": "12", "dimensions": {"resolution": "720p"}},
            {"meter": "audio_second", "maximum": "12", "dimensions": {"audio_mode": "enabled"}},
        ],
    )
    req["model_id"] = "grok-imagine-video"
    req["api_provider"] = "xai"
    cat = _catalog()
    price = cat["prices"][0]
    price["model_id"] = "grok-imagine-video"
    price["api_provider"] = "xai"
    price["billing_provider"] = "xai"
    price["rates"] = [
        {"meter": "video_second", "amount": "0.08", "per": "1", "dimensions": {"resolution": "720p"}},
        {"meter": "audio_second", "amount": "0.01", "per": "1", "dimensions": {"audio_mode": "enabled"}},
    ]
    quote = _quote(req, catalog=cat)
    assert quote.scenario_priced
    assert quote.amount is not None
    assert quote.amount.amount == Decimal("1.08")
    assert [line.meter for line in quote.lines] == ["video_second", "audio_second"]


def test_task_mismatch_is_rejected_before_attempting_price() -> None:
    with pytest.raises(FinOpsError, match="quote_task_not_supported"):
        _quote(_request(task="text_to_video"))


def test_retired_media_route_is_rejected_even_if_tariff_exists() -> None:
    req = _request()
    req["model_id"] = "dall-e-3"
    cat = _catalog()
    cat["prices"][0]["model_id"] = "dall-e-3"
    with pytest.raises(FinOpsError, match="model_lifecycle_not_priceable"):
        _quote(req, catalog=cat)


def test_exact_api_provider_and_biller_scope_are_required() -> None:
    req = _request()
    req["api_provider"] = "google"
    with pytest.raises(FinOpsError, match="unknown_media_route"):
        _quote(req)
    cat = _catalog()
    cat["prices"][0]["billing_provider"] = "reseller"
    assert _quote(catalog=cat).reason == "missing_tariff"


def test_quote_scope_mismatch_refused_by_pure_service() -> None:
    scenario = parse_quote_request(_request())
    price = parse_price_catalog(_catalog()).prices[0]
    with pytest.raises(FinOpsError, match="quote_price_scope_mismatch"):
        quote_scenario(
            scenario, price=price, billing_provider="reseller",
            deployment_channel="direct", catalog_revision="r1",
        )


def test_expired_tariff_is_unknown_not_reused_silently() -> None:
    quote = _quote(catalog=_catalog(valid_to="2026-11-08T12:00:00+00:00"))
    assert quote.reason == "missing_tariff"
    assert quote.amount is None


def test_direct_quote_price_rejects_temporally_stale_version() -> None:
    scenario = parse_quote_request(_request())
    price = parse_price_catalog(
        _catalog(valid_to="2026-11-08T12:00:00+00:00")
    ).prices[0]
    with pytest.raises(FinOpsError, match="quote_stale_price"):
        quote_scenario(
            scenario, price=price, billing_provider="openai",
            deployment_channel="direct", catalog_revision="r1",
        )


def test_unselected_pricing_dimension_rejected() -> None:
    req = _request(params={"quality": "medium"})
    with pytest.raises(FinOpsError, match="quote_dimension_not_selected"):
        parse_quote_request(req)


def test_duplicate_quote_components_refused_even_with_equal_amounts() -> None:
    req = _request()
    req["components"].append(copy.deepcopy(req["components"][0]))
    with pytest.raises(FinOpsError, match="duplicate_quote_component"):
        parse_quote_request(req)


@pytest.mark.parametrize("bad", ["-1", "1e3", "1.0e3", "NaN", "Infinity", "01", "", 1, False, True, {}])
def test_quote_maximum_is_a_strict_nonnegative_decimal_string_or_null(bad: Any) -> None:
    req = _request()
    req["components"][0]["maximum"] = bad
    with pytest.raises(FinOpsError, match="invalid_quote_maximum"):
        parse_quote_request(req)


def test_invalid_quote_request_shapes_and_extra_fields_refused() -> None:
    req = _request()
    req["make_paid_request"] = True
    with pytest.raises(FinOpsError, match="invalid_quote_request_fields"):
        parse_quote_request(req)
    req = _request()
    req["components"][0]["billed"] = "yes"
    with pytest.raises(FinOpsError, match="invalid_quote_component_fields"):
        parse_quote_request(req)
    req = _request([])
    with pytest.raises(FinOpsError, match="invalid_quote_components"):
        parse_quote_request(req)


@pytest.mark.parametrize("bad", [False, "1", 0, 2])
def test_quote_request_schema_must_be_exact_one(bad: Any) -> None:
    req = _request()
    req["schema_version"] = bad
    with pytest.raises(FinOpsError, match="unsupported_quote_request_schema"):
        parse_quote_request(req)


@pytest.mark.parametrize("bad", [
    "2026-11-08", "2026-11-08T12:00:00", "2026-99-11T12:00:00Z", True,
])
def test_quote_request_timestamp_must_have_valid_timezone(bad: Any) -> None:
    req = _request()
    req["at"] = bad
    with pytest.raises(FinOpsError, match="invalid_quote_timestamp"):
        parse_quote_request(req)


@pytest.mark.parametrize("value", ["0", "-2", "01", "10.5", "abc", "00001"])
def test_invalid_numeric_media_options_refused(value: str) -> None:
    req = _request(params={"quality": "high", "max_outputs": value})
    with pytest.raises(FinOpsError, match="invalid_quote_max_outputs"):
        _quote(req)


def test_m1_known_capability_constraints_checked_without_faking_unknown() -> None:
    media = load_media_catalog()
    selected = media.find("gpt-image-2", provider="openai")
    assert selected is not None
    caps = replace(selected.capabilities, resolutions=("1024x1024",), max_outputs=2)
    models = tuple(
        replace(m, capabilities=caps) if m.public_model_id == "gpt-image-2" else m
        for m in media.models
    )
    guarded = replace(media, models=models)
    prices = parse_price_catalog(_catalog())
    req = _request(params={"quality": "high", "resolution": "2048x2048"})
    with pytest.raises(FinOpsError, match="quote_unsupported_resolution"):
        quote_media_scenario(parse_quote_request(req), prices=prices, media=guarded)
    req = _request(params={"quality": "high", "max_outputs": "3"})
    with pytest.raises(FinOpsError, match="quote_exceeds_declared_max_outputs"):
        quote_media_scenario(parse_quote_request(req), prices=prices, media=guarded)


def test_json_duplicate_keys_at_any_depth_are_rejected() -> None:
    serialized = json.dumps(_request())
    damaged = serialized.replace('"maximum": "2"', '"maximum": "2", "maximum": "2"')
    with pytest.raises(FinOpsError, match="duplicate_quote_json_key"):
        parse_quote_request_json(damaged)


def test_json_nan_or_invalid_syntax_rejected() -> None:
    for raw in ("NaN", "{oops", json.dumps(_request()).replace('"maximum": "2"', '"maximum": NaN')):
        with pytest.raises(FinOpsError):
            parse_quote_request_json(raw)


def test_bounded_request_file_without_local_overrides(tmp_path: Path) -> None:
    path = tmp_path / "request.json"
    path.write_text(json.dumps(_request()), encoding="utf-8")
    assert load_quote_request(path) == parse_quote_request(_request())
    path.write_bytes(b" " * 65_537)
    with pytest.raises(FinOpsError, match="quote_request_too_large"):
        load_quote_request(path)


def test_cli_quote_unknown_is_json_and_nonzero_without_credentials(tmp_path: Path) -> None:
    request = tmp_path / "quote.json"
    request.write_text(json.dumps(_request()), encoding="utf-8")
    result = CliRunner().invoke(app, ["finops", "quote", "--request", str(request)])
    assert result.exit_code == 3, result.output
    value = json.loads(result.output)
    assert value["status"] == "unknown"
    assert value["reason"] == "missing_tariff"
    assert value["amount"] is None
    assert value["live_authorized"] is False


def test_cli_quote_synthetic_is_json_and_has_no_live_authority(tmp_path: Path) -> None:
    request = tmp_path / "scenario.json"
    pricing = tmp_path / "synthetic-prices.json"
    request.write_text(json.dumps(_request()), encoding="utf-8")
    pricing.write_text(json.dumps(_catalog()), encoding="utf-8")
    result = CliRunner().invoke(app, [
        "finops", "quote", "--request", str(request),
        "--pricing-catalog", str(pricing),
    ])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["status"] == "priced_scenario"
    assert payload["amount"] == {"value": "0.051", "currency": "USD"}
    assert payload["live_authorized"] is False
    assert payload["atomic_budget_reserved"] is False


def test_cli_rejects_malformed_request_before_loading_price(tmp_path: Path) -> None:
    path = tmp_path / "invalid.json"
    path.write_text('{"schema_version":1}', encoding="utf-8")
    result = CliRunner().invoke(app, ["finops", "quote", "--request", str(path)])
    assert result.exit_code == 2
    payload = json.loads(result.output)
    assert payload["status"] == "error"
    assert payload["live_authorized"] is False


def test_cli_incomplete_quote_exit_three_not_a_false_success(tmp_path: Path) -> None:
    request = tmp_path / "scenario.json"
    pricing = tmp_path / "synthetic-prices.json"
    raw = _request()
    raw["components"][1]["maximum"] = None
    request.write_text(json.dumps(raw), encoding="utf-8")
    pricing.write_text(json.dumps(_catalog()), encoding="utf-8")
    result = CliRunner().invoke(app, [
        "finops", "quote", "--request", str(request),
        "--pricing-catalog", str(pricing),
    ])
    assert result.exit_code == 3
    assert json.loads(result.output)["reason"] == "missing_quantity_bound"
