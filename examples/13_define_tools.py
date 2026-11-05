"""Offline P4 L4.1 walkthrough: declare and validate tools, never execute them."""

from pyllmkit.domain.tooling import (
    Tool,
    ToolChoice,
    ToolChoiceKind,
    ToolSchema,
    validate_tool_choice,
    validate_tool_set,
)


def main() -> None:
    schema = ToolSchema({
        "type": "object",
        "properties": {"city": {"type": "string", "minLength": 1}},
        "required": ["city"],
        "additionalProperties": False,
    })
    tools = validate_tool_set((
        Tool("get_weather", "Describe a city's weather", schema),
        Tool("lookup_city", "Resolve a city label", schema),
    ))
    policy = ToolChoice.specific("get_weather")
    validate_tool_choice(policy, tools)
    assert policy.kind is ToolChoiceKind.SPECIFIC_TOOL
    assert schema.profile == "P4-JSON-1"
    print("L4.1: two immutable tool declarations validated (no execution).")


if __name__ == "__main__":
    main()
