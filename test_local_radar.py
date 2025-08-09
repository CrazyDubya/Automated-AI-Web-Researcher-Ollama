"""
Basic tests for Local Radar functionality
"""

import os
import sys
import unittest
import tempfile
import shutil
from datetime import datetime
from pathlib import Path

# Add the parent directory to path so we can import local_radar
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from local_radar.config import LocalRadarConfig
from local_radar.base import ReportEntry, ResearchBrief, Dossier
from local_radar.report_generator import HTMLReportGenerator
from local_radar.vector_index import VectorIndex
from local_radar.cli import LocalRadarCLI


class TestLocalRadarConfig(unittest.TestCase):
    """Test Local Radar configuration system"""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.config_file = os.path.join(self.temp_dir, 'test_config.json')
    
    def tearDown(self):
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_config_creation(self):
        """Test configuration object creation"""
        config = LocalRadarConfig(self.config_file)
        self.assertIsNotNone(config.report)
        self.assertIsNotNone(config.pdf)
        self.assertIsNotNone(config.vector)
        self.assertIsNotNone(config.cli)
    
    def test_config_save_load(self):
        """Test configuration save and load"""
        config = LocalRadarConfig(self.config_file)
        config.report.max_entries_per_page = 100
        config.save_to_file()
        
        # Load new config from same file
        config2 = LocalRadarConfig(self.config_file)
        self.assertEqual(config2.report.max_entries_per_page, 100)


class TestReportEntry(unittest.TestCase):
    """Test ReportEntry data structure"""
    
    def test_report_entry_creation(self):
        """Test creating a report entry"""
        entry = ReportEntry(
            title="Test Entry",
            content="Test content",
            source_url="https://example.com",
            timestamp=datetime.now(),
            tags=["test", "example"],
            confidence_score=0.8
        )
        
        self.assertEqual(entry.title, "Test Entry")
        self.assertEqual(entry.content, "Test content")
        self.assertEqual(entry.source_url, "https://example.com")
        self.assertIsInstance(entry.tags, list)
        self.assertEqual(entry.confidence_score, 0.8)
        self.assertIsInstance(entry.metadata, dict)


class TestHTMLReportGenerator(unittest.TestCase):
    """Test HTML report generation"""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.config = LocalRadarConfig()
        self.config.report.output_dir = os.path.join(self.temp_dir, 'reports')
        self.config.report.template_dir = os.path.join(self.temp_dir, 'templates')
        self.config.report.static_dir = os.path.join(self.temp_dir, 'static')
        
        self.generator = HTMLReportGenerator()
        self.generator.config = self.config
    
    def tearDown(self):
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_template_creation(self):
        """Test that default templates are created"""
        # Ensure directories exist
        self.config.ensure_directories()
        
        self.generator._create_default_templates()
        
        templates_dir = Path(self.config.report.template_dir)
        self.assertTrue((templates_dir / 'index.html').exists())
        self.assertTrue((templates_dir / 'brief.html').exists())
        self.assertTrue((templates_dir / 'dossier.html').exists())
        
        static_dir = Path(self.config.report.static_dir)
        self.assertTrue((static_dir / 'style.css').exists())
        self.assertTrue((static_dir / 'app.js').exists())
    
    def test_brief_generation(self):
        """Test brief generation"""
        entries = [
            ReportEntry(
                title="Test Entry 1",
                content="Content 1",
                source_url="https://example.com/1",
                timestamp=datetime.now(),
                tags=["test"],
                confidence_score=0.9
            ),
            ReportEntry(
                title="Test Entry 2", 
                content="Content 2",
                source_url="https://example.com/2",
                timestamp=datetime.now(),
                tags=["test", "example"],
                confidence_score=0.8
            )
        ]
        
        brief = self.generator.generate_daily_brief(entries)
        
        self.assertEqual(brief.brief_type, "daily")
        self.assertEqual(len(brief.entries), 2)
        self.assertIsInstance(brief.summary, str)
        self.assertIsInstance(brief.tags, list)
        self.assertIn("test", brief.tags)


