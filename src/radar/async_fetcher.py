"""
Parallel / Asynchronous Fetching Module.
Provides async HTTP fetching with per-domain rate limiting and fallback.
"""
import asyncio
import time
import logging
from typing import List, Dict, Optional, Union, Tuple
from urllib.parse import urlparse
from collections import defaultdict, deque
import random

from .config import get_radar_config

logger = logging.getLogger(__name__)

# Try to import httpx, fall back to requests
try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False
    import requests


class TokenBucket:
    """Simple token bucket for rate limiting."""
    
    def __init__(self, rate: float, capacity: int):
        self.rate = rate  # tokens per second
        self.capacity = capacity
        self.tokens = capacity
        self.last_update = time.time()
    
    def consume(self, tokens: int = 1) -> bool:
        """Try to consume tokens. Returns True if successful."""
        now = time.time()
        
        # Add tokens based on elapsed time
        elapsed = now - self.last_update
        self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
        self.last_update = now
        
        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        return False
    
    def wait_time(self, tokens: int = 1) -> float:
        """Get time to wait before tokens are available."""
        if self.tokens >= tokens:
            return 0.0
        return (tokens - self.tokens) / self.rate


class AsyncFetcher:
    """Async HTTP fetcher with domain-based rate limiting."""
    
    def __init__(self):
        config = get_radar_config()
        concurrency_config = config.get_section('ethics.concurrency')
        
        self.enabled = concurrency_config.get('enabled', True)
        self.max_concurrency = concurrency_config.get('max_concurrency', 8)
        self.per_domain_max = concurrency_config.get('per_domain_max', 2)
        
        # Rate limiting (requests per second per domain)
        self.rate_limit_per_domain = 2.0  # 2 requests per second per domain
        
        # Domain-specific semaphores and rate limiters
        self.domain_semaphores = defaultdict(lambda: asyncio.Semaphore(self.per_domain_max))
        self.domain_buckets = defaultdict(lambda: TokenBucket(self.rate_limit_per_domain, 10))
        self.retry_delays = defaultdict(float)  # For exponential backoff
        
        # Global semaphore
        self.global_semaphore = asyncio.Semaphore(self.max_concurrency)
    
    def _get_domain(self, url: str) -> str:
        """Extract domain from URL."""
        return urlparse(url).netloc.lower()
    
    async def _wait_for_rate_limit(self, domain: str) -> None:
        """Wait for rate limit if necessary."""
        bucket = self.domain_buckets[domain]
        wait_time = bucket.wait_time()
        
        if wait_time > 0:
            logger.debug(f"Rate limiting {domain}: waiting {wait_time:.2f}s")
            await asyncio.sleep(wait_time)
        
        bucket.consume()
    
    async def _handle_retry_after(self, domain: str, retry_after: Optional[str]) -> None:
        """Handle Retry-After header."""
        if retry_after:
            try:
                delay = float(retry_after)
                delay = min(delay, 300)  # Cap at 5 minutes
                logger.info(f"Retry-After for {domain}: {delay}s")
                await asyncio.sleep(delay)
            except ValueError:
                # Could be HTTP date format, just wait a bit
                await asyncio.sleep(5)
    
    async def _exponential_backoff(self, domain: str, attempt: int) -> None:
        """Apply exponential backoff."""
        base_delay = 1.0
        max_delay = 60.0
        jitter_factor = 0.1
        
        delay = min(base_delay * (2 ** attempt), max_delay)
        jitter = delay * jitter_factor * random.random()
        total_delay = delay + jitter
        
        logger.debug(f"Backoff for {domain}: {total_delay:.2f}s (attempt {attempt})")
        await asyncio.sleep(total_delay)
    
    async def _fetch_single_async(self, url: str, session, max_retries: int = 3) -> Tuple[str, Union[str, Exception]]:
        """Fetch a single URL asynchronously."""
        domain = self._get_domain(url)
        
        async with self.global_semaphore:
            async with self.domain_semaphores[domain]:
                for attempt in range(max_retries + 1):
                    try:
                        # Rate limiting
                        await self._wait_for_rate_limit(domain)
                        
                        # Make request
                        response = await session.get(url, timeout=30.0, follow_redirects=True)
                        
                        if response.status_code == 200:
                            content = response.text
                            return url, content
                        elif response.status_code == 429:
                            # Rate limited
                            retry_after = response.headers.get('retry-after')
                            await self._handle_retry_after(domain, retry_after)
                            continue
                        elif response.status_code == 503:
                            # Service unavailable
                            retry_after = response.headers.get('retry-after')
                            await self._handle_retry_after(domain, retry_after)
                            if attempt < max_retries:
                                await self._exponential_backoff(domain, attempt)
                            continue
                        else:
                            return url, Exception(f"HTTP {response.status_code}")
                    
                    except Exception as e:
                        if attempt < max_retries:
                            await self._exponential_backoff(domain, attempt)
                        else:
                            return url, e
                
                return url, Exception("Max retries exceeded")
    
    def _fetch_single_sync(self, url: str, max_retries: int = 3) -> Tuple[str, Union[str, Exception]]:
        """Fetch a single URL synchronously (fallback)."""
        domain = self._get_domain(url)
        
        for attempt in range(max_retries + 1):
            try:
                # Simple rate limiting for sync mode
                time.sleep(0.5)  # Basic delay between requests
                
                response = requests.get(url, timeout=30, allow_redirects=True)
                
                if response.status_code == 200:
                    return url, response.text
                elif response.status_code in (429, 503):
                    retry_after = response.headers.get('retry-after')
                    if retry_after:
                        try:
                            delay = min(float(retry_after), 60)
                            time.sleep(delay)
                        except ValueError:
                            time.sleep(5)
                    
                    if attempt < max_retries:
                        delay = min(2 ** attempt, 30)
                        time.sleep(delay)
                    continue
                else:
                    return url, Exception(f"HTTP {response.status_code}")
            
            except Exception as e:
                if attempt < max_retries:
                    delay = min(2 ** attempt, 30)
                    time.sleep(delay)
                else:
                    return url, e
        
        return url, Exception("Max retries exceeded")
    
    async def fetch_urls_async(self, urls: List[str]) -> Dict[str, Union[str, Exception]]:
        """Fetch multiple URLs asynchronously."""
        if not HTTPX_AVAILABLE:
            raise ImportError("httpx not available for async fetching")
        
        results = {}
        
        # Use TYPE_CHECKING to handle the type annotation
        if HTTPX_AVAILABLE:
            import httpx
            async with httpx.AsyncClient(
                limits=httpx.Limits(max_connections=self.max_concurrency),
                timeout=httpx.Timeout(30.0)
            ) as session:
                
                tasks = [self._fetch_single_async(url, session) for url in urls]
                completed = await asyncio.gather(*tasks, return_exceptions=True)
                
                for result in completed:
                    if isinstance(result, tuple):
                        url, content = result
                        results[url] = content
                    else:
                        # This shouldn't happen with gather, but just in case
                        logger.error(f"Unexpected result type: {type(result)}")
        
        return results
    
    def fetch_urls_sync(self, urls: List[str]) -> Dict[str, Union[str, Exception]]:
        """Fetch multiple URLs synchronously (fallback)."""
        results = {}
        
        for url in urls:
            url_result, content = self._fetch_single_sync(url)
            results[url_result] = content
        
        return results
    
    def fetch_urls(self, urls: List[str], force_sync: bool = False) -> Dict[str, Union[str, Exception]]:
        """
        Fetch multiple URLs with automatic async/sync selection.
        
        Args:
            urls: List of URLs to fetch
            force_sync: Force synchronous mode
        
        Returns:
            Dict mapping URLs to content or exceptions
        """
        if not urls:
            return {}
        
        if force_sync or not self.enabled or not HTTPX_AVAILABLE:
            logger.info(f"Fetching {len(urls)} URLs synchronously")
            return self.fetch_urls_sync(urls)
        else:
            logger.info(f"Fetching {len(urls)} URLs asynchronously")
            try:
                return asyncio.run(self.fetch_urls_async(urls))
            except Exception as e:
                logger.warning(f"Async fetching failed, falling back to sync: {e}")
                return self.fetch_urls_sync(urls)
    
    def get_metrics(self) -> Dict[str, int]:
        """Get fetcher metrics."""
        return {
            'httpx_available': HTTPX_AVAILABLE,
            'async_enabled': self.enabled,
            'max_concurrency': self.max_concurrency,
            'per_domain_max': self.per_domain_max,
            'tracked_domains': len(self.domain_buckets)
        }


# Global fetcher instance
_async_fetcher = None


def get_async_fetcher() -> AsyncFetcher:
    """Get global async fetcher instance."""
    global _async_fetcher
    if _async_fetcher is None:
        _async_fetcher = AsyncFetcher()
    return _async_fetcher


def fetch_urls(urls: List[str], force_sync: bool = False) -> Dict[str, Union[str, Exception]]:
    """Convenience function to fetch URLs."""
    fetcher = get_async_fetcher()
    return fetcher.fetch_urls(urls, force_sync=force_sync)