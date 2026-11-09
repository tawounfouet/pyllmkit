"""M2-G4.2 durable synthetic invoice registry: atomicity, history and audit."""

from __future__ import annotations

import json
import sqlite3
import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pytest
from typer.testing import CliRunner

from pyllmkit.adapters.cli.finops_invoice import load_synthetic_invoice_statement
from pyllmkit.adapters.cli.finops_invoice_registry import SQLiteSyntheticInvoiceRegistry
from pyllmkit.adapters.cli.main import app
from pyllmkit.domain.finops import FinOpsError, Money
from pyllmkit.domain.finops.invoice_reconciliation import SyntheticInvoiceStatement
from pyllmkit.domain.finops.invoice_registry import (
    GENESIS_HASH,
    InvoiceImportRequest,
    audit_report_to_dict,
    canonical_statement,
    imported_invoice_to_dict,
    invoice_import_fingerprint,
)

AT = datetime(2026, 11, 9, 12, tzinfo=UTC)
SAMPLE = Path("examples/finops/synthetic-invoice.json")
SCENARIO = Path("examples/finops/scenario.json")
PRICES = Path("examples/finops/synthetic-prices.json")


def _statement() -> SyntheticInvoiceStatement:
    return load_synthetic_invoice_statement(SAMPLE)


def _store(tmp_path: Path) -> SQLiteSyntheticInvoiceRegistry:
    return SQLiteSyntheticInvoiceRegistry(tmp_path / "g42-invoices.db")


def _request(
    *,
    scope: str = "sandbox",
    key: str = "initial-001",
    revision: int = 1,
    supersedes: int | None = None,
    statement: SyntheticInvoiceStatement | None = None,
    at: datetime = AT,
) -> InvoiceImportRequest:
    return InvoiceImportRequest(
        scope, key, revision, supersedes,
        _statement() if statement is None else statement, at,
    )


def _corrected_statement() -> SyntheticInvoiceStatement:
    old = _statement()
    lines = tuple(
        replace(line, amount=Money(Decimal("0.006"), "USD"))
        if line.kind.value == "credit" else line
        for line in old.lines
    )
    return replace(old, lines=lines)


def test_first_import_is_atomic_durable_and_has_local_hash_chain(tmp_path: Path) -> None:
    store = _store(tmp_path)
    request = _request()
    first = store.import_synthetic(request)
    assert first.replayed is False
    assert first.invoice.revision == 1
    assert first.invoice.supersedes is None
    assert first.invoice.fingerprint == invoice_import_fingerprint(request)
    assert canonical_statement(first.invoice.statement) == canonical_statement(_statement())
    assert first.invoice.audit_sequence == 1
    assert first.invoice.audit_hash != GENESIS_HASH
    projection = imported_invoice_to_dict(first)
    assert projection["source_kind"] == "synthetic_fixture"
    assert projection["provider_invoice_verified"] is False
    assert projection["ledger_mutated"] is False
    assert projection["live_authorized"] is False
    restarted = _store(tmp_path)
    assert restarted.inspect("sandbox", _statement().statement_id) == first.invoice
    audit = restarted.audit("sandbox")
    assert audit.event_count == 1
    assert audit.revision_count == 1
    assert audit.head_hash == first.invoice.audit_hash
    assert audit_report_to_dict(audit)["external_trust_anchor"] is False


def test_import_key_is_idempotent_and_does_not_append_audit(tmp_path: Path) -> None:
    store = _store(tmp_path)
    first = store.import_synthetic(_request())
    retry = _store(tmp_path).import_synthetic(_request(at=AT + timedelta(days=1)))
    assert retry.replayed is True
    assert retry.invoice == first.invoice
    assert store.audit("sandbox").event_count == 1


def test_semantic_line_order_does_not_change_fingerprint(tmp_path: Path) -> None:
    statement = _statement()
    inverted = replace(statement, lines=tuple(reversed(statement.lines)))
    assert canonical_statement(statement) == canonical_statement(inverted)
    store = _store(tmp_path)
    store.import_synthetic(_request(statement=statement))
    replay = store.import_synthetic(_request(statement=inverted))
    assert replay.replayed is True
    assert store.audit("sandbox").event_count == 1


