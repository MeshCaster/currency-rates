#!/usr/bin/env bash
# Create what the Currency Rates containers are deployed with: the database and the env file.
#
# Run this ON the CONTABO host, once, before the first production deploy. deploy-container.yml
# passes the env file to `docker run --env-file` for both the API and the worker, so it must exist.
#
#   ./bootstrap-env.sh <admin-email>
#   SITE_HOST=rates.example.ge ADMIN_HOST=admin.rates.example.ge ./bootstrap-env.sh <admin-email>
#
# Secrets (JWT signing key, first admin password) are generated here and never leave the server,
# except the admin password, which is printed once. The Postgres credentials are read back out
# of the running meshcaster-postgres container (MeshCaster/DevOps applications/infrastructure/common).
#
# An existing env file is never overwritten: a new SECURITY__SECRET_KEY signs every user out.
# Delete the file by hand to regenerate it.

set -euo pipefail

ADMIN_EMAIL="${1:-}"
SITE_HOST="${SITE_HOST:-currency-rates.in-vent.online}"
ADMIN_HOST="${ADMIN_HOST:-currency-rates-admin.in-vent.online}"
PG_CONTAINER=meshcaster-postgres
DB_NAME=meshcaster_currency_rates
ENV_DIR=/opt/meshcaster
ENV_FILE="$ENV_DIR/currency-rates.env"

die() { echo "error: $*" >&2; exit 1; }

[[ "$ADMIN_EMAIL" == *@*.* ]] || die "usage: $0 <admin-email>"
command -v docker >/dev/null || die "docker not found"
command -v openssl >/dev/null || die "openssl not found"
docker inspect "$PG_CONTAINER" >/dev/null 2>&1 \
  || die "$PG_CONTAINER is not running; bring up applications/infrastructure/common first"
docker network inspect meshcaster >/dev/null 2>&1 \
  || die "docker network 'meshcaster' is missing; bring up applications/infrastructure/common first"

[ ! -e "$ENV_FILE" ] || die "$ENV_FILE already exists; delete it first if you really mean to rotate its secrets"

pg_env() {
  docker inspect -f '{{range .Config.Env}}{{println .}}{{end}}' "$PG_CONTAINER" | sed -n "s/^$1=//p"
}
PG_USER="$(pg_env POSTGRES_USER)"
PG_PASS="$(pg_env POSTGRES_PASSWORD)"
PG_USER="${PG_USER:-postgres}"
[ -n "$PG_PASS" ] || die "could not read POSTGRES_PASSWORD from $PG_CONTAINER"

# The API creates the schema (alembic upgrade head on start) but never the database itself.
if docker exec "$PG_CONTAINER" psql -U "$PG_USER" -tAc \
     "SELECT 1 FROM pg_database WHERE datname='$DB_NAME'" | grep -q 1; then
  echo "database '$DB_NAME' already exists"
else
  docker exec "$PG_CONTAINER" createdb -U "$PG_USER" "$DB_NAME"
  echo "created database '$DB_NAME'"
fi

# DATABASE__URL is a URL, so a password with @ : / % or # in it must be percent-encoded.
urlencode() {
  local s="$1" out="" c i
  for (( i = 0; i < ${#s}; i++ )); do
    c="${s:i:1}"
    case "$c" in
      [a-zA-Z0-9.~_-]) out+="$c" ;;
      *) out+="$(printf '%%%02X' "'$c")" ;;
    esac
  done
  printf '%s' "$out"
}

# Base64 without + / =, so nothing in the file needs quoting.
secret() { openssl rand -base64 "$1" | tr -d '\n+/='; }
SECRET_KEY="$(secret 48)"
ADMIN_PASSWORD="$(secret 18)"

mkdir -p "$ENV_DIR"
umask 077

# Values here override .env.production baked into the image (pydantic-settings reads the real
# environment first). Only what is secret or specific to this server belongs in this file.
cat > "$ENV_FILE" <<EOF
APP_ENV=production
DATABASE__URL=postgresql+asyncpg://$(urlencode "$PG_USER"):$(urlencode "$PG_PASS")@$PG_CONTAINER:5432/$DB_NAME
SECURITY__SECRET_KEY=$SECRET_KEY
# 127.0.0.1 is the container's own health check.
SECURITY__ALLOWED_HOSTS=$SITE_HOST,$ADMIN_HOST,127.0.0.1,localhost

# First admin: the worker creates the account on its first start and never changes an existing
# password. Remove both lines once you have signed in, then redeploy the worker.
ADMIN__EMAIL=$ADMIN_EMAIL
ADMIN__PASSWORD=$ADMIN_PASSWORD

# Mail transport. Until SMTP__HOST is set, the subscription email job stays off.
# SMTP__HOST=
# SMTP__USERNAME=
# SMTP__PASSWORD=
# SMTP__FROM_ADDRESS=Currency Rates <rates@in-vent.online>
EOF

chmod 600 "$ENV_FILE"

cat <<EOF

wrote (mode 600): $ENV_FILE
database:         $DB_NAME on $PG_CONTAINER

First admin sign-in, shown once — change it after signing in:
  $ADMIN_EMAIL
  $ADMIN_PASSWORD

Next: run the "Deploy to production" workflow in the currency-rates repository.
EOF
