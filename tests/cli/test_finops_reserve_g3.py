"""M2-G3: durable offline budget reservations, state machine and CLI tests."""

from __future__ import annotations

import json
import sqlite3
import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from pyllmkit.adapters.cli.commands.finops import finops_app
from pyllmkit.adapters.cli.finops_quote import parse_quote_request, quote_media_scenario
from pyllmkit.adapters.cli.finops_reserve import SQLiteBudgetReservationStore
from pyllmkit.adapters.cli.main import app
from pyllmkit.adapters.cli.media_catalog_v2 import load_media_catalog
from pyllmkit.adapters.cli.pricing_catalog_v2 import parse_price_catalog
from pyllmkit.domain.finops import FinOpsError, Money
from pyllmkit.domain.finops.reservations import (
    ReservationRequest,
    ReservationState,
    quote_fingerprint,
    reservation_to_dict,
)

AT = datetime(2026, 11, 8, 12, tzinfo=UTC)


def _prices() -> dict[str, Any]:
    return {
        "schema_version": 2,
        "revision": "synthetic-g3",
        "updated_at": "2026-11-08",
        "prices": [{
            "price_id": "fake-image-rate",
            "revision": "r1",
            "model_id": "gpt-image-2",
            "api_provider": "openai",
            "billing_provider": "openai",
            "deployment_channel": "direct",
            "currency": "USD",
            "valid_from": "2026-11-01T00:00:00+00:00",
            "valid_to": None,
            "verified_at": "2026-11-08",
            "source_url": "https://example.org/synthetic-only",
            "rates": [
                {"meter": "image", "amount": "0.025", "per": "1", "dimensions": {"quality": "high"}},
                {"meter": "input_token", "amount": "1", "per": "1000000", "dimensions": {}},
            ],
        }],
    }


def _scenario() -> dict[str, Any]:
    return {
        "schema_version": 1, "model_id": "gpt-image-2", "api_provider": "openai",
        "task": "text_to_image", "at": AT.isoformat(),
        "parameters": {"quality": "high"}, "components": [
            {"meter": "image", "maximum": "2", "dimensions": {"quality": "high"}},
            {"meter": "input_token", "maximum": "1000", "dimensions": {}},
        ],
    }


def _quote():
    return quote_media_scenario(
        parse_quote_request(_scenario()),
        prices=parse_price_catalog(_prices()),
        media=load_media_catalog(),
    )


def _store(tmp_path: Path) -> SQLiteBudgetReservationStore:
    return SQLiteBudgetReservationStore(tmp_path / "offline-reservations.db")


def _request(key: str = "req-1", *, budget: str = "sandbox") -> ReservationRequest:
    return ReservationRequest(budget, key, _quote(), datetime(2026, 11, 8, 16, tzinfo=UTC))


def test_port_contract_and_transactional_reservation(tmp_path: Path) -> None:
    store = _store(tmp_path)
    budget = store.create_budget("sandbox", Money(Decimal("1.000"), "USD"))
    assert budget.remaining.amount == Decimal("1.000")
    record = store.reserve(_request())
    assert record.reservation.status == ReservationState.PENDING
    assert record.reservation.amount.amount == Decimal("0.051")
    assert record.ledger.reserved.amount == Decimal("0.051")
    assert record.ledger.remaining.amount == Decimal("0.949")
    result = reservation_to_dict(record)
    assert result["offline_sandbox_only"] is True
    assert result["spend_bound_verified"] is False
    assert result["live_authorized"] is False
    assert result["atomic_budget_reserved"] is True


def test_idempotency_replays_without_double_reservation_even_after_reload(tmp_path: Path) -> None:
    store = _store(tmp_path)
    store.create_budget("sandbox", Money(Decimal("1"), "USD"))
    request = _request()
    first = store.reserve(request)
    second = _store(tmp_path).reserve(request)
    assert second.replayed
    assert second.reservation.reservation_id == first.reservation.reservation_id
    assert second.ledger.reserved == first.ledger.reserved
    assert not first.replayed


