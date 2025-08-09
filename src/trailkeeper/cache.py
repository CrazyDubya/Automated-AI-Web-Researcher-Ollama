"""Embedding cache scaffold (future optimization).
Current behavior: pass-through. TODO: implement sqlite or JSONL persistent cache keyed by (model, sha256(text))."""
from __future__ import annotations
import hashlib

class EmbeddingCache:
    def __init__(self, enabled: bool = False, path=None):
        self.enabled = enabled
        self.path = path
        self._mem = {}

    def key(self, model: str, text: str) -> str:
        return hashlib.sha256((model+'\n'+text).encode()).hexdigest()

    def get(self, model: str, text: str):
        if not self.enabled: return None
        return self._mem.get(self.key(model, text))

    def put(self, model: str, text: str, vec):
        if not self.enabled: return
        self._mem[self.key(model, text)] = vec