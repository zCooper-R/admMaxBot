import pytest

from apps.audit.models import AuditLog
from apps.audit.services import audit_action
from apps.bot.models import MenuNode


@pytest.mark.django_db
def test_audit_action_serializes_model_objects(admin_user):
    node = MenuNode.objects.create(title="Root", slug="root-audit")
    payload = {"parent": node}
    audit_action(admin_user, "update", "MenuNode", str(node.id), payload, payload)
    log = AuditLog.objects.latest("id")
    assert isinstance(log.after_data, dict)
    assert log.after_data["parent"]["id"] == node.id
