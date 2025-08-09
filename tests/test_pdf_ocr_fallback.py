import pytest, shutil

TESS = shutil.which('tesseract')

def test_ocr_fallback_presence():
    if not TESS:
        pytest.skip('tesseract not installed; skipping OCR fallback test placeholder')
    # Placeholder: real test would feed a low-text PDF and assert OCR path taken.
    assert True