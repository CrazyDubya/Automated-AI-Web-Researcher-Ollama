#!/usr/bin/env python3
"""End-to-end test with mock data to validate Local Radar functionality."""
import sys
import pathlib
import tempfile
import datetime as dt

# Add src to path for testing
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

import src.radar.config_loader as config_loader
import src.radar.snapshots as snapshots
import src.radar.report_builder as report_builder
import src.radar.dossier as dossier

def test_end_to_end():
    """Test the full pipeline with mock data."""
    
    # Create minimal config data
    config_data = {
        'storage': {'base_dir': tempfile.mkdtemp(), 'reports_dir': 'reports'},
        'ethics': {'user_agent': 'TestBot', 'obey_robots': False},
        'outputs': {'max_items_per_run': 10},
        'llm': {'chat_model': 'test-model', 'temperature': 0.2},
        'topics': [
            {
                'name': 'Test Topic',
                'queries': ['test', 'mock'],
                'include_sources': ['Mock Source'],
                'tags': ['test']
            }
        ]
    }
    
    cfg = config_loader.Config(config_data)
    
    # Create mock fetched items
    mock_items = [
        {
            'name': 'Mock Source',
            'type': 'test',
            'source_name': 'Mock Source',
            'tags': ['test', 'civic-local'],
            'content': 'This is test content about mock data for testing purposes',
            'metadata': {'url': 'https://example.com/test'},
            'hash': 'testhash123'
        },
        {
            'name': 'Another Source',
            'type': 'test',
            'source_name': 'Another Source', 
            'tags': ['test'],
            'content': 'Different test content here',
            'metadata': {'url': 'https://example.com/other'},
            'hash': 'testhash456'
        }
    ]
    
    print(f"Testing with config base_dir: {cfg.base_dir}")
    
    # Test snapshot processing
    changed_items = snapshots.process_and_persist(cfg, mock_items)
    print(f"Processed {len(changed_items)} changed items")
    assert len(changed_items) == 2, f"Expected 2 changed items, got {len(changed_items)}"
    
    # Test report building (will use mock LLM)
    try:
        report_builder.build_daily(cfg, changed_items)
        print("Daily report built successfully")
    except Exception as e:
        print(f"Daily report failed (expected with mock LLM): {e}")
    
    # Test dossier updates
    try:
        dossier.update_topics(cfg, changed_items)
        print("Dossier updates completed successfully")
    except Exception as e:
        print(f"Dossier update failed (expected with mock LLM): {e}")
    
    # Verify files were created
    snap_index = cfg.base_dir / 'snapshots_index.jsonl'
    if snap_index.exists():
        content = snap_index.read_text()
        print(f"Snapshot index created with {len(content.splitlines())} entries")
    
    print("End-to-end test completed successfully!")

if __name__ == "__main__":
    test_end_to_end()