import pytest

from apps.bot.models import MenuNode, MenuNodeType


@pytest.mark.django_db
def test_menu_node_cycle_validation(root_node):
    child = MenuNode.objects.create(
        parent=root_node,
        title="Дочерний",
        slug="child",
        node_type=MenuNodeType.MENU,
    )
    root_node.parent = child
    with pytest.raises(Exception):
        root_node.full_clean()


@pytest.mark.django_db
def test_bot_settings_singleton(bot_settings):
    second = type(bot_settings).get_solo()
    assert bot_settings.id == second.id
