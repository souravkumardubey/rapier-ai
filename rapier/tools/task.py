# Copyright (c) 2026 Sourav Kumar Dubey. All rights reserved.
# SPDX-License-Identifier: MIT
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

"""rapier-ai — task tool for sub-agent spawning."""

from __future__ import annotations

from typing import Any

from rapier.llm.types import ToolDefinition
from rapier.tools.base import BaseTool, register_tool


@register_tool
class TaskTool(BaseTool):
    """Delegate a task to the multi-agent coordinator."""

    name = "task"
    description = "Delegate a focused task to a sub-agent with isolated context"

    def __init__(self, coordinator: Any | None = None):
        self.coordinator = coordinator

    def get_schema(self) -> ToolDefinition:
        return ToolDefinition(
            name=self.name,
            description=self.description,
            parameters={
                "type": "object",
                "properties": {
                    "description": {
                        "type": "string",
                        "description": "Clear description of the task for the sub-agent",
                    },
                    "prompt": {
                        "type": "string",
                        "description": "Detailed prompt for the sub-agent to execute",
                    },
                },
                "required": ["description", "prompt"],
            },
        )

    async def execute(self, input: dict[str, Any]) -> str:
        if not self.coordinator:
            return "Error: Multi-agent system not initialized. Run with --multi-agent flag."

        description = input["description"]
        prompt = input["prompt"]

        result = await self.coordinator.execute(task=prompt)

        status = "PASSED" if result.passed else "FAILED"
        output = f"[Task {status}] {description}\n"
        output += f"Rounds: {result.rounds}\n"
        if result.content:
            output += f"\nResult:\n{result.content}"
        if result.verification_issues:
            output += "\n\nVerification issues:\n" + "\n".join(result.verification_issues)

        return output
