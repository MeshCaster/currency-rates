from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, Response, status

from application import AlertRuleService, AlertService
from core.dependencies import require_scopes
from core.exceptions.not_found_error import NotFoundError
from domain.enums import AlertSeverity, AlertStatus
from host.api.deps import CurrentUserDep, get_alert_rule_service, get_alert_service
from host.api.schemas import (
    AlertOut,
    AlertPageOut,
    AlertRuleIn,
    AlertRuleOut,
    AlertRulePageOut,
    AlertRulePatch,
)

rules_router = APIRouter(prefix="/alert-rules", tags=["alert rules"])
alerts_router = APIRouter(prefix="/alerts", tags=["alerts"])

RulesDep = Annotated[AlertRuleService, Depends(get_alert_rule_service)]
AlertsDep = Annotated[AlertService, Depends(get_alert_service)]
can_read = [Depends(require_scopes("alerts:read"))]
can_write = [Depends(require_scopes("alerts:write"))]
PageDep = Annotated[int, Query(ge=1)]
SizeDep = Annotated[int, Query(ge=1, le=200)]


@rules_router.get("", response_model=AlertRulePageOut, dependencies=can_read)
async def list_alert_rules(rules: RulesDep, *, sync_configuration_id: UUID | None = None,
                           is_active: bool | None = None, page: PageDep = 1,
                           size: SizeDep = 50) -> AlertRulePageOut:
    found = await rules.list(sync_configuration_id=sync_configuration_id,
                             is_active=is_active, page=page, size=size)
    return AlertRulePageOut(items=[AlertRuleOut.of(r) for r in found.items],
                            total=found.total, page=found.page, size=found.size)


@rules_router.get("/{id}", response_model=AlertRuleOut, dependencies=can_read)
async def get_alert_rule(id: UUID, rules: RulesDep) -> AlertRuleOut:
    rule = await rules.get(id)
    if rule is None:
        raise NotFoundError(f"No alert rule {id}")
    return AlertRuleOut.of(rule)


@rules_router.post("", response_model=AlertRuleOut, status_code=status.HTTP_201_CREATED,
                   dependencies=can_write)
async def create_alert_rule(body: AlertRuleIn, rules: RulesDep, request: Request,
                            response: Response) -> AlertRuleOut:
    rule = await rules.create(body.to_command())
    response.headers["Location"] = str(request.url_for("get_alert_rule", id=rule.id))
    return AlertRuleOut.of(rule)


@rules_router.patch("/{id}", response_model=AlertRuleOut, dependencies=can_write)
async def update_alert_rule(id: UUID, body: AlertRulePatch, rules: RulesDep) -> AlertRuleOut:
    return AlertRuleOut.of(await rules.update(id, body.to_changes()))


@rules_router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=can_write)
async def delete_alert_rule(id: UUID, rules: RulesDep) -> None:
    await rules.delete(id)


@alerts_router.get("", response_model=AlertPageOut, dependencies=can_read)
async def list_alerts(alerts: AlertsDep, *, status: AlertStatus | None = None,
                      severity: AlertSeverity | None = None, rule_id: UUID | None = None,
                      page: PageDep = 1, size: SizeDep = 50) -> AlertPageOut:
    found = await alerts.list(status=status, severity=severity, rule_id=rule_id, page=page,
                              size=size)
    return AlertPageOut(items=[AlertOut.of(a) for a in found.items], total=found.total,
                        page=found.page, size=found.size)


@alerts_router.get("/{id}", response_model=AlertOut, dependencies=can_read)
async def get_alert(id: UUID, alerts: AlertsDep) -> AlertOut:
    alert = await alerts.get(id)
    if alert is None:
        raise NotFoundError(f"No alert {id}")
    return AlertOut.of(alert)


@alerts_router.post("/{id}/acknowledge", response_model=AlertOut, dependencies=can_write)
async def acknowledge_alert(id: UUID, alerts: AlertsDep, admin: CurrentUserDep) -> AlertOut:
    return AlertOut.of(await alerts.acknowledge(id, by=admin.email))
