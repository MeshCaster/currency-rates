from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from core.exceptions.app_error import AppError
from core.exceptions.handlers.app_error_handler import app_error_handler
from core.exceptions.handlers.bad_request_error_handler import validation_exception_handler
from core.exceptions.handlers.http_error_handler import http_exception_handler


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
