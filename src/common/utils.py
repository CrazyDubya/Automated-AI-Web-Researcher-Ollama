"""Utility helpers."""

def first_n_chars(s: str, n: int) -> str:
    if len(s) <= n:
        return s
    return s[:n] + '…'