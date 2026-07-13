from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.dependencies import get_db_session_factory


class User:
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False)
    role: Mapped[str] = mapped_column(String(50), nullable=False, default="user")
