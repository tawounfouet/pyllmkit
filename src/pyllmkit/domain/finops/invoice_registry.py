"""Pure G4.2 registry contracts for versioned, synthetic invoice evidence.

Persisted fixtures are not provider invoices. Fingerprints and local hash
chains detect accidental edits, not compromise by a privileged DB operator.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Protocol

from pyllmkit.domain.finops import FinOpsError
from pyllmkit.domain.finops.invoice_reconciliation import SyntheticInvoiceStatement

_TOKEN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,191}$")
_SHA = re.compile(r"^[a-f0-9]{64}$")
GENESIS_HASH = "0" * 64


def _id(value: str, name: str) -> None:
    if type(value) is not str or _TOKEN.fullmatch(value) is None:
        raise FinOpsError(f"invalid_{name}")


def _time(value: datetime, name: str) -> None:
    if type(value) is not datetime or value.tzinfo is None or value.utcoffset() is None:
        raise FinOpsError(f"invalid_{name}")


def _revision(value: int, name: str) -> None:
    if type(value) is not int or value <= 0:
        raise FinOpsError(f"invalid_{name}")


def canonical_statement(statement: SyntheticInvoiceStatement) -> str:
    """Stable representation of the semantic synthetic content, not the raw JSON."""
    if type(statement) is not SyntheticInvoiceStatement:
        raise FinOpsError("invalid_invoice_registry_statement")
    payload = {
        "schema_version": 1,
        "source_kind": statement.source_kind,
        "statement_id": statement.statement_id,
        "model_id": statement.model_id,
        "api_provider": statement.api_provider,
        "billing_provider": statement.billing_provider,
        "deployment_channel": statement.deployment_channel,
        "currency": statement.currency,
        "lines": [
            {
                "line_id": line.line_id,
                "provider_request_id": line.provider_request_id,
                "kind": line.kind.value,
                "amount": format(line.amount.amount, "f"),
            }
            for line in sorted(statement.lines, key=lambda item: item.line_id)
        ],
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


@dataclass(frozen=True, slots=True)
class InvoiceImportRequest:
    scope_id: str
    import_key: str
    revision: int
    supersedes: int | None
    statement: SyntheticInvoiceStatement
    imported_at: datetime

    def __post_init__(self) -> None:
        _id(self.scope_id, "invoice_scope_id")
        _id(self.import_key, "invoice_import_key")
        _revision(self.revision, "invoice_revision")
        if self.supersedes is not None:
            _revision(self.supersedes, "supersedes_revision")
        if type(self.statement) is not SyntheticInvoiceStatement:
            raise FinOpsError("invalid_invoice_registry_statement")
        _time(self.imported_at, "invoice_import_time")


def invoice_import_fingerprint(request: InvoiceImportRequest) -> str:
    """Bind the invoice snapshot to scope, identity, version and parent pointer."""
    payload = {
        "scope_id": request.scope_id,
        "revision": request.revision,
        "supersedes": request.supersedes,
        "statement": json.loads(canonical_statement(request.statement)),
    }
    content = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def audit_entry_hash(
    *, scope_id: str, sequence: int, statement_id: str, revision: int,
    import_key: str, fingerprint: str, imported_at: str, previous_hash: str,
) -> str:
    """Deterministic local chain; not signed or anchored outside SQLite."""
    _id(scope_id, "invoice_scope_id")
    _id(statement_id, "statement_id")
    _id(import_key, "invoice_import_key")
    _revision(sequence, "invoice_audit_sequence")
    _revision(revision, "invoice_revision")
    if (
        type(fingerprint) is not str or _SHA.fullmatch(fingerprint) is None
        or type(previous_hash) is not str or _SHA.fullmatch(previous_hash) is None
    ):
        raise FinOpsError("invalid_invoice_audit_hash")
    payload = {
        "scope_id": scope_id,
        "sequence": sequence,
        "statement_id": statement_id,
        "revision": revision,
        "import_key": import_key,
        "fingerprint": fingerprint,
        "imported_at": imported_at,
        "previous_hash": previous_hash,
    }
    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class ImportedInvoice:
    scope_id: str
    statement_id: str
    revision: int
    supersedes: int | None
    import_key: str
    fingerprint: str
    imported_at: datetime
    statement: SyntheticInvoiceStatement
    audit_sequence: int
    audit_hash: str

    def __post_init__(self) -> None:
        _id(self.scope_id, "invoice_scope_id")
        _id(self.statement_id, "statement_id")
        _id(self.import_key, "invoice_import_key")
        _revision(self.revision, "invoice_revision")
        _revision(self.audit_sequence, "invoice_audit_sequence")
        _time(self.imported_at, "invoice_import_time")
        if self.supersedes is not None:
            _revision(self.supersedes, "supersedes_revision")
        if type(self.statement) is not SyntheticInvoiceStatement:
            raise FinOpsError("invalid_invoice_registry_statement")
        if self.statement_id != self.statement.statement_id:
            raise FinOpsError("invoice_statement_identity_mismatch")
        for value in (self.fingerprint, self.audit_hash):
            if type(value) is not str or _SHA.fullmatch(value) is None:
                raise FinOpsError("invalid_invoice_registry_hash")


@dataclass(frozen=True, slots=True)
class InvoiceImportResult:
    invoice: ImportedInvoice
    replayed: bool = False


@dataclass(frozen=True, slots=True)
class InvoiceAuditReport:
    scope_id: str
    event_count: int
    revision_count: int
    head_hash: str
    integrity: str = "local_chain_consistent"


class InvoiceRegistryPort(Protocol):
    def import_synthetic(self, request: InvoiceImportRequest) -> InvoiceImportResult: ...

    def inspect(self, scope_id: str, statement_id: str, revision: int | None = None) -> ImportedInvoice: ...

    def history(self, scope_id: str, statement_id: str) -> tuple[ImportedInvoice, ...]: ...

    def audit(self, scope_id: str) -> InvoiceAuditReport: ...


def imported_invoice_to_dict(result: InvoiceImportResult) -> dict[str, object]:
    row = result.invoice
    return {
        "status": "imported_synthetic",
        "replayed": result.replayed,
        "scope_id": row.scope_id,
        "statement_id": row.statement_id,
        "revision": row.revision,
        "supersedes": row.supersedes,
        "import_key": row.import_key,
        "fingerprint": row.fingerprint,
        "imported_at": row.imported_at.isoformat(),
        "audit_sequence": row.audit_sequence,
        "audit_hash": row.audit_hash,
        "line_count": len(row.statement.lines),
        "model_id": row.statement.model_id,
        "api_provider": row.statement.api_provider,
        "billing_provider": row.statement.billing_provider,
        "deployment_channel": row.statement.deployment_channel,
        "currency": row.statement.currency,
        "source_kind": "synthetic_fixture",
        "provider_invoice_verified": False,
        "ledger_mutated": False,
        "live_authorized": False,
    }


def audit_report_to_dict(report: InvoiceAuditReport) -> dict[str, object]:
    return {
        "scope_id": report.scope_id,
        "integrity": report.integrity,
        "event_count": report.event_count,
        "revision_count": report.revision_count,
        "head_hash": report.head_hash,
        "external_trust_anchor": False,
        "provider_invoice_verified": False,
        "ledger_mutated": False,
        "live_authorized": False,
    }
