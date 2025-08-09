"""
Persistent Embedding Cache using SQLite.
Provides caching for embedding vectors with metrics tracking.
"""
import sqlite3
import hashlib
import time
import json
import logging
from typing import List, Optional, Tuple, Dict, Any
from pathlib import Path
import pickle

from .config import get_radar_config


logger = logging.getLogger(__name__)


class EmbeddingCache:
    """Persistent embedding cache with SQLite backend."""
    
    def __init__(self, db_path: Optional[str] = None):
        config = get_radar_config()
        self.db_path = Path(db_path or config.get('embedding_cache.db_path', '.radar/emb_cache.sqlite'))
        self.batch_size = config.get('embedding_cache.batch_size', 64)
        self.log_summary = config.get('embedding_cache.log_summary', True)
        
        # Ensure directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Metrics
        self.hits = 0
        self.misses = 0
        self.pending_batch = []
        
        self._init_db()
    
    def _init_db(self) -> None:
        """Initialize database schema."""
        with sqlite3.connect(self.db_path) as conn:
            # Create meta table
            conn.execute('''
                CREATE TABLE IF NOT EXISTS meta (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            ''')
            
            # Create embeddings table
            conn.execute('''
                CREATE TABLE IF NOT EXISTS embeds (
                    hash TEXT,
                    model TEXT,
                    dim INTEGER,
                    vec BLOB,
                    last_access INTEGER,
                    PRIMARY KEY (hash, model)
                )
            ''')
            
            # Create index for performance
            conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_embeds_last_access 
                ON embeds(last_access)
            ''')
            
            conn.commit()
    
    def _normalize_text(self, text: str) -> str:
        """Normalize text for consistent hashing."""
        return text.strip().lower()
    
    def _compute_hash(self, text: str) -> str:
        """Compute SHA256 hash of normalized text."""
        normalized = self._normalize_text(text)
        return hashlib.sha256(normalized.encode('utf-8')).hexdigest()
    
    def get_embedding(self, text: str, model: str) -> Optional[List[float]]:
        """Get embedding from cache if available."""
        if not get_radar_config().is_enabled('embedding_cache'):
            return None
            
        text_hash = self._compute_hash(text)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                'SELECT vec, dim FROM embeds WHERE hash = ? AND model = ?',
                (text_hash, model)
            )
            row = cursor.fetchone()
            
            if row:
                # Update last access time
                conn.execute(
                    'UPDATE embeds SET last_access = ? WHERE hash = ? AND model = ?',
                    (int(time.time()), text_hash, model)
                )
                conn.commit()
                
                # Deserialize embedding
                vec_blob, dim = row
                embedding = pickle.loads(vec_blob)
                
                self.hits += 1
                return embedding
            else:
                self.misses += 1
                return None
    
    def store_embedding(self, text: str, model: str, embedding: List[float]) -> None:
        """Store embedding in cache (batched)."""
        if not get_radar_config().is_enabled('embedding_cache'):
            return
            
        text_hash = self._compute_hash(text)
        vec_blob = pickle.dumps(embedding)
        current_time = int(time.time())
        
        self.pending_batch.append((
            text_hash, model, len(embedding), vec_blob, current_time
        ))
        
        # Flush batch if full
        if len(self.pending_batch) >= self.batch_size:
            self.flush_batch()
    
    def flush_batch(self) -> None:
        """Flush pending embeddings to database."""
        if not self.pending_batch:
            return
            
        with sqlite3.connect(self.db_path) as conn:
            conn.executemany(
                '''INSERT OR REPLACE INTO embeds 
                   (hash, model, dim, vec, last_access) 
                   VALUES (?, ?, ?, ?, ?)''',
                self.pending_batch
            )
            conn.commit()
        
        if self.log_summary:
            logger.info(f"Flushed {len(self.pending_batch)} embeddings to cache")
        
        self.pending_batch.clear()
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get cache metrics."""
        total_requests = self.hits + self.misses
        hit_ratio = self.hits / total_requests if total_requests > 0 else 0.0
        
        # Get database stats
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute('SELECT COUNT(*) FROM embeds')
            total_embeddings = cursor.fetchone()[0]
        
        return {
            'hits': self.hits,
            'misses': self.misses,
            'hit_ratio': hit_ratio,
            'total_embeddings': total_embeddings,
            'pending_batch_size': len(self.pending_batch)
        }
    
    def cleanup_old_entries(self, max_age_days: int = 30) -> int:
        """Remove old cache entries."""
        cutoff_time = int(time.time()) - (max_age_days * 24 * 3600)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                'DELETE FROM embeds WHERE last_access < ?',
                (cutoff_time,)
            )
            deleted_count = cursor.rowcount
            conn.commit()
        
        logger.info(f"Cleaned up {deleted_count} old cache entries")
        return deleted_count
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.flush_batch()


# Global cache instance
_embedding_cache = None


def get_embedding_cache() -> EmbeddingCache:
    """Get global embedding cache instance."""
    global _embedding_cache
    if _embedding_cache is None:
        _embedding_cache = EmbeddingCache()
    return _embedding_cache