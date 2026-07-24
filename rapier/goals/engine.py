# Copyright (c) 2026 Sourav Kumar Dubey. All rights reserved.
# SPDX-License-Identifier: MIT
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

"""rapier-ai — goal engine for lifecycle management."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from rapier.goals.budget import BUDGETS, Budget


class GoalStatus(Enum):
    """Goal lifecycle states."""

    ACTIVE = "active"
    COMPLETE = "complete"
    FAILED = "failed"
    BLOCKED = "blocked"
    PAUSED = "paused"


@dataclass
class Goal:
    """A goal to be achieved by the agent."""

    id: str
    objective: str
    status: GoalStatus
    budget: Budget
    created_at: datetime
    tokens_used: int = 0
    turns_used: int = 0
    result: str | None = None

    @property
    def hours_elapsed(self) -> float:
        return (datetime.now() - self.created_at).total_seconds() / 3600

    @property
    def is_done(self) -> bool:
        return self.status in (GoalStatus.COMPLETE, GoalStatus.FAILED)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "objective": self.objective,
            "status": self.status.value,
            "budget": str(self.budget),
            "tokens_used": self.tokens_used,
            "turns_used": self.turns_used,
            "hours_elapsed": round(self.hours_elapsed, 2),
            "result": self.result,
        }


class GoalEngine:
    """Manages goal lifecycle: create → track → complete/fail.

    Tracks token usage, turn count, and time elapsed against budget limits.
    """

    def __init__(self) -> None:
        self._goals: dict[str, Goal] = {}

    def create(self, objective: str, budget: str = "standard") -> Goal:
        """Create a new goal."""
        budget_obj = BUDGETS.get(budget)
        if budget_obj is None:
            raise ValueError(f"Unknown budget: {budget}. Choose from: {', '.join(BUDGETS)}")

        goal = Goal(
            id=str(uuid4()),
            objective=objective,
            status=GoalStatus.ACTIVE,
            budget=budget_obj,
            created_at=datetime.now(),
        )
        self._goals[goal.id] = goal
        return goal

    def get(self, goal_id: str) -> Goal | None:
        return self._goals.get(goal_id)

    @property
    def active_goal(self) -> Goal | None:
        """Get the current active goal, if any."""
        for goal in self._goals.values():
            if goal.status == GoalStatus.ACTIVE:
                return goal
        return None

    def record_usage(self, goal_id: str, input_tokens: int, output_tokens: int) -> None:
        """Record token usage for a goal."""
        goal = self._goals.get(goal_id)
        if goal is None:
            return
        goal.tokens_used += input_tokens + output_tokens

    def record_turn(self, goal_id: str) -> None:
        """Record one turn for a goal."""
        goal = self._goals.get(goal_id)
        if goal is None:
            return
        goal.turns_used += 1

    def check_budget(self, goal_id: str) -> bool:
        """Check if budget is exhausted. Returns True if exhausted."""
        goal = self._goals.get(goal_id)
        if goal is None:
            return False
        return goal.budget.is_exhausted(goal.tokens_used, goal.turns_used, goal.hours_elapsed)

    def complete(self, goal_id: str, result: str | None = None) -> Goal | None:
        """Mark a goal as complete."""
        goal = self._goals.get(goal_id)
        if goal is None:
            return None
        goal.status = GoalStatus.COMPLETE
        goal.result = result
        return goal

    def fail(self, goal_id: str, reason: str | None = None) -> Goal | None:
        """Mark a goal as failed."""
        goal = self._goals.get(goal_id)
        if goal is None:
            return None
        goal.status = GoalStatus.FAILED
        goal.result = reason
        return goal

    def pause(self, goal_id: str) -> Goal | None:
        goal = self._goals.get(goal_id)
        if goal is None:
            return None
        goal.status = GoalStatus.PAUSED
        return goal

    def resume(self, goal_id: str) -> Goal | None:
        goal = self._goals.get(goal_id)
        if goal is None or goal.status != GoalStatus.PAUSED:
            return None
        goal.status = GoalStatus.ACTIVE
        return goal

    def format_status(self, goal_id: str) -> str:
        """Format a human-readable status line for a goal."""
        goal = self._goals.get(goal_id)
        if goal is None:
            return "No goal found"

        remaining = goal.budget.remaining(goal.tokens_used, goal.turns_used, goal.hours_elapsed)

        parts = [
            f"Goal: {goal.objective}",
            f"Status: {goal.status.value}",
            f"Turns: {goal.turns_used}",
            f"Tokens: {goal.tokens_used // 1000}K",
            f"Time: {goal.hours_elapsed:.1f}h",
        ]

        if remaining["tokens"] is not None:
            parts.append(f"Token budget left: {remaining['tokens'] // 1000}K")
        if remaining["turns"] is not None:
            parts.append(f"Turn budget left: {remaining['turns']}")
        if remaining["hours"] is not None:
            parts.append(f"Time budget left: {remaining['hours']}h")

        return " | ".join(parts)
