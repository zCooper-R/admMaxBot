import os
from datetime import timedelta
from pathlib import Path

import pytest
from django.core.management import call_command
from django.utils import timezone

from apps.analytics.services import DailyStatsSyncService
from apps.analytics.tasks import sync_daily_stats_task
from apps.bot.models import (
    WebhookEvent,
    WebhookEventStatus,
    WebhookOperationLog,
    WebhookOperationType,
)
from apps.bot.tasks import cleanup_technical_logs_task
from apps.core.integration_health import IntegrationHealthService
from apps.core.tasks import create_daily_database_backup_task, refresh_integration_status_task


def test_refresh_integration_status_task_uses_health_service(monkeypatch):
    expected = {"bot_enabled": "Включен", "webhook_badge": "Активен"}

    def fake_refresh_status(self):
        return expected

    monkeypatch.setattr(IntegrationHealthService, "refresh_status", fake_refresh_status)

    assert refresh_integration_status_task.run() == expected


def test_sync_daily_stats_task_uses_configured_window(settings, monkeypatch):
    settings.DAILY_STATS_SYNC_WINDOW_DAYS = 45
    called: list[int] = []

    def fake_ensure_recent(self, window_days):
        called.append(window_days)

    monkeypatch.setattr(DailyStatsSyncService, "ensure_recent", fake_ensure_recent)

    assert sync_daily_stats_task.run() == {"window_days": 45}
    assert sync_daily_stats_task.run(window_days=7) == {"window_days": 7}
    assert called == [45, 7]


@pytest.mark.django_db
def test_cleanup_technical_logs_task_deletes_only_expired_records(settings):
    settings.WEBHOOK_EVENT_RETENTION_DAYS = 90
    settings.WEBHOOK_OPERATION_LOG_RETENTION_DAYS = 90
    now = timezone.now()

    old_event = WebhookEvent.objects.create(
        external_event_id="old-event",
        event_type="message_created",
        payload={"ok": True},
        status=WebhookEventStatus.PROCESSED,
    )
    fresh_event = WebhookEvent.objects.create(
        external_event_id="fresh-event",
        event_type="message_created",
        payload={"ok": True},
        status=WebhookEventStatus.PROCESSED,
    )
    WebhookEvent.objects.filter(pk=old_event.pk).update(received_at=now - timedelta(days=91))
    WebhookEvent.objects.filter(pk=fresh_event.pk).update(received_at=now - timedelta(days=10))

    old_operation = WebhookOperationLog.objects.create(
        operation_type=WebhookOperationType.CHECK,
        request_payload={},
        response_payload={},
        status="ok",
    )
    fresh_operation = WebhookOperationLog.objects.create(
        operation_type=WebhookOperationType.CHECK,
        request_payload={},
        response_payload={},
        status="ok",
    )
    WebhookOperationLog.objects.filter(pk=old_operation.pk).update(
        created_at=now - timedelta(days=91)
    )
    WebhookOperationLog.objects.filter(pk=fresh_operation.pk).update(
        created_at=now - timedelta(days=10)
    )

    result = cleanup_technical_logs_task.run()

    assert result == {"deleted_events": 1, "deleted_operations": 1}
    assert WebhookEvent.objects.filter(external_event_id="old-event").exists() is False
    assert WebhookEvent.objects.filter(external_event_id="fresh-event").exists() is True
    assert WebhookOperationLog.objects.filter(pk=old_operation.pk).exists() is False
    assert WebhookOperationLog.objects.filter(pk=fresh_operation.pk).exists() is True


def test_create_daily_database_backup_task_creates_dump_and_removes_old_files(
    settings, monkeypatch, tmp_path
):
    settings.BACKUP_DIR = tmp_path
    settings.BACKUP_DAILY_RETENTION_DAYS = 14
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:password@db:5432/maxbot")

    old_backup = tmp_path / "daily-20240101-030000.dump"
    old_backup.write_text("old", encoding="utf-8")
    old_timestamp = (timezone.now() - timedelta(days=15)).timestamp()
    os.utime(old_backup, (old_timestamp, old_timestamp))

    fresh_backup = tmp_path / "daily-20260101-030000.dump"
    fresh_backup.write_text("fresh", encoding="utf-8")

    def fake_run(command, check, capture_output, text):
        assert command[:4] == ["pg_dump", "--format=custom", "--no-owner", "--no-privileges"]
        assert "--dbname" in command
        assert "--file" in command
        Path(command[command.index("--file") + 1]).write_bytes(b"dump")

    monkeypatch.setattr("apps.core.tasks.subprocess.run", fake_run)

    result = create_daily_database_backup_task.run()

    assert result["kind"] == "daily"
    assert result["size_bytes"] == 4
    assert result["deleted_old"] == 1
    assert old_backup.exists() is False
    assert fresh_backup.exists() is True


@pytest.mark.django_db
def test_sync_periodic_tasks_command_creates_admin_visible_tasks(settings):
    settings.CELERY_REFRESH_INTEGRATION_STATUS_INTERVAL_SECONDS = 120
    settings.CELERY_SYNC_DAILY_STATS_INTERVAL_SECONDS = 900
    settings.CELERY_CLEANUP_TECHNICAL_LOGS_INTERVAL_SECONDS = 86400

    call_command("sync_periodic_tasks")

    from django_celery_beat.models import PeriodicTask

    assert set(PeriodicTask.objects.filter(enabled=True).values_list("name", flat=True)) >= {
        "Обновление статуса интеграции",
        "Обновление дневной аналитики",
        "Очистка технических логов",
        "Ежедневный backup базы данных",
        "Еженедельный backup базы данных",
    }
