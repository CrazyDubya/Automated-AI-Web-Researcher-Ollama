"""
Enhanced Search CLI Module.
Provides advanced search capabilities with filtering and streaming.
"""
import argparse
import re
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any, Generator
import json

from .config import get_radar_config

logger = logging.getLogger(__name__)


class QueryExpander:
    """Simple query expansion using synonym mapping."""
    
    def __init__(self):
        # Basic synonym map - could be loaded from config
        self.synonyms = {
            'ai': ['artificial intelligence', 'machine learning', 'ml'],
            'ml': ['machine learning', 'ai', 'artificial intelligence'],
            'tech': ['technology', 'technical'],
            'dev': ['development', 'developer'],
            'app': ['application', 'software'],
            'web': ['website', 'internet', 'online'],
            'mobile': ['smartphone', 'phone', 'cellular'],
            'data': ['information', 'dataset'],
        }
    
    def expand_query(self, query: str) -> str:
        """Expand query with synonyms."""
        words = query.lower().split()
        expanded_terms = []
        
        for word in words:
            expanded_terms.append(word)
            if word in self.synonyms:
                expanded_terms.extend(self.synonyms[word])
        
        return ' '.join(expanded_terms)


class SearchHighlighter:
    """Highlight search terms in text passages."""
    
    def __init__(self):
        self.highlight_start = "**"
        self.highlight_end = "**"
    
    def highlight_terms(self, text: str, query: str) -> str:
        """Highlight query terms in text using simple markup."""
        if not query or not text:
            return text
        
        # Extract words from query
        query_words = re.findall(r'\b\w+\b', query.lower())
        if not query_words:
            return text
        
        highlighted_text = text
        
        for word in query_words:
            # Case-insensitive replacement with word boundaries
            pattern = r'\b' + re.escape(word) + r'\b'
            replacement = f"{self.highlight_start}{word}{self.highlight_end}"
            
            highlighted_text = re.sub(
                pattern, 
                replacement, 
                highlighted_text, 
                flags=re.IGNORECASE
            )
        
        return highlighted_text


