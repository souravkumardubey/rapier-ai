# Copyright (c) 2026 Sourav Kumar Dubey. All rights reserved.
# SPDX-License-Identifier: MIT
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

"""rapier-ai — budget definitions for goal engine."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Budget:
    """Resource limits for a goal.

    None means unlimited.
    """

    tokens: int | None = None
    turns: int | None = None
    hours: float | None = None

    def is_exhausted(self, tokens_used: int, turns_used: int, hours_elapsed: float) -> bool:
        """Check if any budget limit is hit."""
        if self.tokens is not None and tokens_used >= self.tokens:
            return True
        if self.turns is not None and turns_used >= self.turns:
            return True
        if self.hours is not None and hours_elapsed >= self.hours:
            return True
        return False

    def remaining(self, tokens_used: int, turns_used: int, hours_elapsed: float) -> dict[str, Any]:
        """Return remaining budget for each dimension."""
        return {
            "tokens": (self.tokens - tokens_used) if self.tokens else None,
            "turns": (self.turns - turns_used) if self.turns else None,
            "hours": round(self.hours - hours_elapsed, 2) if self.hours else None,
        }

    def __str__(self) -> str:
        parts: list[str] = []
        if self.tokens:
            parts.append(f"{self.tokens // 1_000_000}M tokens")
        if self.turns:
            parts.append(f"{self.turns} turns")
        if self.hours:
            parts.append(f"{self.hours}h")
        return " / ".join(parts) if parts else "unlimited"


# Pre-defined budget profiles
BUDGETS: dict[str, Budget] = {
    "quick": Budget(tokens=2_000_000, turns=50, hours=2),
    "standard": Budget(tokens=10_000_000, turns=200, hours=8),
    "deep": Budget(tokens=100_000_000, turns=1000, hours=24),
    "unlimited": Budget(tokens=None, turns=None, hours=None),
}
