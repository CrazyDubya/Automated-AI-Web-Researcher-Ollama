# Trailkeeper Quickstart (Minimal Hardware)

Trailkeeper adds a vector (embedding) index over Radar snapshots & local notes for semantic search and RAG answering.

## Minimal Config Snippet
```yaml
trailkeeper:
  enabled: true
  index_dir: .radar/vector_index
  embed_batch_size: 8
  top_k: 6
  reindex_on_start: false
```

Add (or adjust) embedding model under `llm.embed_model`. If an embedding endpoint is unavailable, Radar will fall back to a hash-based pseudo-embedding with a warning (good enough for structural testing, not for quality search).

## Commands
- Build / update index as part of normal run (if enabled): `python cli/radar.py run --mode daily`
- Force rebuild (future PR / currently via deleting index dir): `rm -rf .radar/vector_index`
- Search (after PR #3): `radar search --query "broadband funding" --answer`

## Performance Tips
- Reduce `embed_batch_size` if memory constrained.
- Disable semantic diff when CPU bound: set `diff.semantic: false`.
- Cap `outputs.max_items_per_run` to keep prompt sizes manageable.

## Storage Layout
- Vector index directory holds binary index + metadata JSONL.
- A checkpoint file stores last processed snapshot hash to ensure incremental updates.

## Limitations
- No persistent embedding cache yet (scaffold added; future optimization).
- OCR-derived text is included if available; consider tagging OCR sources for filtering.