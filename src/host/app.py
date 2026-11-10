from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from application.ports import RateProvider
from host.api.routes import router
from host.jobs.rate_sync import RateSyncJob
from host.jobs.runner import JobRunner
from infrastructure.db.session import SessionFactory
from rates_provider_integration.fx.nbg import NBGProvider
from rates_provider_integration.http_clients import default_client

PAIRS: list[tuple[str, str]] = [("USD", "GEL"), ("EUR", "GEL")]
INTERVAL_SECONDS = 10.0


def create_app(*, session_factory: async_sessionmaker[AsyncSession] = SessionFactory,
               provider: RateProvider | None = None, pairs: list[tuple[str, str]] = PAIRS,
               interval_seconds: float = INTERVAL_SECONDS, start_jobs: bool = True) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        http = None
        prov = provider
        if prov is None:
            http = default_client()
            prov = NBGProvider(http)
        app.state.session_factory = session_factory
        app.state.provider = prov

        runner = JobRunner([
            RateSyncJob(prov, session_factory, pairs, interval_seconds),
        ])
        if start_jobs:
            await runner.start()
        try:
            yield
        finally:
            await runner.stop()
            if http is not None:
                await http.aclose()

    app = FastAPI(
        title="CurrencyRates",
        lifespan=lifespan,
        docs_url="/swagger",
        redoc_url=None,
        openapi_url="/api/openapi.json",
        swagger_ui_parameters={"persistAuthorization": True, "docExpansion": "none"})
    app.include_router(router)
    return app


app = create_app()
