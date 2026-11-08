"""Pure, strictly declarative pre-generation quotes (FinOps M2-G2).

Pricing a declared scenario is not proof that the provider bills no other
components, that quantities are remotely bounded, or that a budget is reserved.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from pyllmkit.domain.finops import (
    Dimensions,
    FinOpsError,
    MeteredQuantity,
    Money,
    PriceVersion,
)

_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,191}$")


def _id(value: str, label: str) -> None:
    if type(value) is not str or _IDENTIFIER.fullmatch(value) is None:
        raise FinOpsError(f"invalid_{label}")


def _instant(value: datetime) -> None:
    if type(value) is not datetime or value.tzinfo is None or value.utcoffset() is None:
        raise FinOpsError("invalid_quote_time")


@dataclass(frozen=True, slots=True)
class QuoteComponent:
    """A declared billable meter; None means the maximum is unknown, not zero."""

    meter: str
    maximum: Decimal | None
    dimensions: Dimensions = ()

    def __post_init__(self) -> None:
        MeteredQuantity(
            self.meter,
            Decimal("0") if self.maximum is None else self.maximum,
            self.dimensions,
        )


@dataclass(frozen=True, slots=True)
class QuoteScenario:
    """Offline SDK input. Every monetary component is supplied by the caller."""

    model_id: str
    api_provider: str
    task: str
    at: datetime
    components: tuple[QuoteComponent, ...]
    parameters: Dimensions = ()

    def __post_init__(self) -> None:
        for name in ("model_id", "api_provider", "task"):
            _id(getattr(self, name), name)
        _instant(self.at)
        if type(self.components) is not tuple or not self.components:
            raise FinOpsError("missing_quote_components")
        MeteredQuantity("parameter_validation", Decimal("0"), self.parameters)
        keys: set[tuple[str, Dimensions]] = set()
        given_parameters = dict(self.parameters)
        for component in self.components:
            if type(component) is not QuoteComponent:
                raise FinOpsError("invalid_quote_component")
            key = (component.meter, component.dimensions)
            if key in keys:
                raise FinOpsError("duplicate_quote_component")
            keys.add(key)
            for dimension, selection in component.dimensions:
                if given_parameters.get(dimension) != selection:
                    raise FinOpsError("quote_dimension_not_selected")


@dataclass(frozen=True, slots=True)
class QuoteLine:
    meter: str
    dimensions: Dimensions
    maximum: Decimal
    rate: Decimal
    per: Decimal
    subtotal: Decimal


@dataclass(frozen=True, slots=True)
class PreflightQuote:
    """No quote object from G2 authorizes spending or serves as a hard cap."""

    status: str
    reason: str
    model_id: str
    api_provider: str
    billing_provider: str
    deployment_channel: str
    task: str
    at: datetime
    catalog_revision: str
    price_id: str | None
    price_revision: str | None
    source_url: str | None
    valid_until: datetime | None
    amount: Money | None
    lines: tuple[QuoteLine, ...]
    missing_rates: tuple[str, ...]
    missing_bounds: tuple[str, ...]
    coverage: str = "declared_components_only"
    live_authorized: bool = False

    @property
    def scenario_priced(self) -> bool:
        return self.status == "priced_scenario" and self.amount is not None


def quote_scenario(
    scenario: QuoteScenario,
    *,
    price: PriceVersion | None,
    billing_provider: str,
    deployment_channel: str,
    catalog_revision: str,
) -> PreflightQuote:
    """Price all declared components or return *no total*; never authorize live.

    The caller must supply the real billing route (M1) and validate its task.
    Even a fully priced scenario is insufficient for a G3 reservation because
    an independent, trusted billing-meter plan is not yet certified.
    """
    if type(scenario) is not QuoteScenario:
        raise FinOpsError("invalid_quote_scenario")
    for label, value in (
        ("billing_provider", billing_provider),
        ("deployment_channel", deployment_channel),
        ("catalog_revision", catalog_revision),
    ):
        _id(value, label)
    missing_bounds = tuple(sorted(
        c.meter for c in scenario.components if c.maximum is None
    ))
    if price is None:
        return PreflightQuote(
            "unknown", "missing_tariff",
            scenario.model_id, scenario.api_provider, billing_provider,
            deployment_channel, scenario.task, scenario.at, catalog_revision,
            None, None, None, None, None, (), (), missing_bounds,
        )
    if type(price) is not PriceVersion:
        raise FinOpsError("invalid_quote_price")
    if (
        price.model_id != scenario.model_id
        or price.api_provider != scenario.api_provider
        or price.billing_provider != billing_provider
        or price.deployment_channel != deployment_channel
    ):
        raise FinOpsError("quote_price_scope_mismatch")
    if not price.applicable(scenario.at):
        raise FinOpsError("quote_stale_price")
    tariffs = {(r.meter, r.dimensions): r for r in price.rates}
    missing_rates: list[str] = []
    lines: list[QuoteLine] = []
    total = Decimal("0")
    for component in scenario.components:
        rate = tariffs.get((component.meter, component.dimensions))
        if rate is None:
            missing_rates.append(component.meter)
        if rate is None or component.maximum is None:
            continue
        subtotal = component.maximum * rate.amount / rate.per
        total += subtotal
        lines.append(QuoteLine(
            component.meter, component.dimensions, component.maximum,
            rate.amount, rate.per, subtotal,
        ))
    if missing_rates:
        status, reason = "incomplete", "missing_meter_rate"
    elif missing_bounds:
        status, reason = "incomplete", "missing_quantity_bound"
    else:
        status, reason = "priced_scenario", "declared_components_priced_only"
    return PreflightQuote(
        status, reason, scenario.model_id, scenario.api_provider,
        billing_provider, deployment_channel, scenario.task, scenario.at,
        catalog_revision, price.price_id, price.revision,
        price.source_url, price.valid_to,
        Money(total, price.currency) if status == "priced_scenario" else None,
        tuple(lines), tuple(sorted(missing_rates)), missing_bounds,
    )


def quote_to_dict(quote: PreflightQuote) -> dict[str, object]:
    """Stable JSON-safe SDK/CLI projection, monetary quantities as strings."""
    if type(quote) is not PreflightQuote:
        raise FinOpsError("invalid_preflight_quote")
    return {
        "status": quote.status,
        "reason": quote.reason,
        "model_id": quote.model_id,
        "api_provider": quote.api_provider,
        "billing_provider": quote.billing_provider,
        "deployment_channel": quote.deployment_channel,
        "task": quote.task,
        "at": quote.at.isoformat(),
        "catalog_revision": quote.catalog_revision,
        "price_id": quote.price_id,
        "price_revision": quote.price_revision,
        "source_url": quote.source_url,
        "valid_until": quote.valid_until.isoformat() if quote.valid_until else None,
        "amount": (
            {"value": str(quote.amount.amount), "currency": quote.amount.currency}
            if quote.amount is not None else None
        ),
        "lines": [
            {
                "meter": line.meter,
                "dimensions": dict(line.dimensions),
                "maximum": str(line.maximum),
                "rate": str(line.rate),
                "per": str(line.per),
                "subtotal": str(line.subtotal),
            }
            for line in quote.lines
        ],
        "missing_rates": list(quote.missing_rates),
        "missing_bounds": list(quote.missing_bounds),
        "coverage": quote.coverage,
        "live_authorized": False,
        "provider_quote_verified": False,
        "atomic_budget_reserved": False,
    }
