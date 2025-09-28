"""Living topic dossier updates with relevance filtering."""
import pathlib, datetime as dt, sys
from typing import List, Dict, Any

# Add absolute import paths
ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

import src.common.llm_adapter as llm_adapter
import src.radar.filters as filters


def update_topics(cfg, changed_items: List[Dict[str, Any]]):
    if not changed_items:
        return
    for topic in cfg.topics:
        rel = filters.filter_relevant(changed_items, topic)
        if rel:
            _update_one(cfg, topic, rel)


def _update_one(cfg, topic: Dict[str, Any], rel_items: List[Dict[str, Any]]):
    name = topic['name']
    out_dir = cfg.reports_dir / 'dossiers'
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{name.replace(' ','_').lower()}.md"
    new_evidence_lines = []
    for it in rel_items[:30]:
        new_evidence_lines.append(f"- {it['name']} @ {it['timestamp']}")
    prompt = (pathlib.Path('prompts') / 'dossier_topic.md').read_text()
    filled = (prompt
              .replace('{{topic_name}}', name)
              .replace('{{queries}}', ', '.join(topic.get('queries', [])))
              .replace('{{new_items}}', '\n'.join(new_evidence_lines)))
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
    print("[dossier] Regeneration not implemented yet. TODO: rebuild from snapshot index.")