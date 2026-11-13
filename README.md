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

Settings come from environment files, chosen by `APP_ENV`. Locally that is `development`, so the
app reads [`.env.development`](.env.development), which works as-is: nothing to fill in.

| Read in this order (later wins) | |
|---|---|
| `.env.development` | committed; works with the Docker Compose services |
| `.env.local` | optional, git-ignored; your personal overrides |
| real environment variables | e.g. `DATABASE__URL=… uv run poe dev` |

Each line is `SECTION__KEY=value`; the double underscore nests it into that section of
`src/core/configuration/settings.py`. From `.env.development`:

```dotenv
DATABASE__URL=postgresql+asyncpg://rates:rates@localhost:5433/rates   # Postgres from docker-compose.yaml
SECURITY__SECRET_KEY=dev-only-signing-key-not-for-deployment-0123456789  # signs JWTs; development only
ADMIN__EMAIL=admin@example.com                                       # admin created by the seed;
ADMIN__PASSWORD=admin-dev-password                                   # the admin app's login
SMTP__HOST=localhost                                                 # Mailpit catches every email
SMTP__PORT=1025
HISTORY_SYNC__INTERVAL_SECONDS=60                                    # how often each background job runs
ALERTS__INTERVAL_SECONDS=60
NOTIFICATIONS__INTERVAL_SECONDS=60
```

The other sections are `LOG__`, `CORS__`, `HTTP_CLIENT__`, `OTEL__` and `WORKER__`; every key is
listed with its value in the file.

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
