"""Utility helpers (extended)."""
import itertools

def first_n_chars(s: str, n: int) -> str:
    if len(s) <= n:
        return s
    return s[:n] + '…'

def first_diff_lines(diff_text: str, n: int) -> str:
    if not diff_text:
        return ''
    lines = [ln for ln in diff_text.splitlines() if ln.startswith('+') or ln.startswith('-')][0:n]
    return ' '.join(lines)