#!/usr/bin/env bash
# One-time local setup: Python and Node dependencies, Postgres and Mailpit in Docker, the schema,
# and the seed (provider catalog, a year of sync configurations for every free provider, and the
# development admin from .env.development). Safe to run again.
#
#   scripts/setup-local.sh
#
# Then start everything with scripts/dev.sh.
set -euo pipefail
cd "$(dirname "$0")/.."

need() { command -v "$1" >/dev/null || { echo "error: $1 is required — $2" >&2; exit 1; }; }
need docker "https://docs.docker.com/get-docker/"
need uv "https://docs.astral.sh/uv/getting-started/installation/"
need npm "Node.js 20 or newer, https://nodejs.org/"

export APP_ENV=development

echo "==> Python dependencies"
uv sync --extra postgres

echo "==> Postgres and Mailpit (docker-compose.yaml)"
docker compose up -d --wait db mailpit

echo "==> Database schema"
uv run alembic upgrade head

echo "==> Seed: provider catalog, sync configurations, admin"
uv run poe seed

echo "==> Web apps"
npm --prefix web/app ci --no-audit --no-fund
npm --prefix web/admin ci --no-audit --no-fund

cat <<'EOF'

Setup done. Start everything with:

  scripts/dev.sh
EOF
