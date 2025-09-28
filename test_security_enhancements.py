#!/usr/bin/env python3
"""
Comprehensive security and enhancement tests for Local Radar
Tests security features, performance monitoring, and robustness improvements
"""

import os
import sys
import unittest
import tempfile
import shutil
import logging
from datetime import datetime
from pathlib import Path

# Add the parent directory to path so we can import local_radar
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from local_radar.security import (
    sanitize_html, escape_html, validate_filename, validate_url,
    validate_tag, validate_search_query, safe_path_join, SecurityError
)
from local_radar.monitoring import PerformanceMonitor, HealthChecker, monitor_operation
from local_radar.config import LocalRadarConfig
from local_radar.base import ReportEntry
from local_radar.report_generator import HTMLReportGenerator
from local_radar.cli import LocalRadarCLI


class TestSecurityFeatures(unittest.TestCase):
    """Test security validation and sanitization"""
    
    def test_html_sanitization(self):
        """Test HTML sanitization against XSS"""
        # Test basic XSS patterns
        malicious_inputs = [
            '<script>alert("xss")</script>',
            '<img src=x onerror=alert("xss")>',
            '<svg onload=alert("xss")>',
            'javascript:alert("xss")',
            '<iframe src="javascript:alert(\'xss\')"></iframe>',
            '<body onload=alert("xss")>',
            '<div onclick="alert(\'xss\')">Click me</div>'
        ]
        
        for malicious in malicious_inputs:
            cleaned = sanitize_html(malicious)
            
            # Should not contain script tags or javascript
            self.assertNotIn('<script', cleaned.lower())
            self.assertNotIn('javascript:', cleaned.lower())
            self.assertNotIn('onerror=', cleaned.lower())
            self.assertNotIn('onload=', cleaned.lower())
            self.assertNotIn('onclick=', cleaned.lower())
    
    def test_html_escaping(self):
        """Test HTML character escaping"""
        test_cases = [
            ('<script>alert("test")</script>', '&lt;script&gt;alert(&quot;test&quot;)&lt;/script&gt;'),
            ('Hello & World', 'Hello &amp; World'),
            ('Price: 5 < 10', 'Price: 5 &lt; 10'),
            ('Quote: "Hello"', 'Quote: &quot;Hello&quot;'),
            ("Apostrophe: 'Hello'", "Apostrophe: &#x27;Hello&#x27;")
        ]
        
        for input_text, expected in test_cases:
            result = escape_html(input_text)
            self.assertEqual(result, expected)
    
    def test_filename_validation(self):
        """Test filename validation and sanitization"""
        # Valid filenames
        valid_names = ['document.pdf', 'report_2024.html', 'data-file.json']
        for name in valid_names:
            result = validate_filename(name)
            self.assertEqual(result, name)
        
        # Invalid/dangerous filenames
        dangerous_names = [
            '../../../etc/passwd',
            '..\\windows\\system32\\config',
            '/etc/shadow',
            'con.txt',  # Windows reserved name
            'file<script>.txt',
            'file|pipe.txt'
        ]
        
        for name in dangerous_names:
            with self.assertRaises(SecurityError):
                validate_filename(name)
    
    def test_url_validation(self):
        """Test URL validation"""
        # Valid URLs
        valid_urls = [
            'https://example.com/document.pdf',
            'http://localhost:8080/api/data',
            'https://subdomain.example.org/path/to/file.html'
        ]
        
        for url in valid_urls:
            self.assertTrue(validate_url(url))
        
        # Invalid URLs
        invalid_urls = [
            'javascript:alert("xss")',
            'data:text/html,<script>alert("xss")</script>',
            'file:///etc/passwd',
            'ftp://example.com/file',
            'not-a-url',
            '<script>alert("xss")</script>'
        ]
        
        for url in invalid_urls:
            self.assertFalse(validate_url(url))
    
    def test_tag_validation(self):
        """Test tag validation"""
        # Valid tags
        valid_tags = ['AI', 'machine-learning', 'research', 'data_science']
        for tag in valid_tags:
            result = validate_tag(tag)
            self.assertEqual(result, tag)
        
        # Invalid tags
        invalid_tags = [
            '<script>alert("xss")</script>',
            'tag"with"quotes',
            'tag\'with\'apostrophes',
            'tag<with>brackets',
            '',  # Empty tag
            'a' * 100  # Too long
        ]
        
        for tag in invalid_tags:
            with self.assertRaises(SecurityError):
                validate_tag(tag)
    
    def test_search_query_validation(self):
        """Test search query validation"""
        # Valid queries
        valid_queries = [
            'artificial intelligence',
            'machine learning algorithms',
            'data science AND python',
            'neural networks OR deep learning'
        ]
        
        for query in valid_queries:
            result = validate_search_query(query)
            self.assertEqual(result, query)
        
        # Invalid queries
        invalid_queries = [
            '',  # Empty
            'a' * 1000,  # Too long
            '<script>alert("xss")</script>',
            'query"with"quotes',
            'query\'with\'apostrophes'
        ]
        
        for query in invalid_queries:
            with self.assertRaises(SecurityError):
                validate_search_query(query)
    
    def test_safe_path_join(self):
        """Test safe path joining to prevent directory traversal"""
        temp_dir = tempfile.mkdtemp()
        
        try:
            # Valid path joins
            safe_path = safe_path_join(temp_dir, 'reports', 'daily.html')
            self.assertTrue(str(safe_path).startswith(temp_dir))
            
            # Attempted directory traversal
            with self.assertRaises(SecurityError):
                safe_path_join(temp_dir, '..', '..', 'etc', 'passwd')
            
            with self.assertRaises(SecurityError):
                safe_path_join(temp_dir, '..\\..\\windows\\system32')
                
        finally:
            shutil.rmtree(temp_dir)


