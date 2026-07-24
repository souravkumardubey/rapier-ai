# Copyright (c) 2026 Sourav Kumar Dubey. All rights reserved.
# SPDX-License-Identifier: MIT
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

"""Tests for agent base class."""

from __future__ import annotations

from typing import Any

import pytest

from rapier.agents.base import Agent, AgentConfig
from rapier.llm.types import LLMResponse, Usage


# ── Helpers ──────────────────────────────────────────────────────────


class MockLLM:
    """Mock LLM that returns a fixed response."""

    def __init__(self, content: str = "Done"):
        self.content = content
        self.call_count = 0

    async def chat(self, messages, tools, system=None, model=None):
        self.call_count += 1
        return LLMResponse(
            content=self.content,
            tool_calls=[],
            usage=Usage(input_tokens=10, output_tokens=5),
        )


class MockTool:
    """Mock tool for testing."""

    def __init__(self, name: str):
        self.name = name
        self.description = f"Mock tool: {name}"

    def get_schema(self):
        from rapier.llm.types import ToolDefinition

        return ToolDefinition(name=self.name, description=self.description)

    async def execute(self, input):
        return f"Executed {self.name}"


def _make_tools() -> dict[str, Any]:
    return {
        t.name: t
        for t in [MockTool("read_file"), MockTool("write_file"), MockTool("bash"), MockTool("grep")]
    }


# ── Tests ────────────────────────────────────────────────────────────


class TestAgentConfig:
    def test_defaults(self):
        config = AgentConfig(name="Test")
        assert config.name == "Test"
        assert config.model is None
        assert config.allowed_tools is None
        assert config.max_iterations == 20
        assert config.system_prompt_extra == ""

    def test_custom_values(self):
        config = AgentConfig(
            name="Coder",
            model="claude-sonnet",
            allowed_tools=["read_file", "write_file"],
            max_iterations=10,
            system_prompt_extra="Be careful.",
        )
        assert config.model == "claude-sonnet"
        assert config.allowed_tools == ["read_file", "write_file"]
        assert config.max_iterations == 10


class TestAgent:
    def test_filters_tools_by_config(self):
        tools = _make_tools()
        agent = Agent(
            config=AgentConfig(name="Test", allowed_tools=["read_file", "bash"]),
            llm=MockLLM(),
            all_tools=tools,
        )
        assert "read_file" in agent.tools
        assert "bash" in agent.tools
        assert "write_file" not in agent.tools
        assert "grep" not in agent.tools

    def test_all_tools_when_none(self):
        tools = _make_tools()
        agent = Agent(
            config=AgentConfig(name="Test", allowed_tools=None),
            llm=MockLLM(),
            all_tools=tools,
        )
        assert len(agent.tools) == 4

    def test_builds_system_prompt(self):
        agent = Agent(
            config=AgentConfig(
                name="Coder",
                allowed_tools=["read_file"],
                system_prompt_extra="Write clean code.",
            ),
            llm=MockLLM(),
            all_tools=_make_tools(),
        )
        prompt = agent._build_system_prompt()
        assert "Coder" in prompt
        assert "read_file" in prompt
        assert "Write clean code." in prompt

    @pytest.mark.asyncio
    async def test_run_calls_agent_loop(self):
        agent = Agent(
            config=AgentConfig(name="Test", max_iterations=5),
            llm=MockLLM(content="Hello"),
            all_tools=_make_tools(),
        )
        result = await agent.run(prompt="Do something")
        assert result.completed is True
        assert result.content == "Hello"

    @pytest.mark.asyncio
    async def test_run_with_context(self):
        llm = MockLLM(content="Done")
        agent = Agent(
            config=AgentConfig(name="Test"),
            llm=llm,
            all_tools=_make_tools(),
        )
        result = await agent.run(prompt="Do task", context="Extra info")
        assert result.completed is True
        # Verify context was prepended to prompt
        assert llm.call_count == 1
