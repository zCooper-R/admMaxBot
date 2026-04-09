import pytest
from django.urls import reverse


@pytest.mark.django_db
def test_viewer_can_open_dashboard(client, viewer_user):
    client.force_login(viewer_user)
    response = client.get(reverse("dashboard:home"))
    assert response.status_code == 200


@pytest.mark.django_db
def test_viewer_cannot_edit_menu(client, viewer_user, root_node):
    client.force_login(viewer_user)
    response = client.get(reverse("menu_builder:edit", kwargs={"pk": root_node.id}))
    assert response.status_code in (302, 403)


@pytest.mark.django_db
def test_admin_can_edit_menu(client, admin_user, root_node):
    client.force_login(admin_user)
    response = client.get(reverse("menu_builder:edit", kwargs={"pk": root_node.id}))
    assert response.status_code == 200
