import uuid
from collections.abc import Callable, Sequence
from datetime import datetime, timedelta
from uuid import UUID

from application.ports import AlertRepository, PriceSampleRepository
from application.services.alerts.models import AlertTickResult
from domain.alerts import Alert, AlertChange, AlertRule, PriceMove


class PriceAlertService:

    def __init__(self, alerts: AlertRepository, samples: PriceSampleRepository, *,
                 stale_after: timedelta, slack: timedelta,
                 new_id: Callable[[], UUID] = uuid.uuid7) -> None:
        self._alerts = alerts
        self._samples = samples
        self._stale_after = stale_after
        self._slack = slack
        self._new_id = new_id

    async def evaluate(self, rules: Sequence[AlertRule], now: datetime) -> AlertTickResult:
        result = AlertTickResult()
        unresolved = await self._alerts.unresolved_for([r.id for r in rules])
        for rule in rules:
            move = await self._move(rule, now)
            if move is None:
                result.skipped.append(rule.name)
                continue
            result.evaluated += 1
            tier = rule.tier_for(move)
            alert = unresolved.get(rule.id)
            if alert is None:
                if tier is not None:
                    await self._alerts.add(Alert.open(self._new_id(), rule, tier, move))
                    result.opened += 1
                continue
            change = alert.observe(tier, move)
            await self._alerts.update(alert)
            if change is AlertChange.ESCALATED:
                result.escalated += 1
            elif change is AlertChange.RESOLVED:
                result.resolved += 1
        return result

    async def _move(self, rule: AlertRule, now: datetime) -> PriceMove | None:
        current = await self._samples.latest(rule.sync_configuration_id, now)
        if current is None or current.sampled_at < now - self._stale_after:
            return None
        reference = await self._samples.latest(rule.sync_configuration_id,
                                               current.sampled_at - rule.window)
        if reference is None or reference.value == 0 \
                or reference.sampled_at < current.sampled_at - rule.window - self._slack:
            return None
        return PriceMove(reference.value, reference.sampled_at, current.value,
                         current.sampled_at)