class TestVectorIndex(unittest.TestCase):
    """Test vector index functionality"""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.index = VectorIndex()
        self.index.config.vector.index_dir = os.path.join(self.temp_dir, 'vector_index')
    
    def tearDown(self):
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_document_addition(self):
        """Test adding documents to the index"""
        # Ensure directories exist
        Path(self.index.config.vector.index_dir).mkdir(parents=True, exist_ok=True)
        
        doc_id = self.index.add_document("This is a test document about AI")
        
        self.assertIsInstance(doc_id, str)
        self.assertEqual(len(self.index.documents), 1)
        self.assertEqual(len(self.index.document_metadata), 1)
    
    def test_search_functionality(self):
        """Test basic search functionality"""
        # Ensure directories exist
        Path(self.index.config.vector.index_dir).mkdir(parents=True, exist_ok=True)
        
        # Add some test documents
        self.index.add_document("This is about artificial intelligence")
        self.index.add_document("This is about machine learning")
        self.index.add_document("This is about natural language processing")
        
        # Search for AI-related content
        results = self.index.search("artificial intelligence", top_k=5)
        
        self.assertIsInstance(results, list)
        self.assertGreater(len(results), 0)
        for result in results:
            self.assertIn('text', result)
            self.assertIn('similarity_score', result)
            self.assertIn('metadata', result)
    
    def test_report_entry_indexing(self):
        """Test indexing report entries"""
        # Ensure directories exist
        Path(self.index.config.vector.index_dir).mkdir(parents=True, exist_ok=True)
        
        entry = ReportEntry(
            title="AI Research",
            content="Latest developments in artificial intelligence",
            source_url="https://example.com",
            timestamp=datetime.now(),
            tags=["AI", "research"],
            confidence_score=0.9
        )
        
        doc_id = self.index.add_report_entry(entry)
        
        self.assertIsInstance(doc_id, str)
        self.assertEqual(len(self.index.documents), 1)
        
        # Verify metadata
        metadata = self.index.document_metadata[0]
        self.assertEqual(metadata['title'], "AI Research")
        self.assertEqual(metadata['type'], 'report_entry')
        self.assertIn("AI", metadata['tags'])


class TestLocalRadarCLI(unittest.TestCase):
    """Test Local Radar CLI functionality"""
    
    def setUp(self):
        self.cli = LocalRadarCLI()
    
    def test_help_command(self):
        """Test help command"""
        result = self.cli.handle_command("lr_help")
        
        self.assertIsInstance(result, str)
        self.assertIn("Local Radar Commands", result)
        self.assertIn("lr_generate_daily", result)
        self.assertIn("lr_search", result)
    
    def test_status_command(self):
        """Test status command"""
        result = self.cli.handle_command("lr_status")
        
        self.assertIsInstance(result, str)
        self.assertIn("Local Radar Status", result)
        self.assertIn("Directories:", result)
        self.assertIn("Content:", result)
    
    def test_config_command(self):
        """Test config command"""
        result = self.cli.handle_command("lr_config")
        
        self.assertIsInstance(result, str)
        self.assertIn("Local Radar Configuration", result)
        self.assertIn("Reports:", result)
        self.assertIn("PDF Crawling:", result)
        self.assertIn("Vector Index:", result)
    
    def test_unknown_command(self):
        """Test unknown command handling"""
        result = self.cli.handle_command("lr_unknown_command")
        
        self.assertIsInstance(result, str)
        self.assertIn("Unknown Local Radar command", result)


class TestIntegration(unittest.TestCase):
    """Integration tests for Local Radar components"""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.cli = LocalRadarCLI()
        
        # Set up temporary directories
        self.cli.config.report.output_dir = os.path.join(self.temp_dir, 'reports')
        self.cli.config.vector.index_dir = os.path.join(self.temp_dir, 'vector_index')
        
        # Ensure directories exist
        Path(self.cli.config.report.output_dir).mkdir(parents=True, exist_ok=True)
        Path(self.cli.config.vector.index_dir).mkdir(parents=True, exist_ok=True)
    
    def tearDown(self):
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_end_to_end_workflow(self):
        """Test complete workflow from data ingestion to report generation"""
        # Add some sample data
        entry1 = ReportEntry(
            title="AI Breakthrough",
            content="New developments in artificial intelligence research",
            source_url="https://example.com/ai",
            timestamp=datetime.now(),
            tags=["AI", "research", "breakthrough"],
            confidence_score=0.95
        )
        
        entry2 = ReportEntry(
            title="ML Applications",
            content="Machine learning applications in healthcare",
            source_url="https://example.com/ml",
            timestamp=datetime.now(),
            tags=["ML", "healthcare", "applications"],
            confidence_score=0.87
        )
        
        # Add to vector index using the imported vector_index
        from local_radar.vector_index import vector_index
        vector_index.add_report_entry(entry1)
        vector_index.add_report_entry(entry2)
        
        # Test search
        search_result = self.cli.handle_command("lr_search artificial intelligence")
        self.assertIn("AI Breakthrough", search_result)
        
        # Test daily brief generation
        brief_result = self.cli.handle_command("lr_generate_daily")
        self.assertIn("Daily brief generated", brief_result)
        
        # Verify files were created
        reports_dir = Path(self.cli.config.report.output_dir)
        self.assertTrue(any(reports_dir.glob("daily_brief_*.html")))
        self.assertTrue((reports_dir / "index.html").exists())


if __name__ == '__main__':
    unittest.main(verbosity=2)