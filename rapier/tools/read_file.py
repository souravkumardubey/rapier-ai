# Copyright (c) 2026 Sourav Kumar Dubey. All rights reserved.
# SPDX-License-Identifier: MIT
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

"""rapier-ai — read file tool."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from rapier.llm.types import ToolDefinition
from rapier.tools.base import BaseTool, register_tool


@register_tool
class ReadFileTool(BaseTool):
    """Read the contents of a file."""

    name = "read_file"
    description = "Read the contents of a file at the given path"

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
                    }
                },
                "required": ["path"],
            },
        )

    async def execute(self, input: dict[str, Any]) -> str:
        path = Path(input["path"])

        if not path.exists():
            return f"Error: File not found: {path}"

        if path.is_dir():
            return f"Error: {path} is a directory, not a file"

        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            return f"Error: {path} is not a text file (binary file)"

        lines = content.split("\n")
        if len(lines) > 2000:
            truncated = "\n".join(lines[:2000])
            remaining = len(lines) - 2000
            return f"{truncated}\n\n... ({remaining} more lines)"

        return content
