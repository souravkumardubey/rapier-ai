# Copyright (c) 2026 Sourav Kumar Dubey. All rights reserved.
# SPDX-License-Identifier: MIT
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

"""rapier-ai — coordinator for multi-agent orchestration."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from rapier.agents.base import Agent
from rapier.llm.types import Usage
from rapier.loop import AgentResult


@dataclass
class TaskResult:
    """Result of a coordinated multi-agent task."""

    content: str | None = None
    passed: bool = False
    rounds: int = 0
    usage: Usage = field(default_factory=lambda: Usage(input_tokens=0, output_tokens=0))
    research: str | None = None
    verification_issues: list[str] = field(default_factory=list)


class Coordinator:
    """Orchestrates specialist agents in a hub-and-spoke model.

    Flow:
    1. Researcher gathers context
    2. Coder implements
    3. Verifier reviews
    4. If fail -> Coder fixes (max 3 rounds)
    5. If still fail -> report to user
    """

    MAX_VERIFY_ROUNDS = 3

    def __init__(
        self,
        researcher: Agent,
        coder: Agent,
        verifier: Agent,
    ):
        self.researcher = researcher
        self.coder = coder
        self.verifier = verifier

    async def execute(
        self,
        task: str,
        on_tool_call: Callable | None = None,
        on_tool_result: Callable | None = None,
    ) -> TaskResult:
        """Coordinate research -> code -> verify cycle."""
        total_usage = Usage(input_tokens=0, output_tokens=0)

        # Phase 1: Research
        research_result = await self.researcher.run(
            prompt=f"Research how to accomplish this task: {task}",
            on_tool_call=on_tool_call,
            on_tool_result=on_tool_result,
        )
        total_usage.input_tokens += research_result.usage.input_tokens
        total_usage.output_tokens += research_result.usage.output_tokens
        research = research_result.content or "No research findings."

        # Phase 2-3: Code -> Verify (up to MAX_VERIFY_ROUNDS)
        code_result: AgentResult | None = None
        issues: list[str] = []

        for round_num in range(1, self.MAX_VERIFY_ROUNDS + 1):
            # Code
            code_prompt = f"Implement: {task}\n\nResearch findings:\n{research}"
            if issues:
                code_prompt += "\n\nFix these issues from previous verification:\n" + "\n".join(
                    issues
                )

            code_result = await self.coder.run(
                prompt=code_prompt,
                context=research,
                on_tool_call=on_tool_call,
                on_tool_result=on_tool_result,
            )
            total_usage.input_tokens += code_result.usage.input_tokens
            total_usage.output_tokens += code_result.usage.output_tokens

            # Verify
            verify_prompt = (
                f"Verify the implementation of: {task}\n\n"
                f"Code/implementer output:\n{code_result.content or '(no output)'}\n\n"
                f"Check: does this correctly implement the task? Are there bugs?"
            )
            verify_result = await self.verifier.run(
                prompt=verify_prompt,
                on_tool_call=on_tool_call,
                on_tool_result=on_tool_result,
            )
            total_usage.input_tokens += verify_result.usage.input_tokens
            total_usage.output_tokens += verify_result.usage.output_tokens

            # Parse verification result
            if self._parse_verification(verify_result.content):
                return TaskResult(
                    content=code_result.content,
                    passed=True,
                    rounds=round_num,
                    usage=total_usage,
                    research=research,
                )
            else:
                issues = self._extract_issues(verify_result.content)

        # Max rounds exhausted
        return TaskResult(
            content=code_result.content if code_result else None,
            passed=False,
            rounds=self.MAX_VERIFY_ROUNDS,
            usage=total_usage,
            research=research,
            verification_issues=issues,
        )

    def _parse_verification(self, content: str | None) -> bool:
        """Parse verifier output for pass/fail."""
        if not content:
            return False
        lower = content.lower()
        return "pass" in lower or "complete" in lower or "approved" in lower

    def _extract_issues(self, content: str | None) -> list[str]:
        """Extract issue list from verifier output."""
        if not content:
            return ["No verification output"]
        issues = []
        for line in content.split("\n"):
            line = line.strip()
            if line.startswith("- ") or line.startswith("* ") or line.startswith("Issue"):
                issues.append(line.lstrip("-* ").strip())
        return issues or [content[:500]]
