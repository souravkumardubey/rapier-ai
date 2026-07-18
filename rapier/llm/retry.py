# Copyright (c) 2026 Sourav Kumar Dubey. All rights reserved.
# SPDX-License-Identifier: MIT
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

"""rapier-ai — retry with exponential backoff for LLM API calls."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


async def with_retry(
    fn: Callable[[], Awaitable[T]],
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    retryable_errors: tuple[type[Exception], ...] = (Exception,),
) -> T:
    """Execute an async function with exponential backoff retry.

    Args:
        fn: Async callable to execute (no arguments).
        max_retries: Maximum number of retry attempts.
        base_delay: Initial delay in seconds between retries.
        max_delay: Maximum delay in seconds between retries.
        retryable_errors: Tuple of exception types that trigger a retry.

    Returns:
        The result of the function call.

    Raises:
        The last exception if all retries fail.
    """
    last_error: Exception | None = None

    for attempt in range(max_retries + 1):
        try:
            return await fn()
        except retryable_errors as e:
            last_error = e
            if attempt < max_retries:
                delay = min(base_delay * (2**attempt), max_delay)
                logger.debug(
                    "Retry %d/%d after %.1fs: %s",
                    attempt + 1,
                    max_retries,
                    delay,
                    e,
                )
                await asyncio.sleep(delay)

    raise last_error  # type: ignore[misc]
