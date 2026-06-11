from __future__ import annotations

import logging
import os
import subprocess
from datetime import datetime, timedelta
from pathlib import Path

from celery import shared_task
from django.conf import settings
from django.utils import timezone

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


def _backup_dir() -> Path:
    backup_dir = Path(getattr(settings, "BACKUP_DIR", settings.BASE_DIR / "backups"))
    backup_dir.mkdir(parents=True, exist_ok=True)
    return backup_dir


def _cleanup_old_backups(prefix: str, retention_days: int) -> int:
    cutoff = timezone.now() - timedelta(days=max(int(retention_days), 1))
    deleted = 0

    for backup_file in _backup_dir().glob(f"{prefix}-*.dump"):
        modified_at = datetime.fromtimestamp(
            backup_file.stat().st_mtime, tz=timezone.get_current_timezone()
        )
        if modified_at >= cutoff:
            continue
        backup_file.unlink()
        deleted += 1

    return deleted


def _create_database_backup(kind: str, retention_days: int) -> dict[str, object]:
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL is required for database backup")

    created_at = timezone.now().strftime("%Y%m%d-%H%M%S")
    target = _backup_dir() / f"{kind}-{created_at}.dump"
    command = [
        "pg_dump",
        "--format=custom",
        "--no-owner",
        "--no-privileges",
        "--dbname",
        database_url,
        "--file",
        str(target),
    ]

    subprocess.run(command, check=True, capture_output=True, text=True)
    deleted = _cleanup_old_backups(kind, retention_days)
    size_bytes = target.stat().st_size

    logger.info(
        "periodic_database_backup_created kind=%s path=%s size_bytes=%s deleted_old=%s",
        kind,
        target,
        size_bytes,
        deleted,
    )
    return {
        "kind": kind,
        "path": str(target),
        "size_bytes": size_bytes,
        "deleted_old": deleted,
    }


@shared_task(name="apps.core.tasks.create_daily_database_backup_task")
def create_daily_database_backup_task() -> dict[str, object]:
    return _create_database_backup("daily", getattr(settings, "BACKUP_DAILY_RETENTION_DAYS", 14))


@shared_task(name="apps.core.tasks.create_weekly_database_backup_task")
def create_weekly_database_backup_task() -> dict[str, object]:
    return _create_database_backup("weekly", getattr(settings, "BACKUP_WEEKLY_RETENTION_DAYS", 56))
