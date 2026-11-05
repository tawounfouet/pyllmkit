"""Provider-agnostic Interaction Domain: typed text and image content.

L2.1/L2.2: Role, Message, ContentPart, TextContent and Content.
L2.3: MediaSourceRef and ImageContent (passive references; no I/O).
L2.4: strict independent Interaction JSON codec v1.
Conversation, provider adapters, tool execution and other media remain deferred.
"""

from .content import Content
from .image import ImageContent
from .media import MediaSourceRef
from .message import Message
from .parts import ContentPart
from .roles import Role
from .serialization import INTERACTION_SCHEMA_VERSION, message_from_dict, message_to_dict
from .text import TextContent

__all__ = [
    "Content",
    "ContentPart",
    "ImageContent",
    "INTERACTION_SCHEMA_VERSION",
    "MediaSourceRef",
    "Message",
    "Role",
    "TextContent",
    "message_from_dict",
    "message_to_dict",
]
