from fastapi.exceptions import RequestValidationError
from starlette.requests import Request
from starlette.responses import JSONResponse

from core.exceptions.helpers import _is_development, _request_id
from core.exceptions.responses.problem_response import problem_response


async def validation_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, RequestValidationError)  # noqa: S101
    expose_input = _is_development(request)
    errors = [
        {
            "loc": list(err.get("loc", ())),
            "msg": err.get("msg"),
            "type": err.get("type"),
            **({"input": err.get("input")} if expose_input else {}),
        }
        for err in exc.errors()
    ]
    return problem_response(
        status=422,
        title="Validation Failed",
        detail="The request is invalid. See 'errors' for details.",
        code="validation_error",
        instance=request.url.path,
        request_id=_request_id(request),
        errors=errors,
    )