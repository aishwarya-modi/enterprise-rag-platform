import asyncio

import pytest

from app.modules.documents.parser import parse_document_content
from app.modules.documents.repository import DocumentRepository
from app.modules.documents.service import DocumentService, LocalStorageAdapter


@pytest.mark.parametrize(
    ("content_type", "content", "expected_keys"),
    [
        ("markdown", b"# Heading\n\nParagraph text\n\n- item one\n- item two\n", ["headings", "paragraphs", "lists"]),
        ("csv", b"name,role\nAda,Admin\n", ["tables"]),
        ("txt", b"Author: Ada\nTitle: Report\n\nPlain paragraph\n", ["paragraphs", "metadata"]),
    ],
)
def test_parse_document_content_returns_structured_json(content_type: str, content: bytes, expected_keys: list[str]) -> None:
    payload = parse_document_content(content_type, content, metadata={"title": "Report", "author": "Ada", "language": "en"})

    assert isinstance(payload, dict)
    for key in expected_keys:
        assert key in payload


def test_service_can_parse_document_content() -> None:
    repository = DocumentRepository()
    service = DocumentService(repository=repository, storage=LocalStorageAdapter(base_dir="/tmp/enterprise-rag-docs"))

    document_id = asyncio.run(repository.save("tenant-1", "Quarterly Report", "markdown", "checksum-123", "/tmp/report.md", "indexed"))
    asyncio.run(repository.update(document_id, parsed_content='{"headings": ["Summary"]}'))

    parsed = asyncio.run(service.parse_document(document_id))

    assert parsed["document_id"] == document_id
    assert parsed["parsed_content"]["headings"] == ["Summary"]
