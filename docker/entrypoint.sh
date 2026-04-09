#!/bin/sh
set -eu

WAIT_FOR_DB="${WAIT_FOR_DB:-true}"
DB_WAIT_MAX_ATTEMPTS="${DB_WAIT_MAX_ATTEMPTS:-30}"
DB_WAIT_INTERVAL_SECONDS="${DB_WAIT_INTERVAL_SECONDS:-2}"
# Миграции выполняются отдельным шагом деплоя, а не на каждом старте web-контейнера.
RUN_DB_MIGRATIONS="${RUN_DB_MIGRATIONS:-false}"
RUN_COLLECTSTATIC="${RUN_COLLECTSTATIC:-true}"

if [ "${WAIT_FOR_DB}" = "true" ]; then
  echo "Waiting for database availability..."
  attempt=1
  while [ "${attempt}" -le "${DB_WAIT_MAX_ATTEMPTS}" ]; do
    if python - <<'PY'
import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
import django
django.setup()
from django.db import connection
connection.ensure_connection()
print("Database is available")
PY
    then
      break
    fi

    if [ "${attempt}" -eq "${DB_WAIT_MAX_ATTEMPTS}" ]; then
      echo "Database is unavailable after ${DB_WAIT_MAX_ATTEMPTS} attempts"
      exit 1
    fi
    echo "Database is unavailable, retrying in ${DB_WAIT_INTERVAL_SECONDS}s (attempt ${attempt}/${DB_WAIT_MAX_ATTEMPTS})"
    attempt=$((attempt + 1))
    sleep "${DB_WAIT_INTERVAL_SECONDS}"
  done
fi

if [ "${RUN_DB_MIGRATIONS}" = "true" ]; then
  echo "Applying database migrations..."
  python manage.py migrate --noinput
fi

if [ "${RUN_COLLECTSTATIC}" = "true" ]; then
  echo "Collecting static files..."
  python manage.py collectstatic --noinput
fi

exec gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 3 --access-logfile - --error-logfile - --capture-output
