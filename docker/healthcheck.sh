#!/bin/sh
# Docker HEALTHCHECK for either role (see entrypoint.sh).
if [ "${APP_ROLE:-api}" = "worker" ]; then
  exec python -m core.jobs.heartbeat "${WORKER__HEARTBEAT_FILE:-/tmp/currency-rates-worker.heartbeat}" 60
fi
exec python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health/live', timeout=2).status == 200 else 1)"
