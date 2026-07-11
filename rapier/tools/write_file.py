# Copyright (c) 2025 Sourav Kumar Dubey. All rights reserved.
# SPDX-License-Identifier: MIT
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

"""rapier-ai — write file tool."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from rapier.llm.types import ToolDefinition
from rapier.tools.base import BaseTool, register_tool


@register_tool
class WriteFileTool(BaseTool):
    """Create or overwrite a file."""

    name = "write_file"
    description = "Write content to a file, creating it if it doesn't exist"

    def get_schema(self) -> ToolDefinition:
        return ToolDefinition(
            name=self.name,
            description=self.description,
            parameters={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative path to the file",
                    },
                    "content": {
                        "type": "string",
                        "description": "Full file content to write",
                    },
                },
                "required": ["path", "content"],
            },
        )

    async def execute(self, input: dict[str, Any]) -> str:
        path = Path(input["path"])
        content = input["content"]

        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
            lines = len(content.split("\n"))
            return f"OK — wrote {lines} lines to {path}"
        except Exception as e:
            return f"Error writing {path}: {e}"
