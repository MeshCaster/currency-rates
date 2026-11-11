import uuid
from collections.abc import Callable
from dataclasses import replace
from uuid import UUID

from application.ports import AlertRuleRepository, SyncConfigurationRepository
from application.services.alerts.models import AlertRuleChanges, NewAlertRule
from core.exceptions.not_found_error import NotFoundError
from core.pagination import Page
from domain.alerts import AlertRule
from domain.errors import InvalidAlertRuleError


class AlertRuleService:

    def __init__(self, rules: AlertRuleRepository, configs: SyncConfigurationRepository, *,
                 max_window_minutes: int, new_id: Callable[[], UUID] = uuid.uuid7) -> None:
        self._rules = rules
        self._configs = configs
        self._max_window = max_window_minutes
        self._new_id = new_id

    async def create(self, new: NewAlertRule) -> AlertRule:
        config = await self._configs.get(new.sync_configuration_id)
        if config is None:
            raise InvalidAlertRuleError(f"no sync configuration {new.sync_configuration_id}")
        rule = AlertRule(
            id=self._new_id(), sync_configuration_id=config.id, name=new.name.strip(),
            window_minutes=new.window_minutes, tiers=tuple(new.tiers), direction=new.direction,
            is_active=new.is_active, provider=config.provider, base=config.base,
            quote=config.quote)
        self._check_window(rule)
        await self._rules.add(rule)
        return rule

    async def get(self, id: UUID) -> AlertRule | None:
        return await self._rules.get(id)

    async def list(self, *, sync_configuration_id: UUID | None = None,
                   is_active: bool | None = None, page: int = 1,
                   size: int = 50) -> Page[AlertRule]:
        return await self._rules.search(sync_configuration_id=sync_configuration_id,
                                        is_active=is_active, page=page, size=size)

    async def update(self, id: UUID, changes: AlertRuleChanges) -> AlertRule:
        rule = await self._rules.get(id)
        if rule is None:
            raise NotFoundError(f"No alert rule {id}")
        updated = replace(
            rule,
            name=changes.name.strip() if changes.name is not None else rule.name,
            window_minutes=changes.window_minutes or rule.window_minutes,
            tiers=tuple(changes.tiers) if changes.tiers is not None else rule.tiers,
            direction=changes.direction or rule.direction,
            is_active=rule.is_active if changes.is_active is None else changes.is_active)
        self._check_window(updated)
        await self._rules.update(updated)
        return updated

    async def delete(self, id: UUID) -> None:
        await self._rules.delete(id)

    def _check_window(self, rule: AlertRule) -> None:
        if rule.window_minutes > self._max_window:
            raise InvalidAlertRuleError(
                f"window_minutes can be at most {self._max_window}: "
                "price samples aren't kept longer")
