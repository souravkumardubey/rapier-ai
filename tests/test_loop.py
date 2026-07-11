"""rapier-ai — tests for the agent loop."""

import pytest
from rapier.loop import agent_loop, AgentResult
from rapier.llm.types import LLMResponse, Message, ToolCall, ToolResult, Usage, ToolDefinition


class MockLLM:
    """Mock LLM client for testing."""

    def __init__(self, responses: list[LLMResponse]):
        self.responses = iter(responses)
        self.calls: list[dict] = []

    async def chat(self, messages, tools, system=None, model=None):
        self.calls.append({"messages": messages, "tools": tools, "system": system})
        return next(self.responses)


class MockTool:
    """Mock tool for testing."""

    def __init__(self, name: str = "mock_tool", output: str = "mock result"):
        self.name = name
        self.output = output

    def get_schema(self):
        return ToolDefinition(
            name=self.name,
            description=f"Mock tool: {self.name}",
            parameters={"type": "object", "properties": {}},
        )

    async def execute(self, input):
        return self.output


@pytest.mark.asyncio
async def test_agent_loop_simple_response():
    """Agent loop returns LLM response when no tool calls."""
    mock_llm = MockLLM([
        LLMResponse(content="Hello! I can help you.", usage=Usage(input_tokens=10, output_tokens=5)),
    ])

    result = await agent_loop(
        prompt="Hi",
        tools={},
        llm=mock_llm,
        system_prompt="You are a test agent.",
        max_iterations=5,
    )

    assert result.content == "Hello! I can help you."
    assert result.completed is True
    assert result.iterations == 1
    assert result.usage.input_tokens == 10
    assert result.usage.output_tokens == 5


@pytest.mark.asyncio
async def test_agent_loop_with_tool_call():
    """Agent loop executes tool calls and feeds results back."""
    mock_tool = MockTool("test_tool", "tool output here")
    mock_llm = MockLLM([
        # First call: request tool
        LLMResponse(
            content=None,
            tool_calls=[ToolCall(id="tc1", name="test_tool", input={})],
            usage=Usage(input_tokens=20, output_tokens=10),
        ),
        # Second call: respond after seeing tool result
        LLMResponse(
            content="The tool returned: tool output here",
            usage=Usage(input_tokens=30, output_tokens=15),
        ),
    ])

    result = await agent_loop(
        prompt="Run the test tool",
        tools={"test_tool": mock_tool},
        llm=mock_llm,
        system_prompt="You are a test agent.",
        max_iterations=5,
    )

    assert result.content == "The tool returned: tool output here"
    assert result.completed is True
    assert result.iterations == 2
    assert result.usage.input_tokens == 50
    assert result.usage.output_tokens == 25


@pytest.mark.asyncio
async def test_agent_loop_hits_iteration_limit():
    """Agent loop stops at max iterations."""
    mock_llm = MockLLM([
        LLMResponse(
            content=None,
            tool_calls=[ToolCall(id="tc1", name="test_tool", input={})],
            usage=Usage(input_tokens=10, output_tokens=5),
        ),
        LLMResponse(
            content=None,
            tool_calls=[ToolCall(id="tc2", name="test_tool", input={})],
            usage=Usage(input_tokens=10, output_tokens=5),
        ),
    ])

    result = await agent_loop(
        prompt="Keep going forever",
        tools={"test_tool": MockTool()},
        llm=mock_llm,
        system_prompt="test",
        max_iterations=2,
    )

    assert result.completed is False
    assert result.iterations == 2
    assert result.content == "Hit iteration limit"


@pytest.mark.asyncio
async def test_agent_loop_unknown_tool():
    """Agent loop handles unknown tool calls gracefully."""
    mock_llm = MockLLM([
        LLMResponse(
            content=None,
            tool_calls=[ToolCall(id="tc1", name="nonexistent_tool", input={})],
            usage=Usage(input_tokens=10, output_tokens=5),
        ),
        LLMResponse(
            content="Got an error about unknown tool",
            usage=Usage(input_tokens=10, output_tokens=5),
        ),
    ])

    result = await agent_loop(
        prompt="Use nonexistent tool",
        tools={},
        llm=mock_llm,
        system_prompt="test",
        max_iterations=5,
    )

    assert result.completed is True
    assert "error" in result.content.lower() or "unknown" in result.content.lower()
