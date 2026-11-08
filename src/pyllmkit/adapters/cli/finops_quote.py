"""M2-G2 offline adapter: strict request files and M1/G1 preflight resolution.

This module does not call a provider, look up credentials, or authorize spend.
"""

from __future__ import annotations

import json
import re
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from pyllmkit.domain.finops import FinOpsError
from pyllmkit.domain.finops.quoting import (
    PreflightQuote,
    QuoteComponent,
    QuoteScenario,
    quote_scenario,
)

from .media_catalog_v2 import MediaCatalog
from .pricing_catalog_v2 import VersionedPriceCatalog, resolve_media_price

SCHEMA_VERSION = 1
MAX_REQUEST_BYTES = 65_536
MAX_COMPONENTS = 64
MAX_PARAMETERS = 24
MAX_DIMENSIONS = 16
_REQUEST_FIELDS = frozenset({
    "schema_version", "model_id", "api_provider", "task",
    "at", "parameters", "components",
})
_COMPONENT_FIELDS = frozenset({"meter", "dimensions", "maximum"})
_TOKEN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,191}$")
_NUMBER = re.compile(r"^(?:0|[1-9]\d*)(?:\.\d+)?$")
_TIMESTAMP = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}"
    r"(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$"
)


def _token(value: object, label: str) -> str:
    if type(value) is not str or _TOKEN.fullmatch(value) is None:
        raise FinOpsError(f"invalid_{label}")
    return value


def _parameters(value: object, *, max_fields: int) -> tuple[tuple[str, str], ...]:
    if type(value) is not dict or len(value) > max_fields:
        raise FinOpsError("invalid_quote_dimensions")
    return tuple(sorted(
        (_token(key, "dimension_name"), _token(val, "dimension_value"))
        for key, val in value.items()
    ))


def _maximum(value: object) -> Decimal | None:
    if value is None:
        return None
    if type(value) is not str or _NUMBER.fullmatch(value) is None or len(value) > 80:
        raise FinOpsError("invalid_quote_maximum")
    try:
        number = Decimal(value)
    except InvalidOperation:
        raise FinOpsError("invalid_quote_maximum") from None
    if not number.is_finite() or number < 0:
        raise FinOpsError("invalid_quote_maximum")
    return number


def _timestamp(value: object) -> datetime:
    if type(value) is not str or _TIMESTAMP.fullmatch(value) is None:
        raise FinOpsError("invalid_quote_timestamp")
    try:
        at = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise FinOpsError("invalid_quote_timestamp") from None
    if at.utcoffset() is None:
        raise FinOpsError("invalid_quote_timestamp")
    return at


def parse_quote_request(payload: object) -> QuoteScenario:
    """Parse only explicitly declared billable components; never infer a missing zero."""
    if type(payload) is not dict or set(payload) != _REQUEST_FIELDS:
        raise FinOpsError("invalid_quote_request_fields")
    if type(payload["schema_version"]) is not int or payload["schema_version"] != SCHEMA_VERSION:
        raise FinOpsError("unsupported_quote_request_schema")
    raw_components = payload["components"]
    if type(raw_components) is not list or not 1 <= len(raw_components) <= MAX_COMPONENTS:
        raise FinOpsError("invalid_quote_components")
    components: list[QuoteComponent] = []
    for raw in raw_components:
        if type(raw) is not dict or set(raw) != _COMPONENT_FIELDS:
            raise FinOpsError("invalid_quote_component_fields")
        components.append(QuoteComponent(
            meter=_token(raw["meter"], "quote_meter"),
            maximum=_maximum(raw["maximum"]),
            dimensions=_parameters(raw["dimensions"], max_fields=MAX_DIMENSIONS),
        ))
    return QuoteScenario(
        model_id=_token(payload["model_id"], "model_id"),
        api_provider=_token(payload["api_provider"], "api_provider"),
        task=_token(payload["task"], "task"),
        at=_timestamp(payload["at"]),
        components=tuple(components),
        parameters=_parameters(payload["parameters"], max_fields=MAX_PARAMETERS),
    )


