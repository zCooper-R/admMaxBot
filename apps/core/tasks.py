from __future__ import annotations

import logging

from celery import shared_task

from apps.core.integration_health import IntegrationHealthService

logger = logging.getLogger(__name__)


@shared_task(name="apps.core.tasks.refresh_integration_status_task")
def refresh_integration_status_task() -> dict[str, str]:
    status = IntegrationHealthService().refresh_status()
    logger.info(
        "periodic_integration_status_refreshed bot=%s webhook=%s",
        status["bot_enabled"],
        status["webhook_badge"],
    )
    return status