def test_idempotency_key_reused_with_modified_content_fails_closed(tmp_path: Path) -> None:
    store = _store(tmp_path)
    store.import_synthetic(_request())
    with pytest.raises(FinOpsError, match="invoice_import_idempotency_conflict"):
        store.import_synthetic(_request(statement=_corrected_statement()))
    assert store.audit("sandbox").event_count == 1


def test_revision_conflict_when_different_key_claims_existing_revision(tmp_path: Path) -> None:
    store = _store(tmp_path)
    store.import_synthetic(_request())
    with pytest.raises(FinOpsError, match="invoice_revision_already_imported"):
        store.import_synthetic(_request(key="different-key"))
    assert store.audit("sandbox").event_count == 1


def test_correction_is_immutable_revision_two_and_preserves_prior_credit(
    tmp_path: Path,
) -> None:
    store = _store(tmp_path)
    first = store.import_synthetic(_request())
    second = store.import_synthetic(_request(
        key="correction-002", revision=2, supersedes=1,
        statement=_corrected_statement(),
    ))
    assert second.invoice.revision == 2
    assert second.invoice.supersedes == 1
    assert second.invoice.audit_sequence == 2
    assert first.invoice.audit_hash != second.invoice.audit_hash
    assert store.inspect("sandbox", _statement().statement_id).revision == 2
    history = store.history("sandbox", _statement().statement_id)
    assert tuple(item.revision for item in history) == (1, 2)
    first_credit = next(item for item in history[0].statement.lines if item.kind.value == "credit")
    second_credit = next(item for item in history[1].statement.lines if item.kind.value == "credit")
    assert first_credit.amount.amount == Decimal("0.005")
    assert second_credit.amount.amount == Decimal("0.006")
    assert store.audit("sandbox").event_count == 2
    # A historical retry is still an idempotent replay.
    assert store.import_synthetic(_request()).replayed


@pytest.mark.parametrize(
    ("revision", "supersedes", "message"),
    [
        (2, None, "invoice_supersedes_latest_required"),
        (3, 1, "invoice_supersedes_latest_required"),
        (1, 1, "invoice_revision_already_imported"),
    ],
)
def test_corrections_require_next_revision_and_explicit_parent(
    tmp_path: Path, revision: int, supersedes: int | None, message: str,
) -> None:
    store = _store(tmp_path)
    store.import_synthetic(_request())
    with pytest.raises(FinOpsError, match=message):
        store.import_synthetic(_request(
            key=f"new-{revision}-{supersedes}",
            revision=revision, supersedes=supersedes,
            statement=_corrected_statement(),
        ))


def test_initial_revision_must_be_one(tmp_path: Path) -> None:
    with pytest.raises(FinOpsError, match="invoice_initial_revision_must_be_one"):
        _store(tmp_path).import_synthetic(_request(
            revision=2, supersedes=1,
        ))


def test_unchanged_revision_not_allowed_even_with_new_key(tmp_path: Path) -> None:
    store = _store(tmp_path)
    store.import_synthetic(_request())
    with pytest.raises(FinOpsError, match="invoice_revision_unchanged"):
        store.import_synthetic(_request(key="unnecessary-r2", revision=2, supersedes=1))


@pytest.mark.parametrize("field", [
    "model_id", "api_provider", "billing_provider", "deployment_channel", "currency",
])
def test_invoice_correction_cannot_change_billing_route(
    tmp_path: Path, field: str,
) -> None:
    store = _store(tmp_path)
    store.import_synthetic(_request())
    corrected = _corrected_statement()
    if field == "currency":
        wrong = replace(
            corrected, currency="EUR", lines=tuple(
                replace(item, amount=Money(item.amount.amount, "EUR"))
                for item in corrected.lines
            ),
        )
    else:
        wrong = replace(corrected, **{field: "other"})
    with pytest.raises(FinOpsError, match="invoice_revision_route_changed"):
        store.import_synthetic(_request(
            key="different-route", revision=2, supersedes=1, statement=wrong,
        ))
    assert store.audit("sandbox").event_count == 1


