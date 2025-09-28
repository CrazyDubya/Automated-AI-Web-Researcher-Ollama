"""Report generation with tag grouping and item cap."""
import datetime as dt, pathlib, json, itertools, sys
from typing import List, Dict, Any

# Add absolute import paths
ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

import src.common.llm_adapter as llm_adapter
import src.common.utils as utils

PROMPTS_DIR = pathlib.Path('prompts')


def _load_prompt(name: str) -> str:
    return (PROMPTS_DIR / name).read_text()


def _group_by_tags(items: List[Dict[str, Any]]):
    groups = {}
    for it in items:
        tags = it.get('tags') or ['untagged']
        for t in tags:
            groups.setdefault(t, []).append(it)
    return groups


def build_daily(cfg, changed_items: List[Dict[str, Any]], regenerate: bool = False):
    cap = cfg.outputs.get('max_items_per_run', 40)
    if not changed_items and not regenerate:
        print("[daily] No changed items; skipping daily report generation.")
        return
    prompt = _load_prompt('radar_daily.md')
    date_str = dt.date.today().isoformat()
    items = changed_items[:cap]
    grouped = _group_by_tags(items)
    lines = []
    for tag, its in grouped.items():
        lines.append(f"### Tag: {tag} ({len(its)})")
        for it in its[:10]:
            diff_excerpt = utils.first_diff_lines(it.get('diff',''), 6)
            lines.append(f"- {it['name']} @ {it['timestamp']}\n  Diff: {diff_excerpt}")
    filled = (prompt
              .replace('{{date}}', date_str)
              .replace('{{sources_count}}', str(len(changed_items)))
              .replace('{{notes}}', '')
              .replace('{{items_with_excerpts_and_links}}', '\n'.join(lines)))
    analysis = llm_adapter.complete(cfg, filled)
    out_path = (cfg.reports_dir / 'daily' / f"daily_{date_str}.md")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(analysis)
    print(f"[daily] Wrote {out_path}")


def build_weekly(cfg, regenerate: bool = False):
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
        print("[weekly] No items last 7 days; skipping weekly report.")
        return
    grouped = _group_by_tags(items)
    segments = []
    for tag, its in grouped.items():
        seg_lines = []
        for it in its[:12]:
            diff_excerpt = utils.first_diff_lines(it.get('diff',''), 6)
            seg_lines.append(f"- {it['name']} change {it['timestamp']} | {diff_excerpt}")
        segments.append(f"### {tag}\n" + '\n'.join(seg_lines))
    filled = (prompt
              .replace('{{date}}', dt.date.today().isoformat())
              .replace('{{sources_count}}', str(len(items)))
              .replace('{{items_grouped_by_tag_with_diffs_and_links}}', '\n\n'.join(segments)))
    analysis = llm_adapter.complete(cfg, filled)
    out_path = cfg.reports_dir / 'weekly' / f"weekly_{dt.date.today().isoformat()}.md"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(analysis)
    print(f"[weekly] Wrote {out_path}")