def _unique_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    seen: dict[str, Any] = {}
    for key, val in pairs:
        if key in seen:
            raise FinOpsError("duplicate_quote_json_key")
        seen[key] = val
    return seen


def _reject_constant(_: str) -> None:
    raise FinOpsError("invalid_quote_json_constant")


def parse_quote_request_json(content: str | bytes) -> QuoteScenario:
    if not isinstance(content, (str, bytes)):
        raise FinOpsError("invalid_quote_content")
    length = len(content) if isinstance(content, bytes) else len(content.encode("utf-8"))
    if length > MAX_REQUEST_BYTES:
        raise FinOpsError("quote_request_too_large")
    try:
        payload = json.loads(
            content, object_pairs_hook=_unique_pairs, parse_constant=_reject_constant,
        )
    except FinOpsError:
        raise
    except (ValueError, UnicodeDecodeError, RecursionError) as exc:
        raise FinOpsError("invalid_quote_json") from exc
    return parse_quote_request(payload)


def load_quote_request(path: Path) -> QuoteScenario:
    """Read an explicitly selected bounded local JSON file; no implicit override."""
    if not isinstance(path, Path):
        raise FinOpsError("invalid_quote_request_path")
    if path.stat().st_size > MAX_REQUEST_BYTES:
        raise FinOpsError("quote_request_too_large")
    return parse_quote_request_json(path.read_bytes())


def _selected_int(parameters: dict[str, str], key: str) -> int | None:
    value = parameters.get(key)
    if value is None:
        return None
    if not value.isdecimal() or value.startswith("0") or len(value) > 10:
        raise FinOpsError(f"invalid_quote_{key}")
    count = int(value)
    if count <= 0:
        raise FinOpsError(f"invalid_quote_{key}")
    return count


def _check_media_parameters(scenario: QuoteScenario, media: MediaCatalog) -> str:
    """Validate declared M1 limits where available; missing metadata stays unknown."""
    route = media.find(scenario.model_id, provider=scenario.api_provider)
    if route is None:
        raise FinOpsError("unknown_media_route")
    if scenario.task not in route.capabilities.tasks:
        raise FinOpsError("quote_task_not_supported")
    params = dict(scenario.parameters)
    caps = route.capabilities
    for key, allowed in (
        ("resolution", caps.resolutions),
        ("codec", caps.codecs),
        ("aspect_ratio", caps.aspect_ratios),
        ("voice", caps.voices),
        ("language", caps.languages),
    ):
        selected = params.get(key)
        if selected is not None and allowed and selected not in allowed:
            raise FinOpsError(f"quote_unsupported_{key}")
    duration = _selected_int(params, "duration_seconds")
    if duration is not None and caps.duration_seconds and duration not in caps.duration_seconds:
        raise FinOpsError("quote_unsupported_duration_seconds")
    outputs = _selected_int(params, "max_outputs")
    if outputs is not None and caps.max_outputs is not None and outputs > caps.max_outputs:
        raise FinOpsError("quote_exceeds_declared_max_outputs")
    return route.public_model_id


def quote_media_scenario(
    scenario: QuoteScenario, *,
    prices: VersionedPriceCatalog, media: MediaCatalog,
) -> PreflightQuote:
    """SDK entrypoint: validate M1 route, select exact biller price, price declared plan.

    No provider call, budget authorization, invoice correlation or live guarantee.
    """
    canonical = _check_media_parameters(scenario, media)
    route = media.find(canonical, provider=scenario.api_provider)
    if route is None:
        raise FinOpsError("unknown_media_route")
    # The canonical identity avoids resolving a vendor price against an alias.
    normalized = QuoteScenario(
        canonical, route.api_provider, scenario.task, scenario.at,
        scenario.components, scenario.parameters,
    )
    tariff = resolve_media_price(
        prices, media, identifier=canonical, api_provider=route.api_provider,
        at=scenario.at,
    )
    return quote_scenario(
        normalized, price=tariff,
        billing_provider=route.billing_provider,
        deployment_channel=route.deployment_channel,
        catalog_revision=prices.revision,
    )
