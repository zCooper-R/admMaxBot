from __future__ import annotations

import logging

from celery import shared_task
from django.conf import settings

from apps.analytics.services import DailyStatsSyncService

logger = logging.getLogger(__name__)


@shared_task(name="apps.analytics.tasks.sync_daily_stats_task")
def sync_daily_stats_task(window_days: int | None = None) -> dict[str, int]:
    resolved_window_days = int(window_days or getattr(settings, "DAILY_STATS_SYNC_WINDOW_DAYS", 120))
    resolved_window_days = max(resolved_window_days, 1)

    DailyStatsSyncService().ensure_recent(window_days=resolved_window_days)
    logger.info("periodic_daily_stats_synced window_days=%s", resolved_window_days)
    return {"window_days": resolved_window_days}
