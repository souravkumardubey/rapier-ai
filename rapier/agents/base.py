# Copyright (c) 2026 Sourav Kumar Dubey. All rights reserved.
# SPDX-License-Identifier: MIT
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

"""rapier-ai — agent base class with tool filtering."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from rapier.loop import AgentResult, agent_loop


@dataclass
class AgentConfig:
    """Configuration for a specialist agent."""

    name: str
    model: str | None = None
    allowed_tools: list[str] | None = None  # None = all tools
    max_iterations: int = 20
    system_prompt_extra: str = ""


class Agent:
    """A specialist agent with its own LLM and tool set.

    Each agent runs its own agent_loop() with filtered tools.
    The coordinator holds full context; specialists get minimal.
    """

    def __init__(
        self,
        config: AgentConfig,
        llm: Any,
        all_tools: dict[str, Any],
    ):
        self.config = config
        self.llm = llm
        if config.allowed_tools is not None:
            self.tools = {k: v for k, v in all_tools.items() if k in config.allowed_tools}
        else:
            self.tools = all_tools

    async def run(
        self,
        prompt: str,
        context: str | None = None,
        on_tool_call: Callable | None = None,
        on_tool_result: Callable | None = None,
    ) -> AgentResult:
        """Run this agent on a task with optional context."""
        full_prompt = prompt
        if context:
            full_prompt = f"Context:\n{context}\n\nTask:\n{prompt}"

        return await agent_loop(
            prompt=full_prompt,
            tools=self.tools,
            llm=self.llm,
            system_prompt=self._build_system_prompt(),
            max_iterations=self.config.max_iterations,
            on_tool_call=on_tool_call,
            on_tool_result=on_tool_result,
        )

    def _build_system_prompt(self) -> str:
        base = f"You are {self.config.name}, a specialist agent."
        if self.config.allowed_tools:
            tools_list = ", ".join(self.config.allowed_tools)
            base += f"\nYou have access to these tools: {tools_list}"
        if self.config.system_prompt_extra:
            base += f"\n{self.config.system_prompt_extra}"
        return base