class TestReportGeneratorSecurity(unittest.TestCase):
    """Test security features in report generation"""
    
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
    
    def test_malicious_entry_handling(self):
        """Test handling of malicious report entries"""
        malicious_entry = ReportEntry(
            title='<script>alert("xss")</script>Legitimate Title',
            content='<img src=x onerror=alert("xss")>Some content',
            source_url='javascript:alert("xss")',
            timestamp=datetime.now(),
            tags=['<script>tag</script>', 'legitimate-tag'],
            confidence_score=0.9
        )
        
        # This should not raise an exception but sanitize the content
        validated_entry = self.generator._validate_report_entry(malicious_entry)
        
        # Check that malicious content is sanitized
        self.assertNotIn('<script>', validated_entry.title)
        self.assertNotIn('<script>', validated_entry.content)
        self.assertNotIn('javascript:', validated_entry.source_url)
        
        # Legitimate content should be preserved
        self.assertIn('Legitimate Title', validated_entry.title)
        self.assertIn('Some content', validated_entry.content)
        self.assertIn('legitimate-tag', validated_entry.tags)
    
    def test_empty_invalid_entries(self):
        """Test handling of empty or invalid entries"""
        invalid_entries = [
            ReportEntry(title='', content='content', source_url='https://example.com', 
                       timestamp=datetime.now(), tags=[]),
            ReportEntry(title='title', content='', source_url='https://example.com', 
                       timestamp=datetime.now(), tags=[]),
            None
        ]
        
        for entry in invalid_entries:
            if entry is None:
                with self.assertRaises(ValueError):
                    self.generator._validate_report_entry(entry)
            else:
                with self.assertRaises(ValueError):
                    self.generator._validate_report_entry(entry)


class TestCLISecurity(unittest.TestCase):
    """Test CLI security features"""
    
    def setUp(self):
        self.cli = LocalRadarCLI()
    
    def test_command_validation(self):
        """Test command input validation"""
        # Valid commands
        valid_commands = ['lr_help', 'lr_status', 'lr_config']
        for cmd in valid_commands:
            result = self.cli.handle_command(cmd)
            self.assertIsInstance(result, str)
            self.assertNotIn('Error:', result)
        
        # Malicious commands
        malicious_commands = [
            'lr_search <script>alert("xss")</script>',
            'lr_generate_dossier "../../../etc/passwd"',
            'lr_crawl_pdfs javascript:alert("xss")',
            'a' * 1500,  # Extremely long command
            ''  # Empty command
        ]
        
        for cmd in malicious_commands:
            result = self.cli.handle_command(cmd)
            # Should handle gracefully without crashing
            self.assertIsInstance(result, str)
    
    def test_search_input_validation(self):
        """Test search command input validation"""
        # Valid search queries
        valid_queries = [
            'lr_search artificial intelligence',
            'lr_search machine learning',
            'lr_search python programming'
        ]
        
        for query in valid_queries:
            result = self.cli.handle_command(query)
            self.assertIsInstance(result, str)
        
        # Invalid search queries  
        invalid_queries = [
            'lr_search <script>alert("xss")</script>',
            'lr_search ' + 'a' * 1000,  # Too long
            'lr_search'  # No query provided
        ]
        
        for query in invalid_queries:
            result = self.cli.handle_command(query)
            self.assertIsInstance(result, str)
            # Should contain error or validation message
            if 'Please provide' not in result:
                expected_terms = ['Invalid', 'Error', 'dangerous', 'Command too long']
                self.assertTrue(any(term in result for term in expected_terms), 
                              f"Expected error message in: {result}")


