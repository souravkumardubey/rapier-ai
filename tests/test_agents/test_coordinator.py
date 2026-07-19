# Copyright (c) 2026 Sourav Kumar Dubey. All rights reserved.
# SPDX-License-Identifier: MIT
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

"""Tests for coordinator multi-agent orchestration."""

from __future__ import annotations

from typing import Any

import pytest

from rapier.agents.base import Agent, AgentConfig
from rapier.agents.coordinator import Coordinator, TaskResult
from rapier.llm.types import LLMResponse, Usage


# ── Helpers ──────────────────────────────────────────────────────────


class MockLLM:
    """Mock LLM with configurable responses."""

    def __init__(self, responses: list[str] | None = None, content: str = "Done"):
        self._responses = responses or []
        self._index = 0
        self._default_content = content
        self.call_count = 0

    async def chat(self, messages, tools, system=None, model=None):
        self.call_count += 1
        if self._responses and self._index < len(self._responses):
            content = self._responses[self._index]
            self._index += 1
        else:
            content = self._default_content
        return LLMResponse(
            content=content,
            tool_calls=[],
            usage=Usage(input_tokens=10, output_tokens=5),
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


def _make_tools() -> dict[str, Any]:
    return {t.name: t for t in [MockTool("read_file"), MockTool("bash")]}


def _make_agent(llm: Any, name: str = "Agent", tools: dict | None = None) -> Agent:
    return Agent(
        config=AgentConfig(name=name, max_iterations=5),
        llm=llm,
        all_tools=tools or _make_tools(),
    )


# ── Tests ────────────────────────────────────────────────────────────


class TestTaskResult:
    def test_defaults(self):
        result = TaskResult()
        assert result.content is None
        assert result.passed is False
        assert result.rounds == 0
        assert result.usage.input_tokens == 0
        assert result.research is None
        assert result.verification_issues == []


class TestCoordinator:
    @pytest.mark.asyncio
    async def test_happy_path(self):
        """Research -> Code -> Verify PASS on first round."""
        # Researcher returns findings, Coder returns code, Verifier returns PASS
        researcher_llm = MockLLM(content="Found relevant patterns.")
        coder_llm = MockLLM(content="def hello(): pass")
        verifier_llm = MockLLM(content="PASS - looks correct.")

        coord = Coordinator(
            researcher=_make_agent(researcher_llm, "Researcher"),
            coder=_make_agent(coder_llm, "Coder"),
            verifier=_make_agent(verifier_llm, "Verifier"),
        )

        result = await coord.execute(task="add hello function")
        assert result.passed is True
        assert result.rounds == 1
        assert result.research == "Found relevant patterns."
        assert result.content == "def hello(): pass"

    @pytest.mark.asyncio
    async def test_retries_on_fail(self):
        """Verify FAIL -> Coder fixes -> Verify PASS."""
        researcher_llm = MockLLM(content="Research done.")
        coder_llm = MockLLM(responses=["Initial code", "Fixed code"])
        verifier_llm = MockLLM(responses=["FAIL - missing test", "PASS"])

        coord = Coordinator(
            researcher=_make_agent(researcher_llm, "Researcher"),
            coder=_make_agent(coder_llm, "Coder"),
            verifier=_make_agent(verifier_llm, "Verifier"),
        )

        result = await coord.execute(task="add feature")
        assert result.passed is True
        assert result.rounds == 2
        assert result.content == "Fixed code"

    @pytest.mark.asyncio
    async def test_max_rounds(self):
        """Verifier always fails -> stops after MAX_VERIFY_ROUNDS."""
        researcher_llm = MockLLM(content="Research.")
        coder_llm = MockLLM(content="Code v1, v2, v3")
        verifier_llm = MockLLM(content="FAIL - still broken")

        coord = Coordinator(
            researcher=_make_agent(researcher_llm, "Researcher"),
            coder=_make_agent(coder_llm, "Coder"),
            verifier=_make_agent(verifier_llm, "Verifier"),
        )

        result = await coord.execute(task="impossible task")
        assert result.passed is False
        assert result.rounds == 3
        assert len(result.verification_issues) > 0

    @pytest.mark.asyncio
    async def test_tracks_usage(self):
        """Usage accumulates across all agents."""
        researcher_llm = MockLLM(content="Research")
        coder_llm = MockLLM(content="Code")
        verifier_llm = MockLLM(content="PASS")

        coord = Coordinator(
            researcher=_make_agent(researcher_llm, "Researcher"),
            coder=_make_agent(coder_llm, "Coder"),
            verifier=_make_agent(verifier_llm, "Verifier"),
        )

        result = await coord.execute(task="task")
        # 3 agents x (10 in + 5 out) = 30 in, 15 out
        assert result.usage.input_tokens == 30
        assert result.usage.output_tokens == 15

    def test_parse_verification_pass(self):
        coord = Coordinator(
            researcher=_make_agent(MockLLM(), "R"),
            coder=_make_agent(MockLLM(), "C"),
            verifier=_make_agent(MockLLM(), "V"),
        )
        assert coord._parse_verification("PASS") is True
        assert coord._parse_verification("Looks complete.") is True
        assert coord._parse_verification("Approved!") is True
        assert coord._parse_verification("FAIL - bugs found") is False
        assert coord._parse_verification(None) is False
        assert coord._parse_verification("") is False

    def test_extract_issues(self):
        coord = Coordinator(
            researcher=_make_agent(MockLLM(), "R"),
            coder=_make_agent(MockLLM(), "C"),
            verifier=_make_agent(MockLLM(), "V"),
        )
        content = "- Missing error handling\n- No tests\n- Style issues"
        issues = coord._extract_issues(content)
        assert len(issues) == 3
        assert "Missing error handling" in issues

    def test_extract_issues_fallback(self):
        coord = Coordinator(
            researcher=_make_agent(MockLLM(), "R"),
            coder=_make_agent(MockLLM(), "C"),
            verifier=_make_agent(MockLLM(), "V"),
        )
        issues = coord._extract_issues("Just some text without bullet points")
        assert len(issues) == 1
        assert "Just some text" in issues[0]
