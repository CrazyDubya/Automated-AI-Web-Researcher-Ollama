"""
Base classes and interfaces for Local Radar components
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


@dataclass
class ReportEntry:
    """Represents a single entry in a Local Radar report"""
    title: str
    content: str
    source_url: str
    timestamp: datetime
    tags: List[str]
    confidence_score: float = 0.0
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass  
class ResearchBrief:
    """Represents a research brief (daily/weekly)"""
    brief_type: str  # 'daily' or 'weekly'
    date_range: str
    entries: List[ReportEntry]
    summary: str
    tags: List[str]
    generated_at: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert brief to dictionary for JSON serialization"""
        return {
            'brief_type': self.brief_type,
            'date_range': self.date_range,
            'entries': [
                {
                    'title': entry.title,
                    'content': entry.content,
                    'source_url': entry.source_url,
                    'timestamp': entry.timestamp.isoformat(),
                    'tags': entry.tags,
                    'confidence_score': entry.confidence_score,
                    'metadata': entry.metadata
                }
                for entry in self.entries
            ],
            'summary': self.summary,
            'tags': self.tags,
            'generated_at': self.generated_at.isoformat()
        }


@dataclass
class Dossier:
    """Represents a research dossier on a specific topic"""
    topic: str
    description: str
    entries: List[ReportEntry]
    analysis: str
    created_at: datetime
    updated_at: datetime
    tags: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert dossier to dictionary for JSON serialization"""
        return {
            'topic': self.topic,
            'description': self.description,
            'entries': [
                {
                    'title': entry.title,
                    'content': entry.content,
                    'source_url': entry.source_url,
                    'timestamp': entry.timestamp.isoformat(),
                    'tags': entry.tags,
                    'confidence_score': entry.confidence_score,
                    'metadata': entry.metadata
                }
                for entry in self.entries
            ],
            'analysis': self.analysis,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'tags': self.tags
        }