def test_idempotency_detects_payload_changes_even_if_total_is_same(tmp_path: Path) -> None:
    store = _store(tmp_path)
    store.create_budget("sandbox", Money(Decimal("1"), "USD"))
    original = _request()
    store.reserve(original)
    altered = replace(original, purpose="another_sandbox")
    assert quote_fingerprint(original) != quote_fingerprint(altered)
    with pytest.raises(FinOpsError, match="reservation_idempotency_conflict"):
        store.reserve(altered)
    assert store.get_budget("sandbox").reserved.amount == Decimal("0.051")


def test_insufficient_budget_never_leaks_partial_reservation(tmp_path: Path) -> None:
    store = _store(tmp_path)
    store.create_budget("sandbox", Money(Decimal("0.05"), "USD"))
    with pytest.raises(FinOpsError, match="insufficient_budget"):
        store.reserve(_request())
    state = store.get_budget("sandbox")
    assert state.reserved.amount == Decimal(0)
    assert state.remaining.amount == Decimal("0.05")


def test_budget_limit_creation_is_idempotent_but_not_mutable(tmp_path: Path) -> None:
    store = _store(tmp_path)
    limit = Money(Decimal("10"), "USD")
    store.create_budget("sandbox", limit)
    assert store.create_budget("sandbox", limit).limit == limit
    with pytest.raises(FinOpsError, match="budget_already_exists"):
        store.create_budget("sandbox", Money(Decimal("11"), "USD"))


def test_missing_budget_and_currency_mismatch_are_fail_closed(tmp_path: Path) -> None:
    store = _store(tmp_path)
    with pytest.raises(FinOpsError, match="budget_not_found"):
        store.reserve(_request())
    store.create_budget("sandbox", Money(Decimal("10"), "EUR"))
    with pytest.raises(FinOpsError, match="budget_currency_mismatch"):
        store.reserve(_request())


def test_quote_must_be_priced_and_not_expired_at_reservation(tmp_path: Path) -> None:
    quote = _quote()
    bad = replace(quote, amount=None, status="unknown")
    with pytest.raises(FinOpsError, match="quote_not_reservable_offline"):
        ReservationRequest("sandbox", "x", bad, AT)
    expired = replace(quote, valid_until=datetime(2026, 11, 8, 15, tzinfo=UTC))
    with pytest.raises(FinOpsError, match="stale_quote"):
        ReservationRequest("sandbox", "x", expired, datetime(2026, 11, 8, 16, tzinfo=UTC))
    with pytest.raises(FinOpsError, match="reservation_before_quote"):
        ReservationRequest("sandbox", "x", quote, datetime(2026, 11, 7, tzinfo=UTC))


def test_status_dispute_keeps_funds_locked_and_blocks_release(tmp_path: Path) -> None:
    store = _store(tmp_path)
    store.create_budget("sandbox", Money(Decimal("1"), "USD"))
    pending = store.reserve(_request())
    rid = pending.reservation.reservation_id
    disputed = store.dispute(rid)
    assert disputed.reservation.status is ReservationState.DISPUTED
    assert disputed.ledger.reserved.amount == Decimal("0.051")
    assert store.dispute(rid).replayed
    with pytest.raises(FinOpsError, match="invalid_reservation_transition"):
        store.release_undispatched(rid)
    assert store.get_budget("sandbox").reserved.amount == Decimal("0.051")


def test_release_undispatched_is_idempotent_and_terminal(tmp_path: Path) -> None:
    store = _store(tmp_path)
    store.create_budget("sandbox", Money(Decimal("1"), "USD"))
    rid = store.reserve(_request()).reservation.reservation_id
    released = store.release_undispatched(rid)
    assert released.reservation.status is ReservationState.RELEASED_UNDISPATCHED
    assert released.ledger.reserved.amount == 0
    assert released.ledger.remaining.amount == 1
    assert store.release_undispatched(rid).replayed
    with pytest.raises(FinOpsError, match="invalid_reservation_transition"):
        store.settle_simulated(rid, Decimal("0.01"))


def test_simulated_settlement_moves_reserved_to_spent_exactly(tmp_path: Path) -> None:
    store = _store(tmp_path)
    store.create_budget("sandbox", Money(Decimal("1"), "USD"))
    rid = store.reserve(_request()).reservation.reservation_id
    result = store.settle_simulated(rid, Decimal("0.041"))
    assert result.reservation.status is ReservationState.SETTLED_SIMULATED
    assert result.ledger.reserved.amount == 0
    assert result.ledger.spent.amount == Decimal("0.041")
    assert result.ledger.remaining.amount == Decimal("0.959")
    assert store.settle_simulated(rid, Decimal("0.041")).replayed
    with pytest.raises(FinOpsError, match="conflicting_simulated_settlement"):
        store.settle_simulated(rid, Decimal("0.042"))
    with pytest.raises(FinOpsError, match="invalid_reservation_transition"):
        store.release_undispatched(rid)


