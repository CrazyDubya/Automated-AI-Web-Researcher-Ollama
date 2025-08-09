# Radar Performance & Tuning Guide

This document explains how to measure and optimize performance.

## Benchmark Harness
Use:
```
python scripts/radar_benchmark.py --mode daily --repeat 3 --sleep 10
```
Generates `.radar/bench/bench_results.jsonl` with timing metrics:
- fetch_seconds
- snapshot_seconds
- daily_report_seconds / weekly_report_seconds
- dossier_seconds
- embedding_index_seconds (when Trailkeeper enabled)

Aggregate with:
```bash
jq -s 'map(.fetch_seconds) | {fetch_avg:(add/length)}' .radar/bench/bench_results.jsonl
```

## Semantic Diff Tuning
Run:
```
python scripts/semantic_diff_tuner.py --simulate 1 --out diff_thresholds.md
```
Inspect changed sentence counts per threshold. Increase `diff.semantic_min_delta_score` to reduce noise; decrease to capture subtle edits.

## Feature Cost Overview
| Feature | CPU | Memory | Notes |
|---------|-----|--------|-------|
| Fetch (RSS/HTML) | Low | Low | Network-bound |
| Semantic Diff (embeddings) | Medium | Medium | Disable via `diff.semantic: false` |
| Trailkeeper Index (FAISS) | Medium-High | Scales with corpus | Disable via `trailkeeper.enabled: false` |
| OCR Fallback | High | Low | Only triggers for low-text PDFs |

## Suggested Modes
Low-power VPS:
```yaml
diff:
  semantic: false
trailkeeper:
  enabled: false
outputs:
  max_items_per_run: 25
```
Power workstation:
```yaml
diff:
  semantic: true
  semantic_min_delta_score: 0.15
trailkeeper:
  enabled: true
  embed_batch_size: 32
```

## CRON Examples
Daily (6am): `0 6 * * * /usr/bin/python /path/cli/radar.py run --mode daily >> radar.log 2>&1`
Weekly (Mon 7am): `0 7 * * 1 /usr/bin/python /path/cli/radar.py run --mode weekly >> radar.log 2>&1`

## Future Optimizations (Planned)
- Persistent embedding cache (files -> vector) to avoid recomputation.
- Boilerplate DOM block removal for cleaner diffs.
- Parallel fetch with adaptive concurrency respecting per-domain rate limits.