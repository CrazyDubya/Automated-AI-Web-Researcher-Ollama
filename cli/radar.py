#!/usr/bin/env python3
"""Local Radar CLI: civic/OSINT change watcher with dossiers and background RAG prep.

Commands:
  radar init                -> create config/watchlist.yaml from example
  radar run --mode daily    -> perform daily ingestion + diff + daily brief + update dossiers
  radar run --mode weekly   -> perform weekly roll-up + weekly brief
  radar run --mode all      -> run full pipeline (daily + weekly logic)
  radar report --kind daily|weekly|dossier -> regenerate reports from cached snapshots only

Note: Implementation is incremental. Some modules contain TODOs for subsequent PRs.
"""
import argparse, pathlib, shutil, sys, datetime as dt

ROOT = pathlib.Path(__file__).resolve().parents[1]
CONFIG_DIR = ROOT / "config"
EXAMPLE = CONFIG_DIR / "watchlist.example.yaml"
ACTIVE = CONFIG_DIR / "watchlist.yaml"
SRC_DIR = ROOT / "src"

# Insert src path at the beginning to avoid name conflicts with the radar.py CLI script
sys.path.insert(0, str(SRC_DIR))  # allow src imports with priority

# Import modules directly to avoid circular import issues
try:
    import radar.config_loader as config_loader
    import radar.fetchers as fetchers
    import radar.snapshots as snapshots
    import radar.diffing as diffing
    import radar.report_builder as report_builder
    import radar.dossier as dossier
    imports_available = True
except ImportError as e:  # During initial skeleton commit the modules exist; keep graceful.
    print(f"[WARN] Import error (expected early skeleton phase): {e}")
    imports_available = False
    
def check_imports():
    if not imports_available:
        print("ERROR: Required modules not available. Check installation.")
        sys.exit(1)


def cmd_init(_args):
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    if ACTIVE.exists():
        print(f"Config already exists at {ACTIVE}")
        return
    shutil.copy(EXAMPLE, ACTIVE)
    print(f"Wrote {ACTIVE}. Edit it to add real sources.")


def cmd_run(args):
    check_imports()
    mode = args.mode
    if not ACTIVE.exists():
        print("Config missing. Run 'radar init' first.")
        sys.exit(1)
    cfg = config_loader.load(ACTIVE)
    ts = dt.datetime.now().isoformat(timespec='seconds')
    print(f"[{ts}] Running mode={mode}")

    # 1. Fetch + snapshot (always for daily/all, weekly may reuse cache unless forced)
    run_daily_like = mode in ("daily", "all")
    run_weekly_like = mode in ("weekly", "all")

    changed_items = []
    if run_daily_like or run_weekly_like:
        fetched = fetchers.fetch_all(cfg)
        changed_items = snapshots.process_and_persist(cfg, fetched)
    # 2. Diff computation already part of snapshot pipeline -> items include diff metadata.

    # 3. Build reports
    if run_daily_like:
        report_builder.build_daily(cfg, changed_items)
    if run_weekly_like:
        report_builder.build_weekly(cfg)

    # 4. Update dossiers (topics) whenever new evidence available
    if run_daily_like and cfg.topics:
        dossier.update_topics(cfg, changed_items)

    print("Done.")


def cmd_report(args):
    check_imports()
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