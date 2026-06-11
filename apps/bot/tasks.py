from __future__ import annotations

import logging
from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.utils import timezone

from apps.bot.models import WebhookEvent, WebhookOperationLog

logger = logging.getLogger(__name__)


@shared_task(name="apps.bot.tasks.cleanup_technical_logs_task")
def cleanup_technical_logs_task() -> dict[str, int]:
    event_retention_days = int(getattr(settings, "WEBHOOK_EVENT_RETENTION_DAYS", 90))
    operation_retention_days = int(getattr(settings, "WEBHOOK_OPERATION_LOG_RETENTION_DAYS", 90))

    event_cutoff = timezone.now() - timedelta(days=event_retention_days)
    operation_cutoff = timezone.now() - timedelta(days=operation_retention_days)

    deleted_events, _ = WebhookEvent.objects.filter(received_at__lt=event_cutoff).delete()
    deleted_operations, _ = WebhookOperationLog.objects.filter(created_at__lt=operation_cutoff).delete()

    result = {
        "deleted_events": deleted_events,
        "deleted_operations": deleted_operations,
    }
    logger.info(
        "periodic_technical_logs_cleanup deleted_events=%s deleted_operations=%s",
        deleted_events,
        deleted_operations,
    )
    return result
