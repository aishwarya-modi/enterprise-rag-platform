from app.modules.documents.ocr import FallbackOCRAdapter, TesseractOCRAdapter


def test_fallback_ocr_returns_empty_result() -> None:
    adapter = FallbackOCRAdapter()
    text, confidence, pages = adapter.extract_text("/tmp/no-file")
    assert text == ""
    assert confidence == 0.0
    assert pages == 1


def test_tesseract_adapter_raises_when_binary_missing() -> None:
    adapter = TesseractOCRAdapter()
    try:
        adapter.extract_text("/tmp/example.png")
    except RuntimeError as exc:
        assert "Tesseract" in str(exc)
