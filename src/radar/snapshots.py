"""Snapshot management: persist fetched content, detect changes, produce diffable units."""
import hashlib, pathlib, json, datetime as dt
from typing import Dict, Any, List
from . import diffing

SNAP_INDEX = "snapshots_index.jsonl"


def _hash_content(text: str) -> str:
    return hashlib.sha256(text.encode('utf-8')).hexdigest()[:16]


def process_and_persist(cfg, fetched_items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    base = cfg.base_dir
    index_path = base / SNAP_INDEX
    changed: List[Dict[str, Any]] = []
    previous = {}
    if index_path.exists():
        for line in index_path.read_text().splitlines():
            try:
                rec = json.loads(line)
                previous.setdefault(rec['name'], []).append(rec)
            except json.JSONDecodeError:
                continue
    with index_path.open('a', encoding='utf-8') as fh:
        for item in fetched_items:
            content = item.get('content', '')
            h = _hash_content(content)
            name = item['name']
            ts = dt.datetime.utcnow().isoformat()
            earlier = previous.get(name, [])
            last_hash = earlier[-1]['hash'] if earlier else None
            if h != last_hash:
                # compute diff with previous content if exists
                before = earlier[-1]['content'] if earlier else ''
                diff_txt = diffing.unified_diff(before, content, from_label='prev', to_label='new')
                rec = {
                    'name': name,
                    'hash': h,
                    'timestamp': ts,
                    'type': item.get('type'),
                    'metadata': item.get('metadata', {}),
                    'content': content,
                    'diff': diff_txt,
                }
                fh.write(json.dumps(rec) + "\n")
                changed.append(rec)
    return changed