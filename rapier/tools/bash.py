# Copyright (c) 2026 Sourav Kumar Dubey. All rights reserved.
# SPDX-License-Identifier: MIT
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

"""rapier-ai — bash command execution tool."""

from __future__ import annotations

import asyncio
from typing import Any

from rapier.llm.types import ToolDefinition
from rapier.tools.base import BaseTool, register_tool


@register_tool
class BashTool(BaseTool):
    """Execute a shell command."""

    name = "bash"
    description = "Execute a shell command and return stdout/stderr"

    def __init__(self, timeout: int = 30, cwd: str | None = None):
        self.timeout = timeout
        self.cwd = cwd

    def get_schema(self) -> ToolDefinition:
        return ToolDefinition(
            name=self.name,
            description=self.description,
            parameters={
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "Shell command to execute",
                    }
                },
                "required": ["command"],
            },
        )

    async def execute(self, input: dict[str, Any]) -> str:
        command = input["command"]

        try:
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self.cwd,
            )

            try:
                stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=self.timeout)
            except asyncio.TimeoutError:
                process.kill()
                await process.communicate()
                return f"Error: Command timed out after {self.timeout}s"

            stdout_str = stdout.decode("utf-8", errors="replace")
            stderr_str = stderr.decode("utf-8", errors="replace")

            output = ""
            if stdout_str:
                output += stdout_str
            if stderr_str:
                output += f"\n[stderr]\n{stderr_str}" if output else stderr_str

            if not output:
                output = f"Command completed with exit code {process.returncode}"

            # Truncate very long output
            lines = output.split("\n")
            if len(lines) > 500:
                truncated = "\n".join(lines[:250])
                tail = "\n".join(lines[-250:])
                output = f"{truncated}\n\n... ({len(lines) - 500} lines omitted) ...\n\n{tail}"

            return output

        except Exception as e:
            return f"Error executing command: {e}"
