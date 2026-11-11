import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI

from application.ports import RateProvider
from core.configuration.settings import Settings, get_settings
from core.exceptions.handlers.register import register_exception_handlers
from core.lifespan import lifespan as core_lifespan
from core.logging import configure_logging
from core.middleware.setup import setup_middleware
from host.api.health import router as health_router
from host.api.routes import router
from host.jobs.rate_sync import RateSyncJob
from host.jobs.runner import JobRunner
from rates_provider_integration.fx.nbg import NBGProvider

logger = logging.getLogger(__name__)


def create_app(settings: Settings | None = None, *, provider: RateProvider | None = None,
               start_jobs: bool = True) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[dict[str, Any]]:
        async with core_lifespan(app) as state:
            prov = provider or NBGProvider(state["http_client"])
            db = state["db"]
            jobs = []
            if start_jobs and settings.rate_sync.enabled:
                if db is None:
                    logger.warning("Rate sync disabled: DATABASE__URL is not configured")
                else:
                    jobs.append(RateSyncJob(prov, db.session_factory,
                                            settings.rate_sync.pair_tuples,
                                            settings.rate_sync.interval_seconds))
            runner = JobRunner(jobs)
            await runner.start()
            try:
                yield {**state, "provider": prov}
            finally:
                await runner.stop()

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        debug=settings.debug,
        root_path=settings.root_path,
        lifespan=lifespan,
        docs_url="/swagger" if settings.show_docs else None,
        redoc_url=None,
        openapi_url=f"{settings.api_prefix}/openapi.json" if settings.show_docs else None,
        swagger_ui_parameters={"persistAuthorization": True, "docExpansion": "none"})
    app.state.settings = settings

    setup_middleware(app, settings)
    register_exception_handlers(app)
    app.include_router(health_router)
    app.include_router(router, prefix=settings.api_prefix)
    return app
