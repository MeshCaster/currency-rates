#!/bin/sh
set -e

if [ "$#" -gt 0 ]; then
  exec "$@"
fi

case "${APP_ROLE:-api}" in
  api)
    alembic upgrade head
    exec uvicorn host.app:create_app --factory --app-dir src \
      --host 0.0.0.0 --port 8000 \
      --proxy-headers --forwarded-allow-ips "*" \
      --no-access-log --timeout-graceful-shutdown 20
    ;;
  worker)
    exec python -m host.worker
    ;;
  *)
    echo "unknown APP_ROLE '$APP_ROLE' (expected api or worker)" >&2
    exit 64
    ;;
esac
