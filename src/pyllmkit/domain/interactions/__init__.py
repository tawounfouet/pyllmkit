"""Provider-agnostic Interaction Domain: content primitives (L2.2).

Role and Message follow in L2.1. Image and media references follow in L2.3;
the independent Interaction JSON codec follows in L2.4.
"""

from .content import Content
from .parts import ContentPart
from .text import TextContent

__all__ = ["Content", "ContentPart", "TextContent"]
