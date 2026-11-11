import asyncio
import logging
from collections import defaultdict
from datetime import UTC, date, datetime, timedelta
from uuid import UUID

from application import EmailSender, FeedQuote, compose_digest, plan_digests
from core.configuration.smtp_config import NotificationSettings
from core.database.session import Database
from core.jobs.base import PeriodicJob
from core.jobs.locking import try_advisory_xact_lock
from domain.enums import IntervalKind
from domain.models import SyncConfig
from host.jobs.history_sync import HistoryProviderFactory
from infrastructure.db.repositories.sync_configuration_repository import (
    SqlSyncConfigurationRepository,
)
from infrastructure.db.repositories.user_repository import SqlSubscriptionRepository

logger = logging.getLogger(__name__)

_QUOTE_DAYS = 4


class SubscriptionEmailJob(PeriodicJob):

    def __init__(self, db: Database, providers: HistoryProviderFactory, mailer: EmailSender,
                 settings: NotificationSettings) -> None:
        super().__init__(settings.interval_seconds, settings.timeout_seconds)
        self._db = db
        self._providers = providers
        self._mailer = mailer
        self._catch_up = timedelta(hours=settings.catch_up_hours)

    async def run_once(self) -> None:
        now = datetime.now(UTC)
        async with self._db.transaction() as session:
            if not await try_advisory_xact_lock(session, self.name):
                return
            deliverable = await SqlSubscriptionRepository(session).list_deliverable()
            digests = plan_digests(deliverable, now, self._catch_up)
            if not digests:
                return
            configs = await SqlSyncConfigurationRepository(session).get_many(
                set().union(*(d.feed_ids for d in digests)))
            fetched = await asyncio.gather(*(self._quote(c, now.date()) for c in configs))
            quotes = {c.id: q for c, q in zip(configs, fetched, strict=True) if q is not None}

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

    async def _quote(self, config: SyncConfig, today: date) -> FeedQuote | None:
        try:
            provider = self._providers(config.provider, config.options)
            rates = await provider.get_history(config.base, config.quote,
                                               today - timedelta(days=_QUOTE_DAYS), today,
                                               IntervalKind.DAILY)
        except Exception as e:
            logger.warning("%s: no rate for %s %s/%s: %s", self.name, config.provider,
                           config.base, config.quote, e)
            return None
        if not rates:
            return None
        latest = rates[-1]
        previous = next((r for r in reversed(rates) if r.as_of.date() < latest.as_of.date()),
                        None)
        return FeedQuote(latest, previous)
