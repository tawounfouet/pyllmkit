"""Pure HTTP status normalization with no error bodies, headers or secrets."""

from pyllmkit.application.inference.contracts import InvocationPortError


def normalize_http_failure(status: int) -> InvocationPortError:
    """Map status to a safe code; transports supply status only, never raw body."""
    if type(status) is not int or not 100 <= status <= 599:
        raise ValueError("invalid_http_status")
    if status == 401:
        return InvocationPortError("authentication_failed")
    if status == 403:
        return InvocationPortError("permission_denied")
    if status == 404:
        return InvocationPortError("model_not_found")
    if status in (408, 504):
        return InvocationPortError("provider_timeout")
    if status == 429:
        return InvocationPortError("rate_limited")
    if 500 <= status <= 599:
        return InvocationPortError("provider_overloaded")
    if 400 <= status <= 499:
        return InvocationPortError("invalid_request")
    if 300 <= status <= 399:
        return InvocationPortError("provider_protocol_error")
    return InvocationPortError("provider_protocol_error")
