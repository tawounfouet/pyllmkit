"""Pure G4.1 offline comparison of synthetic invoice lines with a G2 quote.

A matching identifier or equal amount in a *caller-supplied synthetic fixture*
never verifies a provider bill or licenses budget mutation or live spending.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

from pyllmkit.domain.finops import FinOpsError, Money
from pyllmkit.domain.finops.quoting import PreflightQuote

_TOKEN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,191}$")


def _id(value: str, name: str) -> None:
    if type(value) is not str or _TOKEN.fullmatch(value) is None:
        raise FinOpsError(f"invalid_{name}")


class InvoiceLineKind(StrEnum):
    USAGE = "usage"
    TAX = "tax"
    CREDIT = "credit"


@dataclass(frozen=True, slots=True)
class SyntheticInvoiceLine:
    """A declared statement line. A credit is a positive magnitude, not -cost."""

    line_id: str
    provider_request_id: str
    kind: InvoiceLineKind
    amount: Money

    def __post_init__(self) -> None:
        _id(self.line_id, "invoice_line_id")
        _id(self.provider_request_id, "provider_request_id")
        if type(self.kind) is not InvoiceLineKind:
            raise FinOpsError("invalid_invoice_line_kind")
        if type(self.amount) is not Money:
            raise FinOpsError("invalid_invoice_line_amount")


@dataclass(frozen=True, slots=True)
class SyntheticInvoiceStatement:
    """A non-authenticated fixture with an exact declared billing route."""

    statement_id: str
    model_id: str
    api_provider: str
    billing_provider: str
    deployment_channel: str
    currency: str
    lines: tuple[SyntheticInvoiceLine, ...]
    source_kind: str = "synthetic_fixture"

    def __post_init__(self) -> None:
        for name in (
            "statement_id", "model_id", "api_provider", "billing_provider",
            "deployment_channel",
        ):
            _id(getattr(self, name), name)
        if self.source_kind != "synthetic_fixture":
            raise FinOpsError("invoice_source_not_verified")
        if type(self.lines) is not tuple or not self.lines or len(self.lines) > 2000:
            raise FinOpsError("invalid_invoice_lines")
        Money(Decimal("0"), self.currency)
        seen: set[str] = set()
        for line in self.lines:
            if type(line) is not SyntheticInvoiceLine:
                raise FinOpsError("invalid_invoice_line")
            if line.line_id in seen:
                raise FinOpsError("duplicate_invoice_line_id")
            seen.add(line.line_id)
            if line.amount.currency != self.currency:
                raise FinOpsError("invoice_currency_mismatch")


@dataclass(frozen=True, slots=True)
class SyntheticReconciliation:
    statement_id: str
    provider_request_id: str
    status: str
    reason: str
    quote_amount: Money | None
    usage_amount: Money | None
    tax_amount: Money | None
    credit_amount: Money | None
    net_amount: Decimal | None
    usage_variance: Decimal | None
    matched_line_ids: tuple[str, ...]
    source_kind: str = "synthetic_fixture"
    provider_invoice_verified: bool = False
    live_authorized: bool = False


def reconcile_synthetic_statement(
    quote: PreflightQuote,
    statement: SyntheticInvoiceStatement,
    *,
    expected_provider_request_id: str,
    tolerance: Decimal = Decimal("0"),
) -> SyntheticReconciliation:
    """Compare *usage subtotal only*; report tax/credit separately.

    A quote may omit billable meters. A synthetic match is therefore merely
    arithmetic agreement for declared units, NEVER verified billing evidence.
    """
    if type(quote) is not PreflightQuote or type(statement) is not SyntheticInvoiceStatement:
        raise FinOpsError("invalid_reconciliation_input")
    _id(expected_provider_request_id, "expected_provider_request_id")
    if type(tolerance) is not Decimal or not tolerance.is_finite() or tolerance < 0:
        raise FinOpsError("invalid_reconciliation_tolerance")

    matching = tuple(
        line for line in statement.lines
        if line.provider_request_id == expected_provider_request_id
    )
    line_ids = tuple(line.line_id for line in matching)

    def result(
        status: str, reason: str, *, usage: Money | None = None,
        tax: Money | None = None, credit: Money | None = None,
        net: Decimal | None = None, variance: Decimal | None = None,
    ) -> SyntheticReconciliation:
        return SyntheticReconciliation(
            statement.statement_id, expected_provider_request_id, status, reason,
            quote.amount, usage, tax, credit, net, variance, line_ids,
        )

    if not quote.scenario_priced or quote.amount is None:
        return result("indeterminate", "quote_not_priced")
    if (
        statement.model_id != quote.model_id
        or statement.api_provider != quote.api_provider
        or statement.billing_provider != quote.billing_provider
        or statement.deployment_channel != quote.deployment_channel
        or statement.currency != quote.amount.currency
    ):
        return result("indeterminate", "billing_route_mismatch")
    if not matching:
        return result("unmatched", "provider_request_id_not_found")
    totals = {
        kind: sum(
            (line.amount.amount for line in matching if line.kind is kind),
            Decimal("0"),
        )
        for kind in InvoiceLineKind
    }
    usage = Money(totals[InvoiceLineKind.USAGE], statement.currency)
    tax = Money(totals[InvoiceLineKind.TAX], statement.currency)
    credit = Money(totals[InvoiceLineKind.CREDIT], statement.currency)
    net = usage.amount + tax.amount - credit.amount
    if not any(line.kind is InvoiceLineKind.USAGE for line in matching):
        return result("indeterminate", "usage_lines_missing", tax=tax, credit=credit)
    variance = usage.amount - quote.amount.amount
    status = "matched_synthetic" if abs(variance) <= tolerance else "variance_synthetic"
    reason = (
        "declared_usage_agrees_only"
        if status == "matched_synthetic"
        else "declared_usage_variance"
    )
    return result(
        status, reason, usage=usage, tax=tax, credit=credit, net=net,
        variance=variance,
    )


def reconciliation_to_dict(result: SyntheticReconciliation) -> dict[str, object]:
    """Stable CLI JSON, with null for missing amounts (never silently zero)."""
    if type(result) is not SyntheticReconciliation:
        raise FinOpsError("invalid_reconciliation_result")

    def amount(value: Money | None) -> dict[str, str] | None:
        if value is None:
            return None
        return {"value": str(value.amount), "currency": value.currency}

    return {
        "status": result.status,
        "reason": result.reason,
        "statement_id": result.statement_id,
        "provider_request_id": result.provider_request_id,
        "source_kind": result.source_kind,
        "quote_amount": amount(result.quote_amount),
        "usage_amount": amount(result.usage_amount),
        "tax_amount": amount(result.tax_amount),
        "credit_amount": amount(result.credit_amount),
        "net_amount": (
            str(result.net_amount) if result.net_amount is not None else None
        ),
        "usage_variance": (
            str(result.usage_variance) if result.usage_variance is not None else None
        ),
        "matched_line_ids": list(result.matched_line_ids),
        "comparison_basis": "declared_usage_subtotal_excluding_taxes_and_credits",
        "provider_request_correlation": "caller_declared_not_verified",
        "provider_invoice_verified": False,
        "budget_ledger_mutated": False,
        "live_authorized": False,
    }
