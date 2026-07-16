from __future__ import annotations

import logging
import time
import uuid
from typing import Optional

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.core.logging import TENANT_ID_CTX, REQUEST_ID_CTX

logger = logging.getLogger(__name__)


class CorrelationIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        token = REQUEST_ID_CTX.set(request_id)

        tenant_id: Optional[str] = None
        auth_header = request.headers.get("authorization", "")
        if auth_header.startswith("Bearer "):
            try:
                from app.core.config import get_settings
                import jwt

                settings = get_settings()
                payload = jwt.decode(
                    auth_header[7:],
                    settings.jwt_secret_key,
                    algorithms=[settings.jwt_algorithm],
                )
                tenant_id = payload.get("tenant_id")
            except Exception:
                pass

        tenant_token = TENANT_ID_CTX.set(tenant_id) if tenant_id else None

        start = time.perf_counter()
        response = await call_next(request)
        elapsed_ms = (time.perf_counter() - start) * 1000

        response.headers["X-Request-ID"] = request_id

        logger.info(
            "%s %s -> %d (%.1fms)",
            request.method,
            request.url.path,
            response.status_code,
            elapsed_ms,
        )

        REQUEST_ID_CTX.reset(token)
        if tenant_token is not None:
            TENANT_ID_CTX.reset(tenant_token)

        return response
