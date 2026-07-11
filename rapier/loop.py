"""rapier-ai — agent loop (the heart of everything)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from rapier.llm.types import LLMResponse, Message, ToolCall, ToolResult, Usage


@dataclass
class AgentResult:
    """Result of an agent loop execution."""

    content: str | None = None
    iterations: int = 0
    usage: Usage = field(default_factory=lambda: Usage(input_tokens=0, output_tokens=0))
    completed: bool = False


async def agent_loop(
    prompt: str,
    tools: dict[str, Any],
    llm: Any,
    system_prompt: str,
    max_iterations: int = 50,
    on_tool_call: Callable | None = None,
    on_tool_result: Callable | None = None,
) -> AgentResult:
    """Run the agent loop — the core while(true) that drives everything.

    1. Send messages to LLM
    2. If response has tool calls → execute them, feed results back
    3. If no tool calls → return response
    4. Repeat until done or max iterations
    """
    messages: list[Message] = [Message(role="user", content=prompt)]
    total_usage = Usage(input_tokens=0, output_tokens=0)

    for i in range(max_iterations):
        # Call LLM
        tool_defs = [t.get_schema() for t in tools.values()] if tools else []
        response: LLMResponse = await llm.chat(
            messages=messages,
            tools=tool_defs,
            system=system_prompt,
        )

        # Track usage
        total_usage.input_tokens += response.usage.input_tokens
        total_usage.output_tokens += response.usage.output_tokens

        # No tool calls = agent is done
        if not response.tool_calls:
            return AgentResult(
                content=response.content,
                iterations=i + 1,
                usage=total_usage,
                completed=True,
            )

        # Append assistant message with tool calls
        messages.append(
            Message(
                role="assistant",
                content=response.content,
                tool_calls=response.tool_calls,
            )
        )

        # Execute each tool call
        for tool_call in response.tool_calls:
            tool = tools.get(tool_call.name)

            if on_tool_call:
                await on_tool_call(tool_call)

            if not tool:
                result = ToolResult(
                    tool_call_id=tool_call.id,
                    content=f"Error: Unknown tool '{tool_call.name}'",
                    is_error=True,
                )
            else:
                try:
                    output = await tool.execute(tool_call.input)
                    result = ToolResult(tool_call_id=tool_call.id, content=output)
                except Exception as e:
                    result = ToolResult(
                        tool_call_id=tool_call.id,
                        content=f"Error executing {tool_call.name}: {e}",
                        is_error=True,
                    )

            if on_tool_result:
                await on_tool_result(result)

            # Append tool result
            messages.append(
                Message(
                    role="tool",
                    content=result.content,
                    tool_call_id=result.tool_call_id,
                )
            )

    return AgentResult(
        content="Hit iteration limit",
        iterations=max_iterations,
        usage=total_usage,
        completed=False,
    )
