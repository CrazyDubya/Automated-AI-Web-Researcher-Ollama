"""Diff utilities."""
import difflib

def unified_diff(before: str, after: str, from_label="before", to_label="after") -> str:
    before_lines = before.splitlines(keepends=True)
    after_lines = after.splitlines(keepends=True)
    return ''.join(difflib.unified_diff(before_lines, after_lines, fromfile=from_label, tofile=to_label))