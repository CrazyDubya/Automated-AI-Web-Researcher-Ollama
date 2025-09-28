"""
Interactive CLI for Local Radar
Extends the existing web research CLI with Local Radar capabilities
"""

import os
import sys
import json
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from pathlib import Path
import logging

from .config import config
from .report_generator import HTMLReportGenerator
from .pdf_crawler import PDFPatternCrawler
from .vector_index import vector_index
from .base import ReportEntry
from .security import (
    validate_search_query, validate_filename, validate_url,
    sanitize_html, escape_html, log_security_event, SecurityError
)


class LocalRadarCLI:
    """Interactive CLI for Local Radar features"""
    
    def __init__(self):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.report_generator = HTMLReportGenerator()
        self.pdf_crawler = PDFPatternCrawler()
        
        # Command registry
        self.commands = {
            'lr_help': self.show_help,
            'lr_status': self.show_status,
            'lr_generate_daily': self.generate_daily_brief,
            'lr_generate_weekly': self.generate_weekly_brief,
            'lr_generate_dossier': self.generate_dossier,
            'lr_crawl_pdfs': self.crawl_pdfs,
            'lr_search': self.search_reports,
            'lr_semantic_diff': self.semantic_diff,
            'lr_index_stats': self.show_index_stats,
            'lr_config': self.show_config,
            'lr_list_reports': self.list_reports,
            'lr_clear_index': self.clear_vector_index
        }
    
    def handle_command(self, command: str) -> str:
        """Handle a Local Radar CLI command with security validation"""
        try:
            if not command or not command.strip():
                return "No command provided"
            
            # Basic command validation
            command = command.strip()
            if len(command) > 1000:  # Prevent extremely long commands
                return "Command too long"
            
            parts = command.split()
            cmd = parts[0].lower()
            args = parts[1:] if len(parts) > 1 else []
            
            # Log command execution for security monitoring
            log_security_event("CLI_COMMAND_EXECUTED", {
                "command": cmd,
                "args_count": len(args)
            }, "INFO")
            
            if cmd in self.commands:
                return self.commands[cmd](args)
            else:
                return f"Unknown Local Radar command: {cmd}. Type 'lr_help' for available commands."
                
        except SecurityError as e:
            log_security_event("CLI_SECURITY_ERROR", {
                "command": command,
                "error": str(e)
            })
            return f"Security error: {e}"
        except Exception as e:
            self.logger.error(f"Error executing command {command}: {e}")
            return f"Error: {e}"
    
    def show_help(self, args: List[str]) -> str:
        """Show available Local Radar commands"""
        help_text = """
Local Radar Commands:
===================

Report Generation:
  lr_generate_daily [date]    - Generate daily brief (default: today)
  lr_generate_weekly [date]   - Generate weekly brief (default: current week)
  lr_generate_dossier <topic> - Generate dossier for specific topic
  lr_list_reports            - List all generated reports

PDF Crawling:
  lr_crawl_pdfs              - Crawl all configured PDF sources
  lr_crawl_pdfs <pattern>    - Crawl specific URL pattern

Search & Analysis:
  lr_search <query>          - Search through indexed content
  lr_semantic_diff <id1> <id2> - Compare two documents semantically
  lr_index_stats             - Show vector index statistics

System:
  lr_status                  - Show Local Radar system status
  lr_config                  - Show current configuration
  lr_clear_index             - Clear vector index
  lr_help                    - Show this help message

Examples:
  lr_generate_daily
  lr_generate_dossier "AI research trends"
  lr_crawl_pdfs "https://example.com/reports/*.pdf"
  lr_search "artificial intelligence"
"""
        return help_text
    
    def show_status(self, args: List[str]) -> str:
        """Show Local Radar system status"""
        try:
            # Check if directories exist
            reports_exist = Path(self.config.report.output_dir).exists()
            pdfs_exist = Path(self.config.pdf.output_dir).exists()
            vector_exist = Path(self.config.vector.index_dir).exists()
            
            # Count reports
            reports_dir = Path(self.config.report.output_dir)
            brief_count = len(list(reports_dir.glob("*brief*.html"))) if reports_exist else 0
            dossier_count = len(list(reports_dir.glob("dossier_*.html"))) if reports_exist else 0
            
            # Vector index stats
            index_stats = vector_index.get_stats()
            
            status = f"""
Local Radar Status:
==================

Directories:
  Reports: {'✓' if reports_exist else '✗'} ({self.config.report.output_dir})
  PDFs: {'✓' if pdfs_exist else '✗'} ({self.config.pdf.output_dir})
  Vector Index: {'✓' if vector_exist else '✗'} ({self.config.vector.index_dir})

Content:
  Briefs: {brief_count}
  Dossiers: {dossier_count}
  Indexed Documents: {index_stats['total_documents']}
  Index Method: {index_stats['index_method']}
  Index Size: {index_stats['index_size_mb']:.2f} MB

Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
            return status
            
        except Exception as e:
            return f"Error getting status: {e}"
    
    def generate_daily_brief(self, args: List[str]) -> str:
        """Generate daily brief from recent research"""
        try:
            # Get target date
            target_date = datetime.now()
            if args:
                # TODO: Parse date from args
                pass
            
            # Find recent research entries
            entries = self._find_recent_entries(days=1)
            
            if not entries:
                return f"No research entries found for {target_date.strftime('%Y-%m-%d')}"
            
            # Generate brief
            brief = self.report_generator.generate_daily_brief(entries)
            
            # Save as HTML
            filename = self.report_generator.save_brief_html(brief)
            
            # Update index
            self.report_generator.generate_index()
            
            return f"Daily brief generated: {filename} ({len(entries)} entries)"
            
        except Exception as e:
            return f"Error generating daily brief: {e}"
    
    def generate_weekly_brief(self, args: List[str]) -> str:
        """Generate weekly brief from recent research"""
        try:
            # Find entries from last 7 days
            entries = self._find_recent_entries(days=7)
            
            if not entries:
                return "No research entries found for the past week"
            
            # Generate brief
            brief = self.report_generator.generate_weekly_brief(entries)
            
            # Save as HTML
            filename = self.report_generator.save_brief_html(brief)
            
            # Update index
            self.report_generator.generate_index()
            
            return f"Weekly brief generated: {filename} ({len(entries)} entries)"
            
        except Exception as e:
            return f"Error generating weekly brief: {e}"
    
    def generate_dossier(self, args: List[str]) -> str:
        """Generate dossier for a specific topic"""
        if not args:
            return "Please provide a topic: lr_generate_dossier <topic>"
        
        topic = " ".join(args)
        
        try:
            # Search for entries related to the topic
            search_results = vector_index.search(topic, top_k=50)
            
            # Convert search results to ReportEntry objects
            entries = []
            for result in search_results:
                metadata = result['metadata']
                if metadata.get('type') == 'report_entry':
                    entry = ReportEntry(
                        title=metadata.get('title', 'Untitled'),
                        content=result['text'],
                        source_url=metadata.get('source_url', ''),
                        timestamp=datetime.fromisoformat(metadata['timestamp']) if metadata.get('timestamp') else datetime.now(),
                        tags=metadata.get('tags', []),
                        confidence_score=metadata.get('confidence_score', result['similarity_score'])
                    )
                    entries.append(entry)
            
            if not entries:
                return f"No entries found related to topic: {topic}"
            
            # Generate dossier
            dossier = self.report_generator.generate_dossier(topic, entries)
            
            # Save as HTML
            filename = self.report_generator.save_dossier_html(dossier)
            
            # Update index
            self.report_generator.generate_index()
            
            return f"Dossier generated: {filename} ({len(entries)} entries)"
            
        except Exception as e:
            return f"Error generating dossier: {e}"
    
    def crawl_pdfs(self, args: List[str]) -> str:
        """Crawl PDF sources"""
        try:
            if args:
                # Crawl specific pattern
                pattern = " ".join(args)
                pdf_urls = self.pdf_crawler.crawl_pattern(pattern)
                
                if not pdf_urls:
                    return f"No PDFs found for pattern: {pattern}"
                
                # Extract text
                results = self.pdf_crawler.extract_text_batch(pdf_urls)
                
                # Add to vector index
                indexed_count = 0
                for url, text in results.items():
                    if text:
                        metadata = {
                            'type': 'pdf_document',
                            'source_url': url,
                            'extracted_at': datetime.now().isoformat()
                        }
                        vector_index.add_document(text, metadata)
                        indexed_count += 1
                
                return f"Crawled {len(pdf_urls)} PDFs, extracted {len([t for t in results.values() if t])}, indexed {indexed_count}"
            
            else:
                # Crawl all configured sources
                all_results = self.pdf_crawler.crawl_all_sources()
                
                total_crawled = 0
                total_extracted = 0
                total_indexed = 0
                
                for source_name, source_results in all_results.items():
                    total_crawled += len(source_results)
                    
                    for result in source_results:
                        if result.success:
                            total_extracted += 1
                            
                            # Add to vector index
                            metadata = {
                                'type': 'pdf_document',
                                'source_url': result.url,
                                'source_name': source_name,
                                'extraction_method': result.method,
                                'extracted_at': datetime.now().isoformat()
                            }
                            metadata.update(result.metadata)
                            
                            vector_index.add_document(result.text, metadata)
                            total_indexed += 1
                
                # Save results
                results_file = self.pdf_crawler.save_extraction_results(all_results)
                
                return f"Crawled {total_crawled} PDFs from {len(all_results)} sources. Extracted: {total_extracted}, Indexed: {total_indexed}. Results saved to: {results_file}"
            
        except Exception as e:
            return f"Error crawling PDFs: {e}"
    
    def search_reports(self, args: List[str]) -> str:
        """Search through indexed content with security validation"""
        if not args:
            return "Please provide a search query: lr_search <query>"
        
        query = " ".join(args)
        
        try:
            # Validate and sanitize search query
            safe_query = validate_search_query(query)
            
            results = vector_index.search(safe_query, top_k=10)
            
            if not results:
                return f"No results found for query: {escape_html(safe_query)}"
            
            output = [f"Search results for '{escape_html(safe_query)}':\n"]
            
            for i, result in enumerate(results, 1):
                metadata = result['metadata']
                # Sanitize metadata for display
                title = escape_html(metadata.get('title', f"Document {metadata.get('doc_id', i)}"))
                doc_type = escape_html(metadata.get('type', 'unknown'))
                score = result['similarity_score']
                
                output.append(f"{i}. {title} ({doc_type}) - Score: {score:.3f}")
                
                # Show sanitized excerpt
                text_excerpt = escape_html(result['text'][:200])
                if len(result['text']) > 200:
                    text_excerpt += "..."
                output.append(f"   {text_excerpt}")
                output.append("")
            
            return "\n".join(output)
            
        except SecurityError as e:
            log_security_event("SEARCH_VALIDATION_ERROR", {
                "query": query,
                "error": str(e)
            })
            return f"Invalid search query: {e}"
        except Exception as e:
            return f"Error searching: {e}"
    
    def semantic_diff(self, args: List[str]) -> str:
        """Compare two documents semantically"""
        if len(args) < 2:
            return "Please provide two document IDs: lr_semantic_diff <id1> <id2>"
        
        doc_id1, doc_id2 = args[0], args[1]
        
        try:
            # Find documents by ID
            doc1_text = None
            doc2_text = None
            
            for i, metadata in enumerate(vector_index.document_metadata):
                if metadata.get('doc_id') == doc_id1:
                    doc1_text = vector_index.documents[i]
                elif metadata.get('doc_id') == doc_id2:
                    doc2_text = vector_index.documents[i]
            
            if doc1_text is None:
                return f"Document not found: {doc_id1}"
            if doc2_text is None:
                return f"Document not found: {doc_id2}"
            
            # Calculate semantic difference
            diff_result = vector_index.semantic_diff(doc1_text, doc2_text)
            
            # Calculate sentence-level changes
            sentence_changes = vector_index.sentence_level_changes(doc1_text, doc2_text)
            
            output = [
                f"Semantic Comparison:",
                f"Similarity: {diff_result['similarity_score']:.3f}",
                f"Difference: {diff_result['difference_score']:.3f}",
                f"Method: {diff_result['method']}",
                f"",
                f"Sentence-level changes: {len(sentence_changes)}"
            ]
            
            if sentence_changes:
                output.append("")
                for change in sentence_changes[:5]:  # Show first 5 changes
                    output.append(f"- {change['type']}: {change.get('sentence', change.get('old_sentence', ''))[:100]}...")
            
            return "\n".join(output)
            
        except Exception as e:
            return f"Error comparing documents: {e}"
    
    def show_index_stats(self, args: List[str]) -> str:
        """Show vector index statistics"""
        try:
            stats = vector_index.get_stats()
            
            output = [
                "Vector Index Statistics:",
                "========================",
                f"Total Documents: {stats['total_documents']}",
                f"Index Method: {stats['index_method']}",
                f"Embedding Model: {stats.get('embedding_model', 'N/A')}",
                f"Index Size: {stats['index_size_mb']:.2f} MB",
                f"Last Updated: {stats['last_updated']}"
            ]
            
            return "\n".join(output)
            
        except Exception as e:
            return f"Error getting index stats: {e}"
    
    def show_config(self, args: List[str]) -> str:
        """Show current Local Radar configuration"""
        try:
            output = [
                "Local Radar Configuration:",
                "=========================",
                "",
                "Reports:",
                f"  Output Directory: {self.config.report.output_dir}",
                f"  Max Entries per Page: {self.config.report.max_entries_per_page}",
                f"  Tag Filtering: {self.config.report.enable_tag_filtering}",
                "",
                "PDF Crawling:",
                f"  Output Directory: {self.config.pdf.output_dir}",
                f"  Batch Size: {self.config.pdf.batch_size}",
                f"  Max Concurrent: {self.config.pdf.max_concurrent}",
                f"  OCR Enabled: {self.config.pdf.enable_ocr}",
                f"  OCR Languages: {', '.join(self.config.pdf.ocr_languages)}",
                "",
                "Vector Index:",
                f"  Index Directory: {self.config.vector.index_dir}",
                f"  Embedding Model: {self.config.vector.embedding_model}",
                f"  Chunk Size: {self.config.vector.chunk_size}",
                f"  Similarity Threshold: {self.config.vector.similarity_threshold}"
            ]
            
            return "\n".join(output)
            
        except Exception as e:
            return f"Error showing config: {e}"
    
    def list_reports(self, args: List[str]) -> str:
        """List all generated reports"""
        try:
            reports_dir = Path(self.config.report.output_dir)
            
            if not reports_dir.exists():
                return f"Reports directory does not exist: {reports_dir}"
            
            briefs = list(reports_dir.glob("*brief*.html"))
            dossiers = list(reports_dir.glob("dossier_*.html"))
            
            output = [
                f"Generated Reports ({len(briefs + dossiers)} total):",
                "=================="
            ]
            
            if briefs:
                output.append("\nBriefs:")
                for brief in sorted(briefs, key=lambda x: x.stat().st_mtime, reverse=True):
                    mtime = datetime.fromtimestamp(brief.stat().st_mtime)
                    output.append(f"  {brief.name} - {mtime.strftime('%Y-%m-%d %H:%M')}")
            
            if dossiers:
                output.append("\nDossiers:")
                for dossier in sorted(dossiers, key=lambda x: x.stat().st_mtime, reverse=True):
                    mtime = datetime.fromtimestamp(dossier.stat().st_mtime)
                    output.append(f"  {dossier.name} - {mtime.strftime('%Y-%m-%d %H:%M')}")
            
            if not briefs and not dossiers:
                output.append("\nNo reports found.")
            
            return "\n".join(output)
            
        except Exception as e:
            return f"Error listing reports: {e}"
    
    def clear_vector_index(self, args: List[str]) -> str:
        """Clear the vector index"""
        try:
            vector_index.clear_index()
            return "Vector index cleared successfully."
        except Exception as e:
            return f"Error clearing index: {e}"
    
    def _find_recent_entries(self, days: int) -> List[ReportEntry]:
        """Find recent research entries from various sources"""
        # This is a placeholder - in a real implementation, you would:
        # 1. Check for recent research session files
        # 2. Query the vector index for recent entries
        # 3. Load from a database of research entries
        
        entries = []
        cutoff_date = datetime.now() - timedelta(days=days)
        
        # Search vector index for recent entries
        for i, metadata in enumerate(vector_index.document_metadata):
            if metadata.get('type') == 'report_entry':
                entry_date_str = metadata.get('timestamp')
                if entry_date_str:
                    try:
                        entry_date = datetime.fromisoformat(entry_date_str)
                        if entry_date >= cutoff_date:
                            entry = ReportEntry(
                                title=metadata.get('title', 'Untitled'),
                                content=vector_index.documents[i],
                                source_url=metadata.get('source_url', ''),
                                timestamp=entry_date,
                                tags=metadata.get('tags', []),
                                confidence_score=metadata.get('confidence_score', 0.0)
                            )
                            entries.append(entry)
                    except Exception:
                        pass
        
        return entries


# Global CLI instance
local_radar_cli = LocalRadarCLI()