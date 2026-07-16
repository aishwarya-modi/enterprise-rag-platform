from __future__ import annotations

from typing import Any


class DomainError(Exception):
    """Base exception for domain-layer errors."""

    def __init__(self, message: str, *, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class NotFoundError(DomainError):
    """Raised when a requested entity cannot be found."""


class ValidationError(DomainError):
    """Raised when an incoming request fails validation."""
