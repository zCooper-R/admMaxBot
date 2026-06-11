from datetime import timedelta

import pytest
from django.utils import timezone

from apps.analytics.services import DailyStatsSyncService
from apps.analytics.tasks import sync_daily_stats_task
from apps.bot.models import WebhookEvent, WebhookEventStatus, WebhookOperationLog, WebhookOperationType
from apps.bot.tasks import cleanup_technical_logs_task
from apps.core.integration_health import IntegrationHealthService
from apps.core.tasks import refresh_integration_status_task


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
    WebhookOperationLog.objects.filter(pk=old_operation.pk).update(created_at=now - timedelta(days=91))
    WebhookOperationLog.objects.filter(pk=fresh_operation.pk).update(created_at=now - timedelta(days=10))

    result = cleanup_technical_logs_task.run()

    assert result == {"deleted_events": 1, "deleted_operations": 1}
    assert WebhookEvent.objects.filter(external_event_id="old-event").exists() is False
    assert WebhookEvent.objects.filter(external_event_id="fresh-event").exists() is True
    assert WebhookOperationLog.objects.filter(pk=old_operation.pk).exists() is False
    assert WebhookOperationLog.objects.filter(pk=fresh_operation.pk).exists() is True
