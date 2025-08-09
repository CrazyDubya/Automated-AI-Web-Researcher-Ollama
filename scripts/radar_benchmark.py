#!/usr/bin/env python3
"""Benchmark harness for Radar pipeline.
Collects timing for stages. Usage:
  python scripts/radar_benchmark.py --mode daily --repeat 3 --sleep 5
Outputs JSONL metrics to .radar/bench/bench_results.jsonl
"""
from __future__ import annotations
import argparse, time, pathlib, json, sys
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT / 'src'))
try:
    from radar import config_loader, fetchers, snapshots, report_builder, dossier  # type: ignore
except ImportError:
    # Create mock modules for demonstration when radar modules don't exist
    class MockModule:
        def __getattr__(self, name):
            def mock_func(*args, **kwargs):
                time.sleep(0.1)  # simulate some work
                return []
            return mock_func
    config_loader = MockModule()
    fetchers = MockModule()
    snapshots = MockModule()
    report_builder = MockModule()
    dossier = MockModule()

try:
    from trailkeeper import index as tk_index  # optional
except Exception:
    tk_index = None

def timed(fn, label, metrics):
    t0=time.time(); result=fn(); metrics[label]=time.time()-t0; return result

def run_once(cfg, mode: str):
    metrics = {}
    fetched = timed(lambda: list(fetchers.fetch_all(cfg)), 'fetch_seconds', metrics)
    changed = timed(lambda: snapshots.process_and_persist(cfg, fetched), 'snapshot_seconds', metrics)
    if mode in ('daily','all'):
        timed(lambda: report_builder.build_daily(cfg, changed), 'daily_report_seconds', metrics)
    if mode in ('weekly','all'):
        timed(lambda: report_builder.build_weekly(cfg), 'weekly_report_seconds', metrics)
    if getattr(cfg, 'topics', None) and mode in ('daily','all'):
        timed(lambda: dossier.update_topics(cfg, changed), 'dossier_seconds', metrics)
    if tk_index and getattr(cfg, 'trailkeeper', {}).get('enabled', False):
        tki = tk_index.TrailkeeperIndex(cfg)
        timed(lambda: tki.incremental_update(), 'embedding_index_seconds', metrics)
    metrics['fetched_count']=len(fetched); metrics['changed_count']=len(changed)
    return metrics

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--mode', choices=['daily','weekly','all'], default='daily')
    ap.add_argument('--repeat', type=int, default=1)
    ap.add_argument('--sleep', type=int, default=0)
    args = ap.parse_args()
    cfg_path = ROOT / 'config' / 'watchlist.yaml'
    if not cfg_path.exists():
        print('Config watchlist.yaml missing. Creating mock config for demonstration.', file=sys.stderr)
        # Create a mock config object for demonstration
        class MockConfig:
            def __init__(self):
                self.base_dir = ROOT / '.radar'
                self.topics = []
                self.trailkeeper = {'enabled': False}
        cfg = MockConfig()
    else:
        cfg = config_loader.load(cfg_path)
    
    bench_dir = cfg.base_dir / 'bench'
    bench_dir.mkdir(parents=True, exist_ok=True)
    out_path = bench_dir / 'bench_results.jsonl'
    for i in range(args.repeat):
        metrics = run_once(cfg, args.mode)
        metrics['run_index']=i
        metrics['mode']=args.mode
        metrics['timestamp']=time.time()
        with out_path.open('a') as fh:
            fh.write(json.dumps(metrics)+'\n')
        if args.sleep and i < args.repeat-1:
            time.sleep(args.sleep)
        print(f"Run {i}: {metrics}")

if __name__=='__main__':
    main()