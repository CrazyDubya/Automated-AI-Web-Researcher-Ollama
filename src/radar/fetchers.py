"""Fetchers: RSS/Atom feeds, HTML pages (diffable), PDFs, local paths.
Implements polite crawling with robots.txt checks and per-domain rate limiting.
"""
from __future__ import annotations
import time, pathlib, re, hashlib, mimetypes, os, sys
from typing import Dict, Any, List, Iterable
import requests, feedparser
from urllib.parse import urlparse

# Add absolute import paths
ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

import src.common.rate_limit as rate_limit
import src.common.robots as robots
import src.radar.html_norm as html_norm

USER_AGENT_FALLBACK = "RadarBot/0.2"

class FetchContext:
    def __init__(self, cfg):
        self.cfg = cfg
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": cfg.ethics.get('user_agent') or USER_AGENT_FALLBACK})
        self.rate = rate_limit.DomainRateLimiter(cfg.ethics.get('rate_limit_per_domain_per_minute', 6))
        self.timeout = cfg.ethics.get('request_timeout_seconds', 20)
        self.robot_cache = {}

    def allowed(self, url: str) -> bool:
        if not self.cfg.ethics.get('obey_robots', True):
            return True
        return robots.is_allowed(url, self.robot_cache, self.session.headers.get('User-Agent'))

    def get(self, url: str) -> requests.Response | None:
        if not self.allowed(url):
            return None
        host = urlparse(url).hostname or 'default'
        self.rate.consume(host)
        try:
            resp = self.session.get(url, timeout=self.timeout)
            return resp
        except requests.RequestException:
            return None

def _hash(text: str) -> str:
    return hashlib.sha256(text.encode('utf-8')).hexdigest()[:16]


def fetch_all(cfg) -> List[Dict[str, Any]]:
    ctx = FetchContext(cfg)
    items: List[Dict[str, Any]] = []
    items.extend(_fetch_feeds(cfg, ctx))
    items.extend(_fetch_urls(cfg, ctx))
    items.extend(_fetch_local_paths(cfg))
    # PDFs via pattern: placeholder (could implement discovery crawler later)
    return items


def _feed_entry_to_content(entry) -> str:
    parts = []
    if 'title' in entry:
        parts.append(f"TITLE: {entry.title}")
    if 'summary' in entry:
        parts.append(entry.summary)
    for k in ('description','content'):
        if k in entry and isinstance(entry[k], str):
            parts.append(entry[k])
    return '\n'.join(parts)


def _apply_keyword_filters(text: str, any_kw: List[str] | None, all_kw: List[str] | None) -> bool:
    lower = text.lower()
    if any_kw:
        if not any(kw.lower() in lower for kw in any_kw):
            return False
    if all_kw:
        if not all(kw.lower() in lower for kw in all_kw):
            return False
    return True


def _fetch_feeds(cfg, ctx: FetchContext) -> Iterable[Dict[str, Any]]:
    feeds = cfg.watchlist.get('feeds', []) or []
    for feed in feeds:
        url = feed['url']
        resp = ctx.get(url)
        if not resp or resp.status_code != 200:
            continue
        parsed = feedparser.parse(resp.content)
        for entry in parsed.entries[:50]:  # cap
            content = _feed_entry_to_content(entry)
            if not _apply_keyword_filters(content, feed.get('keywords_any'), feed.get('keywords_all')):
                continue
            item = {
                'name': feed['name'],
                'type': 'feed',
                'source_name': feed['name'],
                'tags': feed.get('tags', []),
                'content': content,
                'metadata': {
                    'link': getattr(entry, 'link', ''),
                    'published': getattr(entry, 'published', ''),
                    'id': getattr(entry, 'id', ''),
                    'feed_url': url,
                }
            }
            item['hash'] = _hash(item['content'])
            yield item


def _fetch_urls(cfg, ctx: FetchContext) -> Iterable[Dict[str, Any]]:
    urls = cfg.watchlist.get('urls_diff', []) or []
    for rec in urls:
        url = rec['url']
        resp = ctx.get(url)
        if not resp or resp.status_code != 200:
            continue
        html = resp.text
        text_norm = html_norm.html_to_text(html)
        if not _apply_keyword_filters(text_norm, rec.get('keywords_any'), rec.get('keywords_all')):
            continue
        yield {
            'name': rec['name'],
            'type': 'url',
            'source_name': rec['name'],
            'tags': rec.get('tags', []),
            'content': text_norm,
            'metadata': {
                'url': url,
                'status_code': resp.status_code,
                'content_type': resp.headers.get('Content-Type',''),
                'snapshot_format': rec.get('snapshot_format','html')
            }
        }


def _fetch_local_paths(cfg) -> Iterable[Dict[str, Any]]:
    locals_ = cfg.watchlist.get('local_paths', []) or []
    for spec in locals_:
        base = pathlib.Path(spec['path']).expanduser()
        if not base.exists():
            continue
        for p in base.glob(spec.get('glob', '**/*')):
            if p.is_dir():
                continue
            try:
                if p.suffix.lower() in ('.md','.txt'):
                    txt = p.read_text(errors='ignore')
                else:
                    if p.suffix.lower() == '.pdf':
                        # lightweight pdf text extraction placeholder
                        try:
                            from pdfminer.high_level import extract_text
                            txt = extract_text(str(p))[:20000]
                        except Exception:
                            txt = ''
                    else:
                        continue
                yield {
                    'name': f"LOCAL:{p.name}",
                    'type': 'local',
                    'source_name': spec['path'],
                    'tags': spec.get('tags', []),
                    'content': txt,
                    'metadata': {
                        'path': str(p),
                        'modified': int(p.stat().st_mtime)
                    }
                }
            except Exception:
                continue