def test_two_scopes_with_same_key_and_statement_have_independent_chains(
    tmp_path: Path,
) -> None:
    store = _store(tmp_path)
    a = store.import_synthetic(_request(scope="tenant-one"))
    b = store.import_synthetic(_request(scope="tenant-two"))
    assert a.invoice.scope_id != b.invoice.scope_id
    assert a.invoice.fingerprint != b.invoice.fingerprint
    for scope in ("tenant-one", "tenant-two"):
        assert store.audit(scope).event_count == 1
    assert store.audit("empty-space").event_count == 0
    assert store.audit("empty-space").head_hash == GENESIS_HASH


def test_no_rollback_leaks_when_audit_insert_fails(tmp_path: Path) -> None:
    db = tmp_path / "g42-invoices.db"
    store = SQLiteSyntheticInvoiceRegistry(db)
    with sqlite3.connect(db) as conn:
        conn.execute(
            "CREATE TRIGGER stop_audit BEFORE INSERT ON finops_synthetic_invoice_audit "
            "BEGIN SELECT RAISE(ABORT,'simulated_crash'); END"
        )
    with pytest.raises(sqlite3.IntegrityError, match="simulated_crash"):
        store.import_synthetic(_request())
    assert store.audit("sandbox").event_count == 0
    assert store.history("sandbox", _statement().statement_id) == ()
    with sqlite3.connect(db) as conn:
        conn.execute("DROP TRIGGER stop_audit")
    assert store.import_synthetic(_request()).invoice.audit_sequence == 1


def test_update_and_delete_triggers_prevent_accidental_history_edits(
    tmp_path: Path,
) -> None:
    db = tmp_path / "g42-invoices.db"
    store = SQLiteSyntheticInvoiceRegistry(db)
    store.import_synthetic(_request())
    for table in ("finops_synthetic_invoice_versions", "finops_synthetic_invoice_audit"):
        with sqlite3.connect(db) as conn:
            with pytest.raises(sqlite3.IntegrityError, match="immutable_synthetic_invoice"):
                conn.execute(f"DELETE FROM {table}")
    assert store.audit("sandbox").event_count == 1


def test_audit_detects_snapshot_or_chain_corruption(tmp_path: Path) -> None:
    db = tmp_path / "g42-invoices.db"
    store = SQLiteSyntheticInvoiceRegistry(db)
    store.import_synthetic(_request())
    with sqlite3.connect(db) as conn:
        conn.execute("DROP TRIGGER finops_synthetic_invoice_versions_no_update")
        conn.execute(
            "UPDATE finops_synthetic_invoice_versions SET snapshot_json='{}'"
        )
    with pytest.raises(FinOpsError, match="invoice_audit_integrity_failure"):
        store.audit("sandbox")
    with pytest.raises(FinOpsError, match="invoice_audit_integrity_failure"):
        store.inspect("sandbox", _statement().statement_id)
    with pytest.raises(FinOpsError, match="invoice_audit_integrity_failure"):
        store.import_synthetic(_request(key="another"))


def test_concurrent_same_key_has_one_import_and_one_replay(tmp_path: Path) -> None:
    database = tmp_path / "race.db"
    store = SQLiteSyntheticInvoiceRegistry(database)
    barrier = threading.Barrier(2)

    def call() -> bool:
        local = SQLiteSyntheticInvoiceRegistry(database)
        barrier.wait(timeout=10)
        return local.import_synthetic(_request()).replayed

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(lambda _: call(), range(2)))
    assert sorted(outcomes) == [False, True]
    assert store.audit("sandbox").event_count == 1


