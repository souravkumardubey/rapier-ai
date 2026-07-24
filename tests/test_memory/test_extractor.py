# Copyright (c) 2026 Sourav Kumar Dubey. All rights reserved.
# SPDX-License-Identifier: MIT
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

"""Tests for fact extractor."""

from __future__ import annotations

from typing import Any

import pytest

from rapier.llm.types import LLMResponse, Usage
from rapier.memory.extractor import FactExtractor


# ── Helpers ──────────────────────────────────────────────────────────


class MockLLM:
    """Mock LLM that returns a JSON array of facts."""

    def __init__(self, response: str = ""):
        self._response = response
        self.call_count = 0

    async def chat(self, messages, tools, system=None, model=None):
        self.call_count += 1
        return LLMResponse(
            content=self._response,
            tool_calls=[],
            usage=Usage(input_tokens=10, output_tokens=5),
        )


# ── Tests ────────────────────────────────────────────────────────────


class TestFactExtractor:
    @pytest.mark.asyncio
    async def test_extract_facts_from_tool_result(self):
        response = (
            '[{"topic": "auth", "concept": "JWT config", '
            '"fact": "Uses RS256 signing with 1h expiry"}]'
        )
        llm = MockLLM(response=response)
        extractor = FactExtractor(llm)

        facts = await extractor.extract(
            tool_name="read_file",
            result="AUTH_CONFIG = {'signing': 'RS256', 'expiry': 3600}",
            source_file="auth.py",
        )

        assert len(facts) == 1
        assert facts[0]["topic"] == "auth"
        assert facts[0]["concept"] == "JWT config"
        assert "RS256" in facts[0]["fact"]

    @pytest.mark.asyncio
    async def test_extract_short_result_returns_empty(self):
        llm = MockLLM()
        extractor = FactExtractor(llm)

        facts = await extractor.extract(tool_name="bash", result="ok")

        assert len(facts) == 0
        assert llm.call_count == 0

    @pytest.mark.asyncio
    async def test_parse_response_malformed_json(self):
        llm = MockLLM(response="not json at all")
        extractor = FactExtractor(llm)

        facts = await extractor.extract(tool_name="bash", result="x" * 100)

        assert len(facts) == 0

    @pytest.mark.asyncio
    async def test_extract_multiple_facts(self):
        response = (
            '[{"topic": "db", "concept": "connection", "fact": "pool_size=10"}, '
            '{"topic": "db", "concept": "driver", "fact": "asyncpg"}]'
        )
        llm = MockLLM(response=response)
        extractor = FactExtractor(llm)

        facts = await extractor.extract(
            tool_name="read_file",
            result="DB_CONFIG = {'pool_size': 10, 'driver': 'asyncpg'}",
        )

        assert len(facts) == 2

    @pytest.mark.asyncio
    async def test_extract_from_multiple_tool_results(self):
        response = '[{"topic": "test", "concept": "config", "fact": "pytest"}]'
        llm = MockLLM(response=response)
        extractor = FactExtractor(llm)

        tool_results = [
            (
                "read_file",
                "pytest config in pyproject.toml with all the settings",
                "pyproject.toml",
            ),
            ("read_file", "another file content here for testing purposes today", "setup.cfg"),
        ]

        facts = await extractor.extract_from_tool_results(tool_results)
        assert len(facts) == 2