@pytest.mark.parametrize("amount", [Decimal("-1"), Decimal("NaN"), Decimal("0.052"), Decimal("Infinity")])
def test_simulated_settlement_cannot_exceed_reserved_or_use_invalid_amount(
    tmp_path: Path, amount: Decimal,
) -> None:
    store = _store(tmp_path)
    store.create_budget("sandbox", Money(Decimal("1"), "USD"))
    rid = store.reserve(_request()).reservation.reservation_id
    with pytest.raises(FinOpsError, match="invalid_simulated_settlement"):
        store.settle_simulated(rid, amount)
    assert store.get_budget("sandbox").reserved.amount == Decimal("0.051")


def test_two_thread_contention_on_same_budget_serializes(tmp_path: Path) -> None:
    database = tmp_path / "contended.db"
    store = SQLiteBudgetReservationStore(database)
    store.create_budget("sandbox", Money(Decimal("0.051"), "USD"))
    barrier = threading.Barrier(2)

    def attempt(key: str) -> str:
        local = SQLiteBudgetReservationStore(database)
        barrier.wait(timeout=10)
        try:
            local.reserve(_request(key))
            return "reserved"
        except FinOpsError as exc:
            return str(exc)

    with ThreadPoolExecutor(max_workers=2) as pool:
        answers = list(pool.map(attempt, ("first", "second")))
    assert sorted(answers) == ["insufficient_budget", "reserved"]
    assert store.get_budget("sandbox").reserved.amount == Decimal("0.051")


def test_cli_offline_reserve_reload_and_transitions(tmp_path: Path) -> None:
    runner = CliRunner()
    database = tmp_path / "sandbox.db"
    req = tmp_path / "request.json"
    tariffs = tmp_path / "synthetic-prices.json"
    req.write_text(json.dumps(_scenario()), encoding="utf-8")
    tariffs.write_text(json.dumps(_prices()), encoding="utf-8")
    common = ["--database", str(database)]
    created = runner.invoke(app, [
        "finops", "budget", "create", *common,
        "--budget-id", "sandbox", "--limit", "1.0", "--currency", "USD",
    ])
    assert created.exit_code == 0, created.output
    command = [
        "finops", "reserve", *common, "--request", str(req),
        "--pricing-catalog", str(tariffs), "--budget-id", "sandbox",
        "--idempotency-key", "same-req",
    ]
    reserve = runner.invoke(app, command)
    assert reserve.exit_code == 0, reserve.output
    first = json.loads(reserve.output)
    assert first["status"] == "pending"
    assert first["reserved"] == {"value": "0.051", "currency": "USD"}
    assert first["live_authorized"] is False
    replay = runner.invoke(app, command)
    assert replay.exit_code == 0, replay.output
    assert json.loads(replay.output)["replayed"] is True
    rid = first["reservation_id"]
    inspect = runner.invoke(app, [
        "finops", "reservation", "inspect", *common, "--reservation-id", rid,
    ])
    assert inspect.exit_code == 0
    assert json.loads(inspect.output)["status"] == "pending"
    release_without_confirmation = runner.invoke(app, [
        "finops", "reservation", "release", *common, "--reservation-id", rid,
    ])
    assert release_without_confirmation.exit_code == 3
    released = runner.invoke(app, [
        "finops", "reservation", "release", *common, "--reservation-id", rid,
        "--confirm-no-dispatch",
    ])
    assert released.exit_code == 0, released.output
    assert json.loads(released.output)["status"] == "released_undispatched"
    budget = runner.invoke(app, [
        "finops", "budget", "inspect", *common, "--budget-id", "sandbox",
    ])
    assert budget.exit_code == 0
    assert json.loads(budget.output)["reserved"] == "0.000"


