from __future__ import annotations

import logging

from django.db import connection
from django.http import JsonResponse

logger = logging.getLogger("errors")


def healthcheck(_: object) -> JsonResponse:
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except Exception:  # noqa: BLE001
        logger.exception("healthcheck_db_failed")
        return JsonResponse({"status": "error"}, status=503)

    return JsonResponse({"status": "ok"}, status=200)
