# Copyright (c) 2026 Sourav Kumar Dubey. All rights reserved.
# SPDX-License-Identifier: MIT
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

"""Tests for specialist agent factories."""

from __future__ import annotations

from typing import Any

from rapier.agents.base import Agent
from rapier.agents.coder import create_coder
from rapier.agents.researcher import create_researcher
from rapier.agents.verifier import create_verifier
from rapier.llm.types import LLMResponse, Usage


# ── Helpers ──────────────────────────────────────────────────────────


class MockLLM:
    async def chat(self, messages, tools, system=None, model=None):
        return LLMResponse(
            content="ok", tool_calls=[], usage=Usage(input_tokens=5, output_tokens=2)
        )


class MockTool:
    def __init__(self, name: str):
        self.name = name
        self.description = f"Mock: {name}"

    def get_schema(self):
        from rapier.llm.types import ToolDefinition

        return ToolDefinition(name=self.name, description=self.description)

    async def execute(self, input):
        return f"Executed {self.name}"


def _all_tools() -> dict[str, Any]:
    names = ["read_file", "write_file", "edit_file", "bash", "grep", "glob", "web_fetch", "task"]
    return {name: MockTool(name) for name in names}


# ── Tests ────────────────────────────────────────────────────────────


class TestCreateCoder:
    def test_returns_agent(self):
        agent = create_coder(MockLLM(), _all_tools())
        assert isinstance(agent, Agent)

    def test_has_correct_tools(self):
        agent = create_coder(MockLLM(), _all_tools())
        expected = {"read_file", "write_file", "edit_file", "bash", "grep", "glob"}
        assert set(agent.tools.keys()) == expected

    def test_max_iterations(self):
        agent = create_coder(MockLLM(), _all_tools())
        assert agent.config.max_iterations == 20

    def test_system_prompt_includes_name(self):
        agent = create_coder(MockLLM(), _all_tools())
        prompt = agent._build_system_prompt()
        assert "Coder" in prompt
        assert "code specialist" in prompt


class TestCreateResearcher:
    def test_returns_agent(self):
        agent = create_researcher(MockLLM(), _all_tools())
        assert isinstance(agent, Agent)

    def test_has_correct_tools(self):
        agent = create_researcher(MockLLM(), _all_tools())
        expected = {"read_file", "grep", "glob", "web_fetch"}
        assert set(agent.tools.keys()) == expected

    def test_max_iterations(self):
        agent = create_researcher(MockLLM(), _all_tools())
        assert agent.config.max_iterations == 10

    def test_system_prompt_includes_name(self):
        agent = create_researcher(MockLLM(), _all_tools())
        prompt = agent._build_system_prompt()
        assert "Researcher" in prompt
        assert "research specialist" in prompt


class TestCreateVerifier:
    def test_returns_agent(self):
        agent = create_verifier(MockLLM(), _all_tools())
        assert isinstance(agent, Agent)

    def test_has_correct_tools(self):
        agent = create_verifier(MockLLM(), _all_tools())
        expected = {"read_file", "bash", "glob", "grep"}
        assert set(agent.tools.keys()) == expected

    def test_max_iterations(self):
        agent = create_verifier(MockLLM(), _all_tools())
        assert agent.config.max_iterations == 10

    def test_system_prompt_includes_name(self):
        agent = create_verifier(MockLLM(), _all_tools())
        prompt = agent._build_system_prompt()
        assert "Verifier" in prompt
        assert "code verifier" in prompt
        assert "PASS" in prompt or "FAIL" in prompt
