import time
from typing import Optional

class RateLimiter:
    def __init__(self, min_gap_s: float) -> None:
        self.min_gap_s = float(min_gap_s)
        self._last: Optional[float] = None

    def wait(self) -> None:
        if self._last is None or self.min_gap_s <= 0: return
        elapsed = time.monotonic() - self._last
        if elapsed < self.min_gap_s:
            time.sleep(self.min_gap_s - elapsed)

    def mark(self) -> None:
        self._last = time.monotonic()
