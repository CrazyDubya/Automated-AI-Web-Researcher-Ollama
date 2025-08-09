import sys
import pathlib

# Add src to path for testing
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

import src.radar.diffing as diffing

def test_unified_diff_basic():
    before = "Hello\nWorld"
    after = "Hello\nRadar"
    d = diffing.unified_diff(before, after)
    assert '-World' in d and '+Radar' in d

if __name__ == "__main__":
    test_unified_diff_basic()
    print("test_diffing.py passed")