from __future__ import annotations

from datetime import timedelta

from django.db.models import Count
from django.db.models.functions import TruncDate
from django.utils import timezone

from apps.bot.models import BotUser, WebhookEvent, WebhookEventStatus
from apps.core.integration_health import IntegrationHealthService


class DashboardService:
    def summary(self) -> dict[str, object]:
        now = timezone.now()
        since = now - timedelta(days=7)
        users_total = BotUser.objects.count()
        users_new = BotUser.objects.filter(created_at__gte=since).count()
        events_total = WebhookEvent.objects.count()
        errors_total = WebhookEvent.objects.filter(status=WebhookEventStatus.FAILED).count()
        last_event = WebhookEvent.objects.order_by("-received_at").first()

        points = (
            WebhookEvent.objects.filter(received_at__gte=now - timedelta(days=14))
            .annotate(day=TruncDate("received_at"))
            .values("day")
            .annotate(total=Count("id"))
            .order_by("day")
        )
        activity_labels = [str(item["day"]) for item in points]
        activity_values = [item["total"] for item in points]

        top_nodes = (
            WebhookEvent.objects.filter(related_node__isnull=False)
            .values("related_node__title")
            .annotate(total=Count("id"))
            .order_by("-total")[:5]
        )

        integration_status = IntegrationHealthService().get_status()
        return {
            "users_total": users_total,
            "users_new": users_new,
            "events_total": events_total,
            "errors_total": errors_total,
            "last_event": last_event,
            "webhook_status": integration_status.get("webhook_badge", "Неизвестно"),
            "activity_labels": activity_labels,
            "activity_values": activity_values,
            "top_nodes": top_nodes,
            "latest_errors": WebhookEvent.objects.filter(status=WebhookEventStatus.FAILED)[:5],
            "latest_events": WebhookEvent.objects.select_related("user")[:10],
        }

