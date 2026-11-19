# Currency Rates

Domain data classes had been created for given features:

1. Resource management
   1. provider information
   2. provider currency pairs with interval kinds
   3. provider is related to sync configurations
2. External rate provider integration
   1. fx
   2. crypto
3. Immutable rate persistence where different sources write their sample values
4. Sync configuration related to provider capabilities
   1. managable from admin view
   2. subscription for notifications available for authenticated users
5. alerting for threshold price change

According to my business needs, I needed to design database described in docs/database-schema.md as infrastructure/db in project.

Best part of project is core, sharing helpers across whole project.

I needed way to interact with python packages like SqlAlchemy, so I designed base instrument, that is extensible to certain business logic in infrastructure layer.

I designed there: converters, type descriptors, auditable declarative bases, generic repository protocol with mapper and key introducing. Then I extend each in infrastructure repositories. That was the key technique for this kind of migration related problem to write clean code on python or more likely clean code.

As I got persistence, I identified some kind of worker need and first implemented instrument in core, periodic job protocols, heartbeats, locking and runner. Then I designed background jobs in hosting: history sync, price alerts and subscription email runners placed there.

We have defined seed models and provided script to feed all free providers across 1 year time window, then showing synchronization progress also, when activating one. Subscribe is possible and you receive daily rates/changes information on mail through our infrastructure SMTP.

Key Challenges

1. History Synchronisation

   Periodic job retrieves sync configuration domain entities, it sets config provider and concurrency. On this path I set synced_until path to specific datetime and updating rate linearly. There is additional functionality for syncing progress UI feature.
2. Monitoring Techniques

   One of techniques I applied is to find threshold percentage of rate up/down movement, this kind of alerts are consumed by admin app
3. Subscription Mechanism

   Another technique, that was applied is to send daily prices for authenticated users for desired pair

There are intgration packages with smtp and rate provider services. Core contains application middleware, error handlers and more of infra side of container with injecting application rules, defining environments and all the important part.

Application is deployed with .env.production file and github actions, I have used one bash script to setup env for container, also defined nginx configuration.

Admin application is tunneled and not public on internet, so interviewers mails are accepted through cloudflare auth.

## Configuration

Settings come from environment files, chosen by `APP_ENV` (`development`, `test`, `staging` or
`production`). Locally that is `development`, so the app reads
[`.env.development`](.env.development), which works as-is: nothing to fill in. In production the
image reads [`.env.production`](.env.production), and the server's env file supplies the secrets.

| Read in this order (later wins) | |
|---|---|
| `.env`, then `.env.<APP_ENV>` | committed defaults for that environment |
| `.env.local` | optional, git-ignored; your personal overrides (not read in `test`) |
| real environment variables | e.g. `DATABASE__URL=… uv run poe dev`, or the container's `--env-file` |

Each line is `SECTION__KEY=value`; the double underscore nests it into that section of
[`settings.py`](src/core/configuration/settings.py). Names are case-insensitive, and list values
are comma-separated (`a.com,b.com`).

### Required

The app starts with only `APP_ENV`, but does nothing useful without these.

| Variable | Needed for | Example |
|---|---|---|
| `DATABASE__URL` | everything: rates, users, alerts. Without it data endpoints answer 503 and the worker runs no jobs | `postgresql+asyncpg://rates:rates@localhost:5433/rates` |
| `SECURITY__SECRET_KEY` | signing sign-in tokens. In `staging` and `production` the app refuses to start unless it is random and 32+ characters | `python -c "import secrets; print(secrets.token_urlsafe(48))"` |
| `ADMIN__EMAIL`, `ADMIN__PASSWORD` | the first admin account, for the admin app. Created once by the seed or worker | `admin@example.com` / 8+ characters |
| `SMTP__HOST` (and the other `SMTP__` values) | any email. Without it the subscription email job stays off | `smtp-relay.brevo.com` |

### Application

| Variable | Default | Description |
|---|---|---|
| `APP_ENV` | `development` | Picks the env file and the defaults below: text logs and docs on in development, JSON logs and docs off in production. `staging` and `production` also enforce the secret-key and debug checks. |
| `APP_ROLE` | `api` | Docker image only: `api` migrates the database and serves HTTP on :8000; `worker` runs the background jobs. |
| `DEBUG` | `false` | FastAPI debug mode. Must be `false` in staging and production. |
| `API_PREFIX` | `/api/v1` | Path prefix of every API route. |
| `ROOT_PATH` | empty | Set when a proxy serves the API under a sub-path, e.g. `/rates`. |
| `DOCS_ENABLED` | on except in production | Swagger UI at `/swagger` and the OpenAPI schema. |
| `APP_NAME`, `APP_VERSION` | | Shown in the API docs and traces. |

