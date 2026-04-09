import pytest
from django.contrib.auth import get_user_model

from apps.accounts.models import UserRole
from apps.bot.models import BotSettings, MenuNode, MenuNodeType


@pytest.fixture
def admin_user(db):
    User = get_user_model()
    return User.objects.create_user(username="admin_test", password="pass12345", role=UserRole.ADMIN)


@pytest.fixture
def viewer_user(db):
    User = get_user_model()
    return User.objects.create_user(username="viewer_test", password="pass12345", role=UserRole.VIEWER)


@pytest.fixture
def bot_settings(db):
    return BotSettings.get_solo()


@pytest.fixture
def root_node(db):
    return MenuNode.objects.create(
        title="Главное меню",
        slug="main",
        node_type=MenuNodeType.MENU,
        response_text="Выберите раздел",
        sort_order=10,
    )
