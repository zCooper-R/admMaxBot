import pytest
from django.urls import reverse

from apps.bot.models import MenuNode


@pytest.mark.django_db
def test_menu_crud(client, admin_user):
    client.force_login(admin_user)
    create_response = client.post(
        reverse("menu_builder:create-root"),
        data={
            "parent": "",
            "title": "Новый раздел",
            "slug": "new-section",
            "response_text": "Контент",
            "node_type": "menu",
            "sort_order": 10,
            "is_active": "on",
            "payload": "",
            "icon": "",
            "admin_comment": "",
        },
    )
    assert create_response.status_code == 302
    node = MenuNode.objects.get(slug="new-section")

    edit_response = client.post(
        reverse("menu_builder:edit", kwargs={"pk": node.id}),
        data={
            "parent": "",
            "title": "Обновленный раздел",
            "slug": "new-section",
            "response_text": "Контент",
            "node_type": "menu",
            "sort_order": 10,
            "is_active": "on",
            "payload": "",
            "icon": "",
            "admin_comment": "",
        },
    )
    assert edit_response.status_code == 302
    node.refresh_from_db()
    assert node.title == "Обновленный раздел"

    delete_response = client.post(reverse("menu_builder:delete", kwargs={"pk": node.id}))
    assert delete_response.status_code == 302
    assert not MenuNode.objects.filter(id=node.id).exists()


@pytest.mark.django_db
def test_delete_node_with_children_redirects_back_to_parent_level(client, admin_user, root_node):
    parent = MenuNode.objects.create(parent=root_node, title="Раздел", slug="section", sort_order=20)
    MenuNode.objects.create(parent=parent, title="Дочерний", slug="child-section", sort_order=10)
    client.force_login(admin_user)

    response = client.post(reverse("menu_builder:delete", kwargs={"pk": parent.id}))

    assert response.status_code == 302
    assert response.url == reverse("menu_builder:tree-child", kwargs={"parent_id": root_node.id})


@pytest.mark.django_db
def test_preview_uses_wrapping_chip_class_for_long_button_titles(client, viewer_user, root_node):
    child = MenuNode.objects.create(
        parent=root_node,
        title="Очень длинное название кнопки для проверки переноса в предпросмотре меню",
        slug="very-long-button",
        sort_order=20,
    )
    client.force_login(viewer_user)

    response = client.get(reverse("menu_builder:preview", kwargs={"pk": root_node.id}))

    assert response.status_code == 200
    content = response.content.decode("utf-8")
    assert "preview-button-chip" in content
    assert child.title in content


@pytest.mark.django_db
def test_menu_tree_supports_filters_and_quality_panel(client, viewer_user, root_node):
    MenuNode.objects.create(
        parent=root_node,
        title="Очень длинное название кнопки для списка и проверки качества меню",
        slug="long-quality-node",
        sort_order=10,
        is_active=True,
        is_visible=False,
    )
    MenuNode.objects.create(
        parent=root_node,
        title="Короткий узел",
        slug="short-node",
        sort_order=20,
        is_active=True,
        is_visible=True,
    )
    client.force_login(viewer_user)

    response = client.get(reverse("menu_builder:tree-child", kwargs={"parent_id": root_node.id}), {"q": "quality"})

    assert response.status_code == 200
    content = response.content.decode("utf-8")
    assert "Качество меню" in content
    assert "long-quality-node" in content
    assert "short-node" not in content


@pytest.mark.django_db
def test_menu_duplicate_creates_copy_with_unique_slug(client, admin_user, root_node):
    original = MenuNode.objects.create(
        parent=root_node,
        title="Раздел",
        slug="section-dup",
        sort_order=10,
        response_text="Текст",
        is_active=True,
        is_visible=True,
    )
    client.force_login(admin_user)

    response = client.post(reverse("menu_builder:duplicate", kwargs={"pk": original.id}))

    assert response.status_code == 302
    copies = MenuNode.objects.filter(parent=root_node, slug__startswith="section-dup-copy").order_by("id")
    assert copies.count() == 1
    duplicate = copies.first()
    assert duplicate is not None
    assert duplicate.title == "Раздел (копия)"
    assert duplicate.response_text == original.response_text


@pytest.mark.django_db
def test_branch_quality_view_shows_detected_issues(client, viewer_user, root_node):
    branch = MenuNode.objects.create(
        parent=root_node,
        title="Очень длинное название кнопки для отдельной проверки ветки меню",
        slug="branch-quality-node",
        node_type="link",
        sort_order=10,
        response_text="",
        payload=None,
    )
    client.force_login(viewer_user)

    response = client.get(reverse("menu_builder:branch-quality", kwargs={"pk": branch.id}))

    assert response.status_code == 200
    content = response.content.decode("utf-8")
    assert branch.title in content
    assert "payload.url" in content


@pytest.mark.django_db
def test_menu_form_shows_only_three_node_types(client, admin_user, root_node):
    client.force_login(admin_user)

    response = client.get(reverse("menu_builder:create-child", kwargs={"parent_id": root_node.id}))

    assert response.status_code == 200
    content = response.content.decode("utf-8")
    assert 'value="menu"' in content
    assert 'value="message"' in content
    assert 'value="link"' in content
    assert 'value="action"' not in content
    assert 'value="transition"' not in content
    assert 'value="back"' not in content
    assert 'value="root"' not in content
