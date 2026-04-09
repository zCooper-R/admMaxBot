from django.core.management.base import BaseCommand

from apps.analytics.services import DailyStatsSyncService


class Command(BaseCommand):
    help = "Синхронизирует DailyStats за указанный диапазон дней"

    def add_arguments(self, parser):
        parser.add_argument(
            "--window-days",
            type=int,
            default=120,
            help="Сколько последних дней синхронизировать",
        )

    def handle(self, *args, **options):
        window_days = max(int(options["window_days"]), 1)
        DailyStatsSyncService().ensure_recent(window_days=window_days)
        self.stdout.write(self.style.SUCCESS(f"DailyStats синхронизированы за последние {window_days} дней"))
