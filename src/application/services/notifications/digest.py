from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal
from html import escape
from uuid import UUID

from domain.models import Rate
from domain.users import Subscription


@dataclass(frozen=True, slots=True)
class FeedQuote:
    latest: Rate
    previous: Rate | None

    @property
    def change_percent(self) -> Decimal | None:
        if self.previous is None or self.previous.value == 0:
            return None
        return (self.latest.value - self.previous.value) / self.previous.value * 100


@dataclass(frozen=True, slots=True)
class DueItem:
    subscription: Subscription
    local_day: date


@dataclass(frozen=True, slots=True)
class Digest:
    email: str
    items: tuple[DueItem, ...]

    @property
    def feed_ids(self) -> set[UUID]:
        return {i.subscription.sync_configuration_id for i in self.items}


@dataclass(frozen=True, slots=True)
class ComposedEmail:
    to: str
    subject: str
    text: str
    html: str
    delivered: tuple[DueItem, ...]


def plan_digests(deliverable: Sequence[tuple[Subscription, str]], now: datetime,
                 catch_up: timedelta) -> list[Digest]:
    by_email: dict[str, list[DueItem]] = {}
    for subscription, email in deliverable:
        day = subscription.due_on(now, catch_up)
        if day is not None:
            by_email.setdefault(email, []).append(DueItem(subscription, day))
    return [Digest(email, tuple(items)) for email, items in by_email.items()]


def compose_digest(digest: Digest, quotes: Mapping[UUID, FeedQuote]) -> ComposedEmail | None:
    lines = [(item, quotes[item.subscription.sync_configuration_id]) for item in digest.items
             if item.subscription.sync_configuration_id in quotes]
    if not lines:
        return None
    day = min(item.local_day for item, _ in lines)
    subject = f"Your currency rates for {day:%a %d %b %Y}"

    text_rows, html_rows = [], []
    for item, quote in lines:
        sub = item.subscription
        pair, value = f"{sub.base}/{sub.quote}", _amount(quote.latest.value)
        change = _change(quote)
        text_rows.append(f"  {pair:<10} {value:>18}   {change:<24} {sub.provider}")
        html_rows.append(
            f"<tr><td><b>{escape(pair)}</b></td><td style='text-align:right'>{escape(value)}"
            f"</td><td>{escape(change)}</td><td style='color:#666'>{escape(sub.provider)}"
            "</td></tr>")
    missing = len(digest.items) - len(lines)
    note = (f"\n{missing} of your rates couldn't be fetched just now; they'll come in a "
            "later email today.\n") if missing else ""

    text = (f"Hello,\n\nYour currency rates for {day:%d %b %Y}:\n\n" + "\n".join(text_rows)
            + f"\n{note}\nYou get this email because you subscribed to these rates. "
            "Change or stop it under your subscriptions in the app.\n")
    html = ("<p>Hello,</p>"
            f"<p>Your currency rates for <b>{day:%d %b %Y}</b>:</p>"
            "<table cellpadding='6' style='border-collapse:collapse;font-family:sans-serif'>"
            + "".join(html_rows) + "</table>"
            + (f"<p>{escape(note.strip())}</p>" if note else "")
            + "<p style='color:#666;font-size:12px'>You get this email because you subscribed"
            " to these rates. Change or stop it under your subscriptions in the app.</p>")
    return ComposedEmail(digest.email, subject, text, html,
                         tuple(item for item, _ in lines))


def _amount(value: Decimal) -> str:
    return f"{value:,.2f}" if abs(value) >= 1000 else f"{value:,.4f}"


def _change(quote: FeedQuote) -> str:
    change = quote.change_percent
    if change is None or quote.previous is None:
        return "no earlier rate"
    arrow = "▲" if change > 0 else "▼" if change < 0 else "="
    return f"{arrow} {change:+.2f}% since {quote.previous.as_of:%d %b}"
