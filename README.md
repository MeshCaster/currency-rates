# Currency Rates

## Architecture

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
  core[core: settings, clock, DB session, jobs,<br/>security, errors, logging]
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
| `src/application` | Use cases (services) and the ports they need: repositories, rate history providers, email sender. Services never commit; the caller owns the transaction. |
| `src/infrastructure` | SQLAlchemy row models, repositories implementing the ports, the provider catalog seed. |
| `src/rates_provider_integration` | One client per provider, turning its responses into domain `Rate` objects. |
| `src/smtp_integration` | A small SMTP client implementing the email port. |
| `src/core` | Shared pieces: settings, clock (`core.clock`), database session, generic repository, pagination (`Page`, `PageResponse`), job framework (`PeriodicJob`, `ExclusiveJob`, `JobRunner`, advisory locks, heartbeat), JWT and password hashing, errors, logging, middleware. |
| `src/host` | Composition root: builds the FastAPI app and the worker, wires adapters into services, holds the provider registry. |
| `web/app`, `web/admin` | The two React apps. |
| `migrations` | Alembic migrations (`0001` to `0004`). |

Tables, keys and relationships: [docs/database-schema.md](docs/database-schema.md).

## Architecture decisions

- **API and worker are separate processes.** Scaling the API never multiplies the background jobs, and a slow provider never slows down HTTP requests.
- **Several worker replicas are safe.** Every job takes a PostgreSQL advisory lock (`pg_try_advisory_xact_lock`), so replicas split the work instead of repeating it. Sync configurations also use optimistic locking (`version`).
- **Resumable backfill.** A sync configuration stores `synced_until`; each run fetches one chunk sized to the provider's limits and moves the marker forward, so an interrupted backfill continues where it stopped.
- **Today is provisional.** Completed days are final. Today's rate is overwritten every minute, then fetched once more and stored as final when the day ends.
- **One provider registry** (`host/providers.py`). The worker and the admin API read the same list, so they can never disagree.
- **Validation against the catalog.** A new sync configuration is checked against the provider catalog (provider, interval, history limit, currencies, duplicates) and gets a clear `422` or `409`; composite foreign keys back this up in the database.
- **One open alert per rule** (partial unique index). It escalates on a higher tier, never downgrades, and resolves itself when the move falls back.
- **Errors are problem+json.** Domain rule violations are `422`, conflicts `409`, missing records `404`, failing providers `502`.
- **Roles map to token scopes.** `user` gets `subscriptions:*`; `admin` also gets `sync:*` and `alerts:*`. One sign-in serves both apps.
- **Shared logic lives in `core`.** The clock, `add()` detaching new rows, `ExclusiveJob` and `PageResponse` are written once and reused by every feature.

## Roles

| Role | Can |
|---|---|
| **Guest** | See every rate with its latest value, daily change and a history chart (7 days to 1 year). |
| **User** | Everything a guest can, plus subscribe to rates and get a daily email at a chosen hour in their own time zone. |
| **Admin** | Add sync configurations and follow their progress (%), define price-move alert rules and acknowledge alerts. |

## Background jobs

| Job | Every | Purpose |
|---|---|---|
| `SyncConfigurationJob` | 60 s | Backfills each sync configuration in chunks, then keeps today's rate fresh. |
| `PriceAlertJob` | 60 s | Samples live prices and opens, escalates or resolves alerts when a move exceeds a rule. |
| `SubscriptionEmailJob` | 60 s | Emails users whose subscriptions are due, one digest per user. |
| `HeartbeatJob` | 15 s | Touches a file so a container health check can tell the worker is alive. |

## Rate providers

| Provider | Kind | History | How it is fetched |
|---|---|---|---|
| Frankfurter | FX | from 1999 | a date range per request |
| National Bank of Georgia (NBG) | FX, official GEL rates | from 1996 | one day per request |
| Coinbase | crypto | from Oct 2023 | one day per request |
| Binance | crypto | full | daily candles, up to 1000 days per request |
| Kraken | crypto | last 720 days | daily candles |
| CoinGecko | crypto | last 365 days (free tier) | price ranges, 90-day chunks |
| ExchangeRate-API | FX | none (free plan) | latest rates only, not synced |

Measured provider limits: [docs/provider-history-sync-plan.pdf](docs/provider-history-sync-plan.pdf).

## API

All endpoints are under `/api/v1`; interactive docs at `/swagger`.

