from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from apps.accounts.models import UserRole
from apps.bot.models import BotSettings


class Command(BaseCommand):
    help = "Создает демо-настройки и пользователей ролей"

    def add_arguments(self, parser):
        parser.add_argument(
            "--confirm",
            action="store_true",
            help="Подтверждает запуск seed_demo вне development-режима",
        )

    def handle(self, *args, **options):
        if getattr(settings, "MAXBOT_ENV", "development").strip().lower() != "development" and not options["confirm"]:
            raise CommandError("Запуск seed_demo вне development требует флага --confirm")

        User = get_user_model()
        if not User.objects.filter(username="admin").exists():
            User.objects.create_superuser("admin", "admin@example.com", "admin")
        for username, role in [("editor", UserRole.EDITOR), ("viewer", UserRole.VIEWER)]:
            if not User.objects.filter(username=username).exists():
                User.objects.create_user(username=username, password="demo12345", role=role)

        settings_obj = BotSettings.get_solo()
        if not settings_obj.base_url:
            settings_obj.base_url = "https://platform-api.max.ru"
            settings_obj.save(update_fields=["base_url", "updated_at"])

        self.stdout.write(self.style.SUCCESS("Демо-данные готовы"))
