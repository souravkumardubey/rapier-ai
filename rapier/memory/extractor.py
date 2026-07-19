# Copyright (c) 2026 Sourav Kumar Dubey. All rights reserved.
# SPDX-License-Identifier: MIT
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

"""rapier-ai — fact extraction from tool results using LLM."""

from __future__ import annotations

import json
from typing import Any

from rapier.llm.types import Message


class FactExtractor:
    """Extracts durable facts from tool results using LLM."""

    def __init__(self, llm: Any):
        self.llm = llm

    async def extract(
        self,
        tool_name: str,
        result: str,
        source_file: str = "",
    ) -> list[dict[str, str]]:
        """Extract facts from a tool result.

        Returns list of dicts with keys: topic, concept, fact.
        """
        if len(result.strip()) < 50:
            return []

        prompt = (
            "Extract durable facts from this tool result.\n"
            "Focus on: configuration values, API signatures, data structures, "
            "conventions, dependencies.\n"
            "Ignore: temporary state, errors, output noise.\n\n"
            f"Tool: {tool_name}\n"
            f"Source file: {source_file}\n"
            f"Result:\n{result[:3000]}\n\n"
            "Return a JSON array of facts. Each fact has: topic, concept, fact.\n"
            "Example:\n"
            '[{"topic": "authentication", "concept": "JWT config", '
            '"fact": "Uses RS256 signing algorithm with 1-hour token expiry"}]\n\n'
            "Return ONLY the JSON array, no other text."
        )

        response = await self.llm.chat(
            messages=[Message(role="user", content=prompt)],
            tools=[],
        )

        return self._parse_response(response.content or "")

    def _parse_response(self, content: str) -> list[dict[str, str]]:
        """Parse LLM response into fact list."""
        try:
            start = content.find("[")
            end = content.rfind("]") + 1
            if start >= 0 and end > start:
                return json.loads(content[start:end])
        except (json.JSONDecodeError, ValueError):
            pass
        return []

    async def extract_from_tool_results(
        self,
        tool_results: list[tuple[str, str, str]],
    ) -> list[dict[str, str]]:
        """Extract facts from multiple tool results.

        tool_results: list of (tool_name, result, source_file)
        """
        all_facts: list[dict[str, str]] = []
        for tool_name, result, source_file in tool_results:
            facts = await self.extract(tool_name, result, source_file)
            all_facts.extend(facts)
        return all_facts
