"""HTML normalization to text for diffing / summarization."""
from __future__ import annotations
from bs4 import BeautifulSoup
import re

def html_to_text(html: str) -> str:
    soup = BeautifulSoup(html, 'html.parser')
    # Remove scripts/styles/nav/footer common noise
    for tag in soup(['script','style','noscript']):
        tag.decompose()
    text = soup.get_text('\n')
    # Collapse excess whitespace
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r'[ \t]{2,}', ' ', text)
    return text.strip()