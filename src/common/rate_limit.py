"""Simple per-domain rate limiter (token bucket style)."""
import time
from collections import defaultdict

class DomainRateLimiter:
    def __init__(self, per_minute: int):
        self.capacity = max(per_minute, 1)
        self.tokens = defaultdict(lambda: self.capacity)
        self.updated = defaultdict(lambda: time.time())

    def consume(self, domain: str):
        now = time.time()
        last = self.updated[domain]
        elapsed = now - last
        # Refill
        refill = (elapsed / 60.0) * self.capacity
        if refill >= 1:
            self.tokens[domain] = min(self.capacity, self.tokens[domain] + int(refill))
            self.updated[domain] = now
        if self.tokens[domain] <= 0:
            # Sleep until one token would be available
            to_wait = 60.0 / self.capacity
            time.sleep(to_wait)
            self.tokens[domain] = 0  # after sleep, fall through
        self.tokens[domain] -= 1