### Database (`DATABASE__`)

PostgreSQL 17 with TimescaleDB (`docker compose up -d db` locally). The API container applies
migrations on start; locally run `uv run alembic upgrade head`.

| Variable | Default | Description |
|---|---|---|
| `DATABASE__URL` | none | SQLAlchemy URL with the async driver: `postgresql+asyncpg://USER:PASSWORD@HOST:PORT/DB`. URL-encode special characters in the password. Secret. |
| `DATABASE__POOL_SIZE` | `5` | Connections kept open per process. |
| `DATABASE__MAX_OVERFLOW` | `10` | Extra connections allowed above the pool size under load. |
| `DATABASE__POOL_TIMEOUT` | `30` | Seconds to wait for a free connection before failing the request. |
| `DATABASE__POOL_RECYCLE` | `1800` | Seconds before a connection is replaced; `-1` never. |
| `DATABASE__POOL_PRE_PING` | `true` | Checks a connection before use, so restarts of Postgres don't fail requests. |
| `DATABASE__ECHO` | `false` | Logs every SQL statement. For debugging only. |

### Email (`SMTP__`)

Used by the worker for daily subscription emails. Locally Mailpit catches everything
(`SMTP__HOST=localhost`, `SMTP__PORT=1025`, `SMTP__SECURITY=none`; inbox at
http://localhost:8025). In production use a provider such as Brevo or Zoho, with the sender's
domain verified there (SPF and DKIM records), or most mail lands in spam.

| Variable | Default | Description |
|---|---|---|
| `SMTP__HOST` | none | SMTP server. Unset means no email is sent. |
| `SMTP__PORT` | `587` | `587` with `starttls` (most providers), `465` with `ssl`. |
| `SMTP__SECURITY` | `starttls` | `starttls`, `ssl` or `none` (local catchers only). |
| `SMTP__USERNAME` | none | SMTP login; leave unset if the server needs none. |
| `SMTP__PASSWORD` | none | SMTP password or API key (an app-specific password for Zoho or Gmail). Secret. |
| `SMTP__FROM_ADDRESS` | `Currency Rates <no-reply@localhost>` | Sender users see. Must be an address or domain your provider lets you send from. |
| `SMTP__TIMEOUT_SECONDS` | `30` | Gives up on one email after this long. |

| Subscription email job (`NOTIFICATIONS__`) | Default | Description |
|---|---|---|
| `NOTIFICATIONS__ENABLED` | `true` | Turns the job off without removing SMTP settings. |
| `NOTIFICATIONS__INTERVAL_SECONDS` | `60` | How often the job checks for emails due. |
| `NOTIFICATIONS__CATCH_UP_HOURS` | `3` | An email missed at its hour (worker down) is still sent within this many hours, never the next day. |
| `NOTIFICATIONS__TIMEOUT_SECONDS` | `300` | Longest one run may take. |

### Security (`SECURITY__`) and CORS (`CORS__`)

| Variable | Default | Description |
|---|---|---|
| `SECURITY__SECRET_KEY` | insecure placeholder | Signs JWTs. Changing it signs everyone out. Secret. |
| `SECURITY__ACCESS_TOKEN_EXPIRE_MINUTES` | `15` | How long a sign-in lasts. |
| `SECURITY__JWT_ALGORITHM` | `HS256` | `HS256`, `HS384` or `HS512`. |
| `SECURITY__JWT_ISSUER`, `SECURITY__JWT_AUDIENCE` | none | Claims added to tokens, if other services verify them. |
| `SECURITY__ALLOWED_HOSTS` | `*` | Host names the API answers; requests for others are refused. Include `127.0.0.1` for the container health check. |
| `CORS__ALLOW_ORIGINS` | none | Only when the web apps run on another origin than the API. Can't be `*` together with `CORS__ALLOW_CREDENTIALS=true`. |
| `CORS__ALLOW_CREDENTIALS`, `CORS__ALLOW_METHODS`, `CORS__ALLOW_HEADERS`, `CORS__MAX_AGE` | `false`, `*`, `*`, `600` | Standard CORS response headers. |

### First admin (`ADMIN__`)

| Variable | Default | Description |
|---|---|---|
| `ADMIN__EMAIL` | none | Admin account created by `uv run poe seed` or on worker start; an existing user with this email is promoted. |
| `ADMIN__PASSWORD` | none | 8+ characters. Only used to create the account; an existing password is never changed. Secret: remove both lines once you have signed in. |

### Background jobs

All run in the worker process (`uv run poe worker`, or `APP_ROLE=worker`).

| Variable | Default | Description |
|---|---|---|
| `HISTORY_SYNC__ENABLED` | `true` | Downloads rate history for each active sync configuration. |
| `HISTORY_SYNC__INTERVAL_SECONDS` | `60` | How often it looks for days to sync. |
| `HISTORY_SYNC__MAX_CONCURRENCY` | `4` | Configurations synced at once. |
| `HISTORY_SYNC__PER_PROVIDER_CONCURRENCY` | `2` | Requests at once to one provider, to respect its rate limits. |
| `HISTORY_SYNC__CONFIG_TIMEOUT_SECONDS` | `120` | Longest one configuration may take per run. |
| `ALERTS__ENABLED` | `true` | Checks prices against alert rules. |
| `ALERTS__INTERVAL_SECONDS` | `60` | How often prices are sampled and rules checked. |
| `ALERTS__SAMPLE_RETENTION_DAYS` | `31` | Price samples are kept this long; also the longest window a rule can use. |
| `ALERTS__MAX_CONCURRENCY`, `ALERTS__TIMEOUT_SECONDS` | `4`, `50` | Rules checked at once; longest one run may take. |
| `WORKER__HEARTBEAT_FILE` | `/tmp/currency-rates-worker.heartbeat` | Touched while the worker is alive; the Docker health check reads it. |
| `WORKER__HEARTBEAT_INTERVAL_SECONDS` | `15` | How often it is touched. |

### Other

| Variable | Default | Description |
|---|---|---|
| `STORAGE__PATH` | `storage` | Folder of static files such as currency icons. |
| `STORAGE__PUBLIC_URL` | `/api/v1/storage` | Where icon URLs point. A path means the API serves `STORAGE__PATH` there; a full URL (CDN or bucket) means it doesn't. |
| `HTTP_CLIENT__TIMEOUT` | `10` | Seconds per call to a rate provider. |
| `HTTP_CLIENT__CONNECT_RETRIES` | `2` | Retries when a provider can't be reached. |
| `HTTP_CLIENT__MAX_CONNECTIONS`, `HTTP_CLIENT__MAX_KEEPALIVE_CONNECTIONS` | `100`, `20` | Connection pool limits for provider calls. |
| `LOG__LEVEL` | `INFO` | `DEBUG`, `INFO`, `WARNING` or `ERROR`. |
| `LOG__FORMAT` | `text` in development, else `json` | `json` is one object per line, for log collectors. |
| `LOG__ACCESS_LOG` | `true` | One log line per HTTP request. |
| `OTEL__ENABLED` | `false` | OpenTelemetry tracing; needs `uv sync --extra otel`. |
| `OTEL__ENDPOINT`, `OTEL__SERVICE_NAME` | none | Your collector, e.g. `http://otel-collector:4317`, and the service name traces carry. |
| `OTEL__EXPORTER`, `OTEL__SAMPLE_RATIO` | `otlp`, `1.0` | `otlp` or `console`; share of requests traced, `0.0` to `1.0`. |

## Run locally

Needs Docker, [uv](https://docs.astral.sh/uv/getting-started/installation/) and Node.js 20+.

```bash
scripts/setup-local.sh
```

```bash
scripts/dev.sh
```

The first installs everything, starts Postgres and Mailpit, creates the schema and seeds the
provider catalog, a year of sync configurations for the free providers, and the admin. The second
runs the API, the worker and both web apps together; Ctrl-C stops them.

| | |
|---|---|
| Public app | http://localhost:5173 |
| Admin app | http://localhost:5174 (`admin@example.com` / `admin-dev-password`) |
| API docs | http://localhost:8010/swagger |
| Mail inbox | http://localhost:8025 |

Deployment: [deploy/README.md](deploy/README.md).
