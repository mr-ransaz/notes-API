import math
import time
from collections.abc import Callable
from dataclasses import dataclass
from threading import Lock


class RateLimitExceeded(Exception):
    def __init__(self, retry_after: int) -> None:
        self.retry_after = retry_after
        super().__init__("Too many login attempts")


@dataclass
class _Failures:
    count: int
    expires_at: float


class LoginRateLimiter:
    """Fixed five-minute failure windows; deliberately local to one process."""

    def __init__(
        self, *, clock: Callable[[], float] = time.monotonic, max_keys: int = 10000
    ) -> None:
        self._clock = clock
        self._max_keys = max_keys
        self._failures: dict[tuple[str, str], _Failures] = {}
        self._lock = Lock()

    def authenticate[T](
        self, key: tuple[str, str], verify: Callable[[], T | None]
    ) -> T | None:
        # Serialize check + verification + accounting so parallel attempts cannot
        # pass the threshold together. This trades login throughput for simplicity.
        with self._lock:
            now = self._clock()
            self._failures = {
                key: failures
                for key, failures in self._failures.items()
                if failures.expires_at > now
            }
            failures = self._failures.get(key)
            if failures is not None and failures.count >= 5:
                raise RateLimitExceeded(max(1, math.ceil(failures.expires_at - now)))
            if failures is None and len(self._failures) >= self._max_keys:
                # Fail closed rather than evicting live limits or growing forever.
                earliest = min(item.expires_at for item in self._failures.values())
                raise RateLimitExceeded(max(1, math.ceil(earliest - now)))
            result = verify()
            if result is None:
                if failures is None:
                    failures = _Failures(count=0, expires_at=now + 300)
                    self._failures[key] = failures
                failures.count += 1
            else:
                self._failures.pop(key, None)
            return result
