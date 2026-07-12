# Copyright (c) 2026 Sourav Kumar Dubey. All rights reserved.
# SPDX-License-Identifier: MIT
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

"""Tests for the goal engine."""

from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from rapier.goals.budget import BUDGETS, Budget
from rapier.goals.engine import Goal, GoalEngine, GoalStatus
from rapier.goals.verifier import GoalVerifier, VerificationResult
from rapier.llm.types import LLMResponse, Usage


# ── Budget tests ────────────────────────────────────────────────────


class TestBudget:
    def test_budget_profiles_exist(self):
        assert "quick" in BUDGETS
        assert "standard" in BUDGETS
        assert "deep" in BUDGETS
        assert "unlimited" in BUDGETS

    def test_quick_budget_limits(self):
        b = BUDGETS["quick"]
        assert b.tokens == 2_000_000
        assert b.turns == 50
        assert b.hours == 2

    def test_unlimited_budget(self):
        b = BUDGETS["unlimited"]
        assert b.tokens is None
        assert b.turns is None
        assert b.hours is None
        assert not b.is_exhausted(999_999_999, 999_999, 999_999)

    def test_budget_exhausted_by_tokens(self):
        b = Budget(tokens=1000, turns=50, hours=8)
        assert b.is_exhausted(tokens_used=1000, turns_used=10, hours_elapsed=1)
        assert not b.is_exhausted(tokens_used=999, turns_used=10, hours_elapsed=1)

    def test_budget_exhausted_by_turns(self):
        b = Budget(tokens=1000, turns=50, hours=8)
        assert b.is_exhausted(tokens_used=100, turns_used=50, hours_elapsed=1)
        assert not b.is_exhausted(tokens_used=100, turns_used=49, hours_elapsed=1)

    def test_budget_exhausted_by_hours(self):
        b = Budget(tokens=1000, turns=50, hours=8)
        assert b.is_exhausted(tokens_used=100, turns_used=10, hours_elapsed=8)
        assert not b.is_exhausted(tokens_used=100, turns_used=10, hours_elapsed=7.99)

    def test_budget_remaining(self):
        b = Budget(tokens=1000, turns=50, hours=8)
        r = b.remaining(tokens_used=200, turns_used=10, hours_elapsed=2)
        assert r["tokens"] == 800
        assert r["turns"] == 40
        assert r["hours"] == 6.0

    def test_budget_remaining_unlimited(self):
        b = Budget()
        r = b.remaining(tokens_used=100, turns_used=10, hours_elapsed=1)
        assert r["tokens"] is None
        assert r["turns"] is None
        assert r["hours"] is None

    def test_budget_str(self):
        assert "2M tokens" in str(BUDGETS["quick"])
        assert "unlimited" in str(BUDGETS["unlimited"])


# ── GoalEngine tests ────────────────────────────────────────────────


