"""Generic retry helpers with bounded backoff."""

from dataclasses import dataclass
from typing import Any, Callable, Optional, Tuple, Type
import time


@dataclass(frozen=True)
class RetryPolicy:
    max_attempts: int = 3
    base_delay_seconds: float = 0.1
    max_delay_seconds: float = 1.5


def _next_delay(policy: RetryPolicy, attempt: int) -> float:
    delay = policy.base_delay_seconds * (2 ** max(0, attempt - 1))
    return min(delay, policy.max_delay_seconds)


def execute_with_retry(
    fn: Callable[[], Any],
    policy: RetryPolicy,
    retry_exceptions: Tuple[Type[BaseException], ...] = (Exception,),
    is_retryable: Optional[Callable[[BaseException], bool]] = None,
    on_retry: Optional[Callable[[BaseException, int, float], None]] = None,
) -> Any:
    """Execute function with retry and exponential backoff."""
    max_attempts = max(1, int(policy.max_attempts))
    attempt = 0
    last_error: Optional[BaseException] = None

    while attempt < max_attempts:
        attempt += 1
        try:
            return fn()
        except retry_exceptions as exc:
            last_error = exc
            retryable = is_retryable(exc) if is_retryable is not None else True
            if not retryable or attempt >= max_attempts:
                raise
            delay = _next_delay(policy, attempt)
            if on_retry is not None:
                on_retry(exc, attempt, delay)
            time.sleep(delay)

    if last_error is not None:
        raise last_error
    raise RuntimeError("Retry execution failed without a captured exception")

