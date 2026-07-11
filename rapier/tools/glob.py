"""rapier-ai — glob file finder tool."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from rapier.llm.types import ToolDefinition
from rapier.tools.base import BaseTool, register_tool


@register_tool
class GlobTool(BaseTool):
    """Find files by pattern."""

    name = "glob"
    description = "Find files matching a glob pattern"

    def get_schema(self) -> ToolDefinition:
        return ToolDefinition(
            name=self.name,
            description=self.description,
            parameters={
                "type": "object",
                "properties": {
                    "pattern": {
                        "type": "string",
                        "description": "Glob pattern (e.g., '**/*.py', 'src/**/*.ts')",
                    }
                },
                "required": ["pattern"],
            },
        )

    async def execute(self, input: dict[str, Any]) -> str:
        pattern = input["pattern"]

        try:
            matches = sorted(Path(".").glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True)

            if not matches:
                return f"No files found matching '{pattern}'"

            files = [str(p) for p in matches if p.is_file()][:200]

            if not files:
                return f"No files found matching '{pattern}'"

            if len(files) > 200:
                return "\n".join(files[:200]) + f"\n\n... ({len(matches) - 200} more files)"

            return "\n".join(files)

        except Exception as e:
            return f"Error: {e}"