class TestGoalEngine:
    def test_create_goal(self):
        engine = GoalEngine()
        g = engine.create("add error handling", budget="quick")
        assert g.objective == "add error handling"
        assert g.status == GoalStatus.ACTIVE
        assert g.budget.tokens == 2_000_000
        assert g.id in engine._goals

    def test_create_unknown_budget_raises(self):
        engine = GoalEngine()
        with pytest.raises(ValueError, match="Unknown budget"):
            engine.create("test", budget="nonexistent")

    def test_get_goal(self):
        engine = GoalEngine()
        g = engine.create("test goal")
        assert engine.get(g.id) is g
        assert engine.get("nonexistent") is None

    def test_active_goal(self):
        engine = GoalEngine()
        assert engine.active_goal is None
        g = engine.create("test")
        assert engine.active_goal is g
        engine.complete(g.id)
        assert engine.active_goal is None

    def test_record_usage(self):
        engine = GoalEngine()
        g = engine.create("test")
        engine.record_usage(g.id, input_tokens=100, output_tokens=50)
        assert g.tokens_used == 150

    def test_record_turn(self):
        engine = GoalEngine()
        g = engine.create("test")
        engine.record_turn(g.id)
        engine.record_turn(g.id)
        assert g.turns_used == 2

    def test_check_budget(self):
        engine = GoalEngine()
        g = engine.create("test", budget="quick")
        assert not engine.check_budget(g.id)
        for _ in range(50):
            engine.record_turn(g.id)
        assert engine.check_budget(g.id)

    def test_complete_goal(self):
        engine = GoalEngine()
        g = engine.create("test")
        result = engine.complete(g.id, result="Done!")
        assert result.status == GoalStatus.COMPLETE
        assert result.result == "Done!"
        assert g.is_done

    def test_fail_goal(self):
        engine = GoalEngine()
        g = engine.create("test")
        result = engine.fail(g.id, reason="Budget exhausted")
        assert result.status == GoalStatus.FAILED
        assert result.result == "Budget exhausted"
        assert g.is_done

    def test_pause_resume(self):
        engine = GoalEngine()
        g = engine.create("test")
        engine.pause(g.id)
        assert g.status == GoalStatus.PAUSED
        engine.resume(g.id)
        assert g.status == GoalStatus.ACTIVE

    def test_format_status(self):
        engine = GoalEngine()
        g = engine.create("test", budget="quick")
        engine.record_usage(g.id, 5000, 2000)
        engine.record_turn(g.id)
        status = engine.format_status(g.id)
        assert "test" in status
        assert "active" in status
        assert "Turns: 1" in status

    def test_goal_to_dict(self):
        engine = GoalEngine()
        g = engine.create("test")
        d = g.to_dict()
        assert d["objective"] == "test"
        assert d["status"] == "active"


# ── GoalVerifier tests ──────────────────────────────────────────────


class TestGoalVerifier:
    @pytest.mark.asyncio
    async def test_verify_complete(self):
        mock_llm = AsyncMock()
        mock_llm.chat.return_value = LLMResponse(
            content='{"complete": true, "reason": "All tests pass", "confidence": 0.95}',
            usage=Usage(input_tokens=100, output_tokens=50),
        )
        verifier = GoalVerifier(llm=mock_llm)
        result = await verifier.verify("add error handling", "Added try/except blocks")
        assert result.complete is True
        assert result.confidence == 0.95

    @pytest.mark.asyncio
    async def test_verify_incomplete(self):
        mock_llm = AsyncMock()
        mock_llm.chat.return_value = LLMResponse(
            content='{"complete": false, "reason": "Missing tests", "confidence": 0.8}',
            usage=Usage(input_tokens=100, output_tokens=50),
        )
        verifier = GoalVerifier(llm=mock_llm)
        result = await verifier.verify("add error handling", "Added some try/except")
        assert result.complete is False
        assert "Missing tests" in result.reason

    @pytest.mark.asyncio
    async def test_verify_json_in_markdown(self):
        mock_llm = AsyncMock()
        mock_llm.chat.return_value = LLMResponse(
            content='Here is my analysis:\n```json\n{"complete": true, "reason": "Looks good", "confidence": 0.9}\n```',
            usage=Usage(input_tokens=100, output_tokens=50),
        )
        verifier = GoalVerifier(llm=mock_llm)
        result = await verifier.verify("test", "evidence")
        assert result.complete is True

    @pytest.mark.asyncio
    async def test_verify_exception(self):
        mock_llm = AsyncMock()
        mock_llm.chat.side_effect = Exception("API error")
        verifier = GoalVerifier(llm=mock_llm)
        result = await verifier.verify("test", "evidence")
        assert result.complete is False
        assert "Verification failed" in result.reason


# ── Goal status transitions ─────────────────────────────────────────


class TestGoalTransitions:
    def test_goal_is_done_when_complete(self):
        engine = GoalEngine()
        g = engine.create("test")
        assert not g.is_done
        engine.complete(g.id)
        assert g.is_done

    def test_goal_is_done_when_failed(self):
        engine = GoalEngine()
        g = engine.create("test")
        assert not g.is_done
        engine.fail(g.id)
        assert g.is_done

    def test_goal_hours_elapsed(self):
        engine = GoalEngine()
        g = engine.create("test")
        assert g.hours_elapsed >= 0
        assert g.hours_elapsed < 0.01  # should be near zero
