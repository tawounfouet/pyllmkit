# Tool Calling - Une demande d'appel n'est pas une exécution

Un `ToolCall` est identifié par `ToolCallId`, explicitement fourni par le caller. Il contient le nom d'outil et des `ToolArguments` bruts et/ou parsés. Deux calls aux arguments identiques mais aux IDs distincts sont deux entités distinctes.

```python
from pyllmkit.domain.tooling import (
    Tool, ToolSchema, ToolArguments, ToolCall, ToolCallId, ToolResult,
    ValidationStatus, validate_tool_call, attach_tool_result,
)

tool = Tool("lookup", None, ToolSchema({"type": "object"}))
call = ToolCall(
    ToolCallId("call-001"), "lookup",
    ToolArguments(raw="{}", parsed={}),
)
assert validate_tool_call(call, (tool,)).status is ValidationStatus.VALID
# Le résultat ci-dessous est fourni explicitement, sans exécuter l'outil.
result = ToolResult(call.call_id, {"illustrative": True})
attached = attach_tool_result((call,), (), result)
assert attached == (result,)
```

`raw` est conservé sans parsing implicite; `has_parsed` distingue une valeur absente de JSON null. `validate_tool_call` retourne VALID seulement après validation du parsed contre P4-JSON-1. Un résultat orphelin ou dupliqué est refusé. Le champ `is_error` indique un échec observé, pas une exception Python à rejouer.

Voir [API Tool Calling](../api/tool-calling.md), ADR-023/025, [exemple 14](../../examples/14_define_tool_call_and_result.py).