def test_cli_missing_tariff_does_not_write_any_reservation(tmp_path: Path) -> None:
    runner = CliRunner()
    database = tmp_path / "sandbox.db"
    request = tmp_path / "quote.json"
    request.write_text(json.dumps(_scenario()), encoding="utf-8")
    command = [
        "finops", "reserve", "--request", str(request),
        "--database", str(database), "--budget-id", "sandbox",
        "--idempotency-key", "test",
    ]
    result = runner.invoke(app, command)
    assert result.exit_code == 3
    payload = json.loads(result.output)
    assert payload["status"] == "unknown"
    assert payload["live_authorized"] is False
    assert not database.exists()


def test_finops_cli_is_exposed_as_real_command() -> None:
    assert finops_app is not None



def test_dispatch_intent_persists_across_crash_like_reload_and_blocks_release(
    tmp_path: Path,
) -> None:
    database = tmp_path / "durable.db"
    store = SQLiteBudgetReservationStore(database)
    store.create_budget("sandbox", Money(Decimal("1"), "USD"))
    rid = store.reserve(_request()).reservation.reservation_id
    at = datetime(2026, 11, 8, 17, tzinfo=UTC)
    intent = store.record_dispatch_intent(rid, "attempt-001", at=at)
    assert intent.reservation.status is ReservationState.DISPATCH_INTENT_RECORDED
    assert intent.reservation.dispatch_attempt_key == "attempt-001"
    assert intent.reservation.dispatch_intent_at == at
    assert intent.ledger.reserved.amount == Decimal("0.051")
    assert reservation_to_dict(intent)["atomic_budget_reserved"] is True
    assert reservation_to_dict(intent)["live_authorized"] is False
    del store
    restarted = SQLiteBudgetReservationStore(database)
    assert restarted.get_reservation(rid).reservation.status is ReservationState.DISPATCH_INTENT_RECORDED
    assert restarted.get_budget("sandbox").reserved.amount == Decimal("0.051")
    with pytest.raises(FinOpsError, match="invalid_reservation_transition"):
        restarted.release_undispatched(rid)
    assert restarted.record_dispatch_intent(rid, "attempt-001", at=at).replayed
    with pytest.raises(FinOpsError, match="dispatch_intent_conflict"):
        restarted.record_dispatch_intent(rid, "attempt-002", at=at)


def test_dispatch_intent_then_dispute_retains_hold_and_correlation(tmp_path: Path) -> None:
    store = _store(tmp_path)
    store.create_budget("sandbox", Money(Decimal("1"), "USD"))
    rid = store.reserve(_request()).reservation.reservation_id
    store.record_dispatch_intent(rid, "demo-001", at=datetime(2026, 11, 8, 17, tzinfo=UTC))
    result = store.dispute(rid)
    assert result.reservation.status is ReservationState.DISPUTED
    assert result.reservation.dispatch_attempt_key == "demo-001"
    assert result.ledger.reserved.amount == Decimal("0.051")
    assert store.dispute(rid).replayed
    with pytest.raises(FinOpsError, match="invalid_reservation_transition"):
        store.release_undispatched(rid)
    with pytest.raises(FinOpsError, match="invalid_reservation_transition"):
        store.record_dispatch_intent(rid, "demo-001", at=datetime(2026, 11, 8, 17, tzinfo=UTC))


def test_simulated_settlement_from_intent_preserves_marker(tmp_path: Path) -> None:
    store = _store(tmp_path)
    store.create_budget("sandbox", Money(Decimal("1"), "USD"))
    rid = store.reserve(_request()).reservation.reservation_id
    store.record_dispatch_intent(rid, "demo-001", at=datetime(2026, 11, 8, 17, tzinfo=UTC))
    settled = store.settle_simulated(rid, Decimal("0.04"))
    assert settled.reservation.status is ReservationState.SETTLED_SIMULATED
    assert settled.reservation.dispatch_attempt_key == "demo-001"
    assert settled.ledger.spent.amount == Decimal("0.04")
    assert settled.ledger.reserved.amount == 0
    with pytest.raises(FinOpsError, match="invalid_reservation_transition"):
        store.release_undispatched(rid)


