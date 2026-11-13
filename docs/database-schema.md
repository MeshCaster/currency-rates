# Database schema

PostgreSQL 17 (with TimescaleDB installed), migration `0004`. Generated from the SQLAlchemy
models in `src/infrastructure/db/models` and checked against the live database.

![Database schema](database-schema.png)

The same diagram as a vector image: [database-schema.svg](database-schema.svg). Its Mermaid
source is below; after editing it, regenerate both images.

<details>
<summary>Mermaid source</summary>

```mermaid
erDiagram
  %% ---- provider catalog
  currencies {
    uuid id PK
    varchar code UK "ISO or ticker, e.g. GEL, BTC"
    varchar name
    varchar kind "fiat | crypto | stablecoin"
    timestamptz created_at
    timestamptz updated_at
  }
  providers {
    uuid id PK
    varchar key UK "e.g. nbg, frankfurter; equals Rate.source prefix"
    varchar display_name
    varchar kind "fx | crypto"
    boolean requires_api_key
    boolean is_active
    timestamptz created_at
    timestamptz updated_at
  }
  provider_intervals {
    uuid id PK
    uuid provider_id FK "UK with interval"
    varchar interval "daily | monthly"
    boolean is_native "false = derived from daily"
    date history_start "fixed earliest day"
    int history_window_days "rolling limit instead"
    int max_points_per_request
    timestamptz created_at
    timestamptz updated_at
  }
  provider_currencies {
    uuid id PK
    uuid provider_id FK "UK with currency_code"
    varchar currency_code FK
    varchar provider_code "provider's own symbol, e.g. XBT"
    date available_from
    timestamptz created_at
    timestamptz updated_at
  }

  %% ---- sync
  sync_configurations {
    uuid id PK
    uuid provider_id FK "UK with base, quote, interval"
    varchar base FK "listed by the provider"
    varchar quote FK "listed by the provider; not base"
    varchar interval FK "offered by the provider"
    date date_from
    date date_to "null = keep going"
    date synced_until "backfill progress marker"
    boolean is_active
    jsonb options "e.g. providers=ECB"
    timestamptz last_run_at
    varchar last_status "succeeded | failed"
    text last_error
    int version "optimistic locking"
    timestamptz created_at
    timestamptz updated_at
  }
  rates {
    varchar base PK
    varchar quote PK
    varchar source PK "provider key, optional :variant"
    timestamptz observed_at PK "a day's rate at 00:00 UTC"
    numeric value "38,18"
    varchar kind "observation | resolved | cross"
    timestamptz fetched_at
    timestamptz created_at
    timestamptz updated_at
  }

  %% ---- price alerts
  alert_rules {
    uuid id PK
    uuid sync_configuration_id FK
    varchar name
    int window_minutes "at least 1"
    varchar direction "up | down | both"
    jsonb tiers "[{threshold_percent, severity}]"
    boolean is_active
    int version
    timestamptz created_at
    timestamptz updated_at
  }
  alerts {
    uuid id PK
    uuid rule_id FK "one unresolved per rule"
    varchar severity "info | warning | critical"
    varchar status "open | acknowledged | resolved"
    timestamptz opened_at
    numeric change_percent "latest move"
    numeric peak_change_percent "largest move"
    numeric reference_price
    numeric current_price
    timestamptz observed_at
    timestamptz acknowledged_at
    varchar acknowledged_by "admin email"
    timestamptz resolved_at
    int version
    timestamptz created_at
    timestamptz updated_at
  }
  price_samples {
    uuid sync_configuration_id PK, FK
    timestamptz sampled_at PK
    numeric value
  }

  %% ---- accounts
  users {
    uuid id PK
    varchar email UK "stored lowercased"
    varchar password_hash "Argon2id"
    varchar role "user | admin"
    boolean is_active
    int version
    timestamptz created_at
    timestamptz updated_at
  }
  subscriptions {
    uuid id PK
    uuid user_id FK "UK with sync_configuration_id"
    uuid sync_configuration_id FK
    smallint hour "0 to 23"
    varchar timezone "IANA, e.g. Asia/Tbilisi"
    boolean is_active
    date last_sent_on "user-local day of the last email"
    int version
    timestamptz created_at
    timestamptz updated_at
  }

  providers ||--o{ provider_intervals : serves
  providers ||--o{ provider_currencies : lists
  currencies ||--o{ provider_currencies : "offered as"
  providers ||--o{ sync_configurations : "synced from"
  provider_intervals ||--o{ sync_configurations : "allows interval"
  provider_currencies ||--o{ sync_configurations : "allows base and quote"
  sync_configurations }o..o{ rates : "stores (by pair and source)"
  sync_configurations ||--o{ alert_rules : "watched by"
  sync_configurations ||--o{ price_samples : "sampled into"
  alert_rules ||--o{ alerts : raises
  sync_configurations ||--o{ subscriptions : "subscribed to"
  users ||--o{ subscriptions : has
```

