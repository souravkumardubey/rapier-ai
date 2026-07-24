# Copyright (c) 2026 Sourav Kumar Dubey. All rights reserved.
# SPDX-License-Identifier: MIT
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

"""Tests for retry with exponential backoff."""

from __future__ import annotations

import asyncio

import pytest

from rapier.llm.retry import with_retry


# ── Helpers ──────────────────────────────────────────────────────────


class TransientError(Exception):
    """A temporary error that should be retried."""


class PermanentError(Exception):
    """A permanent error that should not be retried."""


# ── Tests ────────────────────────────────────────────────────────────


class TestWithRetry:
    @pytest.mark.asyncio
    async def test_succeeds_on_first_try(self):
        call_count = 0

        async def fn():
            nonlocal call_count
            call_count += 1
            return "success"

        result = await with_retry(fn, max_retries=3)
        assert result == "success"
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_succeeds_after_failure(self):
        call_count = 0

        async def fn():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise TransientError("temporary")
            return "recovered"

        result = await with_retry(
            fn,
            max_retries=3,
            base_delay=0.01,  # Fast for tests
            retryable_errors=(TransientError,),
        )
        assert result == "recovered"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_exhausts_retries(self):
        async def fn():
            raise TransientError("always fails")

        with pytest.raises(TransientError):
            await with_retry(
                fn,
                max_retries=2,
                base_delay=0.01,
                retryable_errors=(TransientError,),
            )

    @pytest.mark.asyncio
    async def test_does_not_retry_non_retryable_error(self):
        call_count = 0

        async def fn():
            nonlocal call_count
            call_count += 1
            raise PermanentError("permanent")

        with pytest.raises(PermanentError):
            await with_retry(
                fn,
                max_retries=3,
                base_delay=0.01,
                retryable_errors=(TransientError,),
            )
        assert call_count == 1  # No retries

    @pytest.mark.asyncio
    async def test_respects_max_retries(self):
        call_count = 0

        async def fn():
            nonlocal call_count
            call_count += 1
            raise TransientError("fail")

        with pytest.raises(TransientError):
            await with_retry(
                fn,
                max_retries=0,  # No retries allowed
                base_delay=0.01,
                retryable_errors=(TransientError,),
            )
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_retry_with_exception_types(self):
        """Test that specific exception types are matched."""
        call_count = 0

        async def fn():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ValueError("value error")
            return "ok"

        # ValueError is a subclass of Exception, so it should be retried
        result = await with_retry(
            fn,
            max_retries=3,
            base_delay=0.01,
            retryable_errors=(ValueError,),
        )
        assert result == "ok"
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_exponential_backoff_delays(self):
        """Verify delays increase exponentially."""
        delays = []
        call_count = 0

        async def fn():
            nonlocal call_count
            call_count += 1
            if call_count <= 3:
                raise TransientError("fail")
            return "ok"

        original_sleep = asyncio.sleep

        async def mock_sleep(delay):
            delays.append(delay)

        # Monkey-patch asyncio.sleep for testing
        asyncio.sleep = mock_sleep
        try:
            result = await with_retry(
                fn,
                max_retries=3,
                base_delay=1.0,
                max_delay=30.0,
                retryable_errors=(TransientError,),
            )
        finally:
            asyncio.sleep = original_sleep

        assert result == "ok"
        assert len(delays) == 3
        # Check exponential progression: 1.0, 2.0, 4.0
        assert delays[0] == 1.0
        assert delays[1] == 2.0
        assert delays[2] == 4.0

    @pytest.mark.asyncio
    async def test_max_delay_cap(self):
        """Verify delays are capped at max_delay."""
        delays = []
        call_count = 0

        async def fn():
            nonlocal call_count
            call_count += 1
            if call_count <= 5:
                raise TransientError("fail")
            return "ok"

        original_sleep = asyncio.sleep

        async def mock_sleep(delay):
            delays.append(delay)

        asyncio.sleep = mock_sleep
        try:
            await with_retry(
                fn,
                max_retries=5,
                base_delay=10.0,
                max_delay=15.0,
                retryable_errors=(TransientError,),
            )
        finally:
            asyncio.sleep = original_sleep

        # All delays should be capped at 15.0
        assert all(d <= 15.0 for d in delays)

    @pytest.mark.asyncio
    async def test_no_args_function(self):
        """Test retry with a function that takes no arguments."""

        async def ok_fn():
            return "ok"

        result = await with_retry(
            ok_fn,
            max_retries=1,
            base_delay=0.01,
        )
        assert result == "ok"
