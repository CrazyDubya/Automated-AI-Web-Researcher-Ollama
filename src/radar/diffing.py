"""Diffing utilities for content change detection."""
import difflib

def unified_diff(before: str, after: str, from_label: str = 'before', to_label: str = 'after') -> str:
    """Generate unified diff between two strings."""
    before_lines = before.splitlines(keepends=True)
    after_lines = after.splitlines(keepends=True)
    diff = difflib.unified_diff(
        before_lines, 
        after_lines, 
        fromfile=from_label, 
        tofile=to_label,
        lineterm=''
    )
    return ''.join(diff)