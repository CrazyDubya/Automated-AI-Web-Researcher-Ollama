#!/usr/bin/env python3
"""
Radar CLI - Enhanced research system entry point.
Provides commands for search, PDF discovery, metrics, and UI generation.
"""
import argparse
import sys
import logging
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.radar.config import get_radar_config, ensure_radar_dirs
from src.radar.search_cli import create_search_cli
from src.radar.pdf_discovery import get_pdf_discovery
from src.radar.embedding_cache import get_embedding_cache
from src.radar.async_fetcher import get_async_fetcher


def setup_logging(verbose: bool = False):
    """Set up logging configuration."""
    level = logging.INFO if verbose else logging.WARNING
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


def cmd_search(args):
    """Handle search command."""
    search_cli = create_search_cli()
    parser = search_cli.create_parser()
    
    # Parse search arguments
    search_args = parser.parse_args(args.search_args)
    
    try:
        result = search_cli.execute_search(search_args)
        
        print(f"\n🔍 Search: {result['query']}")
        if result['processed_query'] != result['query']:
            print(f"📈 Expanded: {result['processed_query']}")
        
        print(f"📊 Found {result['total_results']} results\n")
        
        for formatted_result in result['results']:
            print(formatted_result)
            print("-" * 50)
            
    except Exception as e:
        print(f"❌ Search failed: {e}")
        return 1
    
    return 0


def cmd_discover_pdfs(args):
    """Handle PDF discovery command."""
    discovery = get_pdf_discovery()
    
    if not discovery.enabled:
        print("❌ PDF discovery is disabled in configuration")
        return 1
    
    try:
        new_pdfs = discovery.discover_and_enqueue()
        
        if new_pdfs:
            print(f"✅ Discovered {len(new_pdfs)} new PDFs:")
            for pdf_url in new_pdfs:
                print(f"  📄 {pdf_url}")
        else:
            print("ℹ️  No new PDFs discovered")
        
        # Show metrics
        metrics = discovery.get_metrics()
        print(f"\n📊 Discovery Metrics:")
        for key, value in metrics.items():
            print(f"  {key}: {value}")
            
    except Exception as e:
        print(f"❌ PDF discovery failed: {e}")
        return 1
    
    return 0


def cmd_metrics(args):
    """Handle metrics command."""
    try:
        print("📊 Radar System Metrics\n")
        
        # Embedding cache metrics
        if get_radar_config().is_enabled('embedding_cache'):
            cache = get_embedding_cache()
            cache_metrics = cache.get_metrics()
            print("🔍 Embedding Cache:")
            for key, value in cache_metrics.items():
                print(f"  {key}: {value}")
            print()
        
        # PDF discovery metrics
        if get_radar_config().is_enabled('pdf.discovery'):
            discovery = get_pdf_discovery()
            pdf_metrics = discovery.get_metrics()
            print("📄 PDF Discovery:")
            for key, value in pdf_metrics.items():
                print(f"  {key}: {value}")
            print()
        
        # Async fetcher metrics
        fetcher = get_async_fetcher()
        fetch_metrics = fetcher.get_metrics()
        print("🌐 Async Fetcher:")
        for key, value in fetch_metrics.items():
            print(f"  {key}: {value}")
        print()
        
        # Configuration status
        config = get_radar_config()
        print("⚙️  Configuration:")
        print(f"  trailkeeper.enabled: {config.is_enabled('trailkeeper')}")
        print(f"  embedding_cache.enabled: {config.is_enabled('embedding_cache')}")
        print(f"  pdf.discovery.enabled: {config.is_enabled('pdf.discovery')}")
        print(f"  ethics.concurrency.enabled: {config.is_enabled('ethics.concurrency')}")
        
    except Exception as e:
        print(f"❌ Failed to get metrics: {e}")
        return 1
    
    return 0


def cmd_build_ui(args):
    """Handle UI build command."""
    try:
        # Import here to avoid issues if dependencies are missing
        from scripts.build_static_ui import StaticUIBuilder
        
        builder = StaticUIBuilder(args.output_dir)
        builder.build_static_ui()
        
    except ImportError as e:
        print(f"❌ UI build dependencies missing: {e}")
        return 1
    except Exception as e:
        print(f"❌ UI build failed: {e}")
        return 1
    
    return 0


def cmd_init(args):
    """Handle initialization command."""
    try:
        print("🚀 Initializing Radar system...")
        
        # Ensure directories exist
        ensure_radar_dirs()
        print("✅ Created radar directories")
        
        # Initialize databases
        if get_radar_config().is_enabled('embedding_cache'):
            cache = get_embedding_cache()
            print("✅ Initialized embedding cache")
        
        if get_radar_config().is_enabled('pdf.discovery'):
            discovery = get_pdf_discovery()
            print("✅ Initialized PDF discovery")
        
        print("🎯 Radar system initialized successfully!")
        
    except Exception as e:
        print(f"❌ Initialization failed: {e}")
        return 1
    
    return 0


def create_parser():
    """Create the main argument parser."""
    parser = argparse.ArgumentParser(
        description='Radar - Enhanced Research System',
        prog='radar'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose output'
    )
    
    parser.add_argument(
        '--config',
        help='Configuration file path',
        default='config.yaml'
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Search command
    search_parser = subparsers.add_parser('search', help='Enhanced search with filtering')
    search_parser.add_argument(
        'search_args',
        nargs=argparse.REMAINDER,
        help='Search arguments (use --help after search for details)'
    )
    
    # PDF discovery command
    pdf_parser = subparsers.add_parser('discover-pdfs', help='Discover new PDFs from index pages')
    
    # Metrics command
    metrics_parser = subparsers.add_parser('metrics', help='Show system metrics')
    
    # Build UI command
    ui_parser = subparsers.add_parser('build-ui', help='Build static web UI')
    ui_parser.add_argument(
        '--output-dir',
        help='Output directory for UI files'
    )
    
    # Init command
    init_parser = subparsers.add_parser('init', help='Initialize radar system')
    
    return parser


def main():
    """Main CLI entry point."""
    parser = create_parser()
    args = parser.parse_args()
    
    setup_logging(args.verbose)
    
    # Handle case where no command is provided
    if not args.command:
        parser.print_help()
        return 1
    
    # Ensure radar system is initialized
    try:
        ensure_radar_dirs()
    except Exception as e:
        print(f"❌ Failed to initialize radar directories: {e}")
        return 1
    
    # Route to appropriate command handler
    commands = {
        'search': cmd_search,
        'discover-pdfs': cmd_discover_pdfs,
        'metrics': cmd_metrics,
        'build-ui': cmd_build_ui,
        'init': cmd_init
    }
    
    handler = commands.get(args.command)
    if handler:
        return handler(args)
    else:
        print(f"❌ Unknown command: {args.command}")
        return 1


if __name__ == '__main__':
    sys.exit(main())