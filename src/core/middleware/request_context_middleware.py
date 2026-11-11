from __future__ import annotations

import logging
import re
import time
import uuid
from starlette.datastructures import Headers, MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from core.constants import HEALTH_PATHS
from core.exceptions.responses import internal_error_response
from core.logging import request_id_ctx
from core.constants import REQUEST_ID_HEADER

logger = logging.getLogger("app.access")
error_logger = logging.getLogger("app.errors")

_VALID_REQUEST_ID = re.compile(r"^[A-Za-z0-9._\-]{1,128}$")

class RequestContextMiddleware:
    def __init__(self, app: ASGIApp, *, access_log: bool = True, expose_errors: bool = False):
        self.app = app
        self.access_log = access_log
        self.expose_errors = expose_errors

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        incoming = Headers(scope=scope).get(REQUEST_ID_HEADER)
        request_id = (
            incoming if incoming and _VALID_REQUEST_ID.match(incoming) else uuid.uuid4().hex
        )
        scope.setdefault("state", {})["request_id"] = request_id
        token = request_id_ctx.set(request_id)

        status_code = 500
        response_started = False
        start = time.perf_counter()

        async def send_wrapper(message: Message) -> None:
            nonlocal status_code, response_started
            if message["type"] == "http.response.start":
                response_started = True
                status_code = message["status"]
                MutableHeaders(scope=message)[REQUEST_ID_HEADER] = request_id
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        except Exception as exc:
            error_logger.exception("Unhandled exception")
            if response_started:
                raise
            response = internal_error_response(
                exc,
                path=scope["path"],
                request_id=request_id,
                expose_details=self.expose_errors,
            )
            await response(scope, receive, send_wrapper)
        finally:
            if self.access_log and scope["path"] not in HEALTH_PATHS:
                duration_ms = round((time.perf_counter() - start) * 1000, 2)
                client = scope.get("client")
                logger.info(
                    "%s %s %s %sms",
                    scope["method"],
                    scope["path"],
                    status_code,
                    duration_ms,
                    extra={
                        "http_method": scope["method"],
                        "http_path": scope["path"],
                        "http_status": status_code,
                        "duration_ms": duration_ms,
                        "client_ip": client[0] if client else None,
                    },
                )
            request_id_ctx.reset(token)