def test_concurrent_corrections_with_different_keys_allow_only_one(tmp_path: Path) -> None:
    database = tmp_path / "race-revisions.db"
    store = SQLiteSyntheticInvoiceRegistry(database)
    store.import_synthetic(_request())
    barrier = threading.Barrier(2)

    def call(key: str) -> str:
        local = SQLiteSyntheticInvoiceRegistry(database)
        barrier.wait(timeout=10)
        try:
            local.import_synthetic(_request(
                key=key, revision=2, supersedes=1,
                statement=_corrected_statement(),
            ))
            return "imported"
        except FinOpsError as exc:
            return str(exc)

    with ThreadPoolExecutor(max_workers=2) as pool:
        statuses = list(pool.map(call, ("left", "right")))
    assert sorted(statuses) == ["imported", "invoice_revision_already_imported"]
    assert store.audit("sandbox").event_count == 2


def test_cli_import_inspect_history_audit_and_reconcile_imported(
    tmp_path: Path,
) -> None:
    db = tmp_path / "cli-registry.db"
    runner = CliRunner()
    common = ["--database", str(db), "--scope-id", "sandbox"]
    imported = runner.invoke(app, [
        "finops", "invoice", "import-synthetic", *common,
        "--statement", str(SAMPLE), "--import-key", "example-001",
        "--revision", "1",
    ])
    assert imported.exit_code == 0, imported.output
    out = json.loads(imported.output)
    assert out["status"] == "imported_synthetic"
    assert out["provider_invoice_verified"] is False
    assert out["ledger_mutated"] is False
    assert out["live_authorized"] is False
    again = runner.invoke(app, [
        "finops", "invoice", "import-synthetic", *common,
        "--statement", str(SAMPLE), "--import-key", "example-001",
        "--revision", "1",
    ])
    assert again.exit_code == 0, again.output
    assert json.loads(again.output)["replayed"] is True
    statement_id = _statement().statement_id
    for verb in ("inspect", "history"):
        query = runner.invoke(app, [
            "finops", "invoice", verb, *common, "--statement-id", statement_id,
        ])
        assert query.exit_code == 0, query.output
    audit = runner.invoke(app, ["finops", "invoice", "audit", *common])
    assert audit.exit_code == 0, audit.output
    assert json.loads(audit.output)["event_count"] == 1
    reconciliation = runner.invoke(app, [
        "finops", "invoice", "reconcile-imported", *common,
        "--statement-id", statement_id,
        "--request", str(SCENARIO), "--pricing-catalog", str(PRICES),
        "--provider-request-id", "fake-provider-call-001",
    ])
    assert reconciliation.exit_code == 0, reconciliation.output
    report = json.loads(reconciliation.output)
    assert report["status"] == "matched_synthetic"
    assert report["invoice_fingerprint"] == out["fingerprint"]
    assert report["provider_invoice_verified"] is False
    assert report["budget_ledger_mutated"] is False


def test_cli_invalid_revision_and_missing_snapshot_fail_closed(tmp_path: Path) -> None:
    runner = CliRunner()
    db = tmp_path / "bad.db"
    bad = runner.invoke(app, [
        "finops", "invoice", "import-synthetic", "--database", str(db),
        "--scope-id", "sandbox", "--statement", str(SAMPLE),
        "--import-key", "bad", "--revision", "2",
    ])
    assert bad.exit_code == 3, bad.output
    assert json.loads(bad.output)["reason"] == "invoice_initial_revision_must_be_one"
    missing = runner.invoke(app, [
        "finops", "invoice", "inspect", "--database", str(db),
        "--scope-id", "sandbox", "--statement-id", "not-here",
    ])
    assert missing.exit_code == 3, missing.output
    assert json.loads(missing.output)["live_authorized"] is False


def test_import_rejects_untrusted_statement_before_db_touch(tmp_path: Path) -> None:
    runner = CliRunner()
    db = tmp_path / "should-not-be-created.db"
    input_path = tmp_path / "bad-statement.json"
    payload = json.loads(SAMPLE.read_text(encoding="utf-8"))
    payload["source_kind"] = "provider_verified"
    input_path.write_text(json.dumps(payload), encoding="utf-8")
    result = runner.invoke(app, [
        "finops", "invoice", "import-synthetic", "--database", str(db),
        "--scope-id", "sandbox", "--statement", str(input_path),
        "--revision", "1", "--import-key", "bad-source",
    ])
    assert result.exit_code == 3, result.output
    assert not db.exists()
