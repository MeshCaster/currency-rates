from typing import Any

from fastapi.encoders import jsonable_encoder
from starlette.responses import JSONResponse

from core.constants import PROBLEM_JSON_MEDIA_TYPE


def problem_response(
    *,
    status: int,
    title: str,
    detail: str,
    code: str,
    instance: str | None = None,
    request_id: str | None = None,
    headers: dict[str, str] | None = None,
    **extensions: Any,
) -> JSONResponse:
    body: dict[str, Any] = {
        "type": "about:blank",
        "title": title,
        "status": status,
        "detail": detail,
        "code": code,
    }
    if instance:
        body["instance"] = instance
    if request_id:
        body["request_id"] = request_id
    body.update({k: v for k, v in extensions.items() if v is not None})
    return JSONResponse(
        jsonable_encoder(body),
        status_code=status,
        headers=headers,
        media_type=PROBLEM_JSON_MEDIA_TYPE,
    )