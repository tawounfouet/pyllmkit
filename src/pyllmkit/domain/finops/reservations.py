"""Offline FinOps G3 reservation contracts.

No G2 quote guarantees a remote hard cap. A local durable reservation is
never a provider authorization, invoice, or proof of successful dispatch.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Protocol

from pyllmkit.domain.finops import FinOpsError, Money
from pyllmkit.domain.finops.quoting import PreflightQuote, quote_to_dict

_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,191}$")


def _identifier(value: str, label: str) -> None:
    if type(value) is not str or not _IDENTIFIER.fullmatch(value):
        raise FinOpsError(f"invalid_{label}")


def _instant(value: datetime, label: str) -> None:
    if type(value) is not datetime or value.tzinfo is None or value.utcoffset() is None:
        raise FinOpsError(f"invalid_{label}")


class ReservationState(StrEnum):
    PENDING = "pending"
    DISPATCH_INTENT_RECORDED = "dispatch_intent_recorded"
    DISPUTED = "disputed"
    SETTLED_SIMULATED = "settled_simulated"
    RELEASED_UNDISPATCHED = "released_undispatched"


@dataclass(frozen=True, slots=True)
class ReservationRequest:
    """Reservation of a *synthetic offline* quote only, not a remote spend cap."""

    budget_id: str
    idempotency_key: str
    quote: PreflightQuote
    requested_at: datetime
    purpose: str = "offline_sandbox"

    def __post_init__(self) -> None:
        _identifier(self.budget_id, "budget_id")
        _identifier(self.idempotency_key, "idempotency_key")
        _identifier(self.purpose, "reservation_purpose")
        _instant(self.requested_at, "reservation_time")
        if type(self.quote) is not PreflightQuote or not self.quote.scenario_priced:
            raise FinOpsError("quote_not_reservable_offline")
        if self.quote.amount is None or self.quote.price_id is None:
            raise FinOpsError("quote_not_reservable_offline")
        if self.quote.valid_until is not None and self.requested_at >= self.quote.valid_until:
            raise FinOpsError("stale_quote")
        if self.requested_at < self.quote.at:
            raise FinOpsError("reservation_before_quote")
        if self.quote.coverage != "declared_components_only" or self.quote.live_authorized:
            raise FinOpsError("unsupported_quote_authority")


def quote_fingerprint(request: ReservationRequest) -> str:
    """Stable canonical request digest, excluding current clock and DB identity.

    Exact retries must retain the quote, purpose, and budget scope. A mutable
    quote, even one with an identical total, produces a different fingerprint.
    """
    payload = {
        "budget_id": request.budget_id,
        "idempotency_key": request.idempotency_key,
        "purpose": request.purpose,
        "quote": quote_to_dict(request.quote),
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class BudgetLedger:
    budget_id: str
    limit: Money
    spent: Money
    reserved: Money

    def __post_init__(self) -> None:
        _identifier(self.budget_id, "budget_id")
        if (self.limit.currency != self.spent.currency
                or self.limit.currency != self.reserved.currency):
            raise FinOpsError("budget_currency_mismatch")
        if self.spent.amount + self.reserved.amount > self.limit.amount:
            raise FinOpsError("budget_limit_exceeded")

    @property
    def remaining(self) -> Money:
        return Money(
            self.limit.amount - self.spent.amount - self.reserved.amount,
            self.limit.currency,
        )


@dataclass(frozen=True, slots=True)
class BudgetReservation:
    reservation_id: str
    budget_id: str
    idempotency_key: str
    quote_fingerprint: str
    amount: Money
    status: ReservationState
    created_at: datetime
    purpose: str
    settled_amount: Money | None = None
    dispatch_attempt_key: str | None = None
    dispatch_intent_at: datetime | None = None

    def __post_init__(self) -> None:
        for label in ("reservation_id", "budget_id", "idempotency_key", "purpose"):
            _identifier(getattr(self, label), label)
        if type(self.quote_fingerprint) is not str or not re.fullmatch(
            r"[0-9a-f]{64}", self.quote_fingerprint,
        ):
            raise FinOpsError("invalid_reservation_fingerprint")
        _instant(self.created_at, "reservation_created_at")
        if type(self.status) is not ReservationState:
            raise FinOpsError("invalid_reservation_state")
        if self.settled_amount is not None and self.settled_amount.currency != self.amount.currency:
            raise FinOpsError("settlement_currency_mismatch")
        if (self.dispatch_attempt_key is None) != (self.dispatch_intent_at is None):
            raise FinOpsError("incomplete_dispatch_intent")
        if self.dispatch_attempt_key is not None:
            _identifier(self.dispatch_attempt_key, "dispatch_attempt_key")
            assert self.dispatch_intent_at is not None
            _instant(self.dispatch_intent_at, "dispatch_intent_at")
            if self.dispatch_intent_at < self.created_at:
                raise FinOpsError("dispatch_intent_before_reservation")
        if self.status is ReservationState.DISPATCH_INTENT_RECORDED and self.dispatch_attempt_key is None:
            raise FinOpsError("missing_dispatch_intent")
        if self.status is ReservationState.PENDING and self.dispatch_attempt_key is not None:
            raise FinOpsError("pending_with_dispatch_intent")


@dataclass(frozen=True, slots=True)
class ReservationResult:
    reservation: BudgetReservation
    ledger: BudgetLedger
    replayed: bool = False


class BudgetReservationPort(Protocol):
    """Transaction boundary: same budget and idempotency key serialized atomically."""

    def create_budget(self, budget_id: str, limit: Money) -> BudgetLedger: ...

    def get_budget(self, budget_id: str) -> BudgetLedger: ...

    def reserve(self, request: ReservationRequest) -> ReservationResult: ...

    def get_reservation(self, reservation_id: str) -> ReservationResult: ...

    def record_dispatch_intent(
        self, reservation_id: str, attempt_key: str, *, at: datetime,
    ) -> ReservationResult: ...

    def dispute(self, reservation_id: str) -> ReservationResult: ...

    def release_undispatched(self, reservation_id: str) -> ReservationResult: ...

    def settle_simulated(
        self, reservation_id: str, amount: Decimal,
    ) -> ReservationResult: ...


def reservation_to_dict(result: ReservationResult) -> dict[str, object]:
    """CLI projection; reservation and balance never imply remote access."""
    record = result.reservation
    budget = result.ledger
    return {
        "status": record.status.value,
        "replayed": result.replayed,
        "reservation_id": record.reservation_id,
        "budget_id": record.budget_id,
        "idempotency_key": record.idempotency_key,
        "quote_fingerprint": record.quote_fingerprint,
        "purpose": record.purpose,
        "created_at": record.created_at.isoformat(),
        "dispatch_attempt_key": record.dispatch_attempt_key,
        "dispatch_intent_at": (
            record.dispatch_intent_at.isoformat() if record.dispatch_intent_at else None
        ),
        "amount": {"value": str(record.amount.amount), "currency": record.amount.currency},
        "settled_amount": (
            {"value": str(record.settled_amount.amount), "currency": record.settled_amount.currency}
            if record.settled_amount is not None else None
        ),
        "limit": {"value": str(budget.limit.amount), "currency": budget.limit.currency},
        "spent": {"value": str(budget.spent.amount), "currency": budget.spent.currency},
        "reserved": {"value": str(budget.reserved.amount), "currency": budget.reserved.currency},
        "remaining": {"value": str(budget.remaining.amount), "currency": budget.remaining.currency},
        "atomic_budget_reserved": record.status in (
            ReservationState.PENDING, ReservationState.DISPATCH_INTENT_RECORDED,
            ReservationState.DISPUTED,
        ),
        "offline_sandbox_only": True,
        "spend_bound_verified": False,
        "provider_quote_verified": False,
        "live_authorized": False,
    }
