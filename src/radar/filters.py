"""Filtering & relevance helpers for dossiers."""
from __future__ import annotations
from typing import Dict, Any, List

def item_matches_topic(item: Dict[str, Any], topic: Dict[str, Any]) -> bool:
    # Source name direct include
    if item.get('name') in topic.get('include_sources', []):
        return True
    # Tag intersection
    if set(item.get('tags', [])) & set(topic.get('tags', [])):
        return True
    # Query keyword match
    content_lower = item.get('content','').lower()
    for q in topic.get('queries', []):
        if q.lower() in content_lower:
            return True
    return False

def filter_relevant(items: List[Dict[str, Any]], topic: Dict[str, Any]) -> List[Dict[str, Any]]:
    return [it for it in items if item_matches_topic(it, topic)]