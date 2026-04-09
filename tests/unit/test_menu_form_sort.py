import pytest

from apps.menu_builder.forms import MenuNodeForm
from apps.bot.models import MenuNode


@pytest.mark.django_db
def test_new_node_gets_auto_sort_order(root_node):
    MenuNode.objects.create(parent=root_node, title="A", slug="auto-a", sort_order=10)
    form = MenuNodeForm(
        data={
            "parent": root_node.id,
            "title": "B",
            "slug": "",
            "response_text": "",
            "node_type": "menu",
            "sort_order": 0,
            "is_active": "on",
            "payload": "",
            "icon": "",
            "admin_comment": "",
        }
    )
    assert form.is_valid(), form.errors
    node = form.save()
    assert node.sort_order == 20
    assert node.is_visible is True


@pytest.mark.django_db
def test_manual_slug_is_normalized_with_spaces_and_cyrillic(root_node):
    form = MenuNodeForm(
        data={
            "parent": root_node.id,
            "title": "Тестовый узел",
            "slug": "Мой slug test",
            "response_text": "",
            "node_type": "menu",
            "sort_order": 0,
            "is_active": "on",
            "payload": "",
            "icon": "",
            "admin_comment": "",
        }
    )

    assert form.is_valid(), form.errors
    node = form.save()
    assert node.slug == "moy-slug-test"


@pytest.mark.django_db
def test_link_node_requires_payload_url(root_node):
    form = MenuNodeForm(
        data={
            "parent": root_node.id,
            "title": "Ссылка",
            "slug": "",
            "response_text": "Откройте ссылку",
            "node_type": "link",
            "sort_order": 0,
            "is_active": "on",
            "payload": '{"code": "123"}',
            "icon": "",
            "admin_comment": "",
        }
    )

    assert not form.is_valid()
    assert "payload" in form.errors


@pytest.mark.django_db
def test_link_node_accepts_valid_payload_url(root_node):
    form = MenuNodeForm(
        data={
            "parent": root_node.id,
            "title": "Ссылка",
            "slug": "",
            "response_text": "Откройте ссылку",
            "node_type": "link",
            "sort_order": 0,
            "is_active": "on",
            "payload": '{"url": "https://example.com/docs"}',
            "icon": "",
            "admin_comment": "",
        }
    )

    assert form.is_valid(), form.errors
    node = form.save()
    assert node.payload == {"url": "https://example.com/docs"}


@pytest.mark.django_db
def test_message_node_requires_response_text(root_node):
    form = MenuNodeForm(
        data={
            "parent": root_node.id,
            "title": "Сообщение",
            "slug": "",
            "response_text": "",
            "node_type": "message",
            "sort_order": 0,
            "is_active": "on",
            "payload": "",
            "icon": "",
            "admin_comment": "",
        }
    )

    assert not form.is_valid()
    assert "response_text" in form.errors
