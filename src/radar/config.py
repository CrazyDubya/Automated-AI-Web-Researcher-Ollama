"""
Configuration manager for Radar system.
Extends the existing llm_config.py approach with YAML support.
"""
import os
import yaml
from typing import Dict, Any, Optional
from pathlib import Path


class RadarConfig:
    """Configuration manager for Radar system features."""
    
    def __init__(self, config_path: str = "config.yaml"):
        self.config_path = Path(config_path)
        self._config = {}
        self.load_config()
    
    def load_config(self) -> None:
        """Load configuration from YAML file."""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r') as f:
                    self._config = yaml.safe_load(f) or {}
            except Exception as e:
                print(f"Warning: Could not load config from {self.config_path}: {e}")
                self._config = {}
        else:
            # Use default configuration
            self._config = self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Return default configuration."""
        return {
            'trailkeeper': {'enabled': True},
            'embedding_cache': {
                'enabled': True,
                'db_path': '.radar/emb_cache.sqlite',
                'batch_size': 64,
                'log_summary': True
            },
            'diff': {
                'boilerplate_filter': True,
                'boilerplate_history_window': 30,
                'boilerplate_frequency_threshold': 0.85,
                'boilerplate_min_block_chars': 40
            },
            'pdf': {
                'discovery': {
                    'enabled': True,
                    'max_new_per_run': 15,
                    'index_pages': [],
                    'max_bytes_per_file': 5242880
                }
            },
            'ethics': {
                'concurrency': {
                    'enabled': True,
                    'max_concurrency': 8,
                    'per_domain_max': 2
                }
            },
            'search': {
                'filter_default_since_days': 14,
                'query_expansion': False,
                'stream_answers': False,
                'result_limit': 12
            },
            'reports': {
                'web_output_dir': 'reports/web'
            }
        }
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value using dot notation (e.g., 'embedding_cache.enabled')."""
        keys = key.split('.')
        value = self._config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def get_section(self, section: str) -> Dict[str, Any]:
        """Get entire configuration section."""
        return self._config.get(section, {})
    
    def is_enabled(self, feature_path: str) -> bool:
        """Check if a feature is enabled."""
        return self.get(f"{feature_path}.enabled", False)


# Global configuration instance
_radar_config = None


def get_radar_config() -> RadarConfig:
    """Get global radar configuration instance."""
    global _radar_config
    if _radar_config is None:
        _radar_config = RadarConfig()
    return _radar_config


def ensure_radar_dirs() -> None:
    """Ensure radar directories exist."""
    config = get_radar_config()
    
    # Create .radar directory
    radar_dir = Path('.radar')
    radar_dir.mkdir(exist_ok=True)
    
    # Create boilerplate directory
    boilerplate_dir = radar_dir / 'boilerplate'
    boilerplate_dir.mkdir(exist_ok=True)
    
    # Create reports directory
    reports_dir = Path(config.get('reports.web_output_dir', 'reports/web'))
    reports_dir.mkdir(parents=True, exist_ok=True)