#!/bin/sh
# One image, two processes. APP_ROLE picks which one this container runs:
#   api     (default) apply pending migrations, then serve HTTP on :8000
#   worker  the background jobs (python -m host.worker); seeds the catalog and first admin
# Any arguments run instead, e.g. `docker run --rm --env-file … <image> alembic current`.
set -e

if [ "$#" -gt 0 ]; then
  exec "$@"
fi

case "${APP_ROLE:-api}" in
  api)
    # Only the API migrates, so a worker starting at the same moment never races it.
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
