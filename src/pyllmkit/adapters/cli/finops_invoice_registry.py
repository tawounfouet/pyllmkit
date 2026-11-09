"""G4.2 durable, append-only local registry of *synthetic* invoice revisions.

SQLite BEGIN IMMEDIATE serializes local writers. The SHA-256 chain is local
integrity evidence only, not a signature, an external anchor or a real invoice.
No G3 ledger, secrets, HTTP or provider APIs are accessed.
"""

from __future__ import annotations

import sqlite3
from contextlib import closing
from datetime import datetime
from pathlib import Path

from pyllmkit.adapters.cli.finops_invoice import parse_synthetic_invoice_statement_json
from pyllmkit.domain.finops import FinOpsError
from pyllmkit.domain.finops.invoice_registry import (
    GENESIS_HASH,
    ImportedInvoice,
    InvoiceAuditReport,
    InvoiceImportRequest,
    InvoiceImportResult,
    _id,
    _revision,
    audit_entry_hash,
    canonical_statement,
    invoice_import_fingerprint,
)


class SQLiteSyntheticInvoiceRegistry:
    """Local, transactional invoice revision registry, never a trusted biller."""

    def __init__(self, database: Path) -> None:
        if type(database) is not Path or str(database) == ":memory:":
            raise FinOpsError("invalid_invoice_registry_database")
        self._database = database
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self._database), isolation_level=None, timeout=5)
        conn.execute("PRAGMA busy_timeout=5000")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    def _initialize(self) -> None:
        with closing(self._connect()) as conn:
            conn.execute("BEGIN IMMEDIATE")
            with conn:
                conn.execute(
                    """CREATE TABLE IF NOT EXISTS finops_synthetic_invoice_versions (
                        scope_id TEXT NOT NULL,
                        statement_id TEXT NOT NULL,
                        revision INTEGER NOT NULL CHECK (revision > 0),
                        supersedes INTEGER,
                        import_key TEXT NOT NULL,
                        fingerprint TEXT NOT NULL,
                        imported_at TEXT NOT NULL,
                        snapshot_json TEXT NOT NULL,
                        audit_sequence INTEGER NOT NULL,
                        PRIMARY KEY (scope_id, statement_id, revision),
                        UNIQUE (scope_id, import_key),
                        UNIQUE (scope_id, audit_sequence)
                    )"""
                )
                conn.execute(
                    """CREATE TABLE IF NOT EXISTS finops_synthetic_invoice_audit (
                        scope_id TEXT NOT NULL,
                        sequence INTEGER NOT NULL CHECK (sequence > 0),
                        statement_id TEXT NOT NULL,
                        revision INTEGER NOT NULL CHECK (revision > 0),
                        import_key TEXT NOT NULL,
                        fingerprint TEXT NOT NULL,
                        imported_at TEXT NOT NULL,
                        previous_hash TEXT NOT NULL,
                        entry_hash TEXT NOT NULL,
                        PRIMARY KEY (scope_id, sequence),
                        UNIQUE (scope_id, statement_id, revision),
                        FOREIGN KEY (scope_id, statement_id, revision)
                            REFERENCES finops_synthetic_invoice_versions
                            (scope_id, statement_id, revision)
                    )"""
                )
                # Application-level append-only, plus SQLite triggers for accidental edits.
                for table in (
                    "finops_synthetic_invoice_versions",
                    "finops_synthetic_invoice_audit",
                ):
                    conn.execute(
                        f"CREATE TRIGGER IF NOT EXISTS {table}_no_update "
                        f"BEFORE UPDATE ON {table} BEGIN "
                        "SELECT RAISE(ABORT, 'immutable_synthetic_invoice'); END"
                    )
                    conn.execute(
                        f"CREATE TRIGGER IF NOT EXISTS {table}_no_delete "
                        f"BEFORE DELETE ON {table} BEGIN "
                        "SELECT RAISE(ABORT, 'immutable_synthetic_invoice'); END"
                    )

    @staticmethod
    def _read_version(
        conn: sqlite3.Connection, scope_id: str, statement_id: str, revision: int,
    ) -> ImportedInvoice:
        row = conn.execute(
            "SELECT v.supersedes, v.import_key, v.fingerprint, v.imported_at, "
            "v.snapshot_json, v.audit_sequence, a.entry_hash "
            "FROM finops_synthetic_invoice_versions v "
            "JOIN finops_synthetic_invoice_audit a "
            "ON a.scope_id=v.scope_id AND a.sequence=v.audit_sequence "
            "AND a.statement_id=v.statement_id AND a.revision=v.revision "
            "WHERE v.scope_id=? AND v.statement_id=? AND v.revision=?",
            (scope_id, statement_id, revision),
        ).fetchone()
        if row is None:
            raise FinOpsError("invoice_revision_not_found")
        supersedes, import_key, fingerprint, timestamp, snapshot, sequence, digest = row
        try:
            statement = parse_synthetic_invoice_statement_json(snapshot)
            return ImportedInvoice(
                scope_id, statement_id, revision, supersedes, import_key,
                fingerprint, datetime.fromisoformat(timestamp), statement,
                sequence, digest,
            )
        except (TypeError, ValueError) as exc:
            raise FinOpsError("invoice_audit_integrity_failure") from exc

    @staticmethod
    def _audit(conn: sqlite3.Connection, scope_id: str) -> InvoiceAuditReport:
        """Verify every snapshot, link and chain against current local DB contents."""
        events = conn.execute(
            "SELECT sequence, statement_id, revision, import_key, fingerprint, "
            "imported_at, previous_hash, entry_hash "
            "FROM finops_synthetic_invoice_audit WHERE scope_id=? ORDER BY sequence",
            (scope_id,),
        ).fetchall()
        revisions = conn.execute(
            "SELECT statement_id, revision, supersedes, import_key, fingerprint, "
            "imported_at, snapshot_json, audit_sequence "
            "FROM finops_synthetic_invoice_versions WHERE scope_id=?",
            (scope_id,),
        ).fetchall()
        if len(events) != len(revisions):
            raise FinOpsError("invoice_audit_integrity_failure")
        by_sequence = {row[7]: row for row in revisions}
        if len(by_sequence) != len(revisions):
            raise FinOpsError("invoice_audit_integrity_failure")

        head = GENESIS_HASH
        latest_revision: dict[str, int] = {}
        latest_route: dict[str, tuple[str, ...]] = {}
        latest_snapshot: dict[str, str] = {}
        for expected_seq, event in enumerate(events, start=1):
            (seq, statement_id, rev, key, digest, timestamp, prev, current_hash) = event
            version = by_sequence.get(seq)
            if (
                seq != expected_seq or prev != head or version is None
                or version[0] != statement_id or version[1] != rev
                or version[3] != key or version[4] != digest
                or version[5] != timestamp
            ):
                raise FinOpsError("invoice_audit_integrity_failure")
            supersedes, snapshot = version[2], version[6]
            try:
                statement = parse_synthetic_invoice_statement_json(snapshot)
                when = datetime.fromisoformat(timestamp)
                request = InvoiceImportRequest(
                    scope_id, key, rev, supersedes, statement, when,
                )
                recalculated = invoice_import_fingerprint(request)
                expected_hash = audit_entry_hash(
                    scope_id=scope_id, sequence=seq, statement_id=statement_id,
                    revision=rev, import_key=key, fingerprint=digest,
                    imported_at=timestamp, previous_hash=head,
                )
            except (TypeError, ValueError) as exc:
                raise FinOpsError("invoice_audit_integrity_failure") from exc
            route = (
                statement.model_id, statement.api_provider, statement.billing_provider,
                statement.deployment_channel, statement.currency,
            )
            previous = latest_revision.get(statement_id)
            if (
                statement.statement_id != statement_id or recalculated != digest
                or expected_hash != current_hash
                or (previous is None and (rev != 1 or supersedes is not None))
                or (previous is not None and (
                    rev != previous + 1 or supersedes != previous
                    or route != latest_route[statement_id]
                    or snapshot == latest_snapshot[statement_id]
                ))
            ):
                raise FinOpsError("invoice_audit_integrity_failure")
            latest_revision[statement_id] = rev
            latest_route[statement_id] = route
            latest_snapshot[statement_id] = snapshot
            head = current_hash

        return InvoiceAuditReport(scope_id, len(events), len(revisions), head)

    def audit(self, scope_id: str) -> InvoiceAuditReport:
        _id(scope_id, "invoice_scope_id")
        with closing(self._connect()) as conn:
            # A read transaction keeps revisions and chain consistent during inspection.
            conn.execute("BEGIN")
            with conn:
                return self._audit(conn, scope_id)

    def import_synthetic(self, request: InvoiceImportRequest) -> InvoiceImportResult:
        if type(request) is not InvoiceImportRequest:
            raise FinOpsError("invalid_invoice_import_request")
        scope = request.scope_id
        statement_id = request.statement.statement_id
        fingerprint = invoice_import_fingerprint(request)
        snapshot = canonical_statement(request.statement)
        with closing(self._connect()) as conn:
            conn.execute("BEGIN IMMEDIATE")
            with conn:
                report = self._audit(conn, scope)
                by_key = conn.execute(
                    "SELECT statement_id, revision, fingerprint "
                    "FROM finops_synthetic_invoice_versions "
                    "WHERE scope_id=? AND import_key=?",
                    (scope, request.import_key),
                ).fetchone()
                if by_key is not None:
                    if by_key != (statement_id, request.revision, fingerprint):
                        raise FinOpsError("invoice_import_idempotency_conflict")
                    return InvoiceImportResult(
                        self._read_version(conn, scope, statement_id, request.revision), True,
                    )
                old_revision = conn.execute(
                    "SELECT fingerprint FROM finops_synthetic_invoice_versions "
                    "WHERE scope_id=? AND statement_id=? AND revision=?",
                    (scope, statement_id, request.revision),
                ).fetchone()
                if old_revision is not None:
                    raise FinOpsError("invoice_revision_already_imported")
                last = conn.execute(
                    "SELECT revision, snapshot_json FROM finops_synthetic_invoice_versions "
                    "WHERE scope_id=? AND statement_id=? ORDER BY revision DESC LIMIT 1",
                    (scope, statement_id),
                ).fetchone()
                if last is None:
                    if request.revision != 1 or request.supersedes is not None:
                        raise FinOpsError("invoice_initial_revision_must_be_one")
                else:
                    latest_rev, old_snapshot = last
                    if request.revision != latest_rev + 1 or request.supersedes != latest_rev:
                        raise FinOpsError("invoice_supersedes_latest_required")
                    if snapshot == old_snapshot:
                        raise FinOpsError("invoice_revision_unchanged")
                    previous = parse_synthetic_invoice_statement_json(old_snapshot)
                    if (
                        previous.model_id != request.statement.model_id
                        or previous.api_provider != request.statement.api_provider
                        or previous.billing_provider != request.statement.billing_provider
                        or previous.deployment_channel != request.statement.deployment_channel
                        or previous.currency != request.statement.currency
                    ):
                        raise FinOpsError("invoice_revision_route_changed")
                seq = report.event_count + 1
                timestamp = request.imported_at.isoformat()
                digest = audit_entry_hash(
                    scope_id=scope, sequence=seq, statement_id=statement_id,
                    revision=request.revision, import_key=request.import_key,
                    fingerprint=fingerprint, imported_at=timestamp,
                    previous_hash=report.head_hash,
                )
                conn.execute(
                    "INSERT INTO finops_synthetic_invoice_versions "
                    "(scope_id,statement_id,revision,supersedes,import_key,fingerprint,"
                    "imported_at,snapshot_json,audit_sequence) "
                    "VALUES (?,?,?,?,?,?,?,?,?)",
                    (
                        scope, statement_id, request.revision, request.supersedes,
                        request.import_key, fingerprint, timestamp, snapshot, seq,
                    ),
                )
                conn.execute(
                    "INSERT INTO finops_synthetic_invoice_audit "
                    "(scope_id,sequence,statement_id,revision,import_key,fingerprint,"
                    "imported_at,previous_hash,entry_hash) VALUES (?,?,?,?,?,?,?,?,?)",
                    (
                        scope, seq, statement_id, request.revision, request.import_key,
                        fingerprint, timestamp, report.head_hash, digest,
                    ),
                )
                return InvoiceImportResult(
                    self._read_version(conn, scope, statement_id, request.revision),
                )

    def inspect(
        self, scope_id: str, statement_id: str, revision: int | None = None,
    ) -> ImportedInvoice:
        _id(scope_id, "invoice_scope_id")
        _id(statement_id, "statement_id")
        if revision is not None:
            _revision(revision, "invoice_revision")
        with closing(self._connect()) as conn:
            conn.execute("BEGIN")
            with conn:
                self._audit(conn, scope_id)
                selected = revision
                if selected is None:
                    last = conn.execute(
                        "SELECT revision FROM finops_synthetic_invoice_versions "
                        "WHERE scope_id=? AND statement_id=? ORDER BY revision DESC LIMIT 1",
                        (scope_id, statement_id),
                    ).fetchone()
                    if last is None:
                        raise FinOpsError("invoice_revision_not_found")
                    selected = last[0]
                return self._read_version(conn, scope_id, statement_id, selected)

    def history(self, scope_id: str, statement_id: str) -> tuple[ImportedInvoice, ...]:
        _id(scope_id, "invoice_scope_id")
        _id(statement_id, "statement_id")
        with closing(self._connect()) as conn:
            conn.execute("BEGIN")
            with conn:
                self._audit(conn, scope_id)
                versions = conn.execute(
                    "SELECT revision FROM finops_synthetic_invoice_versions "
                    "WHERE scope_id=? AND statement_id=? ORDER BY revision",
                    (scope_id, statement_id),
                ).fetchall()
                return tuple(
                    self._read_version(conn, scope_id, statement_id, row[0])
                    for row in versions
                )
