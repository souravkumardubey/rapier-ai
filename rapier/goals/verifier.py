# Copyright (c) 2026 Sourav Kumar Dubey. All rights reserved.
# SPDX-License-Identifier: MIT
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

"""rapier-ai — goal verifier using a different model (maker/checker)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from rapier.llm.types import Message


@dataclass
class VerificationResult:
    """Result of verifying goal completion."""

    complete: bool
    reason: str
    confidence: float = 0.0


class GoalVerifier:
    """Verifies goal completion using a different model (maker/checker pattern).

    The verifier uses a separate LLM (typically a stronger model like Opus)
    to evaluate whether the coder's work actually achieves the goal.
    This prevents the coder from grading its own homework.
    """

    def __init__(self, llm: Any) -> None:
        self.llm = llm

    async def verify(self, objective: str, evidence: str) -> VerificationResult:
        """Verify if a goal has been achieved based on evidence.

        Args:
            objective: The original goal description.
            evidence: What the agent did (tool outputs, file changes, etc.).

        Returns:
            VerificationResult with complete flag and reason.
        """
        prompt = f"""You are a code reviewer verifying whether a goal has been achieved.

Goal: {objective}

Evidence of completion:
{evidence}

Evaluate whether this goal is ACTUALLY complete. Consider:
1. Does the evidence directly address the goal?
2. Are there any missing pieces or partial implementations?
3. Would the code work as described?

Respond with ONLY a JSON object (no markdown, no extra text):
{{"complete": true/false, "reason": "brief explanation", "confidence": 0.0-1.0}}"""

        try:
            response = await self.llm.chat(
                messages=[Message(role="user", content=prompt)],
                tools=[],
                system="You are a precise code reviewer. Respond only with valid JSON.",
            )

            content = response.content or "{}"
            # Try to extract JSON from the response
            result = self._parse_json(content)
            return VerificationResult(
                complete=result.get("complete", False),
                reason=result.get("reason", "Could not parse verification"),
                confidence=result.get("confidence", 0.5),
            )

        except Exception as e:
            return VerificationResult(
                complete=False,
                reason=f"Verification failed: {e}",
                confidence=0.0,
            )

    def _parse_json(self, text: str) -> dict[str, Any]:
        """Extract JSON from potentially messy LLM output."""
        # Try direct parse
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # Try to find JSON in the text
        start = text.find("{")
        end = text.rfind("}") + 1
        if start != -1 and end > start:
            try:
                return json.loads(text[start:end])
            except json.JSONDecodeError:
                pass

        return {}
