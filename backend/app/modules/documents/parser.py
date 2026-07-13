from __future__ import annotations

import csv
import io
import json
from typing import Any


def parse_document_content(content_type: str, content: bytes, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
    metadata = metadata or {}
    text = content.decode("utf-8", errors="ignore")

    if content_type == "markdown":
        sections = [line.strip() for line in text.splitlines() if line.strip()]
        headings = [line.lstrip("#").strip() for line in sections if line.startswith("#")]
        paragraphs = [line for line in sections if not line.startswith("#") and not line.startswith("-") and not line.startswith("*")]
        lists = [line for line in sections if line.startswith("-") or line.startswith("*")]
        return {
            "headings": headings,
            "paragraphs": paragraphs,
            "lists": lists,
            "tables": [],
            "images": [],
            "page_numbers": [],
            "metadata": {
                "author": metadata.get("author"),
                "title": metadata.get("title"),
                "language": metadata.get("language"),
            },
        }

    if content_type == "csv":
        rows = list(csv.DictReader(io.StringIO(text)))
        return {
            "headings": [],
            "paragraphs": [],
            "lists": [],
            "tables": rows,
            "images": [],
            "page_numbers": [],
            "metadata": {
                "author": metadata.get("author"),
                "title": metadata.get("title"),
                "language": metadata.get("language"),
            },
        }

    if content_type in {"txt", "pdf", "docx", "pptx"}:
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        paragraphs = [line for line in lines if not line.startswith("Author:") and not line.startswith("Title:") and not line.startswith("Language:")]
        metadata_fields = {
            "author": metadata.get("author"),
            "title": metadata.get("title"),
            "language": metadata.get("language"),
        }
        return {
            "headings": [],
            "paragraphs": paragraphs,
            "lists": [],
            "tables": [],
            "images": [],
            "page_numbers": [],
            "metadata": metadata_fields,
        }

    return {
        "headings": [],
        "paragraphs": [],
        "lists": [],
        "tables": [],
        "images": [],
        "page_numbers": [],
        "metadata": {
            "author": metadata.get("author"),
            "title": metadata.get("title"),
            "language": metadata.get("language"),
        },
    }
