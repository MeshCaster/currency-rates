import logging
from collections import defaultdict
from datetime import date, timedelta
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from application import EmailSender, FeedQueryService, FeedQuote, compose_digest, plan_digests
from core.clock import utc_now
from core.configuration.smtp_config import NotificationSettings
from core.database.session import Database
from core.jobs.exclusive import ExclusiveJob
from infrastructure.db.repositories.provider_repository import SqlProviderRepository
from infrastructure.db.repositories.rate_repository import SqlRateRepository
from infrastructure.db.repositories.sync_configuration_repository import (
    SqlSyncConfigurationRepository,
)
from infrastructure.db.repositories.user_repository import SqlSubscriptionRepository

logger = logging.getLogger(__name__)



class SubscriptionEmailJob(ExclusiveJob):

    def __init__(self, db: Database, mailer: EmailSender,
                 settings: NotificationSettings) -> None:
        super().__init__(db, settings.interval_seconds, settings.timeout_seconds)
        self._mailer = mailer
        self._catch_up = timedelta(hours=settings.catch_up_hours)

    async def run_exclusive(self, session: AsyncSession) -> None:
        now = utc_now()
        deliverable = await SqlSubscriptionRepository(session).list_deliverable()
        digests = plan_digests(deliverable, now, self._catch_up)
        if not digests:
            return
        catalog = SqlProviderRepository(session)
        feeds = FeedQueryService(SqlSyncConfigurationRepository(session),
                                 SqlRateRepository(session), catalog)
        quotes: dict[UUID, FeedQuote] = {}
        for pair_id in set().union(*(d.feed_ids for d in digests)):
            pair = await catalog.get_pair_by_id(pair_id)
            day = await feeds.last_completed_day(pair) if pair is not None else None
            if day is not None:
                quotes[pair_id] = FeedQuote(*day)

        sent = failed = 0
        for digest in digests:
            email = compose_digest(digest, quotes)
            if email is None:
                continue
            try:
                await self._mailer.send(email.to, email.subject, email.text, email.html)
            except Exception as e:
                failed += 1
                logger.warning("%s: email to %s failed: %s", self.name, email.to, e)
                continue
            sent += 1
            by_day: dict[date, list[UUID]] = defaultdict(list)
            for item in email.delivered:
                by_day[item.local_day].append(item.subscription.id)
            async with self._db.transaction() as mark_session:
                for day, ids in by_day.items():
                    await SqlSubscriptionRepository(mark_session).mark_sent(ids, day)
        logger.info("%s: %d emails sent, %d failed, %d skipped (no rates yet)", self.name, sent,
                    failed, len(digests) - sent - failed)
