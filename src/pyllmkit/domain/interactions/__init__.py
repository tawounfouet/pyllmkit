"""Provider-agnostic Interaction Domain: typed text and image content.

L2.1/L2.2: Role, Message, ContentPart, TextContent and Content.
L2.3: MediaSourceRef and ImageContent (passive references; no I/O).
L2.4: independent Interaction JSON codec will follow.
Conversation, provider adapters, tool execution and other media remain deferred.
"""

from .content import Content
from .image import ImageContent
from .media import MediaSourceRef
from .message import Message
from .parts import ContentPart
from .roles import Role
from .text import TextContent

__all__ = [
    "Content",
    "ContentPart",
    "ImageContent",
    "MediaSourceRef",
    "Message",
    "Role",
    "TextContent",
]
