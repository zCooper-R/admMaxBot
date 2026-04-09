from django.core.management.base import BaseCommand

from apps.core.integration_health import IntegrationHealthService


class Command(BaseCommand):
    help = "Обновляет кеш статуса интеграции с MAX API"

    def handle(self, *args, **options):
        status = IntegrationHealthService().refresh_status()
        self.stdout.write(
            self.style.SUCCESS(
                f"Статус интеграции обновлен: bot={status['bot_enabled']}, webhook={status['webhook_badge']}"
            )
        )
