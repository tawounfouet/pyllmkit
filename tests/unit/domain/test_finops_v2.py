"""M2 offline FinOps tests: exact Decimal, unknowns, scope and budget gates."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from pyllmkit.domain.finops import (
    BudgetSnapshot,
    FinOpsError,
    InvoiceCharge,
    MeteredQuantity,
    Money,
    PriceCatalog,
    PriceRate,
    PriceVersion,
    assess_budget,
    estimate_cost,
    reconcile_cost,
)

NOW = datetime(2026, 11, 8, tzinfo=UTC)


def _rate_card(*, billing: str = "google", expires: bool = False) -> PriceVersion:
    return PriceVersion(
        price_id="card-001",
        revision="2026-11-08.1",
        model_id="sample-video",
        api_provider="google",
        billing_provider=billing,
        deployment_channel="direct",
        currency="USD",
        valid_from=NOW - timedelta(days=1),
        valid_to=NOW + timedelta(days=1) if expires else None,
        source_url="https://example.com/pricing",
        verified_at=NOW.date(),
        rates=(
            PriceRate(
                "video_second",
                Decimal("0.08"),
                dimensions=(("resolution", "720p"),),
            ),
            PriceRate("image", Decimal("0.12")),
        ),
    )


def _quantities() -> tuple[MeteredQuantity, ...]:
    return (
        MeteredQuantity("video_second", Decimal("6"), (("resolution", "720p"),)),
        MeteredQuantity("image", Decimal("2")),
    )


def test_versioned_multimodal_cost_is_exact() -> None:
    result = estimate_cost(_rate_card(), _quantities(), at=NOW)
    assert result.complete
    assert result.amount == Money(Decimal("0.72"), "USD")
    assert result.revision == "2026-11-08.1"
    assert result.source_url == "https://example.com/pricing"


def test_zero_is_valid_only_for_known_zero_quantity() -> None:
    result = estimate_cost(_rate_card(), (MeteredQuantity("image", Decimal("0")),), at=NOW)
    assert result.complete
    assert result.amount == Money(Decimal("0.00"), "USD")


def test_empty_quantities_not_silently_free() -> None:
    result = estimate_cost(_rate_card(), (), at=NOW)
    assert not result.complete
    assert result.amount is None


def test_unknown_dimension_or_meter_is_not_zero() -> None:
    result = estimate_cost(
        _rate_card(),
        (
            MeteredQuantity("video_second", Decimal("6"), (("resolution", "1080p"),)),
            MeteredQuantity("audio_second", Decimal("12")),
        ),
        at=NOW,
    )
    assert not result.complete
    assert result.amount is None
    assert result.missing_meters == ("audio_second", "video_second")


def test_invalid_or_historical_price_refused() -> None:
    card = _rate_card(expires=True)
    with pytest.raises(FinOpsError, match="price_not_applicable"):
        estimate_cost(card, _quantities(), at=NOW + timedelta(days=2))


def test_provider_and_biller_are_distinct_scopes() -> None:
    catalog = PriceCatalog((_rate_card(),))
    assert catalog.resolve(
        model_id="sample-video", api_provider="google",
        billing_provider="google", deployment_channel="direct", at=NOW,
    ) is not None
    assert catalog.resolve(
        model_id="sample-video", api_provider="google",
        billing_provider="aggregator", deployment_channel="direct", at=NOW,
    ) is None


def test_ambiguous_active_price_rejected() -> None:
    catalog = PriceCatalog((_rate_card(), _rate_card()))
    with pytest.raises(FinOpsError, match="ambiguous_price_version"):
        catalog.resolve(
            model_id="sample-video", api_provider="google",
            billing_provider="google", deployment_channel="direct", at=NOW,
        )


def test_price_valid_to_is_exclusive() -> None:
    card = _rate_card(expires=True)
    assert card.applicable(NOW)
    assert not card.applicable(NOW + timedelta(days=1))


def test_duplicate_rate_is_rejected() -> None:
    card = _rate_card()
    with pytest.raises(FinOpsError, match="duplicate_rate"):
        PriceVersion(
            price_id=card.price_id, revision=card.revision, model_id=card.model_id,
            api_provider=card.api_provider, billing_provider=card.billing_provider,
            deployment_channel=card.deployment_channel, currency=card.currency,
            valid_from=card.valid_from, valid_to=card.valid_to,
            source_url=card.source_url, verified_at=card.verified_at,
            rates=(card.rates[0], card.rates[0]),
        )


def test_duplicate_quantity_is_rejected() -> None:
    q = MeteredQuantity("image", Decimal("1"))
    with pytest.raises(FinOpsError, match="duplicate_quantity"):
        estimate_cost(_rate_card(), (q, q), at=NOW)


@pytest.mark.parametrize("invalid", [Decimal("NaN"), Decimal("Infinity"), Decimal("-1")])
def test_invalid_amounts_rejected(invalid: Decimal) -> None:
    with pytest.raises(FinOpsError):
        Money(invalid, "USD")
    with pytest.raises(FinOpsError):
        PriceRate("image", invalid)
    with pytest.raises(FinOpsError):
        MeteredQuantity("image", invalid)


def test_floats_not_allowed_as_money() -> None:
    with pytest.raises(FinOpsError, match="invalid_money_amount"):
        Money(0.5, "USD")  # type: ignore[arg-type]


def test_dimensions_must_be_canonical() -> None:
    with pytest.raises(FinOpsError, match="noncanonical_dimensions"):
        PriceRate("image", Decimal("1"), dimensions=(("region", "eu"), ("quality", "high"), ("region", "us")))


def test_naive_datetime_rejected() -> None:
    with pytest.raises(FinOpsError, match="invalid_pricing_time"):
        _rate_card().applicable(datetime(2026, 11, 8))


def _budget(*, amount: str = "1") -> BudgetSnapshot:
    return BudgetSnapshot(
        Money(Decimal(amount), "USD"),
        Money(Decimal("0.1"), "USD"),
        Money(Decimal("0.1"), "USD"),
    )


def test_budget_does_not_authorize_just_an_estimate() -> None:
    estimate = estimate_cost(_rate_card(), _quantities(), at=NOW)
    decision = assess_budget(estimate, _budget(), enforceable_maximum=False, at=NOW)
    assert not decision.allowed
    assert decision.reason == "unbounded_provider_spend"


def test_budget_can_mark_bounded_quote_eligible_for_reservation() -> None:
    estimate = estimate_cost(_rate_card(), _quantities(), at=NOW)
    decision = assess_budget(estimate, _budget(), enforceable_maximum=True, at=NOW)
    assert decision.allowed
    assert decision.reason == "eligible_for_atomic_reservation"
    assert decision.remaining.amount == Decimal("0.8")


def test_budget_blocks_overspend_and_unknown_cost() -> None:
    known = estimate_cost(_rate_card(), _quantities(), at=NOW)
    assert assess_budget(
        known, _budget(amount="0.5"), enforceable_maximum=True, at=NOW,
    ).reason == "insufficient_budget"
    unknown = estimate_cost(
        _rate_card(), (MeteredQuantity("video_second", Decimal("2")),), at=NOW,
    )
    assert assess_budget(
        unknown, _budget(), enforceable_maximum=True, at=NOW,
    ).reason == "unknown_cost"


def test_budget_snapshot_rejects_overcommitted_amount() -> None:
    with pytest.raises(FinOpsError, match="budget_exceeded_at_snapshot"):
        BudgetSnapshot(Money(Decimal("1"), "USD"), Money(Decimal("1"), "USD"), Money(Decimal("0.1"), "USD"))


def test_reconciliation_tracks_signed_variance() -> None:
    estimate = estimate_cost(_rate_card(), _quantities(), at=NOW)
    billed = InvoiceCharge("inv-1", "google", Money(Decimal("0.75"), "USD"), "req-1")
    delta = reconcile_cost(estimate, billed, expected_provider_request_id="req-1")
    assert delta.status == "variance"
    assert delta.variance == Decimal("0.03")
    assert reconcile_cost(
        estimate, billed, tolerance=Decimal("0.05"), expected_provider_request_id="req-1",
    ).status == "matched"


def test_invoice_is_separate_from_cost_estimate() -> None:
    estimate = estimate_cost(_rate_card(), _quantities(), at=NOW)
    assert reconcile_cost(estimate, None).status == "unmatched"
    billed = InvoiceCharge("inv-2", "aggregator", Money(Decimal("0.72"), "USD"))
    assert reconcile_cost(estimate, billed).status == "indeterminate"


def test_uncorrelated_invoice_never_matches_by_amount_only() -> None:
    estimate = estimate_cost(_rate_card(), _quantities(), at=NOW)
    billed = InvoiceCharge("inv-4", "google", Money(Decimal("0.72"), "USD"), "req-4")
    assert reconcile_cost(estimate, billed).reason == "unverified_billing_correlation"
    assert reconcile_cost(
        estimate, billed, expected_provider_request_id="req-other",
    ).status == "indeterminate"


def test_invalid_budget_enforcement_flag_is_rejected() -> None:
    estimate = estimate_cost(_rate_card(), _quantities(), at=NOW)
    with pytest.raises(FinOpsError, match="invalid_enforceable_maximum"):
        assess_budget(estimate, _budget(), enforceable_maximum="yes", at=NOW)  # type: ignore[arg-type]


def test_unknown_estimate_does_not_reconcile_with_invoice() -> None:
    unknown = estimate_cost(_rate_card(), (), at=NOW)
    billed = InvoiceCharge("inv-3", "google", Money(Decimal("0"), "USD"))
    assert reconcile_cost(unknown, billed).reason == "estimate_missing"
