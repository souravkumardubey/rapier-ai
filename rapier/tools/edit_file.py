# Copyright (c) 2026 Sourav Kumar Dubey. All rights reserved.
# SPDX-License-Identifier: MIT
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

"""rapier-ai — edit file tool (diff-based)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from rapier.llm.types import ToolDefinition
from rapier.tools.base import BaseTool, register_tool


@register_tool
class EditFileTool(BaseTool):
    """Edit a file by replacing an exact string match."""

    name = "edit_file"
    description = "Edit a file by replacing an exact string match with new content"

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
                    "old_string": {
                        "type": "string",
                        "description": "Exact string to find and replace",
                    },
                    "new_string": {
                        "type": "string",
                        "description": "String to replace with",
                    },
                },
                "required": ["path", "old_string", "new_string"],
            },
        )

    async def execute(self, input: dict[str, Any]) -> str:
        path = Path(input["path"])
        old_string = input["old_string"]
        new_string = input["new_string"]

        if not path.exists():
            return f"Error: File not found: {path}"

        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            return f"Error: {path} is not a text file"

        # Check for exact match
        count = content.count(old_string)
        if count == 0:
            return f"Error: old_string not found in {path}"
        if count > 1:
            return f"Error: old_string found {count} times in {path}. Provide more context to make it unique."

        # Replace
        new_content = content.replace(old_string, new_string, 1)
        path.write_text(new_content, encoding="utf-8")

        old_lines = old_string.count("\n") + 1
        new_lines = new_string.count("\n") + 1
        return f"OK — replaced {old_lines} lines with {new_lines} lines in {path}"