def test_same_dispatch_attempt_key_cannot_be_reused_across_reservations(
    tmp_path: Path,
) -> None:
    store = _store(tmp_path)
    store.create_budget("sandbox", Money(Decimal("1"), "USD"))
    a = store.reserve(_request("first")).reservation.reservation_id
    b = store.reserve(_request("second")).reservation.reservation_id
    at = datetime(2026, 11, 8, 17, tzinfo=UTC)
    store.record_dispatch_intent(a, "shared-attempt", at=at)
    with pytest.raises(FinOpsError, match="dispatch_attempt_key_reused"):
        store.record_dispatch_intent(b, "shared-attempt", at=at)
    assert store.get_reservation(b).reservation.status is ReservationState.PENDING
    assert store.get_budget("sandbox").reserved.amount == Decimal("0.102")


@pytest.mark.parametrize("attempt", ["", "a key", "a*bad", "x" * 193])
def test_invalid_attempt_key_is_rejected_without_change(tmp_path: Path, attempt: str) -> None:
    store = _store(tmp_path)
    store.create_budget("sandbox", Money(Decimal("1"), "USD"))
    rid = store.reserve(_request()).reservation.reservation_id
    with pytest.raises(FinOpsError, match="invalid_dispatch_attempt_key"):
        store.record_dispatch_intent(rid, attempt, at=datetime(2026, 11, 8, 17, tzinfo=UTC))
    assert store.get_reservation(rid).reservation.status is ReservationState.PENDING


def test_dispatch_intent_rejects_non_timezone_aware_and_backdated_times(
    tmp_path: Path,
) -> None:
    store = _store(tmp_path)
    store.create_budget("sandbox", Money(Decimal("1"), "USD"))
    rid = store.reserve(_request()).reservation.reservation_id
    with pytest.raises(FinOpsError, match="invalid_dispatch_intent_time"):
        store.record_dispatch_intent(rid, "attempt", at=datetime(2026, 11, 8, 17))
    with pytest.raises(FinOpsError, match="dispatch_intent_before_reservation"):
        store.record_dispatch_intent(rid, "attempt", at=datetime(2026, 11, 7, tzinfo=UTC))
    assert store.get_reservation(rid).reservation.status is ReservationState.PENDING


def test_two_contending_dispatch_attempts_have_only_one_winner(tmp_path: Path) -> None:
    database = tmp_path / "race.db"
    store = SQLiteBudgetReservationStore(database)
    store.create_budget("sandbox", Money(Decimal("1"), "USD"))
    rid = store.reserve(_request()).reservation.reservation_id
    barrier = threading.Barrier(2)
    at = datetime(2026, 11, 8, 17, tzinfo=UTC)

    def attempt(key: str) -> str:
        local = SQLiteBudgetReservationStore(database)
        barrier.wait(timeout=10)
        try:
            local.record_dispatch_intent(rid, key, at=at)
            return "intent_recorded"
        except FinOpsError as exc:
            return str(exc)

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(attempt, ("attempt-A", "attempt-B")))
    assert sorted(outcomes) == ["dispatch_intent_conflict", "intent_recorded"]
    assert store.get_budget("sandbox").reserved.amount == Decimal("0.051")


def test_old_g3_database_schema_is_extended_without_overwriting_reservations(
    tmp_path: Path,
) -> None:
    db = tmp_path / "legacy-g3.db"
    with sqlite3.connect(db) as conn:
        conn.executescript(
            "CREATE TABLE finops_budgets (budget_id TEXT PRIMARY KEY, "
            "currency TEXT NOT NULL, limit_amount TEXT NOT NULL, "
            "spent_amount TEXT NOT NULL, reserved_amount TEXT NOT NULL);"
            "CREATE TABLE finops_reservations (reservation_id TEXT PRIMARY KEY, "
            "budget_id TEXT NOT NULL, idempotency_key TEXT NOT NULL, "
            "fingerprint TEXT NOT NULL, amount TEXT NOT NULL, "
            "currency TEXT NOT NULL, created_at TEXT NOT NULL, "
            "purpose TEXT NOT NULL, status TEXT NOT NULL, settled_amount TEXT, "
            "UNIQUE (budget_id, idempotency_key), "
            "FOREIGN KEY (budget_id) REFERENCES finops_budgets(budget_id));"
        )
        conn.execute(
            "INSERT INTO finops_budgets VALUES ('sandbox', 'USD', '10.000', '0', '0.051')"
        )
        conn.execute(
            "INSERT INTO finops_reservations VALUES "
            "(?, 'sandbox', 'existing', ?, '0.051', 'USD', ?, "
            "'offline_sandbox', 'pending', NULL)",
            ("resv_legacy", "f" * 64, datetime(2026, 11, 8, 16, tzinfo=UTC).isoformat()),
        )
    store = SQLiteBudgetReservationStore(db)
    assert store.get_reservation("resv_legacy").reservation.status is ReservationState.PENDING
    assert store.get_budget("sandbox").reserved.amount == Decimal("0.051")
    intent = store.record_dispatch_intent(
        "resv_legacy", "attempt-old", at=datetime(2026, 11, 8, 17, tzinfo=UTC),
    )
    assert intent.reservation.status is ReservationState.DISPATCH_INTENT_RECORDED
    assert intent.ledger.reserved.amount == Decimal("0.051")


