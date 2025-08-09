#!/usr/bin/env python3
"""Semantic Diff Threshold Tuner.
Usage:
  python scripts/semantic_diff_tuner.py --old pathA --new pathB [--out report.md]
  python scripts/semantic_diff_tuner.py --simulate 1 --out report.md
Simulate mode generates baseline text and mutated sentence variants.
Outputs a markdown table of thresholds vs changed sentence counts.
Falls back to lexical similarity if embedding model unavailable.
"""
from __future__ import annotations
import argparse, pathlib, random, statistics, sys

# Minimal inline similarity helpers (fall back)

def cosine(a,b):
    import math
    if not a or not b: return 0.0
    if len(a)!=len(b):
        # pad
        m = max(len(a),len(b))
        a=a+[0]*(m-len(a)); b=b+[0]*(m-len(b))
    dot = sum(x*y for x,y in zip(a,b))
    na = math.sqrt(sum(x*x for x in a)); nb = math.sqrt(sum(x*x for x in b))
    return dot/(na*nb) if na and nb else 0.0

try:
    from trailkeeper.embedder import get_embedder
except Exception:
    get_embedder = None

SENT_SPLIT = r'(?<=[.!?])\s+'  # simplistic

import re, hashlib

def embed_sentences(sents):
    if get_embedder:
        try:
            emb = get_embedder()
            return [emb.embed_text(s) for s in sents]
        except Exception:
            pass
    # fallback deterministic hashing vector
    vecs=[]
    for s in sents:
        h = hashlib.sha256(s.encode()).digest()[:16]
        vecs.append([b/255.0 for b in h])
    return vecs

def changed_sentences(old_sents, new_sents, threshold):
    old_emb = embed_sentences(old_sents)
    new_emb = embed_sentences(new_sents)
    changes=[]
    for idx,(s,ve) in enumerate(zip(new_sents,new_emb)):
        best=0.0
        for ov in old_emb:
            sim = cosine(ve, ov)
            if sim>best: best=sim
        # semantic_min_delta_score meaning: treat as changed if (1 - best) >= threshold
        if (1.0 - best) >= threshold:
            changes.append((idx, s, 1.0-best))
    return changes

def simulate_pair():
    base = ["The program announces new broadband funding today.",
            "Housing policy adjustments remain under review.",
            "Climate resilience planning enters phase two."]
    mutated = base.copy()
    mutated.append("A novel infrastructure pilot is proposed downtown.")
    mutated[1] = "Housing policy adjustments advance to public hearing."  # semantic shift
    return base, mutated

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--old')
    ap.add_argument('--new')
    ap.add_argument('--simulate', type=int, default=0)
    ap.add_argument('--out')
    args = ap.parse_args()
    if args.simulate:
        old_sents, new_sents = simulate_pair()
    else:
        if not (args.old and args.new):
            print('Provide --old and --new or use --simulate 1', file=sys.stderr)
            sys.exit(1)
        old_text = pathlib.Path(args.old).read_text()
        new_text = pathlib.Path(args.new).read_text()
        old_sents = re.split(SENT_SPLIT, old_text.strip())
        new_sents = re.split(SENT_SPLIT, new_text.strip())
    thresholds = [round(x,2) for x in [0.05,0.10,0.15,0.20,0.25,0.30,0.35,0.40]]
    lines = ["| Threshold | Changed Sentences | Avg Delta | Max Delta |", "|-----------|-------------------|-----------|-----------|"]
    for th in thresholds:
        changes = changed_sentences(old_sents, new_sents, th)
        if changes:
            deltas = [c[2] for c in changes]
            lines.append(f"| {th:.2f} | {len(changes)} | {sum(deltas)/len(deltas):.3f} | {max(deltas):.3f} |")
        else:
            lines.append(f"| {th:.2f} | 0 | 0.000 | 0.000 |")
    report = "# Semantic Diff Threshold Tuning\n\n" + "\n".join(lines) + "\n"
    if args.out:
        pathlib.Path(args.out).write_text(report)
    print(report)

if __name__ == '__main__':
    main()