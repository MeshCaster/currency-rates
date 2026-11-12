# Currency Rates

A service that collects currency and crypto exchange rates from several public providers,
keeps their history in a time-series database, watches prices for sudden moves, and sends
users a daily email with the rates they subscribed to. It comes with two small web apps: a
public one for browsing rates and managing subscriptions, and an admin one for running the
service.

Built as an internship project in November 2026. This document describes what the system
does, how it is put together, how it was built step by step and how to run it.

---

## Contents

1. [What it does](#what-it-does)
2. [Tech stack](#tech-stack)
3. [Architecture](#architecture)
4. [How it was built](#how-it-was-built)
5. [Running it locally](#running-it-locally)
6. [API overview](#api-overview)
7. [Configuration](#configuration)
8. [How it was verified](#how-it-was-verified)
9. [Known limitations and next steps](#known-limitations-and-next-steps)

---

## What it does

| Who | What they can do |
|---|---|
| **Guest** | See every rate the service tracks with its latest value and daily change, and open a chart of its history (7 days to 1 year). |
| **User** (registered) | Everything a guest can, plus subscribe to rates and get a daily email at a chosen hour in their own time zone. |
| **Admin** | Add and monitor *sync configurations* (which pair to collect, from which provider, from which date), see each one's progress in percent, define *alert rules* on price moves and acknowledge the alerts they raise. |

Behind the scenes a worker process runs four background jobs:

| Job | Every | Purpose |
|---|---|---|
| `SyncConfigurationJob` | 60 s | Backfills each sync configuration's history in chunks, then keeps today's (still changing) rate fresh. |
| `PriceAlertJob` | 60 s | Samples live prices and opens, escalates or resolves alerts when a price moves more than a rule allows. |
| `SubscriptionEmailJob` | 60 s | Emails each user whose subscriptions are due, one digest per user. |
| `HeartbeatJob` | 15 s | Touches a file so a container health check can tell the worker is alive. |

### Rate providers

| Provider | Kind | History | How it is fetched |
|---|---|---|---|
| Frankfurter (ECB and others) | FX | from 1999 | a whole date range per request |
| National Bank of Georgia (NBG) | FX, official GEL rates | from 1996 | one day per request |
| Coinbase | crypto | from Oct 2023 | one day per request |
| Binance | crypto | full | daily candles, up to 1000 days per request |
| Kraken | crypto | last 720 days only | daily candles |
| CoinGecko | crypto | last 365 days (free tier) | price ranges, 90-day chunks |
| ExchangeRate-API | FX | none on the free plan | latest rates only (adapter exists, not synced) |

The limits above were probed against the live APIs before the sync was designed; the
findings are in [docs/provider-history-sync-plan.pdf](docs/provider-history-sync-plan.pdf).

---

## Tech stack

- **Back-end:** Python 3.14, FastAPI, Pydantic Settings, SQLAlchemy 2 (async) with asyncpg,
  Alembic migrations, httpx for provider calls, PyJWT and Argon2 (pwdlib) for auth.
- **Database:** PostgreSQL 17 with TimescaleDB (via Docker Compose).
- **Email:** the standard library's `smtplib`; Mailpit catches mail in development.
- **Front-end:** two Vite + React 19 + TypeScript apps, no UI or router libraries, plain CSS
  with light and dark themes.
- **Tooling:** uv (dependencies), poethepoet (tasks), ruff (lint), mypy (types), Docker
  (multi-stage image, non-root runtime, health checks).

---

## Architecture

The back-end follows a layered ("ports and adapters") design. Inner layers never import
outer ones, so business rules can be read and tested without a database or network.

```mermaid
flowchart TB
  subgraph clients[Clients]
    app[Public app<br/>web/app]
    admin[Admin app<br/>web/admin]
  end
  subgraph host[host: composition root]
    api[FastAPI routers<br/>host/api]
    worker[Worker process<br/>host/jobs]
  end
  subgraph core_app[Business logic]
    application[application<br/>use cases + ports]
    domain[domain<br/>entities + rules]
  end
  subgraph adapters[Adapters]
    infra[infrastructure<br/>SQLAlchemy repositories]
    rpi[rates_provider_integration<br/>provider clients]
    smtp[smtp_integration<br/>SmtpMailer]
  end
  core[core: settings, DB session, jobs runner,<br/>security, errors, logging]
  db[(PostgreSQL<br/>+ TimescaleDB)]
  ext[(Rate provider APIs)]
  mail[(SMTP server)]

  app & admin -->|/api/v1| api
  api --> application
  worker --> application
  application --> domain
  infra -.implements ports.-> application
  rpi -.implements ports.-> application
  smtp -.implements ports.-> application
  infra --> db
  rpi --> ext
  smtp --> mail
  host --> core
```

| Package | Responsibility |
|---|---|
| `src/domain` | Entities and rules with no I/O: `Rate`, `SyncConfig` and its progress, `AlertRule` with severity tiers, `Alert` and its lifecycle, `User` and roles, `Subscription` and when it is due. |
| `src/application` | Use cases (services) and the *ports* (interfaces) they need: repositories, rate history providers, email sender. Services never commit; the caller owns the transaction. |
| `src/infrastructure` | SQLAlchemy row models, repositories implementing the ports, Alembic-friendly table definitions, the seed catalog. |
| `src/rates_provider_integration` | One client per provider, each turning the provider's response into domain `Rate` objects. |
| `src/smtp_integration` | A small SMTP client implementing the email port. |
| `src/core` | Cross-cutting pieces reused by every layer: configuration, the clock, database session, generic repository, pagination (`Page`, `PageResponse`), background job framework (`PeriodicJob`, `ExclusiveJob`, `JobRunner`, advisory locks, heartbeat), JWT and password hashing, error types and handlers, logging and middleware. |
| `src/host` | The composition root: builds the FastAPI app and the worker, wires adapters into services, and holds the provider registry. |
| `web/app`, `web/admin` | The two React apps. |
| `migrations` | Alembic migrations (`0001` to `0004`). |

### Key design points

- **API and worker are separate processes.** Scaling the API never multiplies the
  background jobs, and a slow provider never slows down HTTP requests.
- **Several worker replicas are safe.** Every job takes a PostgreSQL advisory lock
  (`pg_try_advisory_xact_lock`) for the work it does, so replicas split the work instead of
  repeating it. Sync configurations also use optimistic locking (a `version` column).
- **Resumable backfill.** A sync configuration stores `synced_until`. Each run fetches one
  chunk (sized to the provider's limits) and moves the marker forward, so an interrupted
  backfill continues where it stopped.
- **Today is provisional.** Completed days are final. Today's rate is overwritten every
  minute until the day ends; then the day is fetched once more and stored as final.
- **One registry of providers.** `host/providers.py` maps each catalog key to its
  integration. The worker builds providers from it and the admin API only accepts keys it
  knows, so they can never disagree.
- **Errors are problem+json.** Domain rule violations become `422`, conflicts `409`,
  missing records `404`, failing upstream providers `502`.
- **Roles map to token scopes.** A `user` token carries `subscriptions:*`; an `admin` token
  also carries `sync:*` and `alerts:*`. Endpoints check scopes, so the same sign-in serves
  both apps.

---

## How it was built

The project grew in iterations. Each step started from a working state, added one
capability and was verified end to end before moving on. The dates follow the commit
history.

### 1. Provider integrations (8 Nov)

The starting point was talking to real rate APIs. Clients were written for three FX
providers (NBG, ExchangeRate-API, Frankfurter) and four crypto exchanges (Binance,
CoinGecko, Coinbase, Kraken). Each one hides its provider's quirks (different symbols such as
Kraken's `XBT` for bitcoin, CoinGecko's coin ids, NBG's table format) behind the same `Rate`
value object, with typed Pydantic models for every response.

### 2. Layered architecture and persistence (9 to 11 Nov)

The code was split into `domain`, `application`, `infrastructure` and `host`, with a `core`
package for shared helpers. A generic SQLAlchemy repository (CRUD, paging, optimistic
locking, idempotent inserts) was written once in `core` and reused by every aggregate.
Configuration moved to environment-specific settings (`.env.development`, `.env.production`)
with nested variables such as `DATABASE__URL`, and a consistent error model with handlers was
added. The first Alembic migration created the `rates` table.

### 3. Provider catalog and sync configurations (11 Nov)

Before syncing history, each provider's real limits were measured: how far back it goes,
how many days one request may cover, and which intervals it serves. These facts became a
**provider catalog** (providers, intervals, supported currencies), and a **sync
configuration** table describing *what* to collect. Composite foreign keys make the
database itself reject a configuration the catalog doesn't allow. The catalog is seeded
from one Python file in every environment, and development additionally gets example sync
configurations.

### 4. Background jobs and the history sync (12 Nov)

A small job framework went into `core/jobs`: `PeriodicJob` (interval, per-run timeout,
error isolation), `JobRunner`, advisory locking and a heartbeat for health checks. Jobs run
in their own worker process with clean shutdown on `SIGTERM`.

`SyncConfigurationJob` loads the due configurations every minute and syncs them **in
parallel** (a global limit and a per-provider limit), each in its own transaction. A
failure is recorded on that configuration and never stops the others. Later in the
project the job was extended so that caught-up configurations refresh today's rate as a
provisional value.

### 5. Progress for admins (12 Nov)

Admins need to know how far each backfill has got. `SyncConfig.progress()` computes the
synced days out of the completed days in range, a percentage and a state (`pending`,
`backfilling`, `live`, `completed`, `failed`, `paused`). An admin API exposes it, and
creating a configuration is checked against the catalog first (provider exists and has an
integration, interval supported, date within the provider's history, currencies listed,
no duplicate), giving clear `422` and `409` answers instead of database errors.

### 6. Provider registry and more providers (12 Nov)

The mapping from provider key to integration became a single registry. History support
was added for Binance (daily candles), Kraken (OHLC, with a guard for its 720-day window)
and CoinGecko (price ranges reduced to one closing value per day). Testing against the
live APIs found that Kraken returns the current candle twice, so duplicate keys are now
collapsed before storing.

### 7. Price monitoring and alerts (12 Nov)

Admins can define **alert rules**: watch one synced rate, a window from minutes to days,
a direction (up, down or both) and severity tiers such as *3% → warning, 5% → critical*.
`PriceAlertJob` samples live prices every minute into `price_samples` and compares each
price with the one a window earlier. Each rule has at most one unresolved alert (enforced
by a partial unique index): it opens on the first tier crossed, escalates (and reopens if
acknowledged) on a higher tier, never downgrades, and resolves itself when the move falls
back. Rules are skipped when there is no fair comparison, for example right after the
worker was down, to avoid false alarms.

### 8. Users, authentication and subscriptions (12 Nov)

FastAPI has no built-in identity system, so a small one was built on what the project
already had: Argon2 password hashing, JWT access tokens and scope checks. Users register
and sign in; a role decides the token's scopes. The first admin comes from the
`ADMIN__EMAIL` and `ADMIN__PASSWORD` settings. Signed-in users subscribe to a synced rate
at an hour in their own IANA time zone. Sign-in failures look and take the same whether
the email exists or not, so accounts can't be probed.

### 9. Email delivery (12 Nov)

`smtp_integration` provides a dependency-free SMTP client. `SubscriptionEmailJob` decides
which subscriptions are due (their hour in their time zone, with a short catch-up window
so a worker restart doesn't skip a day), groups them into one email per user with each
rate's latest value and daily change, and records the user-local day it sent, so no day
is mailed twice. A failed send is retried on the next tick.

### 10. Web apps (12 Nov)

Two lightweight React apps were built on top of the API: a public one (rates table,
history chart, sign-in, subscriptions) and an admin one (sync progress, alert rules,
alerts). To give guests a per-provider view, the API gained `/feeds` endpoints with each
feed's latest value, daily change and history.

### 11. Cleanup (12 Nov)

Code that the later design had replaced was removed: the first rate query and backfill
endpoints (replaced by sync configurations and feeds), their services and ports, and
repository methods nothing called any more.

### 12. Consolidating shared code in core (12 Nov)

With every feature in place, patterns that several features had each written for
themselves were moved into `core`, so a new feature gets them for free:

- **Clock** (`core.clock`): one `utc_now` / `utc_today` for services, jobs, the seed and
  tokens; services accept a clock argument so tests can pin the time.
- **Repository** (`core.database.repository`): `add()` detaches the inserted row, so reading
  it back in the same transaction loads its joined data. Three repositories had each
  worked around this on their own.
- **Exclusive jobs** (`core.jobs.ExclusiveJob`): a periodic job that runs on one replica at
  a time (transaction, advisory lock, skip if taken). The price-alert and email jobs build
  on it.
- **Pagination** (`core.pagination`, `core.dependencies`): list endpoints take `page` and
  `size` through one dependency and return one generic `PageResponse[T]`.

---

## Running it locally

### Prerequisites

- Python 3.14 and [uv](https://docs.astral.sh/uv/)
- Docker (for PostgreSQL and, optionally, Mailpit)
- Node.js 20+ and npm (for the web apps)

### 1. Back-end

```bash
uv sync --extra postgres            # install dependencies into .venv
docker compose up -d db             # PostgreSQL + TimescaleDB on localhost:5433
APP_ENV=development uv run alembic upgrade head
APP_ENV=development ADMIN__EMAIL=you@example.com ADMIN__PASSWORD='choose-a-password' uv run poe seed
```

The seed loads the provider catalog and, in development, example sync configurations. With
the two `ADMIN__*` variables set it also creates your admin account; you only need them
once.

Start the API and the worker in two terminals:

```bash
APP_ENV=development uv run uvicorn host.app:create_app --factory --app-dir src --reload --port 8010
```

```bash
uv run poe worker
```

API docs are at http://localhost:8010/swagger. Within a minute the worker starts filling in
history; the admin app shows the progress.

### 2. Email (optional)

```bash
docker compose up -d mailpit
```

`.env.development` already points SMTP at Mailpit. Every email the app sends appears at
http://localhost:8025, and nothing leaves your machine.

### 3. Web apps

```bash
cd web/app && npm install && npm run dev        # http://localhost:5173
cd web/admin && npm install && npm run dev      # http://localhost:5174
```

Both dev servers forward `/api` to the API on port 8010, so no CORS setup is needed. For
production, `npm run build` produces static files in each app's `dist/`; serve them on the
same host as the API.

### Useful tasks

| Command | What it does |
|---|---|
| `uv run poe dev` | API with hot reload on port 8000 |
| `uv run poe worker` | Background worker |
| `uv run poe seed` | Re-run the seed (safe to repeat) |
| `uv run poe lint` / `typecheck` | ruff / mypy |

### Docker

The `Dockerfile` builds one image for both processes. The API is the default command; the
worker is the same image started with `python -m host.worker` (the file shows the matching
health check).

---

## API overview

All endpoints are under `/api/v1`. Full, interactive documentation is at `/swagger`.

| Area | Endpoints | Access |
|---|---|---|
| Feeds (synced rates) | `GET /feeds`, `GET /feeds/{id}`, `GET /feeds/{id}/history?days=30` | anyone |
| Accounts | `POST /auth/register`, `POST /auth/login`, `GET /me` | anyone / signed in |
| Subscriptions | `GET`, `POST /me/subscriptions`; `PATCH`, `DELETE /me/subscriptions/{id}` | `subscriptions:*` |
| Sync configurations | `GET`, `POST /sync-configurations`; `GET /sync-configurations/{id}` | `sync:read`, `sync:write` |
| Alert rules | `GET`, `POST /alert-rules`; `GET`, `PATCH`, `DELETE /alert-rules/{id}` | `alerts:read`, `alerts:write` |
| Alerts | `GET /alerts`, `GET /alerts/{id}`, `POST /alerts/{id}/acknowledge` | `alerts:read`, `alerts:write` |
| Health | `GET /health/live`, `GET /health/ready` | anyone |

---

## Configuration

Settings come from environment variables and `.env.<APP_ENV>` files. Nested settings use a
double underscore, for example `HISTORY_SYNC__MAX_CONCURRENCY=8`.

| Variable | Default | Meaning |
|---|---|---|
| `APP_ENV` | `development` | `development`, `staging` or `production` |
| `DATABASE__URL` | none | e.g. `postgresql+asyncpg://rates:rates@localhost:5433/rates` |
| `SECURITY__SECRET_KEY` | dev placeholder | JWT signing key; set a long random value outside development |
| `SECURITY__ACCESS_TOKEN_EXPIRE_MINUTES` | `15` | Token lifetime |
| `ADMIN__EMAIL`, `ADMIN__PASSWORD` | none | First admin, created or promoted by the seed |
| `HISTORY_SYNC__INTERVAL_SECONDS` | `60` | How often the sync job runs |
| `HISTORY_SYNC__MAX_CONCURRENCY` | `4` | Configurations synced at once (`PER_PROVIDER_CONCURRENCY` limits each provider) |
| `ALERTS__SAMPLE_RETENTION_DAYS` | `31` | How long price samples are kept; also the longest rule window |
| `SMTP__HOST`, `SMTP__PORT`, `SMTP__SECURITY` | none, `587`, `starttls` | Outgoing mail; without a host the email job stays off |
| `SMTP__USERNAME`, `SMTP__PASSWORD`, `SMTP__FROM_ADDRESS` | none | SMTP login and sender |
| `NOTIFICATIONS__CATCH_UP_HOURS` | `3` | How late a missed daily email may still go out |

Keep secrets out of committed files: `.gitignore` covers `.env` only, so use your shell,
your deployment's secret store, or add `.env.local` to `.gitignore` first.

---

## How it was verified

There is no automated test suite yet (see next steps). Each step was instead verified with
scripted end-to-end checks against the development database and the live provider APIs,
then cleaned up:

- **Sync:** two worker replicas did not duplicate work; Frankfurter backfilled two years in
  chunks; Binance, Kraken and CoinGecko returned contiguous daily closes that agree with
  each other; re-running the seed changed nothing.
- **Provisional today:** a fake-provider test covered a midnight rollover (today refreshed
  in place, then replaced by the final value the next day) and the Postgres upsert was
  checked inside a rolled-back transaction.
- **Admin API:** every rejection case (unknown provider, unsupported interval, date before
  history, unlisted currency, duplicate, wrong scope) returned the expected status.
- **Alerts:** forced price moves opened a warning, escalated it to critical after it was
  acknowledged, kept it critical when the move eased, and resolved it when flat.
- **Accounts:** registration, case-insensitive emails, identical failures for wrong
  password and unknown email, scope checks, other users' subscriptions answering `404`,
  disabled accounts rejected.
- **Email:** with a local SMTP receiver, users in two time zones got one digest each for
  their own local date, a second run sent nothing, and an SMTP outage left subscriptions
  due for retry.
- **Web apps:** every screen was exercised in a browser: browsing, chart, registration,
  subscribing, admin sign-in (and refusal for non-admins), creating a rule, acknowledging
  an alert. Both apps type-check and build.

---

## Known limitations and next steps

- **Automated tests.** The checks above should become a pytest suite (the dev
  dependencies already include pytest and aiosqlite).
- **Monthly intervals.** The catalog knows monthly data, but only daily sync is
  implemented; monthly configurations are seeded inactive.
- **Sessions.** Access tokens only, no refresh tokens; there is no email verification,
  password reset or sign-in rate limiting yet.
- **Admin token lifetime.** Admin endpoints trust the token's scopes, so a disabled admin
  keeps access until the token expires (15 minutes).
- **Notifications.** Alerts are visible in the admin app only; pushing them to email,
  Slack or a webhook would be a natural addition. Emails are delivered at least once: a
  crash between sending and recording can repeat one.
- **Scale.** The email job checks every subscription each minute because each has its own
  time zone; for very large numbers a precomputed next-send time would be better.
- **Unused index.** `ix_rates_base_quote_kind_observed_at` is no longer used by any query
  and can be dropped in a future migration.
- **Old requirements file.** `requirements.txt` predates `pyproject.toml` and `uv.lock`,
  which are now the source of truth; it can be removed.
