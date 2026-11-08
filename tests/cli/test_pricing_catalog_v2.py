"""M2-G1: strict pricing catalogue tests, entirely offline and synthetic."""

from __future__ import annotations

import copy
import json
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, cast

import pytest

from pyllmkit.adapters.cli.media_catalog_v2 import load_media_catalog
from pyllmkit.adapters.cli.pricing_catalog_v2 import (
    CATALOG_PATH,
    VersionedPriceCatalog,
    load_price_catalog,
    merge_price_catalog,
    parse_price_catalog,
    parse_price_catalog_json,
    price_catalog_to_dict,
    resolve_media_price,
)
from pyllmkit.domain.finops import FinOpsError, MeteredQuantity, estimate_cost

AT = datetime(2026, 11, 8, 12, 0, tzinfo=UTC)


def _price(
    *, price_id: str = "synthetic-image-v1",
    revision: str = "r1",
    valid_from: str = "2026-11-01T00:00:00+00:00",
    valid_to: str | None = "2026-12-01T00:00:00+00:00",
    model_id: str = "gpt-image-2",
) -> dict[str, Any]:
    return {
        "price_id": price_id,
        "revision": revision,
        "model_id": model_id,
        "api_provider": "openai",
        "billing_provider": "openai",
        "deployment_channel": "direct",
        "currency": "USD",
        "valid_from": valid_from,
        "valid_to": valid_to,
        "verified_at": "2026-11-08",
        "source_url": "https://example.org/synthetic-pricing-only",
        "rates": [
            {"meter": "image", "amount": "0.025", "per": "1", "dimensions": {"quality": "high"}},
            {"meter": "output_token", "amount": "4.00", "per": "1000000", "dimensions": {}},
        ],
    }


