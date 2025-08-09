"""
Integration hooks for Radar system with existing Web-LLM researcher.
Provides optional enhancements that can be integrated into the existing workflow.
"""
import logging
from typing import Dict, List, Optional, Any, Union
from pathlib import Path

# Import radar modules
try:
    from src.radar.config import get_radar_config
    from src.radar.embedding_cache import get_embedding_cache
    from src.radar.boilerplate_filter import strip_boilerplate
    from src.radar.pdf_discovery import get_pdf_discovery
    from src.radar.async_fetcher import fetch_urls
    RADAR_AVAILABLE = True
except ImportError:
    RADAR_AVAILABLE = False

logger = logging.getLogger(__name__)


class RadarIntegration:
    """Integration layer for Radar enhancements."""
    
    def __init__(self):
        self.enabled = RADAR_AVAILABLE
        if not self.enabled:
            logger.info("Radar modules not available, using fallback implementations")
    
    def is_enabled(self, feature: str) -> bool:
        """Check if a radar feature is enabled."""
        if not self.enabled:
            return False
        
        try:
            config = get_radar_config()
            return config.is_enabled(feature)
        except Exception:
            return False
    
    def get_cached_embedding(self, text: str, model: str) -> Optional[List[float]]:
        """Get embedding from cache if available."""
        if not self.is_enabled('embedding_cache'):
            return None
        
        try:
            cache = get_embedding_cache()
            return cache.get_embedding(text, model)
        except Exception as e:
            logger.warning(f"Failed to get cached embedding: {e}")
            return None
    
    def store_embedding(self, text: str, model: str, embedding: List[float]) -> None:
        """Store embedding in cache."""
        if not self.is_enabled('embedding_cache'):
            return
        
        try:
            cache = get_embedding_cache()
            cache.store_embedding(text, model, embedding)
        except Exception as e:
            logger.warning(f"Failed to store embedding: {e}")
    
    def flush_embedding_cache(self) -> None:
        """Flush pending embeddings to cache."""
        if not self.is_enabled('embedding_cache'):
            return
        
        try:
            cache = get_embedding_cache()
            cache.flush_batch()
        except Exception as e:
            logger.warning(f"Failed to flush embedding cache: {e}")
    
    def filter_boilerplate(self, content: str, source_name: str) -> str:
        """Remove boilerplate content from text."""
        if not self.enabled:
            return content
        
        try:
            filtered_content, metadata = strip_boilerplate(content, source_name)
            if metadata.get('boilerplate_removed', 0) > 0:
                logger.info(f"Removed {metadata['boilerplate_removed']} boilerplate blocks from {source_name}")
            return filtered_content
        except Exception as e:
            logger.warning(f"Failed to filter boilerplate: {e}")
            return content
    
    def discover_pdfs(self) -> List[str]:
        """Discover new PDFs for processing."""
        if not self.is_enabled('pdf.discovery'):
            return []
        
        try:
            discovery = get_pdf_discovery()
            return discovery.discover_and_enqueue()
        except Exception as e:
            logger.warning(f"Failed to discover PDFs: {e}")
            return []
    
    def fetch_urls_async(self, urls: List[str], force_sync: bool = False) -> Dict[str, Union[str, Exception]]:
        """Fetch URLs with async support if available."""
        if not self.enabled:
            # Fallback to basic requests
            import requests
            results = {}
            for url in urls:
                try:
                    response = requests.get(url, timeout=30)
                    response.raise_for_status()
                    results[url] = response.text
                except Exception as e:
                    results[url] = e
            return results
        
        try:
            return fetch_urls(urls, force_sync=force_sync)
        except Exception as e:
            logger.warning(f"Failed to fetch URLs async: {e}")
            # Fallback to basic requests
            import requests
            results = {}
            for url in urls:
                try:
                    response = requests.get(url, timeout=30)
                    response.raise_for_status()
                    results[url] = response.text
                except Exception as e:
                    results[url] = e
            return results
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get comprehensive metrics summary."""
        if not self.enabled:
            return {'radar_enabled': False}
        
        metrics = {'radar_enabled': True}
        
        try:
            # Embedding cache metrics
            if self.is_enabled('embedding_cache'):
                cache = get_embedding_cache()
                metrics['embedding_cache'] = cache.get_metrics()
            
            # PDF discovery metrics
            if self.is_enabled('pdf.discovery'):
                discovery = get_pdf_discovery()
                metrics['pdf_discovery'] = discovery.get_metrics()
            
            # Async fetcher metrics
            from src.radar.async_fetcher import get_async_fetcher
            fetcher = get_async_fetcher()
            metrics['async_fetcher'] = fetcher.get_metrics()
            
        except Exception as e:
            logger.warning(f"Failed to get metrics: {e}")
            metrics['error'] = str(e)
        
        return metrics


# Global integration instance
_radar_integration = None


def get_radar_integration() -> RadarIntegration:
    """Get global radar integration instance."""
    global _radar_integration
    if _radar_integration is None:
        _radar_integration = RadarIntegration()
    return _radar_integration


# Convenience functions for easy integration

def enhance_web_content(content: str, source_name: str) -> str:
    """Enhance web content by removing boilerplate."""
    integration = get_radar_integration()
    return integration.filter_boilerplate(content, source_name)


def get_embedding_with_cache(text: str, model: str, embedding_func) -> List[float]:
    """Get embedding with caching support."""
    integration = get_radar_integration()
    
    # Try cache first
    cached = integration.get_cached_embedding(text, model)
    if cached is not None:
        return cached
    
    # Compute embedding
    embedding = embedding_func(text)
    
    # Store in cache
    integration.store_embedding(text, model, embedding)
    
    return embedding


def fetch_research_urls(urls: List[str], use_async: bool = True) -> Dict[str, str]:
    """Fetch research URLs with async support."""
    integration = get_radar_integration()
    results = integration.fetch_urls_async(urls, force_sync=not use_async)
    
    # Filter out errors and return only successful content
    successful_results = {}
    for url, content in results.items():
        if isinstance(content, str):
            successful_results[url] = content
        else:
            logger.warning(f"Failed to fetch {url}: {content}")
    
    return successful_results


def discover_additional_sources() -> List[str]:
    """Discover additional PDF sources for research."""
    integration = get_radar_integration()
    return integration.discover_pdfs()


def get_system_metrics() -> Dict[str, Any]:
    """Get comprehensive system metrics."""
    integration = get_radar_integration()
    return integration.get_metrics_summary()