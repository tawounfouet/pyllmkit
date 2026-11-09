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
from pyllmkit.adapters.cli.finops_invoice_registry import SQLiteSyntheticInvoiceRegistry
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
from pyllmkit.domain.finops.invoice_registry import (
    ImportedInvoice,
    InvoiceImportRequest,
    InvoiceImportResult,
    audit_report_to_dict,
    imported_invoice_to_dict,
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


def _invoice_registry(database: Path) -> SQLiteSyntheticInvoiceRegistry:
    return SQLiteSyntheticInvoiceRegistry(database)


@invoice_app.command(name="import-synthetic")
def invoice_import_synthetic(
    database: Annotated[Path, typer.Option("--database", help="Base SQLite locale explicite.")],
    statement: Annotated[Path, typer.Option("--statement", help="Fixture synthétique JSON v1.")],
    scope_id: Annotated[str, typer.Option("--scope-id", help="Espace logique d'import.")],
    revision: Annotated[int, typer.Option("--revision", help="Révision positive (1 pour l'origine).")],
    import_key: Annotated[str, typer.Option("--import-key", help="Idempotence persistante.")],
    supersedes: Annotated[
        int | None, typer.Option("--supersedes", help="Révision précédente, si correction."),
    ] = None,
) -> None:
    """Importer une révision de facture synthétique et son événement d'audit atomiquement."""
    try:
        record = _invoice_registry(database).import_synthetic(InvoiceImportRequest(
            scope_id, import_key, revision, supersedes,
            load_synthetic_invoice_statement(statement), datetime.now(UTC),
        ))
        typer.echo(json.dumps(imported_invoice_to_dict(record), ensure_ascii=False))
    except (OSError, ValueError, sqlite3.Error) as exc:
        _report_error(exc)


@invoice_app.command(name="inspect")
def invoice_inspect(
    database: Annotated[Path, typer.Option("--database")],
    scope_id: Annotated[str, typer.Option("--scope-id")],
    statement_id: Annotated[str, typer.Option("--statement-id")],
    revision: Annotated[int | None, typer.Option("--revision")] = None,
) -> None:
    """Consulter une révision persistée (la dernière par défaut), après audit local."""
    try:
        invoice = _invoice_registry(database).inspect(scope_id, statement_id, revision)
        typer.echo(json.dumps(imported_invoice_to_dict(
            __import_result(invoice),
        ), ensure_ascii=False))
    except (OSError, ValueError, sqlite3.Error) as exc:
        _report_error(exc)


def __import_result(invoice: ImportedInvoice) -> InvoiceImportResult:
    return InvoiceImportResult(invoice)


@invoice_app.command(name="history")
def invoice_history(
    database: Annotated[Path, typer.Option("--database")],
    scope_id: Annotated[str, typer.Option("--scope-id")],
    statement_id: Annotated[str, typer.Option("--statement-id")],
) -> None:
    """Lister les révisions immuables et le hash de chaque événement."""
    try:
        versions = _invoice_registry(database).history(scope_id, statement_id)
        typer.echo(json.dumps({
            "scope_id": scope_id, "statement_id": statement_id,
            "versions": [
                imported_invoice_to_dict(InvoiceImportResult(item)) for item in versions
            ],
            "source_kind": "synthetic_fixture",
            "provider_invoice_verified": False, "ledger_mutated": False,
            "live_authorized": False,
        }, ensure_ascii=False))
    except (OSError, ValueError, sqlite3.Error) as exc:
        _report_error(exc)


@invoice_app.command(name="audit")
def invoice_audit(
    database: Annotated[Path, typer.Option("--database")],
    scope_id: Annotated[str, typer.Option("--scope-id")],
) -> None:
    """Vérifier les empreintes, snapshots et liens de hash de l'espace local."""
    try:
        report = _invoice_registry(database).audit(scope_id)
        typer.echo(json.dumps(audit_report_to_dict(report), ensure_ascii=False))
    except (OSError, ValueError, sqlite3.Error) as exc:
        _report_error(exc)


@invoice_app.command(name="reconcile-imported")
def invoice_reconcile_imported(
    database: Annotated[Path, typer.Option("--database")],
    scope_id: Annotated[str, typer.Option("--scope-id")],
    statement_id: Annotated[str, typer.Option("--statement-id")],
    request: Annotated[Path, typer.Option("--request")],
    provider_request_id: Annotated[str, typer.Option("--provider-request-id")],
    revision: Annotated[int | None, typer.Option("--revision")] = None,
    pricing_catalog: Annotated[Path | None, typer.Option("--pricing-catalog")] = None,
    tolerance: Annotated[str, typer.Option("--tolerance")] = "0",
) -> None:
    """Comparer un snapshot local G4.2 à G2, sans modifier le registre ni le ledger."""
    try:
        if re.fullmatch(r"(?:0|[1-9]\d*)(?:\.\d+)?", tolerance) is None or len(tolerance) > 80:
            raise FinOpsError("invalid_reconciliation_tolerance")
        statement = _invoice_registry(database).inspect(scope_id, statement_id, revision)
        quote = quote_media_scenario(
            load_quote_request(request),
            prices=load_price_catalog(pricing_catalog),
            media=load_media_catalog(),
        )
        report = reconcile_synthetic_statement(
            quote, statement.statement,
            expected_provider_request_id=provider_request_id,
            tolerance=Decimal(tolerance),
        )
        output = reconciliation_to_dict(report)
        output["scope_id"] = scope_id
        output["imported_revision"] = statement.revision
        output["invoice_fingerprint"] = statement.fingerprint
        output["invoice_audit_hash"] = statement.audit_hash
        typer.echo(json.dumps(output, ensure_ascii=False))
        if report.status != "matched_synthetic":
            raise typer.Exit(code=3)
    except typer.Exit:
        raise
    except (OSError, ValueError, sqlite3.Error) as exc:
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


invoice_app = typer.Typer(help="Registre de factures synthétiques SQLite, audit local hors réseau.")
finops_app.add_typer(invoice_app, name="invoice")

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
