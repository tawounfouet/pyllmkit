"""Offline FinOps quote and sandbox budget CLI. No paid provider calls."""

from __future__ import annotations

import json
import re
import sqlite3
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Annotated

import typer

from pyllmkit.adapters.cli.finops_invoice import load_synthetic_invoice_statement
from pyllmkit.adapters.cli.finops_quote import (
    load_quote_request,
    quote_media_scenario,
)
from pyllmkit.adapters.cli.finops_reserve import SQLiteBudgetReservationStore
from pyllmkit.adapters.cli.media_catalog_v2 import load_media_catalog
from pyllmkit.adapters.cli.pricing_catalog_v2 import load_price_catalog
from pyllmkit.domain.finops import FinOpsError, Money
from pyllmkit.domain.finops.invoice_reconciliation import (
    reconcile_synthetic_statement,
    reconciliation_to_dict,
)
from pyllmkit.domain.finops.quoting import quote_to_dict
from pyllmkit.domain.finops.reservations import (
    ReservationRequest,
    ReservationState,
    reservation_to_dict,
)

finops_app = typer.Typer(
    help="Devis et réservations SQLite hors réseau, jamais une autorisation payante.",
    no_args_is_help=True,
    add_completion=False,
)


@finops_app.command(name="quote")
def quote_command(
    request: Annotated[
        Path,
        typer.Option("--request", "-r", help="Fichier de scénario JSON v1 explicite."),
    ],
    pricing_catalog: Annotated[
        Path | None,
        typer.Option(
            "--pricing-catalog",
            help="Catalogue tarifaire JSON v2 explicite. Défaut: catalogue embarqué vide.",
        ),
    ] = None,
) -> None:
    """Coter uniquement les composantes déclarées; ce résultat n'autorise pas le live."""
    try:
        scenario = load_quote_request(request)
        prices = load_price_catalog(pricing_catalog)
        quote = quote_media_scenario(scenario, prices=prices, media=load_media_catalog())
    except (OSError, ValueError) as exc:
        typer.echo(json.dumps({
            "status": "error",
            "reason": str(exc),
            "live_authorized": False,
        }, ensure_ascii=False))
        raise typer.Exit(code=2) from None

    typer.echo(json.dumps(quote_to_dict(quote), ensure_ascii=False))
    if not quote.scenario_priced:
        raise typer.Exit(code=3)



@finops_app.command(name="reconcile")
def reconcile_command(
    request: Annotated[Path, typer.Option("--request", help="Scénario G2 JSON v1.")],
    statement: Annotated[
        Path, typer.Option("--statement", help="Facture synthétique JSON v1 locale."),
    ],
    provider_request_id: Annotated[
        str, typer.Option("--provider-request-id", help="Corrélation déclarée non vérifiée."),
    ],
    pricing_catalog: Annotated[
        Path | None, typer.Option("--pricing-catalog"),
    ] = None,
    tolerance: Annotated[
        str, typer.Option("--tolerance", help="Tolérance exacte, valeur décimale non négative."),
    ] = "0",
) -> None:
    """Comparer les montants synthétiques de consommation à un devis, sans débit."""
    try:
        if re.fullmatch(r"(?:0|[1-9]\d*)(?:\.\d+)?", tolerance) is None or len(tolerance) > 80:
            raise FinOpsError("invalid_reconciliation_tolerance")
        quote = quote_media_scenario(
            load_quote_request(request),
            prices=load_price_catalog(pricing_catalog),
            media=load_media_catalog(),
        )
        invoice = load_synthetic_invoice_statement(statement)
        report = reconcile_synthetic_statement(
            quote, invoice, expected_provider_request_id=provider_request_id,
            tolerance=Decimal(tolerance),
        )
        typer.echo(json.dumps(reconciliation_to_dict(report), ensure_ascii=False))
        if report.status != "matched_synthetic":
            raise typer.Exit(code=3)
    except typer.Exit:
        raise
    except (OSError, ValueError) as exc:
        _report_error(exc)


def _report_error(exc: Exception) -> None:
    typer.echo(json.dumps({
        "status": "error", "reason": str(exc), "live_authorized": False,
    }, ensure_ascii=False))
    raise typer.Exit(code=3 if isinstance(exc, FinOpsError) else 2) from None


def _money(value: str, currency: str) -> Money:
    try:
        return Money(Decimal(value), currency)
    except (InvalidOperation, ValueError) as exc:
        raise FinOpsError("invalid_budget_amount") from exc


def _store(database: Path) -> SQLiteBudgetReservationStore:
    return SQLiteBudgetReservationStore(database)


budget_app = typer.Typer(help="Budget de démonstration SQLite, strictement hors réseau.")
reservation_app = typer.Typer(help="Transitions des réservations locales simulées.")
finops_app.add_typer(budget_app, name="budget")
finops_app.add_typer(reservation_app, name="reservation")


@budget_app.command(name="create")
def budget_create(
    database: Annotated[Path, typer.Option("--database", help="Fichier SQLite explicite.")],
    budget_id: Annotated[str, typer.Option("--budget-id")],
    limit: Annotated[str, typer.Option("--limit", help="Montant exact en chaîne décimale.")],
    currency: Annotated[str, typer.Option("--currency")] = "USD",
) -> None:
    """Créer un plafond immuable pour une démonstration locale."""
    try:
        ledger = _store(database).create_budget(budget_id, _money(limit, currency))
        typer.echo(json.dumps({
            "status": "created", "budget_id": ledger.budget_id,
            "limit": str(ledger.limit.amount), "currency": ledger.limit.currency,
            "offline_sandbox_only": True, "live_authorized": False,
        }))
    except (OSError, ValueError, sqlite3.Error) as exc:
        _report_error(exc)


