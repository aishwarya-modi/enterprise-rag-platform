from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Protocol


class OCRAdapter(Protocol):
    def extract_text(self, file_path: str) -> tuple[str, float, int]: ...


class TesseractOCRAdapter:
    def extract_text(self, file_path: str) -> tuple[str, float, int]:
        path = Path(file_path)
        if not path.exists():
            raise RuntimeError("Tesseract unavailable")

        try:
            completed = subprocess.run(
                ["tesseract", str(path), "stdout", "--psm", "6"],
                capture_output=True,
                check=True,
                text=True,
            )
        except (subprocess.CalledProcessError, FileNotFoundError) as exc:
            raise RuntimeError("Tesseract unavailable") from exc

        text = completed.stdout.strip()
        pages = 1
        confidence = 0.85 if text else 0.0
        return text, confidence, pages


class FallbackOCRAdapter:
    def extract_text(self, file_path: str) -> tuple[str, float, int]:
        return "", 0.0, 1
