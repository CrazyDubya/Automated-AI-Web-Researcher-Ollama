"""Report generation (daily & weekly). Uses simple template substitution for now."""
import datetime as dt, pathlib, json
from typing import List, Dict, Any
import sys
import os

# Add the parent directory to sys.path to allow imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from common import llm_adapter, utils

PROMPTS_DIR = pathlib.Path('prompts')


def _load_prompt(name: str) -> str:
    return (PROMPTS_DIR / name).read_text()


def build_daily(cfg, changed_items: List[Dict[str, Any]], regenerate: bool = False):
    if not changed_items and not regenerate:
        print("[daily] No changed items; skipping daily report generation.")
        return
    prompt = _load_prompt('radar_daily.md')
    date_str = dt.date.today().isoformat()
    # Minimal rendering of items
    items_text = []
    for it in changed_items:
        excerpt = utils.first_n_chars(it.get('content',''), 500).replace('\n',' ')
        items_text.append(f"- {it['name']} @ {it['timestamp']}\n  Excerpt: {excerpt}\n")
    filled = prompt.replace('{{date}}', date_str) \
                   .replace('{{sources_count}}', str(len(changed_items))) \
                   .replace('{{notes}}', '') \
                   .replace('{{items_with_excerpts_and_links}}', '\n'.join(items_text))
    analysis = llm_adapter.complete(cfg, filled)
    out_dir = cfg.reports_dir / 'daily'
    out_path = out_dir / f"daily_{date_str}.md"
    out_path.write_text(analysis)
    print(f"[daily] Wrote {out_path}")


def build_weekly(cfg, regenerate: bool = False):
    # Collect last 7 days changed items from snapshot index
    index_path = cfg.base_dir / 'snapshots_index.jsonl'
    if not index_path.exists():
        print("[weekly] No snapshots yet.")
        return
    prompt = _load_prompt('radar_weekly.md')
    cutoff = dt.datetime.utcnow() - dt.timedelta(days=7)
    items = []
    for line in index_path.read_text().splitlines():
        try:
            rec = json.loads(line)
            ts = dt.datetime.fromisoformat(rec['timestamp'])
            if ts >= cutoff:
                items.append(rec)
        except Exception:
            continue
    if not items and not regenerate:
        print("[weekly] No items in last 7 days; skipping weekly report.")
        return
    items_text = []
    for it in items[:50]:  # cap for prompt size
        diff_excerpt = utils.first_n_chars(it.get('diff',''), 400).replace('\n',' ')
        items_text.append(f"- {it['name']} change {it['timestamp']} Diff: {diff_excerpt}")
    filled = prompt.replace('{{date}}', dt.date.today().isoformat()) \
                   .replace('{{sources_count}}', str(len(items))) \
                   .replace('{{items_grouped_by_tag_with_diffs_and_links}}', '\n'.join(items_text))
    analysis = llm_adapter.complete(cfg, filled)
    out_dir = cfg.reports_dir / 'weekly'
    out_path = out_dir / f"weekly_{dt.date.today().isoformat()}.md"
    out_path.write_text(analysis)
    print(f"[weekly] Wrote {out_path}")