@budget_app.command(name="inspect")
def budget_inspect(
    database: Annotated[Path, typer.Option("--database")],
    budget_id: Annotated[str, typer.Option("--budget-id")],
) -> None:
    """Consulter les montants persistants sans les modifier."""
    try:
        ledger = _store(database).get_budget(budget_id)
        typer.echo(json.dumps({
            "budget_id": ledger.budget_id, "currency": ledger.limit.currency,
            "limit": str(ledger.limit.amount), "spent": str(ledger.spent.amount),
            "reserved": str(ledger.reserved.amount), "remaining": str(ledger.remaining.amount),
            "live_authorized": False,
        }))
    except (OSError, ValueError, sqlite3.Error) as exc:
        _report_error(exc)


@finops_app.command(name="reserve")
def reserve_command(
    request: Annotated[Path, typer.Option("--request")],
    database: Annotated[Path, typer.Option("--database")],
    budget_id: Annotated[str, typer.Option("--budget-id")],
    idempotency_key: Annotated[str, typer.Option("--idempotency-key")],
    pricing_catalog: Annotated[
        Path | None, typer.Option("--pricing-catalog"),
    ] = None,
) -> None:
    """Réserver dans SQLite uniquement pour un scénario offline non exécutable."""
    try:
        scenario = load_quote_request(request)
        quote = quote_media_scenario(
            scenario, prices=load_price_catalog(pricing_catalog),
            media=load_media_catalog(),
        )
        if not quote.scenario_priced:
            typer.echo(json.dumps(quote_to_dict(quote), ensure_ascii=False))
            raise typer.Exit(code=3)
        record = _store(database).reserve(
            ReservationRequest(budget_id, idempotency_key, quote, datetime.now(UTC)),
        )
        typer.echo(json.dumps(reservation_to_dict(record), ensure_ascii=False))
        if record.reservation.status is not ReservationState.PENDING:
            raise typer.Exit(code=3)
    except typer.Exit:
        raise
    except (OSError, ValueError, sqlite3.Error) as exc:
        _report_error(exc)


@reservation_app.command(name="inspect")
def reservation_inspect(
    database: Annotated[Path, typer.Option("--database")],
    reservation_id: Annotated[str, typer.Option("--reservation-id")],
) -> None:
    """Relire la réservation persistée entre processus CLI."""
    try:
        typer.echo(json.dumps(reservation_to_dict(
            _store(database).get_reservation(reservation_id)
        ), ensure_ascii=False))
    except (OSError, ValueError, sqlite3.Error) as exc:
        _report_error(exc)


@reservation_app.command(name="simulate-dispatch-intent")
def reservation_simulate_dispatch_intent(
    database: Annotated[Path, typer.Option("--database")],
    reservation_id: Annotated[str, typer.Option("--reservation-id")],
    attempt_key: Annotated[str, typer.Option(
        "--attempt-key", help="Identifiant unique du scénario de dispatch simulé.",
    )],
) -> None:
    """Marquer un point de non-retour local. Ne déclenche AUCUN appel réseau."""
    try:
        typer.echo(json.dumps(reservation_to_dict(
            _store(database).record_dispatch_intent(
                reservation_id, attempt_key, at=datetime.now(UTC),
            )
        ), ensure_ascii=False))
    except (OSError, ValueError, sqlite3.Error) as exc:
        _report_error(exc)


@reservation_app.command(name="dispute")
def reservation_dispute(
    database: Annotated[Path, typer.Option("--database")],
    reservation_id: Annotated[str, typer.Option("--reservation-id")],
) -> None:
    """Marquer une issue inconnue sans jamais libérer automatiquement les fonds."""
    try:
        typer.echo(json.dumps(reservation_to_dict(
            _store(database).dispute(reservation_id)
        ), ensure_ascii=False))
    except (OSError, ValueError, sqlite3.Error) as exc:
        _report_error(exc)


@reservation_app.command(name="release")
def reservation_release(
    database: Annotated[Path, typer.Option("--database")],
    reservation_id: Annotated[str, typer.Option("--reservation-id")],
    confirm_no_dispatch: Annotated[
        bool, typer.Option(
            "--confirm-no-dispatch",
            help="Confirmer que cette réservation locale n'a déclenché aucun appel distant.",
        ),
    ] = False,
) -> None:
    """Libération manuelle d'un sandbox jamais dispatché, impossible en disputed."""
    try:
        if not confirm_no_dispatch:
            raise FinOpsError("undispatched_confirmation_required")
        typer.echo(json.dumps(reservation_to_dict(
            _store(database).release_undispatched(reservation_id)
        ), ensure_ascii=False))
    except (OSError, ValueError, sqlite3.Error) as exc:
        _report_error(exc)


@reservation_app.command(name="settle-simulated")
def reservation_settle_simulated(
    database: Annotated[Path, typer.Option("--database")],
    reservation_id: Annotated[str, typer.Option("--reservation-id")],
    amount: Annotated[str, typer.Option("--amount", help="Débit synthétique de démonstration.")],
) -> None:
    """Simuler un débit plafonné; aucune ligne de facture importée."""
    try:
        value = Decimal(amount)
        typer.echo(json.dumps(reservation_to_dict(
            _store(database).settle_simulated(reservation_id, value)
        ), ensure_ascii=False))
    except InvalidOperation:
        _report_error(FinOpsError("invalid_simulated_settlement"))
    except (OSError, ValueError, sqlite3.Error) as exc:
        _report_error(exc)
