"""Provider-agnostic Interaction Domain: text Message primitives.

L2.1/L2.2 implement Role, Message, ContentPart, TextContent, Content.
Image/media and versioned Interaction JSON codec follow in L2.3/L2.4.
Conversation, provider mapping and tool execution remain deferred.
"""

from .content import Content
from .message import Message
from .parts import ContentPart
from .roles import Role
from .text import TextContent

__all__ = ["Content", "ContentPart", "Message", "Role", "TextContent"]
