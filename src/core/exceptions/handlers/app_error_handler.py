from fastapi import Request
from fastapi.responses import JSONResponse

import logging

from core.exceptions.app_error import AppError
from core.exceptions.helpers import _request_id
from core.exceptions.responses.problem_response import problem_response


logger = logging.getLogger(__name__)

async def app_error_handler(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, AppError)  # noqa: S101
    log = logger.error if exc.status_code >= 500 else logger.info
    log(
        "%s: %s",
        exc.error_code,
        exc.detail,
        exc_info=exc if exc.status_code >= 500 else None,
        extra={"status_code": exc.status_code, "error_code": exc.error_code},
    )
    return problem_response(
        status=exc.status_code,
        title=exc.title,
        detail=exc.detail,
        code=exc.error_code,
        instance=request.url.path,
        request_id=_request_id(request),
        headers=exc.headers,
        **exc.extra,
    )