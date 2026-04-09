import json

import pytest
from django.urls import reverse

from apps.bot.models import MenuNode


@pytest.mark.django_db
def test_menu_reorder_endpoint(client, admin_user, root_node):
    a = MenuNode.objects.create(parent=root_node, title="A", slug="a-reorder", sort_order=10)
    b = MenuNode.objects.create(parent=root_node, title="B", slug="b-reorder", sort_order=20)
    client.force_login(admin_user)
    response = client.post(
        reverse("menu_builder:reorder"),
        data=json.dumps({"ordered_ids": [b.id, a.id], "parent_id": root_node.id}),
        content_type="application/json",
    )
    assert response.status_code == 200
    a.refresh_from_db()
    b.refresh_from_db()
    assert b.sort_order < a.sort_order


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("case_name", "payload_builder"),
    [
        ("partial", lambda root_node, a, b, child: {"ordered_ids": [b.id], "parent_id": root_node.id}),
        ("foreign_parent", lambda root_node, a, b, child: {"ordered_ids": [a.id, b.id], "parent_id": a.id}),
        ("mixed", lambda root_node, a, b, child: {"ordered_ids": [a.id, child.id], "parent_id": root_node.id}),
    ],
)
def test_menu_reorder_rejects_invalid_payloads(
    client,
    admin_user,
    root_node,
    case_name,
    payload_builder,
):
    a = MenuNode.objects.create(parent=root_node, title="A", slug=f"a-{case_name}", sort_order=10)
    b = MenuNode.objects.create(parent=root_node, title="B", slug=f"b-{case_name}", sort_order=20)
    child = MenuNode.objects.create(parent=a, title="A1", slug=f"a1-{case_name}", sort_order=10)
    client.force_login(admin_user)

    before = {node.id: node.sort_order for node in MenuNode.objects.filter(id__in=[a.id, b.id, child.id])}
    response = client.post(
        reverse("menu_builder:reorder"),
        data=json.dumps(payload_builder(root_node, a, b, child)),
        content_type="application/json",
    )

    assert response.status_code == 400
    for node in MenuNode.objects.filter(id__in=[a.id, b.id, child.id]):
        node.refresh_from_db()
        assert node.sort_order == before[node.id]
