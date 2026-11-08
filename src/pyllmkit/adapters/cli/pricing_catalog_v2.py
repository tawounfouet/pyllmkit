"""Strict offline pricing catalogue v2 for media FinOps (M2-G1).

Only infrastructure reads files. These declared tariffs are not provider quotes,
account entitlements, verified live pricing or permission to spend money.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from pyllmkit.adapters.cli.media_catalog_v2 import (
    MediaCatalog,
    effective_lifecycle,
)
from pyllmkit.adapters.inference.media_lifecycle import MediaLifecycle
from pyllmkit.domain.finops import (
    FinOpsError,
    PriceCatalog,
    PriceRate,
    PriceVersion,
)

SCHEMA_VERSION = 2
MAX_CATALOG_BYTES = 1_000_000
MAX_PRICE_ENTRIES = 2_000
MAX_RATES_PER_ENTRY = 128
MAX_DIMENSIONS_PER_RATE = 16
CATALOG_PATH = Path(__file__).parent / "data" / "pricing_catalog_v2.json"

_TOKEN_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,191}$")
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_DECIMAL_RE = re.compile(r"^(?:0|[1-9]\d*)(?:\.\d+)?$")
_TIMESTAMP_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}"
    r"(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$"
)
_ENVELOPE_KEYS = frozenset({"schema_version", "revision", "updated_at", "prices"})
_PRICE_KEYS = frozenset({
    "price_id", "revision", "model_id", "api_provider", "billing_provider",
    "deployment_channel", "currency", "valid_from", "valid_to",
    "source_url", "verified_at", "rates",
})
_RATE_KEYS = frozenset({"meter", "amount", "per", "dimensions"})


@dataclass(frozen=True, slots=True)
class VersionedPriceCatalog:
    """Validated, immutable read model; never automatically merges local overlays."""

    schema_version: int
    revision: str
    updated_at: date
    prices: tuple[PriceVersion, ...]

    def as_domain_catalog(self) -> PriceCatalog:
        return PriceCatalog(self.prices)


def _object(value: object, keys: frozenset[str], error: str) -> dict[str, Any]:
    if type(value) is not dict or set(value) != keys:
        raise FinOpsError(error)
    return value


def _token(value: object, label: str) -> str:
    if type(value) is not str or _TOKEN_RE.fullmatch(value) is None:
        raise FinOpsError(f"invalid_{label}")
    return value


def _day(value: object, label: str) -> date:
    if type(value) is not str or _DATE_RE.fullmatch(value) is None:
        raise FinOpsError(f"invalid_{label}")
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise FinOpsError(f"invalid_{label}") from None


def _timestamp(value: object, label: str) -> datetime:
    if type(value) is not str or _TIMESTAMP_RE.fullmatch(value) is None:
        raise FinOpsError(f"invalid_{label}")
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise FinOpsError(f"invalid_{label}") from None
    if result.utcoffset() is None:
        raise FinOpsError(f"invalid_{label}")
    return result


def _decimal(value: object, label: str, *, positive: bool = False) -> Decimal:
    if type(value) is not str or _DECIMAL_RE.fullmatch(value) is None or len(value) > 80:
        raise FinOpsError(f"invalid_{label}")
    try:
        result = Decimal(value)
    except InvalidOperation:
        raise FinOpsError(f"invalid_{label}") from None
    if not result.is_finite() or result < 0 or (positive and result == 0):
        raise FinOpsError(f"invalid_{label}")
    return result


def _rate(value: object) -> PriceRate:
    raw = _object(value, _RATE_KEYS, "invalid_price_rate_fields")
    dimensions = raw["dimensions"]
    if type(dimensions) is not dict or len(dimensions) > MAX_DIMENSIONS_PER_RATE:
        raise FinOpsError("invalid_rate_dimensions")
    pairs = tuple(sorted(
        (_token(key, "dimension_key"), _token(val, "dimension_value"))
        for key, val in dimensions.items()
    ))
    return PriceRate(
        meter=_token(raw["meter"], "rate_meter"),
        amount=_decimal(raw["amount"], "rate_amount"),
        per=_decimal(raw["per"], "rate_denominator", positive=True),
        dimensions=pairs,
    )


def _price(value: object) -> PriceVersion:
    raw = _object(value, _PRICE_KEYS, "invalid_price_fields")
    rates = raw["rates"]
    if type(rates) is not list or not 1 <= len(rates) <= MAX_RATES_PER_ENTRY:
        raise FinOpsError("invalid_price_rates")
    return PriceVersion(
        price_id=_token(raw["price_id"], "price_id"),
        revision=_token(raw["revision"], "revision"),
        model_id=_token(raw["model_id"], "model_id"),
        api_provider=_token(raw["api_provider"], "api_provider"),
        billing_provider=_token(raw["billing_provider"], "billing_provider"),
        deployment_channel=_token(raw["deployment_channel"], "deployment_channel"),
        currency=raw["currency"],
        valid_from=_timestamp(raw["valid_from"], "valid_from"),
        valid_to=(
            _timestamp(raw["valid_to"], "valid_to")
            if raw["valid_to"] is not None else None
        ),
        source_url=raw["source_url"],
        verified_at=_day(raw["verified_at"], "verified_at"),
        rates=tuple(_rate(rate) for rate in rates),
    )


def _validate_history(prices: tuple[PriceVersion, ...]) -> None:
    seen_revisions: set[tuple[str, str]] = set()
    scoped: dict[tuple[str, str, str, str], list[PriceVersion]] = {}
    for price in prices:
        version = (price.price_id, price.revision)
        if version in seen_revisions:
            raise FinOpsError("duplicate_price_revision")
        seen_revisions.add(version)
        key = (
            price.model_id, price.api_provider, price.billing_provider,
            price.deployment_channel,
        )
        scoped.setdefault(key, []).append(price)
    for versions in scoped.values():
        versions.sort(key=lambda item: item.valid_from)
        for previous, following in zip(versions[:-1], versions[1:], strict=True):
            if previous.valid_to is None or previous.valid_to > following.valid_from:
                raise FinOpsError("overlapping_price_intervals")


def parse_price_catalog(payload: object) -> VersionedPriceCatalog:
    """Fail closed on unknown schema, extra fields and overlapping historical rates."""
    raw = _object(payload, _ENVELOPE_KEYS, "invalid_price_catalog_fields")
    if type(raw["schema_version"]) is not int or raw["schema_version"] != SCHEMA_VERSION:
        raise FinOpsError("unsupported_price_catalog_schema")
    revision = _token(raw["revision"], "catalog_revision")
    updated_at = _day(raw["updated_at"], "catalog_updated_at")
    entries = raw["prices"]
    if type(entries) is not list or len(entries) > MAX_PRICE_ENTRIES:
        raise FinOpsError("invalid_price_entries")
    prices = tuple(_price(item) for item in entries)
    _validate_history(prices)
    return VersionedPriceCatalog(SCHEMA_VERSION, revision, updated_at, prices)


def _unique_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise FinOpsError("duplicate_json_key")
        result[key] = value
    return result


def _reject_constant(_: str) -> None:
    raise FinOpsError("invalid_json_constant")


def parse_price_catalog_json(content: str | bytes) -> VersionedPriceCatalog:
    """Strict JSON decoder: duplicate keys, NaN and Infinity are rejected."""
    if type(content) not in (str, bytes):
        raise FinOpsError("invalid_price_catalog_content")
    if len(content if type(content) is bytes else content.encode("utf-8")) > MAX_CATALOG_BYTES:
        raise FinOpsError("price_catalog_too_large")
    try:
        payload = json.loads(
            content, object_pairs_hook=_unique_pairs, parse_constant=_reject_constant,
        )
    except (ValueError, UnicodeDecodeError, RecursionError) as exc:
        raise FinOpsError("invalid_price_catalog_json") from exc
    return parse_price_catalog(payload)


def load_price_catalog(path: Path | None = None) -> VersionedPriceCatalog:
    """Read a bounded local file. No automatic local overrides, network or secrets."""
    target = CATALOG_PATH if path is None else path
    if not isinstance(target, Path):
        raise FinOpsError("invalid_price_catalog_path")
    if target.stat().st_size > MAX_CATALOG_BYTES:
        raise FinOpsError("price_catalog_too_large")
    return parse_price_catalog_json(target.read_bytes())


def price_catalog_to_dict(catalog: VersionedPriceCatalog) -> dict[str, object]:
    """Canonical, JSON-compatible round-trip with decimal strings."""
    if type(catalog) is not VersionedPriceCatalog or catalog.schema_version != SCHEMA_VERSION:
        raise FinOpsError("unsupported_price_catalog_schema")
    _validate_history(catalog.prices)
    prices = []
    for price in catalog.prices:
        prices.append({
            "price_id": price.price_id,
            "revision": price.revision,
            "model_id": price.model_id,
            "api_provider": price.api_provider,
            "billing_provider": price.billing_provider,
            "deployment_channel": price.deployment_channel,
            "currency": price.currency,
            "valid_from": price.valid_from.isoformat(),
            "valid_to": (
                price.valid_to.isoformat()
                if price.valid_to is not None else None
            ),
            "source_url": price.source_url,
            "verified_at": price.verified_at.isoformat(),
            "rates": [
                {
                    "meter": rate.meter,
                    "amount": str(rate.amount),
                    "per": str(rate.per),
                    "dimensions": dict(rate.dimensions),
                }
                for rate in price.rates
            ],
        })
    return {
        "schema_version": catalog.schema_version,
        "revision": catalog.revision,
        "updated_at": catalog.updated_at.isoformat(),
        "prices": prices,
    }


def merge_price_catalog(
    base: VersionedPriceCatalog, extension: VersionedPriceCatalog,
) -> VersionedPriceCatalog:
    """Append immutable versions only; conflicting history and overlaps fail closed."""
    if base.schema_version != SCHEMA_VERSION or extension.schema_version != SCHEMA_VERSION:
        raise FinOpsError("unsupported_price_catalog_schema")
    known = {(entry.price_id, entry.revision): entry for entry in base.prices}
    additional: list[PriceVersion] = []
    for candidate in extension.prices:
        key = candidate.price_id, candidate.revision
        existing = known.get(key)
        if existing is not None:
            if existing != candidate:
                raise FinOpsError("immutable_price_revision_conflict")
            continue
        known[key] = candidate
        additional.append(candidate)
    combined = tuple(sorted(
        (*base.prices, *additional),
        key=lambda item: (
            item.api_provider, item.billing_provider, item.model_id,
            item.deployment_channel, item.valid_from, item.price_id,
        ),
    ))
    _validate_history(combined)
    return VersionedPriceCatalog(
        SCHEMA_VERSION, f"{base.revision}+{extension.revision}",
        max(base.updated_at, extension.updated_at), combined,
    )


def resolve_media_price(
    prices: VersionedPriceCatalog, media: MediaCatalog, *,
    identifier: str, api_provider: str, at: datetime,
) -> PriceVersion | None:
    """Resolve by an exact M1 route, never a fuzzy model ID or inferred biller."""
    if type(api_provider) is not str or not api_provider.strip():
        raise FinOpsError("api_provider_required")
    if type(at) is not datetime or at.tzinfo is None or at.utcoffset() is None:
        raise FinOpsError("invalid_pricing_time")
    route = media.find(identifier, provider=api_provider)
    if route is None:
        raise FinOpsError("unknown_media_route")
    state = effective_lifecycle(route, on_date=at.date())
    if state not in (MediaLifecycle.CURRENT, MediaLifecycle.DEPRECATED):
        raise FinOpsError("model_lifecycle_not_priceable")
    return prices.as_domain_catalog().resolve(
        model_id=route.public_model_id,
        api_provider=route.api_provider,
        billing_provider=route.billing_provider,
        deployment_channel=route.deployment_channel,
        at=at,
    )
