"""L2.4: offline, provider-free, versioned text/image Message JSON round-trip."""

import json

from pyllmkit.domain import (
    Content,
    ImageContent,
    MediaSourceRef,
    Message,
    Role,
    TextContent,
    message_from_dict,
    message_to_dict,
)

message = Message(
    Role.USER,
    Content((
        TextContent("Décris "),
        ImageContent(MediaSourceRef("asset", "image-123")),
        TextContent(" puis résume."),
    )),
)
payload = json.loads(json.dumps(message_to_dict(message), ensure_ascii=False))
assert payload["schema_version"] == 1
assert [part["kind"] for part in payload["content"]["parts"]] == ["text", "image", "text"]
assert message_from_dict(payload) == message
print("L2.4 Interaction JSON round-trip: OK")