def test_cli_simulated_dispatch_intent_never_emits_remote_authorization(
    tmp_path: Path,
) -> None:
    runner = CliRunner()
    database = tmp_path / "demo.db"
    req = tmp_path / "request.json"
    tariff = tmp_path / "synthetic.json"
    req.write_text(json.dumps(_scenario()), encoding="utf-8")
    tariff.write_text(json.dumps(_prices()), encoding="utf-8")
    common = ["--database", str(database)]
    created = runner.invoke(app, [
        "finops", "budget", "create", *common, "--budget-id", "sandbox",
        "--limit", "1", "--currency", "USD",
    ])
    assert created.exit_code == 0, created.output
    reservation_args = [
        "finops", "reserve", *common, "--budget-id", "sandbox",
        "--idempotency-key", "demo-key", "--request", str(req),
        "--pricing-catalog", str(tariff),
    ]
    reserve = runner.invoke(app, reservation_args)
    assert reserve.exit_code == 0, reserve.output
    rid = json.loads(reserve.output)["reservation_id"]
    intent_args = [
        "finops", "reservation", "simulate-dispatch-intent", *common,
        "--reservation-id", rid, "--attempt-key", "attempt-demo",
    ]
    result = runner.invoke(app, intent_args)
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["status"] == "dispatch_intent_recorded"
    assert payload["dispatch_attempt_key"] == "attempt-demo"
    assert payload["reserved"]["value"] == "0.051"
    assert payload["live_authorized"] is False
    assert payload["spend_bound_verified"] is False
    assert json.loads(runner.invoke(app, intent_args).output)["replayed"] is True
    replay = runner.invoke(app, reservation_args)
    assert replay.exit_code == 3
    assert json.loads(replay.output)["status"] == "dispatch_intent_recorded"
    release = runner.invoke(app, [
        "finops", "reservation", "release", *common,
        "--reservation-id", rid, "--confirm-no-dispatch",
    ])
    assert release.exit_code == 3
    assert json.loads(release.output)["reason"] == "invalid_reservation_transition"
    after = runner.invoke(app, [
        "finops", "budget", "inspect", *common, "--budget-id", "sandbox",
    ])
    assert json.loads(after.output)["reserved"] == "0.051"


def test_cli_replay_of_released_reservation_is_not_success(tmp_path: Path) -> None:
    runner = CliRunner()
    db = tmp_path / "sandbox.db"
    path = tmp_path / "quote.json"
    price = tmp_path / "price.json"
    path.write_text(json.dumps(_scenario()), encoding="utf-8")
    price.write_text(json.dumps(_prices()), encoding="utf-8")
    common = ["--database", str(db)]
    assert runner.invoke(app, ["finops", "budget", "create", *common,
                               "--budget-id", "sandbox", "--limit", "1"]).exit_code == 0
    args = [
        "finops", "reserve", *common, "--budget-id", "sandbox",
        "--idempotency-key", "r", "--request", str(path),
        "--pricing-catalog", str(price),
    ]
    first = runner.invoke(app, args)
    assert first.exit_code == 0, first.output
    rid = json.loads(first.output)["reservation_id"]
    assert runner.invoke(app, [
        "finops", "reservation", "release", *common,
        "--reservation-id", rid, "--confirm-no-dispatch",
    ]).exit_code == 0
    replay = runner.invoke(app, args)
    assert replay.exit_code == 3
    assert json.loads(replay.output)["status"] == "released_undispatched"
    assert SQLiteBudgetReservationStore(db).get_budget("sandbox").reserved.amount == 0
