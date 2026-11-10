from starlette.requests import Request


def _request_id(request: Request) -> str | None:
    return getattr(request.state, "request_id", None)


def _is_development(request: Request) -> bool:
    settings = getattr(request.app.state, "settings", None)
    return bool(settings and settings.is_development)

def _reason(status: int) -> str:
    from http import HTTPStatus

    try:
        return HTTPStatus(status).phrase
    except ValueError:
        return "Error"