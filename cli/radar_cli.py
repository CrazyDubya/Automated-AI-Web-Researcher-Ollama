#!/usr/bin/env python3
"""Local Radar CLI updated: fetchers + filters + tag grouping."""
import argparse, pathlib, shutil, sys, datetime as dt

ROOT = pathlib.Path(__file__).resolve().parents[1]
CONFIG_DIR = ROOT / "config"
EXAMPLE = CONFIG_DIR / "watchlist.example.yaml"
ACTIVE = CONFIG_DIR / "watchlist.yaml"
SRC_DIR = ROOT / "src"

sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(SRC_DIR))

# Import with absolute imports to avoid circular import issues
import src.radar.config_loader as config_loader
import src.radar.fetchers as fetchers
import src.radar.snapshots as snapshots
import src.radar.report_builder as report_builder
import src.radar.dossier as dossier

def cmd_init(_args):
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    if ACTIVE.exists():
        print(f"Config already exists at {ACTIVE}")
        return
    shutil.copy(EXAMPLE, ACTIVE)
    print(f"Wrote {ACTIVE}. Edit it to add real sources.")


def cmd_run(args):
    mode = args.mode
    if not ACTIVE.exists():
        print("Config missing. Run 'radar init' first.")
        sys.exit(1)
    cfg = config_loader.load(ACTIVE)
    ts = dt.datetime.now().isoformat(timespec='seconds')
    print(f"[{ts}] Running mode={mode}")

    run_daily_like = mode in ("daily", "all")
    run_weekly_like = mode in ("weekly", "all")

    changed_items = []
    if run_daily_like or run_weekly_like:
        fetched = list(fetchers.fetch_all(cfg))
        print(f"Fetched items: {len(fetched)}")
        changed_items = snapshots.process_and_persist(cfg, fetched)
        print(f"Changed items this run: {len(changed_items)}")

    if run_daily_like:
        report_builder.build_daily(cfg, changed_items)
    if run_weekly_like:
        report_builder.build_weekly(cfg)

    if run_daily_like and cfg.topics:
        dossier.update_topics(cfg, changed_items)

    print("Done.")


def cmd_report(args):
    kind = args.kind
    if not ACTIVE.exists():
        print("Config missing. Run 'radar init' first.")
        sys.exit(1)
    cfg = config_loader.load(ACTIVE)
    if kind == "daily":
        report_builder.build_daily(cfg, [], regenerate=True)
    elif kind == "weekly":
        report_builder.build_weekly(cfg, regenerate=True)
    else:
        dossier.regenerate_all(cfg)
    print(f"Regenerated {kind} report(s) from cache.")


def main():
    ap = argparse.ArgumentParser(prog="radar", description="Local Radar + Dossier CLI")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_init = sub.add_parser("init", help="Create config/watchlist.yaml from example")
    p_init.set_defaults(func=cmd_init)

    p_run = sub.add_parser("run", help="Run pipeline (daily|weekly|all)")
    p_run.add_argument("--mode", choices=["daily", "weekly", "all"], default="daily")
    p_run.set_defaults(func=cmd_run)

    p_rep = sub.add_parser("report", help="Render report from cache")
    p_rep.add_argument("--kind", choices=["daily", "weekly", "dossier"], default="daily")
    p_rep.set_defaults(func=cmd_report)

    args = ap.parse_args()
    args.func(args)

if __name__ == "__main__":
    main()