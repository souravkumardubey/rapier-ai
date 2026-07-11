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
    """Spawn a sub-agent for a specific task."""

    name = "task"
    description = "Delegate a focused task to a sub-agent with isolated context"

    def __init__(self, llm_client: Any = None, tools: dict[str, Any] | None = None):
        self.llm_client = llm_client
        self.tools = tools or {}

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
        # Phase 6 will implement full sub-agent spawning
        # For now, return a placeholder
        description = input["description"]
        return f"[Task tool placeholder] Would spawn sub-agent for: {description}"
