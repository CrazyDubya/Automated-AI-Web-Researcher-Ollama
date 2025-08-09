"""
Advanced PDF Discovery Module.
Discovers PDFs from index pages with queue management.
"""
import sqlite3
import time
import hashlib
import json
import logging
import re
import fnmatch
from typing import List, Dict, Optional, Set
from pathlib import Path
from urllib.parse import urljoin, urlparse
import requests
try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None

from .config import get_radar_config


logger = logging.getLogger(__name__)


class PDFDiscovery:
    """PDF discovery system with queue management."""
    
    def __init__(self):
        config = get_radar_config()
        self.enabled = config.is_enabled('pdf.discovery')
        self.max_new_per_run = config.get('pdf.discovery.max_new_per_run', 15)
        self.index_pages = config.get('pdf.discovery.index_pages', [])
        self.max_bytes_per_file = config.get('pdf.discovery.max_bytes_per_file', 5242880)
        
        # Database paths
        self.queue_db_path = Path('.radar/pdf_queue.sqlite')
        self.index_file = Path('.radar/pdf_index.jsonl')
        
        # Ensure directory exists
        self.queue_db_path.parent.mkdir(parents=True, exist_ok=True)
        
        self._init_db()
        self._known_urls = self._load_known_urls()
    
    def _init_db(self) -> None:
        """Initialize queue database."""
        with sqlite3.connect(self.queue_db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS queue (
                    url TEXT PRIMARY KEY,
                    status TEXT,
                    added_ts INTEGER,
                    last_attempt_ts INTEGER
                )
            ''')
            conn.commit()
    
    def _load_known_urls(self) -> Set[str]:
        """Load known PDF URLs from index file."""
        known_urls = set()
        
        if self.index_file.exists():
            try:
                with open(self.index_file, 'r') as f:
                    for line in f:
                        if line.strip():
                            entry = json.loads(line.strip())
                            known_urls.add(entry.get('url', ''))
            except Exception as e:
                logger.warning(f"Could not load PDF index: {e}")
        
        return known_urls
    
    def _save_pdf_entry(self, url: str, sha256: str) -> None:
        """Save PDF entry to index file."""
        entry = {
            'url': url,
            'sha256': sha256,
            'first_seen_ts': int(time.time())
        }
        
        try:
            with open(self.index_file, 'a') as f:
                f.write(json.dumps(entry) + '\n')
        except Exception as e:
            logger.warning(f"Could not save PDF entry: {e}")
    
    def _check_robots_txt(self, base_url: str, path: str) -> bool:
        """Check if path is allowed by robots.txt."""
        # Simple robots.txt check - in production would use robotparser
        try:
            robots_url = urljoin(base_url, '/robots.txt')
            response = requests.get(robots_url, timeout=10)
            if response.status_code == 200:
                # Basic check for disallowed paths
                for line in response.text.split('\n'):
                    if line.strip().lower().startswith('disallow:'):
                        disallowed = line.split(':', 1)[1].strip()
                        if disallowed and path.startswith(disallowed):
                            return False
            return True
        except Exception:
            # If we can't check robots.txt, assume allowed
            return True
    
    def _extract_pdf_links(self, html_content: str, base_url: str) -> List[str]:
        """Extract PDF links from HTML content."""
        if BeautifulSoup is None:
            logger.warning("BeautifulSoup not available, skipping PDF link extraction")
            return []
            
        soup = BeautifulSoup(html_content, 'html.parser')
        pdf_links = []
        
        for link in soup.find_all('a', href=True):
            href = link['href']
            
            # Skip non-PDF links
            if not href.lower().endswith('.pdf'):
                continue
            
            # Make absolute URL
            full_url = urljoin(base_url, href)
            
            # Validate URL
            parsed = urlparse(full_url)
            if parsed.scheme in ('http', 'https'):
                pdf_links.append(full_url)
        
        return pdf_links
    
    def _check_file_size(self, url: str) -> Optional[int]:
        """Check file size using HEAD request."""
        try:
            response = requests.head(url, timeout=10, allow_redirects=True)
            if response.status_code == 200:
                content_length = response.headers.get('content-length')
                if content_length:
                    return int(content_length)
            return None
        except Exception as e:
            logger.debug(f"Could not check size for {url}: {e}")
            return None
    
    def _matches_pattern(self, url: str, pattern: str) -> bool:
        """Check if URL matches glob pattern."""
        filename = Path(urlparse(url).path).name
        return fnmatch.fnmatch(filename, pattern)
    
    def discover_pdfs_from_index(self, index_page: Dict[str, str]) -> List[str]:
        """Discover PDFs from a single index page."""
        url = index_page['url']
        pattern = index_page.get('pattern', '*.pdf')
        
        logger.info(f"Scanning index page: {url}")
        
        try:
            # Fetch index page
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            
            # Extract PDF links
            pdf_links = self._extract_pdf_links(response.text, url)
            logger.info(f"Found {len(pdf_links)} PDF links on {url}")
            
            # Filter by pattern and size
            new_pdfs = []
            for pdf_url in pdf_links:
                # Skip if already known
                if pdf_url in self._known_urls:
                    continue
                
                # Check pattern
                if not self._matches_pattern(pdf_url, pattern):
                    continue
                
                # Check robots.txt
                parsed_url = urlparse(pdf_url)
                if not self._check_robots_txt(f"{parsed_url.scheme}://{parsed_url.netloc}", parsed_url.path):
                    logger.debug(f"Robots.txt disallows {pdf_url}")
                    continue
                
                # Check file size
                file_size = self._check_file_size(pdf_url)
                if file_size and file_size > self.max_bytes_per_file:
                    logger.debug(f"File too large: {pdf_url} ({file_size} bytes)")
                    continue
                
                new_pdfs.append(pdf_url)
                
                # Respect max_new_per_run limit
                if len(new_pdfs) >= self.max_new_per_run:
                    break
            
            return new_pdfs
            
        except Exception as e:
            logger.error(f"Error scanning index page {url}: {e}")
            return []
    
    def enqueue_pdf(self, url: str) -> None:
        """Add PDF to processing queue."""
        current_time = int(time.time())
        
        with sqlite3.connect(self.queue_db_path) as conn:
            conn.execute(
                '''INSERT OR REPLACE INTO queue 
                   (url, status, added_ts, last_attempt_ts) 
                   VALUES (?, ?, ?, ?)''',
                (url, 'pending', current_time, 0)
            )
            conn.commit()
        
        # Update known URLs
        self._known_urls.add(url)
    
    def get_queued_pdfs(self, status: str = 'pending', limit: int = 10) -> List[str]:
        """Get PDFs from queue with specified status."""
        with sqlite3.connect(self.queue_db_path) as conn:
            cursor = conn.execute(
                'SELECT url FROM queue WHERE status = ? ORDER BY added_ts LIMIT ?',
                (status, limit)
            )
            return [row[0] for row in cursor.fetchall()]
    
    def update_pdf_status(self, url: str, status: str) -> None:
        """Update PDF status in queue."""
        current_time = int(time.time())
        
        with sqlite3.connect(self.queue_db_path) as conn:
            conn.execute(
                'UPDATE queue SET status = ?, last_attempt_ts = ? WHERE url = ?',
                (status, current_time, url)
            )
            conn.commit()
    
    def discover_and_enqueue(self) -> List[str]:
        """Run discovery process and enqueue new PDFs."""
        if not self.enabled:
            return []
        
        all_new_pdfs = []
        total_discovered = 0
        
        for index_page in self.index_pages:
            new_pdfs = self.discover_pdfs_from_index(index_page)
            
            for pdf_url in new_pdfs:
                if total_discovered >= self.max_new_per_run:
                    break
                
                self.enqueue_pdf(pdf_url)
                all_new_pdfs.append(pdf_url)
                total_discovered += 1
                
                # Generate a dummy SHA256 for now (would be computed after download)
                dummy_sha = hashlib.sha256(pdf_url.encode()).hexdigest()
                self._save_pdf_entry(pdf_url, dummy_sha)
            
            if total_discovered >= self.max_new_per_run:
                break
        
        if all_new_pdfs:
            logger.info(f"Discovered and enqueued {len(all_new_pdfs)} new PDFs")
        
        return all_new_pdfs
    
    def get_metrics(self) -> Dict[str, int]:
        """Get discovery metrics."""
        with sqlite3.connect(self.queue_db_path) as conn:
            cursor = conn.execute('SELECT status, COUNT(*) FROM queue GROUP BY status')
            status_counts = dict(cursor.fetchall())
        
        return {
            'total_known': len(self._known_urls),
            'pending': status_counts.get('pending', 0),
            'processing': status_counts.get('processing', 0),
            'completed': status_counts.get('completed', 0),
            'failed': status_counts.get('failed', 0)
        }


# Global discovery instance
_pdf_discovery = None


def get_pdf_discovery() -> PDFDiscovery:
    """Get global PDF discovery instance."""
    global _pdf_discovery
    if _pdf_discovery is None:
        _pdf_discovery = PDFDiscovery()
    return _pdf_discovery