"""Living topic dossier updates."""
import pathlib, datetime as dt, json
from typing import List, Dict, Any
import sys
import os

# Add the parent directory to sys.path to allow imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from common import llm_adapter


def update_topics(cfg, changed_items: List[Dict[str, Any]]):
    if not changed_items:
        return
    # naive: treat all changed items as potential new evidence for all topics (filter later by tags / queries)
    for topic in cfg.topics:
        _update_one(cfg, topic, changed_items)


def _update_one(cfg, topic: Dict[str, Any], changed_items: List[Dict[str, Any]]):
    name = topic['name']
    out_dir = cfg.reports_dir / 'dossiers'
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{name.replace(' ','_').lower()}.md"
    new_evidence_lines = []
    for it in changed_items[:20]:
        new_evidence_lines.append(f"- {it['name']} @ {it['timestamp']}")
    prompt = (pathlib.Path('prompts') / 'dossier_topic.md').read_text()
    filled = prompt.replace('{{topic_name}}', name) \
                   .replace('{{queries}}', ', '.join(topic.get('queries', []))) \
                   .replace('{{new_items}}', '\n'.join(new_evidence_lines))
    update_text = llm_adapter.complete(cfg, filled)
    stamp = dt.datetime.utcnow().isoformat()
    header = f"\n\n## Update {stamp}\n" + update_text + "\n"
    if not path.exists():
        path.write_text(f"# Dossier: {name}\n\nInitial creation {stamp}\n" + header)
    else:
        with path.open('a', encoding='utf-8') as fh:
            fh.write(header)
    print(f"[dossier] Updated {path}")


def regenerate_all(cfg):
    print("[dossier] Regeneration not yet implemented (would consolidate from snapshot index). TODO")