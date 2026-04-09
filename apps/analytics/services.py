from __future__ import annotations

from datetime import timedelta

from django.db.models import Count
from django.db.models.functions import TruncDate
from django.utils import timezone

from apps.bot.models import BotUser, WebhookEvent, WebhookEventStatus

from .models import DailyStats


class DailyStatsSyncService:
    """Keeps DailyStats up-to-date without external schedulers."""

    def ensure_recent(self, window_days: int = 90) -> None:
        today = timezone.localdate()
        latest_saved_date = DailyStats.objects.order_by("-date").values_list("date", flat=True).first()

        if latest_saved_date:
            start_date = latest_saved_date
        else:
            first_user_dt = BotUser.objects.order_by("first_seen_at").values_list("first_seen_at", flat=True).first()
            first_event_dt = (
                WebhookEvent.objects.order_by("received_at").values_list("received_at", flat=True).first()
            )
            earliest_user_day = first_user_dt.date() if first_user_dt else None
            earliest_event_day = first_event_dt.date() if first_event_dt else None
            candidates = [d for d in [earliest_user_day, earliest_event_day] if d is not None]
            if not candidates:
                return
            start_date = max(min(candidates), today - timedelta(days=max(window_days - 1, 0)))

        if latest_saved_date is None:
            users_before_start = 0
        else:
            users_before_start = BotUser.objects.filter(first_seen_at__date__lt=start_date).count()

        new_users_by_day = dict(
            BotUser.objects.filter(first_seen_at__date__gte=start_date, first_seen_at__date__lte=today)
            .annotate(day=TruncDate("first_seen_at"))
            .values("day")
            .annotate(total=Count("id"))
            .values_list("day", "total")
        )
        events_by_day = dict(
            WebhookEvent.objects.filter(received_at__date__gte=start_date, received_at__date__lte=today)
            .annotate(day=TruncDate("received_at"))
            .values("day")
            .annotate(total=Count("id"))
            .values_list("day", "total")
        )
        active_users_by_day = dict(
            WebhookEvent.objects.filter(
                received_at__date__gte=start_date, received_at__date__lte=today, user__isnull=False
            )
            .annotate(day=TruncDate("received_at"))
            .values("day")
            .annotate(total=Count("user_id", distinct=True))
            .values_list("day", "total")
        )
        clicks_by_day = dict(
            WebhookEvent.objects.filter(
                received_at__date__gte=start_date,
                received_at__date__lte=today,
                event_type="message_callback",
            )
            .annotate(day=TruncDate("received_at"))
            .values("day")
            .annotate(total=Count("id"))
            .values_list("day", "total")
        )
        errors_by_day = dict(
            WebhookEvent.objects.filter(
                received_at__date__gte=start_date,
                received_at__date__lte=today,
                status=WebhookEventStatus.FAILED,
            )
            .annotate(day=TruncDate("received_at"))
            .values("day")
            .annotate(total=Count("id"))
            .values_list("day", "total")
        )

        running_users_total = users_before_start
        day_cursor = start_date
        while day_cursor <= today:
            running_users_total += int(new_users_by_day.get(day_cursor, 0))
            DailyStats.objects.update_or_create(
                date=day_cursor,
                defaults={
                    "users_total": running_users_total,
                    "active_users": int(active_users_by_day.get(day_cursor, 0)),
                    "events_total": int(events_by_day.get(day_cursor, 0)),
                    "button_clicks_total": int(clicks_by_day.get(day_cursor, 0)),
                    "errors_total": int(errors_by_day.get(day_cursor, 0)),
                },
            )
            day_cursor += timedelta(days=1)