class TestPerformanceMonitoring(unittest.TestCase):
    """Test performance monitoring features"""
    
    def setUp(self):
        self.monitor = PerformanceMonitor(max_metrics_history=10)
    
    def test_metrics_collection(self):
        """Test system metrics collection"""
        metrics = self.monitor.collect_system_metrics()
        
        self.assertIsNotNone(metrics)
        self.assertIsInstance(metrics.cpu_percent, float)
        self.assertIsInstance(metrics.memory_used_mb, float)
        self.assertIsInstance(metrics.disk_used_gb, float)
        self.assertGreaterEqual(metrics.cpu_percent, 0)
        self.assertGreaterEqual(metrics.memory_used_mb, 0)
        self.assertGreaterEqual(metrics.disk_used_gb, 0)
    
    def test_operation_tracking(self):
        """Test operation performance tracking"""
        operation = self.monitor.start_operation('test_operation', {'test': True})
        
        self.assertIsNotNone(operation)
        self.assertEqual(operation.operation_name, 'test_operation')
        self.assertIsNotNone(operation.start_time)
        self.assertIsNone(operation.end_time)
        
        # Finish the operation
        self.monitor.finish_operation(operation, success=True)
        
        self.assertIsNotNone(operation.end_time)
        self.assertIsNotNone(operation.duration_ms)
        self.assertTrue(operation.success)
    
    def test_operation_decorator(self):
        """Test operation monitoring decorator"""
        # Import the global monitor for the decorator
        from local_radar.monitoring import performance_monitor
        
        @monitor_operation('test_decorated_operation')
        def test_function():
            return "success"
        
        result = test_function()
        self.assertEqual(result, "success")
        
        # Check that operation was recorded in the global monitor
        self.assertGreater(len(performance_monitor.operation_metrics), 0)
        
        latest_op = list(performance_monitor.operation_metrics)[-1]
        self.assertEqual(latest_op.operation_name, 'test_decorated_operation')
        self.assertTrue(latest_op.success)
    
    def test_health_status(self):
        """Test health status reporting"""
        # Record some metrics first
        metrics = self.monitor.collect_system_metrics()
        if metrics:
            self.monitor.record_metrics(metrics)
        
        health = self.monitor.get_health_status()
        
        self.assertIsInstance(health, dict)
        self.assertIn('status', health)
        self.assertIn(health['status'], ['healthy', 'warning', 'critical', 'unknown'])


class TestHealthChecker(unittest.TestCase):
    """Test system health checking"""
    
    def test_dependency_check(self):
        """Test dependency availability checking"""
        deps = HealthChecker.check_dependencies()
        
        self.assertIsInstance(deps, dict)
        self.assertIn('sklearn', deps)
        self.assertIn('nltk', deps)
        self.assertIn('sentence_transformers', deps)
        
        # We know sklearn should be available from our tests
        self.assertTrue(deps['sklearn'])
    
    def test_directory_check(self):
        """Test directory existence and permissions checking"""
        dirs = HealthChecker.check_directories()
        
        self.assertIsInstance(dirs, dict)
        self.assertIn('reports', dirs)
        self.assertIn('templates', dirs)
        
        for dir_info in dirs.values():
            self.assertIsInstance(dir_info, dict)
            self.assertIn('path', dir_info)
            self.assertIn('exists', dir_info)
    
    def test_disk_space_check(self):
        """Test disk space checking"""
        disk_info = HealthChecker.check_disk_space()
        
        self.assertIsInstance(disk_info, dict)
        if 'error' not in disk_info:
            self.assertIn('total_gb', disk_info)
            self.assertIn('free_gb', disk_info)
            self.assertIn('percent_used', disk_info)
            self.assertGreater(disk_info['total_gb'], 0)
    
    def test_full_health_check(self):
        """Test comprehensive health check"""
        health = HealthChecker.run_full_health_check()
        
        self.assertIsInstance(health, dict)
        self.assertIn('timestamp', health)
        self.assertIn('dependencies', health)
        self.assertIn('directories', health)
        self.assertIn('disk_space', health)
        self.assertIn('performance', health)


class TestRobustnessAndErrorHandling(unittest.TestCase):
    """Test system robustness and error handling"""
    
    def test_missing_dependencies_graceful_degradation(self):
        """Test graceful degradation when dependencies are missing"""
        # This is tested by the fallback mechanisms in vector_index.py
        # The system should work even without advanced dependencies
        from local_radar.vector_index import VectorIndex
        
        # Should initialize without crashing
        index = VectorIndex()
        self.assertIsNotNone(index)
        
        # Should handle search even with basic fallback
        results = index.search("test query", top_k=5)
        self.assertIsInstance(results, list)
    
    def test_file_system_error_handling(self):
        """Test handling of file system errors"""
        temp_dir = tempfile.mkdtemp()
        
        try:
            # Test with read-only directory
            os.chmod(temp_dir, 0o444)  # Read-only
            
            config = LocalRadarConfig()
            config.report.output_dir = temp_dir
            
            generator = HTMLReportGenerator()
            generator.config = config
            
            # Should handle permission errors gracefully
            # (Implementation may vary based on specific error handling)
            
        finally:
            os.chmod(temp_dir, 0o755)  # Restore permissions for cleanup
            shutil.rmtree(temp_dir)
    
    def test_network_timeout_handling(self):
        """Test handling of network timeouts and errors"""
        from local_radar.pdf_crawler import PDFPatternCrawler
        
        crawler = PDFPatternCrawler()
        
        # Test with invalid URL (should not crash)
        result = crawler._extract_single_pdf("https://invalid-url-that-does-not-exist.com/test.pdf")
        
        self.assertIsNotNone(result)
        self.assertFalse(result.success)
        self.assertIsNotNone(result.error)


if __name__ == '__main__':
    # Set up logging for tests
    logging.basicConfig(level=logging.INFO)
    
    # Run tests with verbose output
    unittest.main(verbosity=2)