class EnhancedSearchCLI:
    """Enhanced search CLI with advanced filtering and options."""
    
    def __init__(self):
        config = get_radar_config()
        search_config = config.get_section('search')
        
        self.default_since_days = search_config.get('filter_default_since_days', 14)
        self.query_expansion_enabled = search_config.get('query_expansion', False)
        self.stream_answers = search_config.get('stream_answers', False)
        self.result_limit = search_config.get('result_limit', 12)
        
        self.query_expander = QueryExpander()
        self.highlighter = SearchHighlighter()
    
    def create_parser(self) -> argparse.ArgumentParser:
        """Create argument parser for search CLI."""
        parser = argparse.ArgumentParser(
            description='Enhanced radar search with filtering and streaming'
        )
        
        parser.add_argument(
            'query',
            help='Search query'
        )
        
        parser.add_argument(
            '--filter-tags',
            help='Filter by tags (comma-separated)',
            default=''
        )
        
        parser.add_argument(
            '--since',
            help='Filter results since date (YYYY-MM-DD)',
            default=None
        )
        
        parser.add_argument(
            '--until',
            help='Filter results until date (YYYY-MM-DD)',
            default=None
        )
        
        parser.add_argument(
            '--limit',
            type=int,
            help=f'Limit number of results (default: {self.result_limit})',
            default=self.result_limit
        )
        
        parser.add_argument(
            '--stream',
            action='store_true',
            help='Stream answers if LLM backend supports it'
        )
        
        parser.add_argument(
            '--no-expand',
            action='store_true',
            help='Disable query expansion'
        )
        
        parser.add_argument(
            '--no-highlight',
            action='store_true',
            help='Disable term highlighting'
        )
        
        return parser
    
    def parse_date(self, date_str: str) -> Optional[datetime]:
        """Parse date string in YYYY-MM-DD format."""
        try:
            return datetime.strptime(date_str, '%Y-%m-%d')
        except ValueError:
            logger.warning(f"Invalid date format: {date_str}")
            return None
    
    def apply_date_filters(self, results: List[Dict], since: Optional[str], until: Optional[str]) -> List[Dict]:
        """Apply date filters to search results."""
        filtered_results = results
        
        # Apply since filter
        if since:
            since_date = self.parse_date(since)
            if since_date:
                filtered_results = [
                    r for r in filtered_results 
                    if self._get_result_date(r) >= since_date
                ]
        else:
            # Apply default since filter
            default_since = datetime.now() - timedelta(days=self.default_since_days)
            filtered_results = [
                r for r in filtered_results 
                if self._get_result_date(r) >= default_since
            ]
        
        # Apply until filter
        if until:
            until_date = self.parse_date(until)
            if until_date:
                filtered_results = [
                    r for r in filtered_results 
                    if self._get_result_date(r) <= until_date
                ]
        
        return filtered_results
    
    def _get_result_date(self, result: Dict) -> datetime:
        """Extract date from search result."""
        # This would depend on the actual result format
        # For now, assume results have a 'timestamp' or 'date' field
        timestamp = result.get('timestamp') or result.get('date') or result.get('ts')
        
        if isinstance(timestamp, (int, float)):
            return datetime.fromtimestamp(timestamp)
        elif isinstance(timestamp, str):
            try:
                return datetime.fromisoformat(timestamp)
            except ValueError:
                pass
        
        # Default to current time if no date found
        return datetime.now()
    
    def apply_tag_filters(self, results: List[Dict], filter_tags: str) -> List[Dict]:
        """Apply tag filters to search results."""
        if not filter_tags:
            return results
        
        tags = [tag.strip().lower() for tag in filter_tags.split(',')]
        filtered_results = []
        
        for result in results:
            result_tags = result.get('tags', [])
            if isinstance(result_tags, str):
                result_tags = [result_tags]
            
            result_tags_lower = [tag.lower() for tag in result_tags]
            
            # Check if any of the filter tags match
            if any(tag in result_tags_lower for tag in tags):
                filtered_results.append(result)
        
        return filtered_results
    
    def process_query(self, query: str, expand: bool = True) -> str:
        """Process and optionally expand the search query."""
        if expand and self.query_expansion_enabled:
            expanded = self.query_expander.expand_query(query)
            logger.info(f"Expanded query: '{query}' -> '{expanded}'")
            return expanded
        return query
    
    def highlight_passages(self, passages: List[str], query: str, highlight: bool = True) -> List[str]:
        """Highlight search terms in passages."""
        if not highlight:
            return passages
        
        highlighted = []
        for passage in passages:
            highlighted_passage = self.highlighter.highlight_terms(passage, query)
            highlighted.append(highlighted_passage)
        
        return highlighted
    
    def format_result(self, result: Dict, query: str, highlight: bool = True) -> str:
        """Format a single search result for display."""
        title = result.get('title', 'Untitled')
        source = result.get('source', 'Unknown')
        url = result.get('url', '')
        timestamp = result.get('timestamp', '')
        
        # Format timestamp
        if isinstance(timestamp, (int, float)):
            time_str = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M')
        else:
            time_str = str(timestamp)
        
        # Get content excerpt
        content = result.get('content', result.get('excerpt', ''))
        if highlight:
            content = self.highlighter.highlight_terms(content, query)
        
        # Limit content length
        if len(content) > 300:
            content = content[:300] + "..."
        
        formatted = f"""
📄 {title}
🌐 Source: {source}
🕐 Date: {time_str}
📝 {content}
"""
        
        if url:
            formatted += f"🔗 {url}\n"
        
        return formatted
    
    def stream_response(self, response: str) -> Generator[str, None, None]:
        """Stream response if supported."""
        # This would integrate with LLM streaming capabilities
        # For now, just yield the full response
        yield response
    
    def execute_search(self, args: argparse.Namespace) -> Dict[str, Any]:
        """Execute search with given arguments."""
        # Process query
        processed_query = self.process_query(args.query, not args.no_expand)
        
        # This would integrate with the actual search backend
        # For now, return a mock response structure
        mock_results = [
            {
                'title': 'Sample Result 1',
                'source': 'example.com',
                'url': 'https://example.com/article1',
                'timestamp': datetime.now().timestamp(),
                'content': f'This is sample content containing {args.query} terms.',
                'tags': ['technology', 'research']
            },
            {
                'title': 'Sample Result 2',
                'source': 'research.org',
                'url': 'https://research.org/paper2',
                'timestamp': (datetime.now() - timedelta(days=5)).timestamp(),
                'content': f'Another sample with relevant {args.query} information.',
                'tags': ['science', 'analysis']
            }
        ]
        
        # Apply filters
        filtered_results = self.apply_date_filters(mock_results, args.since, args.until)
        filtered_results = self.apply_tag_filters(filtered_results, args.filter_tags)
        
        # Apply limit
        filtered_results = filtered_results[:args.limit]
        
        # Format results
        formatted_results = []
        for result in filtered_results:
            formatted = self.format_result(result, processed_query, not args.no_highlight)
            formatted_results.append(formatted)
        
        return {
            'query': args.query,
            'processed_query': processed_query,
            'total_results': len(filtered_results),
            'results': formatted_results,
            'streaming': args.stream and self.stream_answers
        }


def create_search_cli() -> EnhancedSearchCLI:
    """Create enhanced search CLI instance."""
    return EnhancedSearchCLI()


def main():
    """Main CLI entry point."""
    search_cli = create_search_cli()
    parser = search_cli.create_parser()
    args = parser.parse_args()
    
    try:
        result = search_cli.execute_search(args)
        
        print(f"\n🔍 Search: {result['query']}")
        if result['processed_query'] != result['query']:
            print(f"📈 Expanded: {result['processed_query']}")
        
        print(f"📊 Found {result['total_results']} results\n")
        
        for formatted_result in result['results']:
            print(formatted_result)
            print("-" * 50)
        
    except Exception as e:
        logger.error(f"Search failed: {e}")
        print(f"❌ Search failed: {e}")


if __name__ == '__main__':
    main()