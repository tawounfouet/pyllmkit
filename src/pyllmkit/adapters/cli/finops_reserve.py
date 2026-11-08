"""Transactional offline SQLite FinOps reservation adapter (M2-G3).

Atomic across local processes sharing one database file (BEGIN IMMEDIATE).
No secrets, HTTP, provider invocations, billing evidence or live authority.
All currency arithmetic uses Decimal strings, never SQLite REAL/SUM.
"""

from __future__ import annotations

import sqlite3
from contextlib import closing
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

from pyllmkit.domain.finops import FinOpsError, Money
from pyllmkit.domain.finops.reservations import (
    BudgetLedger,
    BudgetReservation,
    ReservationRequest,
    ReservationResult,
    ReservationState,
    quote_fingerprint,
)


class SQLiteBudgetReservationStore:
    """Single-file offline ledger. Each mutation uses one IMMEDIATE transaction.

    Not a distributed coordination backend. NFS/networked volumes, externally
    edited database files, live dispatch and multi-region spend are out of scope.
    """

    def __init__(self, database: Path) -> None:
        if not isinstance(database, Path) or str(database) == ":memory:":
            raise FinOpsError("invalid_budget_database")
        self._database = database
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(str(self._database), timeout=5, isolation_level=None)
        connection.execute("PRAGMA busy_timeout=5000")
        return connection

    def _initialize(self) -> None:
        with closing(self._connect()) as conn:
            conn.execute("BEGIN IMMEDIATE")
            with conn:
                conn.execute(
                    """CREATE TABLE IF NOT EXISTS finops_budgets (
                        budget_id TEXT PRIMARY KEY,
                        currency TEXT NOT NULL,
                        limit_amount TEXT NOT NULL,
                        spent_amount TEXT NOT NULL,
                        reserved_amount TEXT NOT NULL
                    )"""
                )
                conn.execute(
                    """CREATE TABLE IF NOT EXISTS finops_reservations (
                        reservation_id TEXT PRIMARY KEY,
                        budget_id TEXT NOT NULL,
                        idempotency_key TEXT NOT NULL,
                        fingerprint TEXT NOT NULL,
                        amount TEXT NOT NULL,
                        currency TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        purpose TEXT NOT NULL,
                        status TEXT NOT NULL,
                        settled_amount TEXT,
                        UNIQUE (budget_id, idempotency_key),
                        FOREIGN KEY (budget_id) REFERENCES finops_budgets(budget_id)
                    )"""
                )

    @staticmethod
    def _budget(conn: sqlite3.Connection, budget_id: str) -> BudgetLedger:
        record = conn.execute(
            "SELECT currency, limit_amount, spent_amount, reserved_amount "
            "FROM finops_budgets WHERE budget_id=?", (budget_id,),
        ).fetchone()
        if record is None:
            raise FinOpsError("budget_not_found")
        currency, limit_value, spent, reserved = record
        return BudgetLedger(
            budget_id,
            Money(Decimal(limit_value), currency),
            Money(Decimal(spent), currency),
            Money(Decimal(reserved), currency),
        )

    @staticmethod
    def _reservation(conn: sqlite3.Connection, reservation_id: str) -> BudgetReservation:
        record = conn.execute(
            "SELECT budget_id, idempotency_key, fingerprint, amount, currency, "
            "created_at, purpose, status, settled_amount "
            "FROM finops_reservations WHERE reservation_id=?", (reservation_id,),
        ).fetchone()
        if record is None:
            raise FinOpsError("reservation_not_found")
        budget_id, key, fingerprint, amount, currency, created, purpose, status, settled = record
        return BudgetReservation(
            reservation_id, budget_id, key, fingerprint,
            Money(Decimal(amount), currency), ReservationState(status),
            datetime.fromisoformat(created), purpose,
            Money(Decimal(settled), currency) if settled is not None else None,
        )

    @classmethod
    def _result(
        cls, conn: sqlite3.Connection, reservation_id: str, *,
        replayed: bool = False,
    ) -> ReservationResult:
        reservation = cls._reservation(conn, reservation_id)
        return ReservationResult(
            reservation, cls._budget(conn, reservation.budget_id), replayed,
        )

    def create_budget(self, budget_id: str, limit: Money) -> BudgetLedger:
        if type(limit) is not Money:
            raise FinOpsError("invalid_budget_limit")
        BudgetLedger(budget_id, limit, Money(Decimal(0), limit.currency),
                     Money(Decimal(0), limit.currency))
        with closing(self._connect()) as conn:
            conn.execute("BEGIN IMMEDIATE")
            with conn:
                existing = conn.execute(
                    "SELECT currency, limit_amount FROM finops_budgets WHERE budget_id=?",
                    (budget_id,),
                ).fetchone()
                if existing is None:
                    conn.execute(
                        "INSERT INTO finops_budgets VALUES (?, ?, ?, ?, ?)",
                        (budget_id, limit.currency, str(limit.amount), "0", "0"),
                    )
                elif existing[0] != limit.currency or Decimal(existing[1]) != limit.amount:
                    raise FinOpsError("budget_already_exists_with_different_limit")
                return self._budget(conn, budget_id)

    def get_budget(self, budget_id: str) -> BudgetLedger:
        with closing(self._connect()) as conn:
            return self._budget(conn, budget_id)

    def reserve(self, request: ReservationRequest) -> ReservationResult:
        if type(request) is not ReservationRequest:
            raise FinOpsError("invalid_reservation_request")
        assert request.quote.amount is not None
        digest = quote_fingerprint(request)
        with closing(self._connect()) as conn:
            conn.execute("BEGIN IMMEDIATE")
            with conn:
                old = conn.execute(
                    "SELECT reservation_id, fingerprint FROM finops_reservations "
                    "WHERE budget_id=? AND idempotency_key=?",
                    (request.budget_id, request.idempotency_key),
                ).fetchone()
                if old is not None:
                    if old[1] != digest:
                        raise FinOpsError("reservation_idempotency_conflict")
                    return self._result(conn, old[0], replayed=True)
                ledger = self._budget(conn, request.budget_id)
                amount = request.quote.amount
                if amount.currency != ledger.limit.currency:
                    raise FinOpsError("budget_currency_mismatch")
                if amount.amount > ledger.remaining.amount:
                    raise FinOpsError("insufficient_budget")
                reservation_id = "resv_" + uuid4().hex
                conn.execute(
                    "INSERT INTO finops_reservations "
                    "(reservation_id, budget_id, idempotency_key, fingerprint, "
                    "amount, currency, created_at, purpose, status, settled_amount) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, NULL)",
                    (
                        reservation_id, request.budget_id, request.idempotency_key,
                        digest, str(amount.amount), amount.currency,
                        request.requested_at.isoformat(), request.purpose,
                        ReservationState.PENDING.value,
                    ),
                )
                conn.execute(
                    "UPDATE finops_budgets SET reserved_amount=? WHERE budget_id=?",
                    (str(ledger.reserved.amount + amount.amount), request.budget_id),
                )
                return self._result(conn, reservation_id)

    def get_reservation(self, reservation_id: str) -> ReservationResult:
        with closing(self._connect()) as conn:
            return self._result(conn, reservation_id)

    def _transition(
        self, reservation_id: str, action: str, simulated: Decimal | None = None,
    ) -> ReservationResult:
        with closing(self._connect()) as conn:
            conn.execute("BEGIN IMMEDIATE")
            with conn:
                record = self._reservation(conn, reservation_id)
                ledger = self._budget(conn, record.budget_id)
                if action == "dispute":
                    destination = ReservationState.DISPUTED
                    if record.status == destination:
                        return self._result(conn, reservation_id, replayed=True)
                    if record.status != ReservationState.PENDING:
                        raise FinOpsError("invalid_reservation_transition")
                    new_reserved = ledger.reserved.amount
                    new_spent = ledger.spent.amount
                elif action == "release":
                    destination = ReservationState.RELEASED_UNDISPATCHED
                    if record.status == destination:
                        return self._result(conn, reservation_id, replayed=True)
                    if record.status != ReservationState.PENDING:
                        raise FinOpsError("invalid_reservation_transition")
                    new_reserved = ledger.reserved.amount - record.amount.amount
                    new_spent = ledger.spent.amount
                elif action == "settle":
                    destination = ReservationState.SETTLED_SIMULATED
                    if record.status == destination:
                        if record.settled_amount is not None and simulated == record.settled_amount.amount:
                            return self._result(conn, reservation_id, replayed=True)
                        raise FinOpsError("conflicting_simulated_settlement")
                    if record.status not in (ReservationState.PENDING, ReservationState.DISPUTED):
                        raise FinOpsError("invalid_reservation_transition")
                    if (
                        type(simulated) is not Decimal
                        or not simulated.is_finite()
                        or simulated < 0
                        or simulated > record.amount.amount
                    ):
                        raise FinOpsError("invalid_simulated_settlement")
                    new_reserved = ledger.reserved.amount - record.amount.amount
                    new_spent = ledger.spent.amount + simulated
                else:
                    raise FinOpsError("invalid_reservation_action")
                if new_reserved < 0 or new_spent + new_reserved > ledger.limit.amount:
                    raise FinOpsError("budget_invariant_violation")
                conn.execute(
                    "UPDATE finops_budgets SET spent_amount=?, reserved_amount=? "
                    "WHERE budget_id=?",
                    (str(new_spent), str(new_reserved), record.budget_id),
                )
                conn.execute(
                    "UPDATE finops_reservations SET status=?, settled_amount=? "
                    "WHERE reservation_id=?",
                    (
                        destination.value,
                        str(simulated) if action == "settle" else None,
                        reservation_id,
                    ),
                )
                return self._result(conn, reservation_id)

    def dispute(self, reservation_id: str) -> ReservationResult:
        """Keep the full reservation locked after an uncertain remote outcome."""
        return self._transition(reservation_id, "dispute")

    def release_undispatched(self, reservation_id: str) -> ReservationResult:
        """Only for a local sandbox request that was never sent to a provider."""
        return self._transition(reservation_id, "release")

    def settle_simulated(self, reservation_id: str, amount: Decimal) -> ReservationResult:
        """Synthetic debit for offline tests; never an imported provider invoice."""
        return self._transition(reservation_id, "settle", amount)
