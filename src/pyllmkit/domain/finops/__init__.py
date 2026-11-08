"""Pure FinOps contracts for versioned prices, estimates, budgets and invoices.

M2 foundation: no provider I/O, credentials, persistence or live authorization.
An estimate is not a supplier quote or a guaranteed maximum spend.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

_IDENTIFIER = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._:/-]{0,191}$")
_CURRENCY = re.compile(r"^[A-Z]{3}$")
Dimensions = tuple[tuple[str, str], ...]


class FinOpsError(ValueError):
    """A deterministic refusal of an invalid or unpriceable FinOps operation."""


def _identifier(value: str, name: str) -> None:
    if type(value) is not str or not _IDENTIFIER.fullmatch(value):
        raise FinOpsError(f"invalid_{name}")


def _nonnegative(value: Decimal, name: str) -> None:
    if type(value) is not Decimal or not value.is_finite() or value < 0:
        raise FinOpsError(f"invalid_{name}")


def _instant(value: datetime, name: str) -> None:
    if type(value) is not datetime or value.tzinfo is None or value.utcoffset() is None:
        raise FinOpsError(f"invalid_{name}")


def _dimensions(value: Dimensions) -> None:
    if type(value) is not tuple:
        raise FinOpsError("invalid_dimensions")
    keys: list[str] = []
    for item in value:
        if type(item) is not tuple or len(item) != 2:
            raise FinOpsError("invalid_dimensions")
        key, val = item
        _identifier(key, "dimension_key")
        _identifier(val, "dimension_value")
        keys.append(key)
    if keys != sorted(set(keys)):
        raise FinOpsError("noncanonical_dimensions")


@dataclass(frozen=True, slots=True)
class Money:
    """Exact currency amount. Zero is meaningful; absence uses None."""

    amount: Decimal
    currency: str

    def __post_init__(self) -> None:
        _nonnegative(self.amount, "money_amount")
        if type(self.currency) is not str or not _CURRENCY.fullmatch(self.currency):
            raise FinOpsError("invalid_currency")


@dataclass(frozen=True, slots=True)
class MeteredQuantity:
    """Known number of billable units, with exact pricing dimensions."""

    meter: str
    amount: Decimal
    dimensions: Dimensions = ()

    def __post_init__(self) -> None:
        _identifier(self.meter, "meter")
        _nonnegative(self.amount, "quantity")
        _dimensions(self.dimensions)


@dataclass(frozen=True, slots=True)
class PriceRate:
    """Exact rate, for example USD 0.08 per video_second at 720p."""

    meter: str
    amount: Decimal
    per: Decimal = Decimal("1")
    dimensions: Dimensions = ()

    def __post_init__(self) -> None:
        _identifier(self.meter, "meter")
        _nonnegative(self.amount, "rate")
        _nonnegative(self.per, "rate_denominator")
        if self.per == 0:
            raise FinOpsError("zero_rate_denominator")
        _dimensions(self.dimensions)


@dataclass(frozen=True, slots=True)
class PriceVersion:
    """Immutable, provenance-bearing price card scoped to the biller and route."""

    price_id: str
    revision: str
    model_id: str
    api_provider: str
    billing_provider: str
    deployment_channel: str
    currency: str
    valid_from: datetime
    valid_to: datetime | None
    source_url: str
    verified_at: date
    rates: tuple[PriceRate, ...]

    def __post_init__(self) -> None:
        for name in (
            "price_id", "revision", "model_id", "api_provider",
            "billing_provider", "deployment_channel",
        ):
            _identifier(getattr(self, name), name)
        if type(self.currency) is not str or not _CURRENCY.fullmatch(self.currency):
            raise FinOpsError("invalid_currency")
        _instant(self.valid_from, "valid_from")
        if self.valid_to is not None:
            _instant(self.valid_to, "valid_to")
            if self.valid_to <= self.valid_from:
                raise FinOpsError("invalid_price_interval")
        if (
            type(self.source_url) is not str
            or not self.source_url.startswith("https://")
            or len(self.source_url) > 2048
        ):
            raise FinOpsError("invalid_price_source")
        if type(self.verified_at) is not date:
            raise FinOpsError("invalid_verified_at")
        if type(self.rates) is not tuple or not self.rates:
            raise FinOpsError("missing_rates")
        keys: set[tuple[str, Dimensions]] = set()
        for rate in self.rates:
            if type(rate) is not PriceRate:
                raise FinOpsError("invalid_rate")
            key = (rate.meter, rate.dimensions)
            if key in keys:
                raise FinOpsError("duplicate_rate")
            keys.add(key)

    def applicable(self, at: datetime) -> bool:
        _instant(at, "pricing_time")
        return self.valid_from <= at and (self.valid_to is None or at < self.valid_to)


@dataclass(frozen=True, slots=True)
class PriceCatalog:
    """Explicitly scoped rates; multiple matching versions are an error."""

    versions: tuple[PriceVersion, ...]

    def resolve(
        self, *, model_id: str, api_provider: str, billing_provider: str,
        deployment_channel: str, at: datetime,
    ) -> PriceVersion | None:
        _instant(at, "pricing_time")
        matches = [
            entry for entry in self.versions
            if entry.model_id == model_id
            and entry.api_provider == api_provider
            and entry.billing_provider == billing_provider
            and entry.deployment_channel == deployment_channel
            and entry.applicable(at)
        ]
        if len(matches) > 1:
            raise FinOpsError("ambiguous_price_version")
        return matches[0] if matches else None


@dataclass(frozen=True, slots=True)
class CostEstimate:
    """Offline calculation, not a bill, authorization or provider guarantee."""

    price_id: str
    revision: str
    api_provider: str
    billing_provider: str
    deployment_channel: str
    at: datetime
    valid_until: datetime | None
    amount: Money | None
    missing_meters: tuple[str, ...]
    source_url: str

    @property
    def complete(self) -> bool:
        return self.amount is not None and not self.missing_meters


def estimate_cost(
    price: PriceVersion, quantities: tuple[MeteredQuantity, ...], *, at: datetime,
) -> CostEstimate:
    """Fail closed on incomplete rates, quantities or inactive price versions."""
    if not price.applicable(at):
        raise FinOpsError("price_not_applicable")
    if type(quantities) is not tuple:
        raise FinOpsError("invalid_quantities")
    known = {(rate.meter, rate.dimensions): rate for rate in price.rates}
    total = Decimal("0")
    missing: list[str] = []
    seen: set[tuple[str, Dimensions]] = set()
    for quantity in quantities:
        if type(quantity) is not MeteredQuantity:
            raise FinOpsError("invalid_quantity")
        key = (quantity.meter, quantity.dimensions)
        if key in seen:
            raise FinOpsError("duplicate_quantity")
        seen.add(key)
        rate = known.get(key)
        if rate is None:
            missing.append(quantity.meter)
        else:
            total += quantity.amount * rate.amount / rate.per
    amount = Money(total, price.currency) if quantities and not missing else None
    return CostEstimate(
        price.price_id, price.revision, price.api_provider,
        price.billing_provider, price.deployment_channel,
        at, price.valid_to, amount, tuple(sorted(missing)), price.source_url,
    )


@dataclass(frozen=True, slots=True)
class BudgetSnapshot:
    """Read-only policy snapshot, not an atomic spending reservation."""

    limit: Money
    spent: Money
    reserved: Money

    def __post_init__(self) -> None:
        if self.limit.currency != self.spent.currency or self.limit.currency != self.reserved.currency:
            raise FinOpsError("budget_currency_mismatch")
        if self.spent.amount + self.reserved.amount > self.limit.amount:
            raise FinOpsError("budget_exceeded_at_snapshot")


@dataclass(frozen=True, slots=True)
class BudgetDecision:
    allowed: bool
    reason: str
    remaining: Money


def assess_budget(
    estimate: CostEstimate, budget: BudgetSnapshot, *,
    enforceable_maximum: bool, at: datetime,
) -> BudgetDecision:
    """Preflight policy only; callers still need atomic reserve and hard remote caps."""
    _instant(at, "authorization_time")
    remaining = Money(
        budget.limit.amount - budget.spent.amount - budget.reserved.amount,
        budget.limit.currency,
    )
    if not estimate.complete:
        return BudgetDecision(False, "unknown_cost", remaining)
    if estimate.amount is None or estimate.amount.currency != budget.limit.currency:
        return BudgetDecision(False, "currency_mismatch", remaining)
    if estimate.valid_until is not None and at >= estimate.valid_until:
        return BudgetDecision(False, "stale_price", remaining)
    if at < estimate.at:
        return BudgetDecision(False, "invalid_authorization_time", remaining)
    if not enforceable_maximum:
        return BudgetDecision(False, "unbounded_provider_spend", remaining)
    if estimate.amount.amount > remaining.amount:
        return BudgetDecision(False, "insufficient_budget", remaining)
    return BudgetDecision(True, "eligible_for_atomic_reservation", remaining)


@dataclass(frozen=True, slots=True)
class InvoiceCharge:
    """Observed supplier charge, never derived from an estimated Usage object."""

    invoice_line_id: str
    billing_provider: str
    amount: Money
    provider_request_id: str | None = None

    def __post_init__(self) -> None:
        _identifier(self.invoice_line_id, "invoice_line_id")
        _identifier(self.billing_provider, "billing_provider")
        if self.provider_request_id is not None:
            _identifier(self.provider_request_id, "provider_request_id")


@dataclass(frozen=True, slots=True)
class CostReconciliation:
    status: str
    variance: Decimal | None
    reason: str


def reconcile_cost(
    estimated: CostEstimate, billed: InvoiceCharge | None, *,
    tolerance: Decimal = Decimal("0"),
) -> CostReconciliation:
    """Compare a priced estimate with a *separately observed* supplier charge."""
    _nonnegative(tolerance, "tolerance")
    if billed is None:
        return CostReconciliation("unmatched", None, "invoice_line_missing")
    if estimated.amount is None or not estimated.complete:
        return CostReconciliation("indeterminate", None, "estimate_missing")
    if (
        billed.billing_provider != estimated.billing_provider
        or billed.amount.currency != estimated.amount.currency
    ):
        return CostReconciliation("indeterminate", None, "billing_scope_mismatch")
    variance = billed.amount.amount - estimated.amount.amount
    if abs(variance) <= tolerance:
        return CostReconciliation("matched", variance, "within_tolerance")
    return CostReconciliation("variance", variance, "outside_tolerance")
