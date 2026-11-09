"""Strict, size-bounded offline JSON parser for *synthetic* invoice fixtures.

No provider authentication, invoices API, ledger writes or live authorization.
"""

from __future__ import annotations

import json
import re
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from pyllmkit.domain.finops import FinOpsError, Money
from pyllmkit.domain.finops.invoice_reconciliation import (
    InvoiceLineKind,
    SyntheticInvoiceLine,
    SyntheticInvoiceStatement,
)

MAX_STATEMENT_BYTES = 1_000_000
MAX_INVOICE_LINES = 2_000
_TOKEN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,191}$")
_NUMBER = re.compile(r"^(?:0|[1-9]\d*)(?:\.\d+)?$")
_FIELDS = frozenset({
    "schema_version", "source_kind", "statement_id", "model_id", "api_provider",
    "billing_provider", "deployment_channel", "currency", "lines",
})
_LINE_FIELDS = frozenset({"line_id", "provider_request_id", "kind", "amount"})


def _id(value: object, label: str) -> str:
    if type(value) is not str or _TOKEN.fullmatch(value) is None:
        raise FinOpsError(f"invalid_{label}")
    return value


def _decimal(value: object) -> Decimal:
    if type(value) is not str or _NUMBER.fullmatch(value) is None or len(value) > 80:
        raise FinOpsError("invalid_invoice_amount")
    try:
        return Decimal(value)
    except InvalidOperation:
        raise FinOpsError("invalid_invoice_amount") from None


def parse_synthetic_invoice_statement(payload: object) -> SyntheticInvoiceStatement:
    if type(payload) is not dict or set(payload) != _FIELDS:
        raise FinOpsError("invalid_invoice_statement_fields")
    if type(payload["schema_version"]) is not int or payload["schema_version"] != 1:
        raise FinOpsError("unsupported_invoice_schema")
    if payload["source_kind"] != "synthetic_fixture":
        raise FinOpsError("invoice_source_not_verified")
    raw_lines = payload["lines"]
    if type(raw_lines) is not list or not 1 <= len(raw_lines) <= MAX_INVOICE_LINES:
        raise FinOpsError("invalid_invoice_lines")
    currency = payload["currency"]
    lines: list[SyntheticInvoiceLine] = []
    for raw in raw_lines:
        if type(raw) is not dict or set(raw) != _LINE_FIELDS:
            raise FinOpsError("invalid_invoice_line_fields")
        try:
            if type(raw["kind"]) is not str:
                raise ValueError("invalid kind type")
            kind = InvoiceLineKind(raw["kind"])
        except ValueError:
            raise FinOpsError("invalid_invoice_line_kind") from None
        lines.append(SyntheticInvoiceLine(
            line_id=_id(raw["line_id"], "invoice_line_id"),
            provider_request_id=_id(raw["provider_request_id"], "provider_request_id"),
            kind=kind,
            amount=Money(_decimal(raw["amount"]), currency),
        ))
    return SyntheticInvoiceStatement(
        statement_id=_id(payload["statement_id"], "statement_id"),
        model_id=_id(payload["model_id"], "model_id"),
        api_provider=_id(payload["api_provider"], "api_provider"),
        billing_provider=_id(payload["billing_provider"], "billing_provider"),
        deployment_channel=_id(payload["deployment_channel"], "deployment_channel"),
        currency=currency,
        lines=tuple(lines),
    )


def _pairs_unique(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise FinOpsError("duplicate_invoice_json_key")
        result[key] = value
    return result


def _invalid_constant(_: str) -> None:
    raise FinOpsError("invalid_invoice_json_constant")


def parse_synthetic_invoice_statement_json(
    content: str | bytes,
) -> SyntheticInvoiceStatement:
    if not isinstance(content, (str, bytes)):
        raise FinOpsError("invalid_invoice_json_content")
    size = len(content) if isinstance(content, bytes) else len(content.encode("utf-8"))
    if size > MAX_STATEMENT_BYTES:
        raise FinOpsError("invoice_statement_too_large")
    try:
        payload = json.loads(
            content, object_pairs_hook=_pairs_unique, parse_constant=_invalid_constant,
        )
    except FinOpsError:
        raise
    except (ValueError, UnicodeDecodeError, RecursionError) as exc:
        raise FinOpsError("invalid_invoice_json") from exc
    return parse_synthetic_invoice_statement(payload)


def load_synthetic_invoice_statement(path: Path) -> SyntheticInvoiceStatement:
    if not isinstance(path, Path):
        raise FinOpsError("invalid_invoice_statement_path")
    if path.stat().st_size > MAX_STATEMENT_BYTES:
        raise FinOpsError("invoice_statement_too_large")
    return parse_synthetic_invoice_statement_json(path.read_bytes())
