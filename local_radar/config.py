"""
Local Radar Configuration System
Manages settings for HTML reports, PDF crawling, vector embeddings, and other features.
"""

import os
import json
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ReportConfig:
    """Configuration for HTML report generation"""
    output_dir: str = "reports"
    template_dir: str = "local_radar/templates"
    static_dir: str = "local_radar/static"
    max_entries_per_page: int = 50
    enable_tag_filtering: bool = True
    auto_refresh_interval: int = 300  # seconds


@dataclass
class PDFConfig:
    """Configuration for PDF pattern crawler"""
    sources_file: str = "pdf_sources.json"
    output_dir: str = "pdf_extracts"
    batch_size: int = 10
    max_concurrent: int = 3
    enable_ocr: bool = True
    ocr_languages: List[str] = field(default_factory=lambda: ["eng"])
    max_file_size_mb: int = 100
    timeout_seconds: int = 30


@dataclass
class VectorConfig:
    """Configuration for vector embeddings and RAG"""
    index_dir: str = "vector_index"
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    chunk_size: int = 512
    chunk_overlap: int = 50
    similarity_threshold: float = 0.75
    max_results: int = 10


@dataclass
class CLIConfig:
    """Configuration for interactive CLI features"""
    enable_autocomplete: bool = True
    history_file: str = ".local_radar_history"
    max_history_size: int = 1000
    prompt_style: str = "local_radar"


class LocalRadarConfig:
    """Main configuration class for Local Radar features"""
    
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or "local_radar_config.json"
        self.report = ReportConfig()
        self.pdf = PDFConfig()
        self.vector = VectorConfig()
        self.cli = CLIConfig()
        
        # Load from file if exists
        if os.path.exists(self.config_path):
            self.load_from_file()
    
    def load_from_file(self):
        """Load configuration from JSON file"""
        try:
            with open(self.config_path, 'r') as f:
                data = json.load(f)
            
            # Update configurations with loaded data
            if 'report' in data:
                for key, value in data['report'].items():
                    if hasattr(self.report, key):
                        setattr(self.report, key, value)
            
            if 'pdf' in data:
                for key, value in data['pdf'].items():
                    if hasattr(self.pdf, key):
                        setattr(self.pdf, key, value)
            
            if 'vector' in data:
                for key, value in data['vector'].items():
                    if hasattr(self.vector, key):
                        setattr(self.vector, key, value)
                        
            if 'cli' in data:
                for key, value in data['cli'].items():
                    if hasattr(self.cli, key):
                        setattr(self.cli, key, value)
                        
        except Exception as e:
            print(f"Warning: Could not load config from {self.config_path}: {e}")
    
    def save_to_file(self):
        """Save current configuration to JSON file"""
        data = {
            'report': self.report.__dict__,
            'pdf': self.pdf.__dict__,
            'vector': self.vector.__dict__,
            'cli': self.cli.__dict__
        }
        
        try:
            with open(self.config_path, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Warning: Could not save config to {self.config_path}: {e}")
    
    def ensure_directories(self):
        """Create necessary directories for Local Radar operations"""
        directories = [
            self.report.output_dir,
            self.report.template_dir,
            self.report.static_dir,
            self.pdf.output_dir,
            self.vector.index_dir
        ]
        
        for directory in directories:
            Path(directory).mkdir(parents=True, exist_ok=True)
    
    def get_pdf_sources(self) -> List[Dict[str, Any]]:
        """Load PDF source patterns from configuration file"""
        if not os.path.exists(self.pdf.sources_file):
            # Create default PDF sources file
            default_sources = [
                {
                    "name": "Example Pattern",
                    "url_pattern": "https://example.com/docs/*.pdf",
                    "description": "Example PDF source pattern",
                    "enabled": False
                }
            ]
            with open(self.pdf.sources_file, 'w') as f:
                json.dump(default_sources, f, indent=2)
            return default_sources
        
        try:
            with open(self.pdf.sources_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Warning: Could not load PDF sources from {self.pdf.sources_file}: {e}")
            return []


# Global configuration instance
config = LocalRadarConfig()