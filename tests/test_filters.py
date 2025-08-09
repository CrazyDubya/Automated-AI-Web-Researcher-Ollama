import sys
import pathlib

# Add src to path for testing
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

import src.radar.filters as filters

def test_item_matches_topic_source():
    item = {'name': 'SourceA', 'tags': [], 'content': 'foo'}
    topic = {'include_sources': ['SourceA'], 'tags': [], 'queries': []}
    assert filters.item_matches_topic(item, topic)

def test_item_matches_topic_tags():
    item = {'name': 'SourceB', 'tags': ['civic-local'], 'content': 'foo'}
    topic = {'include_sources': [], 'tags': ['civic-local'], 'queries': []}
    assert filters.item_matches_topic(item, topic)

def test_item_matches_topic_queries():
    item = {'name': 'SourceC', 'tags': [], 'content': 'broadband infrastructure'}
    topic = {'include_sources': [], 'tags': [], 'queries': ['broadband']}
    assert filters.item_matches_topic(item, topic)

def test_item_no_match():
    item = {'name': 'SourceD', 'tags': ['unrelated'], 'content': 'nothing here'}
    topic = {'include_sources': ['Other'], 'tags': ['civic-local'], 'queries': ['broadband']}
    assert not filters.item_matches_topic(item, topic)

if __name__ == "__main__":
    test_item_matches_topic_source()
    test_item_matches_topic_tags()
    test_item_matches_topic_queries()
    test_item_no_match()
    print("test_filters.py passed")