"""robots.txt allowance helper with caching."""
from urllib.parse import urlparse
import urllib.robotparser as rp

CACHE_TTL = 3600  # seconds

class _RobotEntry:
    def __init__(self, parser, fetched_at):
        self.parser = parser
        self.fetched_at = fetched_at

import time, requests

def is_allowed(url: str, cache: dict, user_agent: str) -> bool:
    parts = urlparse(url)
    base = f"{parts.scheme}://{parts.netloc}"
    entry = cache.get(base)
    now = time.time()
    if not entry or now - entry.fetched_at > CACHE_TTL:
        rparser = rp.RobotFileParser()
        robots_url = base + '/robots.txt'
        try:
            resp = requests.get(robots_url, timeout=10)
            if resp.status_code == 200:
                rparser.parse(resp.text.splitlines())
            else:
                rparser = None
        except Exception:
            rparser = None
        cache[base] = _RobotEntry(rparser, now)
        entry = cache[base]
    if not entry.parser:
        return True  # assume allowed if cannot parse
    return entry.parser.can_fetch(user_agent, url)