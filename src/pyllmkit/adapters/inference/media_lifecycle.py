"""M0 media-model retirement policy from dated primary provider notices.

Unknown model names are not silently rewritten into other billable endpoints.
This policy is a protective offline snapshot, not an account-access guarantee.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import StrEnum

from pyllmkit.application.inference import InvocationPortError


class MediaLifecycle(StrEnum):
    CURRENT = "current"
    DEPRECATED = "deprecated"
    RETIRED = "retired"
    UNVERIFIED = "unverified"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class MediaModelPolicy:
    state: MediaLifecycle
    source_url: str
    replacement: str | None = None
    shutdown_date: date | None = None


OPENAI = "https://developers.openai.com/api/docs/deprecations"
GOOGLE = "https://ai.google.dev/gemini-api/docs/deprecations"

POLICY: dict[str, MediaModelPolicy] = {
    "dall-e-2": MediaModelPolicy(MediaLifecycle.RETIRED, OPENAI, "gpt-image-2", date(2026, 5, 12)),
    "dall-e-3": MediaModelPolicy(MediaLifecycle.RETIRED, OPENAI, "gpt-image-2", date(2026, 5, 12)),
    "gpt-image-1": MediaModelPolicy(MediaLifecycle.RETIRED, OPENAI, "gpt-image-2", date(2026, 10, 23)),
    "imagen-3": MediaModelPolicy(MediaLifecycle.RETIRED, GOOGLE, "gemini-3.1-flash-image", date(2025, 11, 10)),
    "imagen-4": MediaModelPolicy(MediaLifecycle.RETIRED, GOOGLE, "gemini-3.1-flash-image", date(2026, 8, 17)),
    "veo-2": MediaModelPolicy(MediaLifecycle.RETIRED, GOOGLE, "veo-3.1-lite-generate-preview", date(2026, 6, 30)),
    "veo-3": MediaModelPolicy(MediaLifecycle.RETIRED, GOOGLE, "veo-3.1-lite-generate-preview", date(2026, 6, 30)),
    "gemini-2.5-flash-image": MediaModelPolicy(MediaLifecycle.RETIRED, GOOGLE, "gemini-3.1-flash-image", date(2026, 10, 2)),
    "grok-imagine-image-quality": MediaModelPolicy(
        MediaLifecycle.RETIRED,
        "https://docs.x.ai/developers/migration/imagine-image-quality-nov-2",
        "grok-imagine-image-2.0", date(2026, 11, 2),
    ),
    "gpt-image-1-mini": MediaModelPolicy(MediaLifecycle.DEPRECATED, OPENAI, "gpt-image-2", date(2026, 12, 1)),
    "gpt-image-1.5": MediaModelPolicy(MediaLifecycle.DEPRECATED, OPENAI, "gpt-image-2", date(2026, 12, 1)),
    "tts-1": MediaModelPolicy(MediaLifecycle.DEPRECATED, OPENAI, "gpt-realtime-2.1-mini", date(2027, 1, 6)),
    "tts-1-hd": MediaModelPolicy(MediaLifecycle.DEPRECATED, OPENAI, "gpt-realtime-2.1-mini", date(2027, 1, 6)),
    "gpt-4o-mini-tts": MediaModelPolicy(MediaLifecycle.DEPRECATED, OPENAI, "gpt-realtime-2.1-mini", date(2027, 1, 6)),
    "gemini-nano-banana-2.1": MediaModelPolicy(
        MediaLifecycle.UNVERIFIED,
        "https://ai.google.dev/gemini-api/docs/models/gemini-3.1-flash-image",
        "gemini-3.1-flash-image",
    ),
    "gpt-image-2": MediaModelPolicy(
        MediaLifecycle.CURRENT, "https://developers.openai.com/api/docs/models/gpt-image-2",
    ),
    "gemini-3.1-flash-image": MediaModelPolicy(
        MediaLifecycle.CURRENT, "https://ai.google.dev/gemini-api/docs/models/gemini-3.1-flash-image",
    ),
    "veo-3.1-lite-generate-preview": MediaModelPolicy(
        MediaLifecycle.CURRENT, "https://ai.google.dev/gemini-api/docs/pricing",
    ),
}


def media_model_policy(model_id: str, *, on_date: date | None = None) -> MediaModelPolicy:
    """Read exact-ID lifecycle and enforce the known shutdown date dynamically."""
    rule = POLICY.get(model_id.strip().lower())
    if rule is None:
        return MediaModelPolicy(MediaLifecycle.UNKNOWN, "")
    now = date.today() if on_date is None else on_date
    if rule.shutdown_date is not None and now >= rule.shutdown_date:
        return MediaModelPolicy(
            MediaLifecycle.RETIRED, rule.source_url,
            rule.replacement, rule.shutdown_date,
        )
    return rule


def require_live_media_model(model_id: str, *, on_date: date | None = None) -> None:
    """No credential resolution or HTTP for retired or explicitly unverified IDs."""
    state = media_model_policy(model_id, on_date=on_date).state
    if state is MediaLifecycle.RETIRED:
        raise InvocationPortError("model_retired")
    if state is MediaLifecycle.UNVERIFIED:
        raise InvocationPortError("model_unverified")
