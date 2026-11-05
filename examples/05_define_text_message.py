"""AC-006: create a text Message without provider, transport or Conversation."""

from pyllmkit.domain import Content, Message, Role, TextContent

message = Message(
    role=Role.USER,
    content=Content(parts=(TextContent("Bonjour "), TextContent("PyLLMKit"))),
)

assert message.role is Role.USER
assert tuple(part.kind for part in message.content.parts) == ("text", "text")
assert message.content.parts[1].text == "PyLLMKit"
print("AC-006 text Message: OK")
