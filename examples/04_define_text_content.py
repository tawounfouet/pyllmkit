"""L2.2: compose typed text parts without network, provider or credentials."""

from pyllmkit.domain import Content, TextContent

content = Content(
    parts=(TextContent("Bonjour"), TextContent(" "), TextContent("PyLLMKit")),
)

assert [part.kind for part in content.parts] == ["text", "text", "text"]
assert "".join(part.text for part in content.parts if isinstance(part, TextContent)) == (
    "Bonjour PyLLMKit"
)
print("L2.2 content primitives: OK")