def _payload(prices: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    return {
        "schema_version": 2,
        "revision": "m2-g1-test.1",
        "updated_at": "2026-11-08",
        "prices": [] if prices is None else prices,
    }


def test_packaged_catalog_is_empty_and_has_no_invented_vendor_prices() -> None:
    catalog = load_price_catalog()
    assert CATALOG_PATH.is_file()
    assert isinstance(catalog, VersionedPriceCatalog)
    assert catalog.schema_version == 2
    assert catalog.prices == ()
    assert catalog.as_domain_catalog().resolve(
        model_id="gpt-image-2", api_provider="openai",
        billing_provider="openai", deployment_channel="direct", at=AT,
    ) is None


def test_price_catalog_decimal_round_trip_preserves_exact_rates() -> None:
    payload = _payload([_price()])
    catalog = parse_price_catalog_json(json.dumps(payload))
    assert price_catalog_to_dict(catalog) == payload
    assert parse_price_catalog(price_catalog_to_dict(catalog)) == catalog
    assert catalog.prices[0].rates[0].amount == Decimal("0.025")
    assert catalog.prices[0].rates[1].per == Decimal("1000000")
    result = estimate_cost(
        catalog.prices[0],
        (MeteredQuantity("image", Decimal("2"), (("quality", "high"),)),),
        at=AT,
    )
    assert result.amount is not None
    assert result.amount.amount == Decimal("0.050")


def test_price_history_can_switch_on_exclusive_boundary() -> None:
    first = _price(valid_to="2026-11-08T00:00:00+00:00")
    second = _price(
        price_id="synthetic-image-v2", revision="r2",
        valid_from="2026-11-08T00:00:00+00:00", valid_to=None,
    )
    catalog = parse_price_catalog(_payload([first, second]))
    domain = catalog.as_domain_catalog()
    assert domain.resolve(
        model_id="gpt-image-2", api_provider="openai", billing_provider="openai",
        deployment_channel="direct", at=datetime(2026, 11, 7, tzinfo=UTC),
    ).revision == "r1"
    assert domain.resolve(
        model_id="gpt-image-2", api_provider="openai", billing_provider="openai",
        deployment_channel="direct", at=AT,
    ).revision == "r2"


def test_overlapping_versions_fail_even_when_query_time_would_be_unambiguous() -> None:
    old = _price()
    new = _price(
        price_id="synthetic-new", revision="r2",
        valid_from="2026-11-15T00:00:00+00:00",
    )
    with pytest.raises(FinOpsError, match="overlapping_price_intervals"):
        parse_price_catalog(_payload([old, new]))


def test_open_ended_price_cannot_be_followed_by_another_version() -> None:
    first = _price(valid_to=None)
    second = _price(
        price_id="synthetic-new", revision="r2",
        valid_from="2027-01-01T00:00:00+00:00", valid_to=None,
    )
    with pytest.raises(FinOpsError, match="overlapping_price_intervals"):
        parse_price_catalog(_payload([first, second]))


def test_duplicate_revision_rejected_across_all_scopes() -> None:
    second = _price(model_id="another-model")
    with pytest.raises(FinOpsError, match="duplicate_price_revision"):
        parse_price_catalog(_payload([_price(), second]))


def test_source_provenance_is_required_and_url_must_be_https() -> None:
    for bad in ("", "http://example.org", "sample", None):
        candidate = _price()
        candidate["source_url"] = bad
        with pytest.raises(FinOpsError):
            parse_price_catalog(_payload([candidate]))


def test_unknown_json_fields_are_rejected_at_every_level() -> None:
    for level in ("envelope", "price", "rate"):
        payload = _payload([_price()])
        if level == "envelope":
            payload["unknown"] = False
        elif level == "price":
            payload["prices"][0]["approved_for_live"] = True
        else:
            payload["prices"][0]["rates"][0]["discount"] = "0"
        with pytest.raises(FinOpsError):
            parse_price_catalog(payload)


@pytest.mark.parametrize(
    "bad", ["NaN", "Infinity", "-Infinity", "-1", "1e-3", "+1", "01", ".2", "1_000", 3, True, None],
)
def test_invalid_decimal_string_rejected(bad: Any) -> None:
    payload = _payload([_price()])
    payload["prices"][0]["rates"][0]["amount"] = bad
    with pytest.raises(FinOpsError):
        parse_price_catalog(payload)


@pytest.mark.parametrize("bad", ["0", "0.00", "NaN", "1.0e3", False, 1])
def test_invalid_denominator_rejected(bad: Any) -> None:
    payload = _payload([_price()])
    payload["prices"][0]["rates"][0]["per"] = bad
    with pytest.raises(FinOpsError):
        parse_price_catalog(payload)


def test_noncanonical_dimensions_are_normalized_by_key_order() -> None:
    payload = _payload([_price()])
    payload["prices"][0]["rates"][0]["dimensions"] = {
        "resolution": "1024", "quality": "high",
    }
    catalog = parse_price_catalog(payload)
    assert catalog.prices[0].rates[0].dimensions == (
        ("quality", "high"), ("resolution", "1024"),
    )


def test_duplicate_rate_meter_and_dimensions_rejected() -> None:
    payload = _payload([_price()])
    payload["prices"][0]["rates"].append(copy.deepcopy(payload["prices"][0]["rates"][0]))
    with pytest.raises(FinOpsError, match="duplicate_rate"):
        parse_price_catalog(payload)


@pytest.mark.parametrize(
    "value", ["2026-11-08", "2026-11-08T00:00:00", "2026-99-01T00:00:00Z", False],
)
def test_price_timestamp_requires_valid_explicit_timezone(value: Any) -> None:
    payload = _payload([_price()])
    payload["prices"][0]["valid_from"] = value
    with pytest.raises(FinOpsError, match="invalid_valid_from"):
        parse_price_catalog(payload)


def test_subsecond_timestamps_survive_json_roundtrip() -> None:
    stamp = "2026-11-01T00:00:00.123456+00:00"
    payload = _payload([_price(valid_from=stamp)])
    first = parse_price_catalog(payload)
    assert price_catalog_to_dict(first)["prices"][0]["valid_from"] == stamp
    assert parse_price_catalog(price_catalog_to_dict(first)) == first


@pytest.mark.parametrize("value", [True, 1, "2", 3])
def test_schema_version_must_be_exact_integer_two(value: Any) -> None:
    payload = _payload()
    payload["schema_version"] = value
    with pytest.raises(FinOpsError, match="unsupported_price_catalog_schema"):
        parse_price_catalog(payload)


@pytest.mark.parametrize(
    "raw", [
        '{"schema_version":2,"schema_version":2,"revision":"x","updated_at":"2026-11-08","prices":[]}',
        '{"schema_version":2,"revision":"x","updated_at":"2026-11-08","prices":[{"foo":1,"foo":2}]}',
        '{"schema_version":2,"revision":"x","updated_at":"2026-11-08","prices":NaN}',
        '{"schema_version":2,"revision":"x","updated_at":"2026-11-08","prices":[}',
    ],
)
def test_json_invalid_or_duplicated_keys_never_silently_accepted(raw: str) -> None:
    with pytest.raises(FinOpsError):
        parse_price_catalog_json(raw)


def test_file_loader_is_bounded_and_explicit(tmp_path: Path) -> None:
    path = tmp_path / "prices.json"
    path.write_text(json.dumps(_payload([_price()])), encoding="utf-8")
    catalog = load_price_catalog(path)
    assert len(catalog.prices) == 1
    path.write_bytes(b" " * 1_000_001)
    with pytest.raises(FinOpsError, match="price_catalog_too_large"):
        load_price_catalog(path)


def test_no_implicit_local_catalog_override(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "pricing_catalog_v2.json").write_text(
        json.dumps(_payload([_price()])), encoding="utf-8",
    )
    assert load_price_catalog().prices == ()


def test_merge_can_append_successor_without_replacing_history() -> None:
    old = parse_price_catalog(_payload([_price(valid_to="2026-11-08T00:00:00+00:00")]))
    new = parse_price_catalog(_payload([
        _price(
            price_id="synthetic-image-v2", revision="r2",
            valid_from="2026-11-08T00:00:00+00:00", valid_to=None,
        ),
    ]))
    merged = merge_price_catalog(old, new)
    assert len(merged.prices) == 2
    assert merged.prices[0] == old.prices[0]
    assert merged.prices[1] == new.prices[0]
    assert len(merge_price_catalog(merged, new).prices) == 2


def test_merge_rejects_mutation_of_existing_revision() -> None:
    old = parse_price_catalog(_payload([_price()]))
    modified = _price()
    modified["rates"][0]["amount"] = "100.00"
    extension = parse_price_catalog(_payload([modified]))
    with pytest.raises(FinOpsError, match="immutable_price_revision_conflict"):
        merge_price_catalog(old, extension)


def test_merge_rejects_conflicting_new_version_with_overlapping_dates() -> None:
    old = parse_price_catalog(_payload([_price()]))
    new = parse_price_catalog(_payload([
        _price(price_id="other-id", revision="r2", valid_from="2026-11-15T00:00:00Z"),
    ]))
    with pytest.raises(FinOpsError, match="overlapping_price_intervals"):
        merge_price_catalog(old, new)


def test_m1_route_explicit_provider_and_billing_identity_is_required() -> None:
    media = load_media_catalog()
    pricing = parse_price_catalog(_payload([_price()]))
    correct = resolve_media_price(
        pricing, media, identifier="gpt-image-2", api_provider="openai", at=AT,
    )
    assert correct == pricing.prices[0]
    with pytest.raises(FinOpsError, match="unknown_media_route"):
        resolve_media_price(pricing, media, identifier="gpt-image-2", api_provider="google", at=AT)
    with pytest.raises(FinOpsError, match="api_provider_required"):
        resolve_media_price(pricing, media, identifier="gpt-image-2", api_provider="", at=AT)


def test_m1_retired_model_is_never_priceable_even_with_a_fabricated_tariff() -> None:
    media = load_media_catalog()
    pricing = parse_price_catalog(_payload([_price(model_id="dall-e-3")]))
    with pytest.raises(FinOpsError, match="model_lifecycle_not_priceable"):
        resolve_media_price(pricing, media, identifier="dall-e-3", api_provider="openai", at=AT)


def test_resolver_does_not_infer_price_when_billing_provider_differs() -> None:
    media = load_media_catalog()
    modified = _price()
    modified["billing_provider"] = "reseller"
    pricing = parse_price_catalog(_payload([modified]))
    assert resolve_media_price(
        pricing, media, identifier="gpt-image-2", api_provider="openai", at=AT,
    ) is None


def test_resolver_requires_timezone_aware_instant() -> None:
    media = load_media_catalog()
    pricing = parse_price_catalog(_payload([_price()]))
    with pytest.raises(FinOpsError, match="invalid_pricing_time"):
        resolve_media_price(
            pricing, media, identifier="gpt-image-2",
            api_provider="openai", at=datetime(2026, 11, 8),
        )


def test_legacy_float_pricing_is_not_imported_as_v2_rate() -> None:
    legacy = _payload([_price()])
    legacy["prices"][0]["rates"][0]["amount"] = 0.025
    with pytest.raises(FinOpsError, match="invalid_rate_amount"):
        parse_price_catalog(cast(object, legacy))
