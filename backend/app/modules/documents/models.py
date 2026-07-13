from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column


class Document:
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")
    content_type: Mapped[str] = mapped_column(String(50), nullable=False)
    checksum: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    storage_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    extracted_text: Mapped[str | None] = mapped_column(String(8192), nullable=True)
    confidence_score: Mapped[float | None] = mapped_column(default=None, nullable=True)
    pages: Mapped[int | None] = mapped_column(default=None, nullable=True)
    error: Mapped[str | None] = mapped_column(String(1024), nullable=True)
