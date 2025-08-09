"""
Boilerplate / Noise Reduction using block frequency model.
Tracks common blocks across snapshots and removes repetitive content.
"""
import hashlib
import json
import time
import logging
from typing import List, Dict, Set, Optional, Tuple, Any
from pathlib import Path
from collections import defaultdict

from .config import get_radar_config


logger = logging.getLogger(__name__)


class BoilerplateFilter:
    """Filter to remove repetitive boilerplate content."""
    
    def __init__(self):
        config = get_radar_config()
        self.enabled = config.get('diff.boilerplate_filter', True)
        self.history_window = config.get('diff.boilerplate_history_window', 30)
        self.frequency_threshold = config.get('diff.boilerplate_frequency_threshold', 0.85)
        self.min_block_chars = config.get('diff.boilerplate_min_block_chars', 40)
        
        # Ensure boilerplate directory exists
        self.boilerplate_dir = Path('.radar/boilerplate')
        self.boilerplate_dir.mkdir(parents=True, exist_ok=True)
    
    def _compute_block_hash(self, block: str) -> str:
        """Compute hash for a text block."""
        normalized = block.strip().lower()
        return hashlib.sha256(normalized.encode('utf-8')).hexdigest()[:16]
    
    def _extract_blocks(self, text: str) -> List[str]:
        """Extract text blocks from content."""
        # Split by common delimiters
        lines = text.split('\n')
        blocks = []
        current_block = []
        
        for line in lines:
            line = line.strip()
            if not line:
                if current_block:
                    block_text = '\n'.join(current_block)
                    if len(block_text) >= self.min_block_chars:
                        blocks.append(block_text)
                    current_block = []
            else:
                current_block.append(line)
        
        # Don't forget the last block
        if current_block:
            block_text = '\n'.join(current_block)
            if len(block_text) >= self.min_block_chars:
                blocks.append(block_text)
        
        return blocks
    
    def _get_stats_file(self, source_name: str) -> Path:
        """Get stats file path for a source."""
        safe_name = "".join(c for c in source_name if c.isalnum() or c in "._-")
        return self.boilerplate_dir / f"{safe_name}.jsonl"
    
    def _load_history(self, source_name: str) -> List[Dict]:
        """Load recent history for a source."""
        stats_file = self._get_stats_file(source_name)
        history = []
        
        if stats_file.exists():
            try:
                with open(stats_file, 'r') as f:
                    for line in f:
                        if line.strip():
                            entry = json.loads(line.strip())
                            history.append(entry)
            except Exception as e:
                logger.warning(f"Could not load history for {source_name}: {e}")
        
        # Keep only recent entries within window
        return history[-self.history_window:]
    
    def _save_entry(self, source_name: str, block_hashes: List[str]) -> None:
        """Save current entry to history."""
        stats_file = self._get_stats_file(source_name)
        entry = {
            'ts': int(time.time()),
            'block_hashes': block_hashes
        }
        
        try:
            with open(stats_file, 'a') as f:
                f.write(json.dumps(entry) + '\n')
        except Exception as e:
            logger.warning(f"Could not save entry for {source_name}: {e}")
    
    def _get_frequent_blocks(self, history: List[Dict]) -> Set[str]:
        """Get blocks that appear frequently in history."""
        if not history:
            return set()
        
        block_counts = defaultdict(int)
        total_entries = len(history)
        
        for entry in history:
            block_hashes = entry.get('block_hashes', [])
            for block_hash in set(block_hashes):  # Count each hash once per entry
                block_counts[block_hash] += 1
        
        # Find blocks that exceed frequency threshold
        frequent_blocks = set()
        for block_hash, count in block_counts.items():
            if count / total_entries >= self.frequency_threshold:
                frequent_blocks.add(block_hash)
        
        return frequent_blocks
    
    def strip_boilerplate(self, text: str, source_name: str) -> Tuple[str, Dict[str, Any]]:
        """
        Remove boilerplate content from text.
        
        Returns:
            Tuple of (filtered_text, metadata)
        """
        if not self.enabled:
            return text, {'boilerplate_removed': 0}
        
        # Extract blocks from current text
        blocks = self._extract_blocks(text)
        block_hashes = [self._compute_block_hash(block) for block in blocks]
        
        # Load history and determine frequent blocks
        history = self._load_history(source_name)
        frequent_block_hashes = self._get_frequent_blocks(history)
        
        # Filter out frequent blocks
        filtered_blocks = []
        removed_count = 0
        
        for i, block_hash in enumerate(block_hashes):
            if block_hash in frequent_block_hashes:
                removed_count += 1
                logger.debug(f"Removing frequent block: {block_hash}")
            else:
                filtered_blocks.append(blocks[i])
        
        # Save current entry to history
        self._save_entry(source_name, block_hashes)
        
        # Reconstruct text
        filtered_text = '\n\n'.join(filtered_blocks)
        
        metadata = {
            'boilerplate_removed': removed_count,
            'total_blocks': len(blocks),
            'filtered_blocks': len(filtered_blocks)
        }
        
        if removed_count > 0:
            logger.info(f"Removed {removed_count} boilerplate blocks from {source_name}")
        
        return filtered_text, metadata


# Global filter instance
_boilerplate_filter = None


def get_boilerplate_filter() -> BoilerplateFilter:
    """Get global boilerplate filter instance."""
    global _boilerplate_filter
    if _boilerplate_filter is None:
        _boilerplate_filter = BoilerplateFilter()
    return _boilerplate_filter


def strip_boilerplate(text: str, source_name: str) -> Tuple[str, Dict[str, Any]]:
    """Convenience function to strip boilerplate content."""
    filter_instance = get_boilerplate_filter()
    return filter_instance.strip_boilerplate(text, source_name)