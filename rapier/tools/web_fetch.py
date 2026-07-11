# Copyright (c) 2025 Sourav Kumar Dubey. All rights reserved.
# SPDX-License-Identifier: MIT
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

"""rapier-ai — web fetch tool."""

from __future__ import annotations

from typing import Any

from rapier.llm.types import ToolDefinition
from rapier.tools.base import BaseTool, register_tool


@register_tool
class WebFetchTool(BaseTool):
    """Fetch content from a URL."""

    name = "web_fetch"
    description = "Fetch and return the content of a URL"

    def get_schema(self) -> ToolDefinition:
        return ToolDefinition(
            name=self.name,
            description=self.description,
            parameters={
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "URL to fetch",
                    }
                },
                "required": ["url"],
            },
        )

    async def execute(self, input: dict[str, Any]) -> str:
        import aiohttp

        url = input["url"]

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                    if resp.status != 200:
                        return f"Error: HTTP {resp.status}"

                    content_type = resp.headers.get("content-type", "")
                    if "text" not in content_type and "json" not in content_type:
                        return f"Error: Non-text content type: {content_type}"

                    text = await resp.text()

                    # Truncate very long content
                    if len(text) > 50000:
                        return text[:50000] + f"\n\n... (truncated, {len(text)} total chars)"

                    return text

        except Exception as e:
            return f"Error fetching {url}: {e}"
