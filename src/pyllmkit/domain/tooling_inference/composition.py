"""Immutable P4 wrappers, preserving M3 request/response and Inference JSON v1."""

from dataclasses import dataclass, field

from pyllmkit.domain.errors import DomainValidationError
from pyllmkit.domain.inference import InferenceRequest, InferenceRunId
from pyllmkit.domain.structured_output import (
    JsonResponseFormat,
    ResponseFormat,
    SchemaResponseFormat,
    StructuredOutput,
    TextResponseFormat,
)
from pyllmkit.domain.tooling import (
    Tool,
    ToolCall,
    ToolCallId,
    ToolChoice,
    ToolResult,
    attach_tool_result,
    validate_tool_choice,
    validate_tool_set,
)


@dataclass(frozen=True, slots=True)
class ToolingInferenceIntent:
    """Compose an untouched M3 request with P4 declarations and format intent."""

    request: InferenceRequest = field(repr=False)
    tools: tuple[Tool, ...] = field(default=(), repr=False)
    tool_choice: ToolChoice | None = None
    response_format: ResponseFormat | None = field(default=None, repr=False)

    def __post_init__(self) -> None:
        if type(self.request) is not InferenceRequest:
            raise DomainValidationError("ToolingInferenceIntent.request must be InferenceRequest")
        validate_tool_set(self.tools)
        validate_tool_choice(self.tool_choice, self.tools)
        if self.response_format is not None and type(self.response_format) not in (
            TextResponseFormat, JsonResponseFormat, SchemaResponseFormat
        ):
            raise DomainValidationError("ToolingInferenceIntent.response_format is invalid")


@dataclass(frozen=True, slots=True)
class ToolCallOutput:
    """An observed group of requests for tools, not executed tool results."""

    calls: tuple[ToolCall, ...] = field(repr=False)

    def __post_init__(self) -> None:
        if type(self.calls) is not tuple or not self.calls or any(
            type(call) is not ToolCall for call in self.calls
        ):
            raise DomainValidationError("ToolCallOutput.calls must be nonempty tuple[ToolCall]")
        ids: set[ToolCallId] = set()
        for call in self.calls:
            if call.call_id in ids:
                raise DomainValidationError("ToolCallOutput contains duplicate call IDs")
            ids.add(call.call_id)


@dataclass(frozen=True, slots=True)
class ToolingInferenceObservation:
    """P4-only observation; does not claim an M3 response or run completion.

    Any run_id must be provided explicitly by the caller. Correlation of
    caller-supplied final results is checked without executing tools.
    """

    call_output: ToolCallOutput | None = field(default=None, repr=False)
    structured_output: StructuredOutput | None = field(default=None, repr=False)
    results: tuple[ToolResult, ...] = field(default=(), repr=False)
    run_id: InferenceRunId | None = None

    def __post_init__(self) -> None:
        if self.call_output is not None and type(self.call_output) is not ToolCallOutput:
            raise DomainValidationError("observation.call_output must be ToolCallOutput or None")
        if self.structured_output is not None and (
            type(self.structured_output) is not StructuredOutput
        ):
            raise DomainValidationError("observation.structured_output must be StructuredOutput or None")
        if self.run_id is not None and type(self.run_id) is not InferenceRunId:
            raise DomainValidationError("observation.run_id must be InferenceRunId or None")
        if type(self.results) is not tuple or any(
            type(result) is not ToolResult for result in self.results
        ):
            raise DomainValidationError("observation.results must be tuple[ToolResult]")
        if self.call_output is None and self.structured_output is None:
            raise DomainValidationError("observation requires calls or a structured output")
        if self.results and self.call_output is None:
            raise DomainValidationError("observation results require observed tool calls")
        if self.call_output is not None:
            attached: tuple[ToolResult, ...] = ()
            for result in self.results:
                attached = attach_tool_result(self.call_output.calls, attached, result)
