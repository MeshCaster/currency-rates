import asyncio
import logging

from application import AuthService
from core.clock import utc_today
from core.configuration.settings import Settings, get_settings
from core.database.session import Database
from core.logging import configure_logging
from infrastructure.db.repositories.user_repository import SqlUserRepository
from infrastructure.db.seed import seed_catalog, seed_dev_sync

logger = logging.getLogger(__name__)


async def seed(settings: Settings, db: Database) -> None:
    async with db.transaction() as session:
        catalog = await seed_catalog(session)
        sync = (await seed_dev_sync(session, utc_today())
                if settings.is_development else 0)
        admin = settings.admin
        if admin.email and admin.password:
            outcome = await AuthService(SqlUserRepository(session)).ensure_admin(
                admin.email, admin.password.get_secret_value())
            logger.info("Seed: admin %s %s", admin.email, outcome)
    logger.info("Seed: %d currencies, %d providers, %d intervals, %d provider currencies "
                "inserted or changed; %d dev sync configurations added",
                catalog.currencies, catalog.providers, catalog.intervals,
                catalog.provider_currencies, sync)


async def _main(settings: Settings) -> None:
    db = Database.from_settings(settings)
    try:
        await seed(settings, db)
    finally:
        await db.dispose()


def main() -> None:
    settings = get_settings()
    configure_logging(settings)
    asyncio.run(_main(settings))


if __name__ == "__main__":
    main()
