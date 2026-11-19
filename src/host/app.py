import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from core.configuration.settings import Settings, get_settings
from core.exceptions.handlers.register import register_exception_handlers
from core.lifespan import lifespan as core_lifespan
from core.logging import configure_logging
from core.middleware.setup import setup_middleware
from host.api.alerts import alerts_router, rules_router
from host.api.auth import router as auth_router
from host.api.currencies import router as currencies_router
from host.api.health import router as health_router
from host.api.subscriptions import router as subscriptions_router
from host.api.sync_configurations import router as sync_configurations_router

logger = logging.getLogger(__name__)


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings)

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        debug=settings.debug,
        root_path=settings.root_path,
        lifespan=core_lifespan,
        docs_url="/swagger" if settings.show_docs else None,
        redoc_url=None,
        openapi_url=f"{settings.api_prefix}/openapi.json" if settings.show_docs else None,
        swagger_ui_parameters={"persistAuthorization": True, "docExpansion": "none"})
    app.state.settings = settings

    setup_middleware(app, settings)
    register_exception_handlers(app)
    app.include_router(health_router)
    app.include_router(sync_configurations_router, prefix=settings.api_prefix)
    app.include_router(rules_router, prefix=settings.api_prefix)
    app.include_router(alerts_router, prefix=settings.api_prefix)
    app.include_router(auth_router, prefix=settings.api_prefix)
    app.include_router(subscriptions_router, prefix=settings.api_prefix)
    app.include_router(currencies_router, prefix=settings.api_prefix)
    storage = settings.storage
    if storage.is_served_locally and Path(storage.path).is_dir():
        app.mount(storage.public_url, StaticFiles(directory=storage.path), name="storage")
    return app