</details>

Solid lines are foreign keys. The dotted line is a logical link only: `rates` has a natural
key and no foreign key, so a configuration's rates are found by pair and source.

## Design

The schema has to keep track of state while it collects FX and crypto rates from several
providers, each with different limits, and serve two consumers on top: price monitoring for
admins and daily emails for users.

### A catalog of what each provider can do

Providers differ in what they quote and how far back they go, so those facts are data, not
code. `providers`, `currencies`, `provider_currencies` and `provider_intervals` form a
catalog that is seeded from one Python file. A sync configuration can only point at what
the catalog allows: composite foreign keys tie its interval to `provider_intervals` and its
base and quote to `provider_currencies`, so the database itself rejects a pair or interval
the provider doesn't offer. `provider_currencies.provider_code` keeps each provider's own
symbol (Kraken's `XBT`, CoinGecko's `bitcoin`) out of the rest of the model.

### Intervals at three levels

| Level | Where | Meaning |
|---|---|---|
| What a provider can serve | `provider_intervals` | Per interval: native or derived from daily, a fixed `history_start` or a rolling `history_window_days`, and `max_points_per_request` |
| What we collect | `sync_configurations.interval` | The interval chosen for one provider and pair; must be one the provider offers |
| How often a user hears about it | `subscriptions` | Once a day, at `hour` in the user's `timezone` |

Each level is checked against the one above it: the admin API rejects a configuration whose
interval the provider lacks or whose `date_from` is earlier than the provider's history. The
worker's request sizes still come from each integration's `chunk_days` in code; moving them
into `provider_intervals.max_points_per_request` would make the catalog the only place for
provider limits.

### Sync state as data

A sync configuration records where it stands, so any worker replica can pick up the work
and an admin can see it without reading logs:

| Column | Records |
|---|---|
| `synced_until` | The last completed day stored; a backfill resumes from the day after |
| `last_run_at`, `last_status`, `last_error` | The outcome of the latest run, failures included |
| `is_active`, `date_from`, `date_to` | Whether and over which window to collect |
| `version` | Optimistic locking, so two workers can't both advance the same configuration |

From these the domain derives a state (`pending`, `backfilling`, `live`, `completed`,
`failed`, `paused`) and a percentage, so they are never stored twice. Rates themselves are
written idempotently: the primary key (`base`, `quote`, `source`, `observed_at`) makes a
repeated fetch overwrite the same row, which is also how today's still-changing rate is
replaced every minute until the day is over.

### Monitoring

`alert_rules` hold admin-defined price-move rules on one configuration; `price_samples`
store the live price once a minute and are pruned after 31 days, which is what lets a rule
watch a window of minutes or hours although `rates` only keeps one value per day. `alerts`
keep each episode with its own state (`open`, `acknowledged`, `resolved`) and peak move;
a partial unique index allows only one unresolved alert per rule, so a long move escalates
one alert instead of opening many.

### Subscriptions: problems with the current link

A subscription currently points at a `sync_configuration_id`. That ties a user-facing promise
to an admin's operational record, and it causes real problems:

| # | Problem | Where it shows |
|---|---|---|
| 1 | The email sends a live price fetched from the provider, not the stored daily rate, so it can disagree with the app and fails when the provider is down even though the rate is stored | `host/jobs/subscription_emails.py` calls the provider for every due feed |
| 2 | Deleting a configuration silently deletes every user's subscription to it | `ON DELETE CASCADE` on `subscriptions.sync_configuration_id` |
| 3 | Pausing a configuration silently stops the emails, while the user still sees the subscription as on | the delivery query filters on `sync_configurations.is_active` |
| 4 | Replacing a configuration (new options, or recreating it) leaves subscribers on the old one | subscriptions follow the id, not the rate |
| 5 | The configuration's interval and window mean nothing to a daily email: a monthly or finished configuration can still be subscribed to | the subscribe check only requires an active configuration |
| 6 | `rates` has no interval column, so a monthly series can't be stored next to the daily one from the same source | monthly sync is rejected as unsupported |

