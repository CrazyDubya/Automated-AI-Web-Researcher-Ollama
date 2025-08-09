"""
Local Radar - Production-oriented enhancements for Automated AI Web Researcher
Provides HTML reports, PDF crawling, vector embeddings, and interactive CLI capabilities.
"""

__version__ = "1.0.0"
__author__ = "Local Radar Enhancement Team"

from .config import LocalRadarConfig
from .base import ReportEntry, ResearchBrief, Dossier

__all__ = [
    'LocalRadarConfig',
    'ReportEntry',
    'ResearchBrief', 
    'Dossier'
]