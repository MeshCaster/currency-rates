#!/usr/bin/env bash
# Run the whole application locally: API, worker and both web apps, with their output prefixed
# by name. Ctrl-C stops all of them. Run scripts/setup-local.sh once first.
set -euo pipefail
cd "$(dirname "$0")/.."

export APP_ENV=development
docker compose up -d --wait db mailpit >/dev/null

cat <<'EOF'
  Public app   http://localhost:5173
  Admin app    http://localhost:5174   (login from ADMIN__* in .env.development)
  API docs     http://localhost:8010/swagger
  Mail inbox   http://localhost:8025   (Mailpit catches every email)

EOF

trap 'trap - INT TERM EXIT; kill 0' INT TERM EXIT

run() {
  local name="$1"; shift
  "$@" 2>&1 | awk -v p="$(printf '%-7s' "$name") | " '{ print p $0; fflush() }' &
}

run api    uv run poe dev
run worker uv run poe worker
run app    npm --prefix web/app run dev
run admin  npm --prefix web/admin run dev
wait
