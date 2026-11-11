from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.gzip import GZipMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from core.configuration.settings import Settings
from core.constants import REQUEST_ID_HEADER
from core.middleware.request_context_middleware import RequestContextMiddleware
from core.middleware.security_headers_middleware import SecurityHeadersMiddleware


def setup_middleware(app: FastAPI, settings: Settings) -> None:
    app.add_middleware(GZipMiddleware, minimum_size=1024)

    if settings.cors.allow_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors.allow_origins,
            allow_credentials=settings.cors.allow_credentials,
            allow_methods=settings.cors.allow_methods,
            allow_headers=settings.cors.allow_headers,
            expose_headers=[REQUEST_ID_HEADER],
            max_age=settings.cors.max_age,
        )

    if settings.security.allowed_hosts != ["*"]:
        app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.security.allowed_hosts)

    app.add_middleware(SecurityHeadersMiddleware, hsts=settings.is_deployed)
    app.add_middleware(
        RequestContextMiddleware,
        access_log=settings.log.access_log,
        expose_errors=settings.is_development,
    )