| Area | Endpoints | Access |
|---|---|---|
| Feeds (synced rates) | `GET /feeds`, `GET /feeds/{id}`, `GET /feeds/{id}/history?days=30` | anyone |
| Accounts | `POST /auth/register`, `POST /auth/login`, `GET /me` | anyone / signed in |
| Subscriptions | `GET`, `POST /me/subscriptions`; `PATCH`, `DELETE /me/subscriptions/{id}` | `subscriptions:*` |
| Sync configurations | `GET`, `POST /sync-configurations`; `GET /sync-configurations/{id}` | `sync:read`, `sync:write` |
| Alert rules | `GET`, `POST /alert-rules`; `GET`, `PATCH`, `DELETE /alert-rules/{id}` | `alerts:read`, `alerts:write` |
| Alerts | `GET /alerts`, `GET /alerts/{id}`, `POST /alerts/{id}/acknowledge` | `alerts:read`, `alerts:write` |
| Health | `GET /health/live`, `GET /health/ready` | anyone |

List endpoints take `?page=` and `?size=` and return `{items, total, page, size}`.

## Configuration

`.env.development` works as-is with Docker Compose; `.env.production` lists every value to
provide as a `[ ]` item. Personal values go in `.env.local`, which is git-ignored.

| Variable | Default | Meaning |
|---|---|---|
| `APP_ENV` | `development` | `development`, `staging` or `production` |
| `DATABASE__URL` | — | e.g. `postgresql+asyncpg://rates:rates@localhost:5433/rates` |
| `SECURITY__SECRET_KEY` | dev placeholder | JWT signing key; set a long random value outside development |
| `SECURITY__ACCESS_TOKEN_EXPIRE_MINUTES` | `15` | Token lifetime |
| `ADMIN__EMAIL`, `ADMIN__PASSWORD` | — | First admin, created or promoted by the seed |
| `HISTORY_SYNC__INTERVAL_SECONDS` | `60` | How often the sync job runs |
| `HISTORY_SYNC__MAX_CONCURRENCY` | `4` | Configurations synced at once (`PER_PROVIDER_CONCURRENCY` limits each provider) |
| `ALERTS__SAMPLE_RETENTION_DAYS` | `31` | How long price samples are kept; also the longest rule window |
| `SMTP__HOST`, `SMTP__PORT`, `SMTP__SECURITY` | —, `587`, `starttls` | Outgoing mail; without a host the email job stays off |
| `SMTP__USERNAME`, `SMTP__PASSWORD`, `SMTP__FROM_ADDRESS` | — | SMTP login and sender |
| `NOTIFICATIONS__CATCH_UP_HOURS` | `3` | How late a missed daily email may still go out |

## Running locally

| Step | Command |
|---|---|
| Dependencies | `uv sync --extra postgres` |
| Database | `docker compose up -d db` |
| Migrations | `APP_ENV=development uv run alembic upgrade head` |
| Seed (+ admin) | `APP_ENV=development ADMIN__EMAIL=… ADMIN__PASSWORD=… uv run poe seed` |
| API (port 8010) | `APP_ENV=development uv run uvicorn host.app:create_app --factory --app-dir src --reload --port 8010` |
| Worker | `uv run poe worker` |
| Email (Mailpit, `localhost:8025`) | `docker compose up -d mailpit` |
| Public app (`localhost:5173`) | `cd web/app && npm install && npm run dev` |
| Admin app (`localhost:5174`) | `cd web/admin && npm install && npm run dev` |

| Stack | |
|---|---|
| Back-end | Python 3.14, FastAPI, Pydantic Settings, SQLAlchemy 2 (async), Alembic, httpx, PyJWT, Argon2 |
| Database | PostgreSQL 17 + TimescaleDB |
| Front-end | Vite, React 19, TypeScript |
| Email | `smtplib`; Mailpit in development |
| Tooling | uv, poethepoet, ruff, mypy, Docker |

## Development stages

| # | Date | Stage |
|---|---|---|
| 1 | 8 Nov | Provider integrations: 3 FX and 4 crypto |
| 2 | 9–11 Nov | Layered architecture, generic repository, configuration and error model |
| 3 | 11 Nov | Provider catalog and sync configurations |
| 4 | 12 Nov | Job framework, worker and history sync |
| 5 | 12 Nov | Sync progress and admin API |
| 6 | 12 Nov | Provider registry; Binance, Kraken and CoinGecko history |
| 7 | 12 Nov | Price monitoring and alerts |
| 8 | 12 Nov | Users, authentication and subscriptions |
| 9 | 12 Nov | SMTP integration and daily emails |
| 10 | 12 Nov | Public and admin React apps |
| 11 | 12 Nov | Removal of superseded code |
| 12 | 12 Nov | Shared logic moved into `core` |
