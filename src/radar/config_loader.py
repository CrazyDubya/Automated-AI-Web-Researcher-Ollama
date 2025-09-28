"""Configuration loading and management."""
from __future__ import annotations
import yaml
import pathlib
from typing import Dict, Any, List

class Config:
    def __init__(self, data: Dict[str, Any]):
        self._data = data
        self.base_dir = pathlib.Path(data.get('storage', {}).get('base_dir', '.radar'))
        self.reports_dir = self.base_dir / data.get('storage', {}).get('reports_dir', 'reports')
        self.ethics = data.get('ethics', {})
        self.watchlist = data.get('watchlist', {})
        self.topics = data.get('topics', [])
        self.outputs = data.get('outputs', {})
        self.llm = data.get('llm', {})
        self.pdf = data.get('pdf', {})
        
        # Ensure directories exist
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.reports_dir.mkdir(parents=True, exist_ok=True)

def load(path: pathlib.Path) -> Config:
    """Load configuration from YAML file."""
    with path.open('r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    return Config(data)