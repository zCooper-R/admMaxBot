from django.core.management.base import BaseCommand

from apps.bot.models import MenuNode, MenuNodeType


class Command(BaseCommand):
    help = "Создает стартовое дерево меню"

    def handle(self, *args, **options):
        root, _ = MenuNode.objects.get_or_create(
            slug="main-menu",
            defaults={
                "title": "Главное меню",
                "node_type": MenuNodeType.MENU,
                "response_text": "Выберите интересующий раздел:",
                "sort_order": 10,
            },
        )

        MenuNode.objects.get_or_create(
            slug="about",
            defaults={
                "parent": root,
                "title": "О сервисе",
                "node_type": MenuNodeType.MESSAGE,
                "response_text": "Информационный раздел бота.",
                "sort_order": 10,
            },
        )

        MenuNode.objects.get_or_create(
            slug="contacts",
            defaults={
                "parent": root,
                "title": "Контакты",
                "node_type": MenuNodeType.MESSAGE,
                "response_text": "Контакты доступны в рабочее время.",
                "sort_order": 20,
            },
        )

        self.stdout.write(self.style.SUCCESS("Стартовое дерево меню создано/обновлено"))
