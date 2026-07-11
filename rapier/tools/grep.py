# Copyright (c) 2025 Sourav Kumar Dubey. All rights reserved.
# SPDX-License-Identifier: MIT
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

"""rapier-ai — grep search tool."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

from rapier.llm.types import ToolDefinition
from rapier.tools.base import BaseTool, register_tool


@register_tool
class GrepTool(BaseTool):
    """Search file contents using ripgrep."""

    name = "grep"
    description = "Search for a pattern in file contents using regex"

    def get_schema(self) -> ToolDefinition:
        return ToolDefinition(
            name=self.name,
            description=self.description,
            parameters={
                "type": "object",
                "properties": {
                    "pattern": {
                        "type": "string",
                        "description": "Regex pattern to search for",
                    },
                    "path": {
                        "type": "string",
                        "description": "Directory or file to search in (default: current directory)",
                    },
                    "include": {
                        "type": "string",
                        "description": "File pattern to include (e.g., '*.py')",
                    },
                },
                "required": ["pattern"],
            },
        )

    async def execute(self, input: dict[str, Any]) -> str:
        pattern = input["pattern"]
        path = input.get("path", ".")
        include = input.get("include")

        cmd = ["rg", "--no-heading", "-n", pattern]
        if include:
            cmd.extend(["--glob", include])
        cmd.append(path)

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode == 1:
                return "No matches found"

            output = result.stdout
            if not output:
                return "No matches found"

            lines = output.strip().split("\n")
            if len(lines) > 100:
                truncated = "\n".join(lines[:100])
                return f"{truncated}\n\n... ({len(lines) - 100} more matches)"

            return output

        except FileNotFoundError:
            return "Error: ripgrep (rg) not installed. Install with: brew install ripgrep"
        except subprocess.TimeoutExpired:
            return "Error: Search timed out"
        except Exception as e:
            return f"Error: {e}"