### Subscriptions: proposed change

Subscribe to the **rate**, not to the configuration, and send the **stored daily rate**:

- **What a subscription points at:** `provider_id`, `base` and `quote`, checked by composite
  foreign keys against `provider_currencies` the same way sync configurations are. It then
  names the same thing `rates` stores (pair and source), survives any change to
  configurations, and can't be removed by an admin action.
- **What the email contains:** the latest final daily rate from `rates` (the last completed
  day) and its change against the day before, optionally with today's provisional value
  labelled as such. The job reads only the database, so it never calls a provider and
  always matches what the app shows.
- **When nothing collects it any more:** if no active configuration syncs that provider and
  pair, the subscription is shown as waiting for data instead of silently going quiet.
- **Intervals:** subscriptions stay daily; if weekly or monthly digests are added later they
  become a `frequency` column on the subscription, independent of the sync interval.

## Tables

| Table | Area | Holds | Keys and constraints |
|---|---|---|---|
| `currencies` | catalog | Every currency the catalog knows | `code` unique |
| `providers` | catalog | Rate providers; `key` matches the integration | `key` unique |
| `provider_intervals` | catalog | Each provider's intervals and history limits | unique (`provider_id`, `interval`); cascade on provider delete |
| `provider_currencies` | catalog | Currencies each provider quotes | unique (`provider_id`, `currency_code`); cascade on provider or currency delete |
| `sync_configurations` | sync | What to collect: provider, pair, interval, date window, progress | unique (`provider_id`, `base`, `quote`, `interval`); composite FKs to `provider_intervals` and `provider_currencies` (twice) so the database rejects what the catalog doesn't allow; checks `base <> quote` and `date_to IS NULL OR date_from <= date_to`; partial index on `synced_until WHERE is_active` |
| `rates` | rates | Every stored rate; today's is overwritten until the day ends | primary key (`base`, `quote`, `source`, `observed_at`); indexes on (`base`, `quote`, `observed_at`) and (`base`, `quote`, `kind`, `observed_at`) |
| `alert_rules` | alerts | Price-move rules on one configuration | check `window_minutes >= 1`; cascade on configuration delete |
| `alerts` | alerts | One episode of a rule's price move | unique `rule_id WHERE status <> 'resolved'` (one open alert per rule); index on (`status`, `opened_at`); cascade on rule delete |
| `price_samples` | alerts | Live price per configuration per tick, pruned after 31 days | primary key (`sync_configuration_id`, `sampled_at`); index on `sampled_at`; cascade on configuration delete |
| `users` | accounts | Accounts and roles | `email` unique |
| `subscriptions` | accounts | A user's daily email about one configuration | unique (`user_id`, `sync_configuration_id`); check `hour BETWEEN 0 AND 23`; cascade on user or configuration delete |

All `id` columns are UUIDv7, so new rows sort by creation time. `created_at` and `updated_at`
are kept by the repository layer; `version` columns back optimistic locking.

## Allowed values

Stored as `varchar(16)`; the allowed values come from the domain enums in `src/domain/enums.py`.

| Column | Values |
|---|---|
| `currencies.kind` | `fiat`, `crypto`, `stablecoin` |
| `providers.kind` | `fx`, `crypto` |
| `provider_intervals.interval`, `sync_configurations.interval` | `daily`, `monthly` |
| `sync_configurations.last_status` | `succeeded`, `failed` |
| `rates.kind` | `observation`, `resolved`, `cross` |
| `alert_rules.direction` | `up`, `down`, `both` |
| `alerts.severity` | `info`, `warning`, `critical` |
| `alerts.status` | `open`, `acknowledged`, `resolved` |
| `users.role` | `user`, `admin` |

## Deleting

Deleting a sync configuration deletes its alert rules (and their alerts), its price samples
and its subscriptions. Deleting a user deletes their subscriptions. A provider can't be
deleted while sync configurations use it.
