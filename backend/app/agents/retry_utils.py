"""Async retry utility with exponential backoff."""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Callable, Coroutine, TypeVar

_T = TypeVar("_T")
_log = logging.getLogger(__name__)


async def retry_async(
    fn: Callable[..., Coroutine[Any, Any, _T]],
    *,
    max_retries: int = 3,
    delay_ms: int = 1000,
    backoff_factor: float = 2.0,
) -> _T:
    """Retry an async function with exponential backoff.

    Args:
        fn: Async callable to retry.
        max_retries: Maximum number of attempts.
        delay_ms: Initial delay in milliseconds.
        backoff_factor: Multiplier for each successive delay.

    Returns:
        The result of fn().

    Raises:
        The last exception if all retries fail.
    """
    delay = delay_ms / 1000.0
    last_exc: Exception | None = None

    for attempt in range(max_retries):
        try:
            return await fn()
        except Exception as e:
            last_exc = e
            if attempt < max_retries - 1:
                _log.debug(
                    "retry_async attempt %d/%d failed: %s",
                    attempt + 1, max_retries, e,
                )
                await asyncio.sleep(delay)
                delay *= backoff_factor
            else:
                _log.warning(
                    "retry_async exhausted %d attempts: %s",
                    max_retries, e,
                )

    raise last_exc  # type: ignore[misc]
