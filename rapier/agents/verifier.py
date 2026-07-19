# Copyright (c) 2026 Sourav Kumar Dubey. All rights reserved.
# SPDX-License-Identifier: MIT
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

"""rapier-ai — verifier specialist agent."""

from __future__ import annotations

from typing import Any

from rapier.agents.base import Agent, AgentConfig


def create_verifier(llm: Any, all_tools: dict[str, Any]) -> Agent:
    """Create a Verifier agent (Opus-class, read-only + bash for tests)."""
    return Agent(
        config=AgentConfig(
            name="Verifier",
            allowed_tools=["read_file", "bash", "glob", "grep"],
            max_iterations=10,
            system_prompt_extra=(
                "You are a code verifier. Review code for correctness.\n"
                "Run tests to verify functionality.\n"
                "Be critical — find bugs, edge cases, and style issues.\n"
                "End your response with PASS or FAIL on its own line."
            ),
        ),
        llm=llm,
        all_tools=all_tools,
    )
