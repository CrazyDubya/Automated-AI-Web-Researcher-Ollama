import sys
import pathlib

# Add src to path for testing
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

import src.radar.html_norm as html_norm

def test_html_to_text():
    html = "<html><body><h1>Title</h1><p>Content here</p><script>ignored</script></body></html>"
    text = html_norm.html_to_text(html)
    assert "Title" in text
    assert "Content here" in text
    assert "ignored" not in text

if __name__ == "__main__":
    test_html_to_text()
    print("test_html_norm.py passed")