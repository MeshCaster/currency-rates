from starlette.responses import JSONResponse

from core.exceptions.responses.problem_response import problem_response

def internal_error_response(
    exc: BaseException, *, path: str, request_id: str | None, expose_details: bool
) -> JSONResponse:
    return problem_response(
        status=500,
        title="Internal Server Error",
        detail=repr(exc) if expose_details else "An unexpected error occurred.",
        code="internal_error",
        instance=path,
        request_id=request_id,
    )