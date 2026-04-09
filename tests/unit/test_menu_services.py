import pytest

from apps.bot.models import MenuNode, MenuNodeType
from apps.menu_builder.services import MenuRuntimeService, MenuTreeService


@pytest.mark.django_db
def test_menu_tree_move(root_node):
    first = MenuNode.objects.create(parent=root_node, title="A", slug="a", sort_order=10)
    second = MenuNode.objects.create(parent=root_node, title="B", slug="b", sort_order=20)
    MenuTreeService.move_down(first)
    first.refresh_from_db()
    second.refresh_from_db()
    assert first.sort_order == 20
    assert second.sort_order == 10


@pytest.mark.django_db
def test_menu_runtime_build_keyboard(root_node):
    MenuNode.objects.create(parent=root_node, title="Раздел", slug="sec", node_type=MenuNodeType.MENU)
    result = MenuRuntimeService().render_node(root_node)
    assert result.buttons
    assert result.text
