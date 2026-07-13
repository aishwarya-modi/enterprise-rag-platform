from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column


class Document:
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")
    content_type: Mapped[str] = mapped_column(String(50), nullable=False)
