from __future__ import annotations

from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Синхронизирует стандартные Celery periodic tasks в django-celery-beat."

    def handle(self, *args, **options):
        from django_celery_beat.models import CrontabSchedule, IntervalSchedule, PeriodicTask

        interval_tasks = [
            {
                "name": "Обновление статуса интеграции",
                "task": "apps.core.tasks.refresh_integration_status_task",
                "every": int(settings.CELERY_REFRESH_INTEGRATION_STATUS_INTERVAL_SECONDS),
            },
            {
                "name": "Обновление дневной аналитики",
                "task": "apps.analytics.tasks.sync_daily_stats_task",
                "every": int(settings.CELERY_SYNC_DAILY_STATS_INTERVAL_SECONDS),
            },
            {
                "name": "Очистка технических логов",
                "task": "apps.bot.tasks.cleanup_technical_logs_task",
                "every": int(settings.CELERY_CLEANUP_TECHNICAL_LOGS_INTERVAL_SECONDS),
            },
        ]

        for task_config in interval_tasks:
            schedule, _ = IntervalSchedule.objects.get_or_create(
                every=task_config["every"],
                period=IntervalSchedule.SECONDS,
            )
            PeriodicTask.objects.update_or_create(
                name=task_config["name"],
                defaults={
                    "task": task_config["task"],
                    "interval": schedule,
                    "crontab": None,
                    "enabled": True,
                },
            )

        cron_tasks = [
            {
                "name": "Ежедневный backup базы данных",
                "task": "apps.core.tasks.create_daily_database_backup_task",
                "minute": "0",
                "hour": "3",
                "day_of_week": "*",
            },
            {
                "name": "Еженедельный backup базы данных",
                "task": "apps.core.tasks.create_weekly_database_backup_task",
                "minute": "0",
                "hour": "4",
                "day_of_week": "0",
            },
        ]

        for task_config in cron_tasks:
            schedule, _ = CrontabSchedule.objects.get_or_create(
                minute=task_config["minute"],
                hour=task_config["hour"],
                day_of_week=task_config["day_of_week"],
                day_of_month="*",
                month_of_year="*",
                timezone=settings.TIME_ZONE,
            )
            PeriodicTask.objects.update_or_create(
                name=task_config["name"],
                defaults={
                    "task": task_config["task"],
                    "interval": None,
                    "crontab": schedule,
                    "enabled": True,
                },
            )

        self.stdout.write(self.style.SUCCESS("Periodic tasks синхронизированы."))
