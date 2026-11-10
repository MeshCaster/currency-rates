from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from core.exceptions.helpers import _request_id, _reason
from core.exceptions.responses.problem_response import problem_response


async def http_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, StarletteHTTPException)  # noqa: S101
    return problem_response(
        status=exc.status_code,
        title=_reason(exc.status_code),
        detail=str(exc.detail),
        code=f"http_{exc.status_code}",
        instance=request.url.path,
        request_id=_request_id(request),
        headers=getattr(exc, "headers", None),
    )